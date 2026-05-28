"""
Lightweight Kimi API client using curl subprocess.
Supports both text and vision (image_url) messages.
No pip-installable dependencies required.

Uses Kimi For Coding endpoint (api.kimi.com/coding) with the credentials
from ~/.kimi_openclaw/openclaw.json.

IMPORTANT: k2p5 is a reasoning model. It outputs everything in reasoning_content
and leaves content empty. We extract JSON from reasoning_content markdown blocks.
"""
import json
import os
import re
import subprocess
import tempfile

# Fallback to env var; default comes from ~/.kimi_openclaw/credentials/
KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "")
KIMI_BASE_URL = "https://api.kimi.com/coding"
KIMI_MODEL = "k2p5"          # k2p5 maps to kimi-for-coding on this endpoint
KIMI_CLAW_ID = "19e12536-4ec2-8c2f-8000-000011f79d72"


def _extract_json(text: str):
    """Extract the largest valid JSON object or array from text."""
    best = None
    best_size = 0

    # Try markdown code blocks first
    for pattern in [r"```json\s*(.*?)\s*```", r"```\s*(.*?)\s*```"]:
        matches = re.findall(pattern, text, re.DOTALL)
        for m in matches:
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

    # Fallback: find balanced braces
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


def call_kimi(
    messages,
    temperature: float = 0.3,
    max_tokens: int = 4096,
) -> dict:
    """
    Call Kimi For Coding chat completions API via curl.
    `messages` follows the OpenAI-compatible format and may contain
    multimodal content (text + image_url).
    """
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

    # Write payload to temp file to avoid command-line length limits
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
        payload_path = f.name

    cmd = ["curl", "-s", "-w", r"\nHTTP_CODE:%{http_code}\n", "--max-time", "180"]
    for h in headers:
        cmd.extend(["-H", h])
    cmd.extend(["-d", f"@{payload_path}", url])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=200)
    finally:
        os.unlink(payload_path)

    stdout = result.stdout
    # Extract HTTP code from last line
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
        raise RuntimeError(f"Kimi API error {http_code}: {body[:1000]}")

    data = json.loads(body)
    msg = data["choices"][0]["message"]

    # k2p5 reasoning model: content is usually empty, analysis is in reasoning_content
    sources = [
        msg.get("content", ""),
        msg.get("reasoning_content", ""),
    ]

    for src in sources:
        if not src:
            continue
        parsed = _extract_json(src)
        if parsed is not None:
            return parsed

    raise RuntimeError("Could not extract valid JSON from API response.")
