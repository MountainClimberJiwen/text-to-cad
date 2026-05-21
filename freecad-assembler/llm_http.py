"""
Universal LLM client using curl subprocess.
Supports multiple providers: Doubao (Volces/ark), Kimi For Coding, etc.
No pip-installable dependencies required.

Reads Doubao config from freecad-assembler/.env by default.
Falls back to Kimi For Coding credentials from ~/.kimi_openclaw/.
"""
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent


def _read_dotenv() -> dict:
    env = {}
    dotenv = REPO_ROOT / ".env"
    if dotenv.exists():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


# ---- Doubao (primary for vision) ----
_ENV = _read_dotenv()
DOUBAO_API_KEY = _ENV.get("LLM_API_KEY", "")
DOUBAO_BASE_URL = _ENV.get("LLM_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3")
DOUBAO_MODEL = _ENV.get("LLM_MODEL", "doubao-seed-2-0-pro-260215")

# ---- Kimi For Coding (fallback) ----
KIMI_API_KEY = os.environ.get(
    "KIMI_API_KEY",
    "REMOVED_KIMI_API_KEY",
)
KIMI_BASE_URL = "https://api.kimi.com/coding"
KIMI_MODEL = "k2p5"
KIMI_CLAW_ID = "19e12536-4ec2-8c2f-8000-000011f79d72"


def _extract_json(text: str):
    """Extract the largest valid JSON object or array from text."""
    best = None
    best_size = 0

    # Markdown code blocks
    for pattern in [r"```json\s*(.*?)\s*```", r"```\s*(.*?)\s*```"]:
        for m in re.findall(pattern, text, re.DOTALL):
            m = m.strip()
            if m.startswith("json"):
                m = m[3:].strip()
            try:
                candidate = json.loads(m)
                size = len(json.dumps(candidate))
                if size > best_size:
                    best = candidate
                    best_size = size
            except json.JSONDecodeError:
                continue

    # Balanced braces
    for start in [m.start() for m in re.finditer(r"[\{\[]", text)]:
        brace = text[start]
        close = "}" if brace == "{" else "]"
        count = 0
        end = -1
        for i in range(start, len(text)):
            if text[i] == brace:
                count += 1
            elif text[i] == close:
                count -= 1
                if count == 0:
                    end = i + 1
                    break
        if end > start:
            try:
                candidate = json.loads(text[start:end])
                size = len(json.dumps(candidate))
                if size > best_size:
                    best = candidate
                    best_size = size
            except json.JSONDecodeError:
                pass

    return best


def call_llm(
    messages,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    provider: str = "doubao",
) -> dict:
    """
    Call LLM chat completions API via curl.
    provider: "doubao" (default) or "kimi"
    """
    if provider == "doubao":
        url = f"{DOUBAO_BASE_URL}/chat/completions"
        headers = [
            "Content-Type: application/json",
            f"Authorization: Bearer {DOUBAO_API_KEY}",
        ]
        payload = {
            "model": DOUBAO_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
    else:  # kimi
        url = f"{KIMI_BASE_URL}/v1/chat/completions"
        headers = [
            "Content-Type: application/json",
            f"Authorization: Bearer {KIMI_API_KEY}",
            "User-Agent: Desktop Kimi Claw Plugin",
            f"X-Kimi-Claw-ID: {KIMI_CLAW_ID}",
        ]
        payload = {
            "model": KIMI_MODEL,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

    # Write payload to temp file
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
        payload_path = f.name

    cmd = ["curl", "-s", "-w", r"\nHTTP_CODE:%{http_code}\n", "--max-time", "120"]
    for h in headers:
        cmd.extend(["-H", h])
    cmd.extend(["-d", f"@{payload_path}", url])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=140)
    finally:
        os.unlink(payload_path)

    stdout = result.stdout
    lines = stdout.strip().splitlines()
    if not lines:
        raise RuntimeError("Empty response from curl")

    http_code_line = lines[-1]
    if http_code_line.startswith("HTTP_CODE:"):
        http_code = int(http_code_line.split(":", 1)[1])
        body = "\n".join(lines[:-1])
    else:
        http_code = 0
        body = stdout

    if http_code != 200:
        raise RuntimeError(f"API error {http_code}: {body[:1000]}")

    data = json.loads(body)
    msg = data["choices"][0]["message"]

    # Try content first (Doubao puts answer here)
    for src in [msg.get("content", ""), msg.get("reasoning_content", "")]:
        if not src:
            continue
        parsed = _extract_json(src)
        if parsed is not None:
            return parsed

    raise RuntimeError("Could not extract valid JSON from API response.")
