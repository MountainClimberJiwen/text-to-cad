"""Lightweight VLM client for CAD visual review.

Supports multimodal messages (text + base64-encoded PNG images).
Uses curl subprocess to avoid extra pip dependencies.

Defaults to Kimi; falls back to Doubao on failure if credentials are available.
Provider and credentials can be overridden via env vars.
"""
from __future__ import annotations

import base64
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any

# ---- Load freecad-assembler .env for Doubao credentials ----
def _load_dotenv(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip()
    return env


_FA_DOTENV = _load_dotenv(Path(__file__).resolve().parent.parent.parent / "freecad-assembler" / ".env")

# ---- Doubao (fallback) ----
DOUBAO_API_KEY = os.environ.get("DOUBAO_API_KEY", os.environ.get("LLM_API_KEY", _FA_DOTENV.get("LLM_API_KEY", "")))
DOUBAO_BASE_URL = os.environ.get("DOUBAO_BASE_URL", _FA_DOTENV.get("LLM_BASE_URL", "https://ark.cn-beijing.volces.com/api/v3"))
DOUBAO_MODEL = os.environ.get("DOUBAO_MODEL", os.environ.get("LLM_MODEL", _FA_DOTENV.get("LLM_MODEL", "doubao-seed-2-0-pro-260215")))

# ---- Kimi (default) ----
KIMI_API_KEY = os.environ.get("KIMI_API_KEY", "")
KIMI_BASE_URL = os.environ.get("KIMI_BASE_URL", "https://api.kimi.com/coding")
KIMI_MODEL = os.environ.get("KIMI_MODEL", "k2p5")
KIMI_CLAW_ID = os.environ.get("KIMI_CLAW_ID", "19e12536-4ec2-8c2f-8000-000011f79d72")


def _extract_json(text: str) -> Any | None:
    """Extract the largest valid JSON object or array from text."""
    best = None
    best_size = 0

    # Markdown code blocks first
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

    # Fallback: balanced braces
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


def encode_image(image_path: Path) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _call_provider(
    messages: list[dict[str, Any]],
    *,
    temperature: float,
    max_tokens: int,
    provider: str,
    response_format: dict[str, str] | None = None,
    timeout: int = 180,
) -> dict[str, Any]:
    """Call a single provider and return parsed JSON."""
    if provider == "doubao":
        url = f"{DOUBAO_BASE_URL}/chat/completions"
        headers = [
            "Content-Type: application/json",
            f"Authorization: Bearer {DOUBAO_API_KEY}",
        ]
        payload: dict[str, Any] = {
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

    if response_format is not None:
        payload["response_format"] = response_format

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
        payload_path = f.name

    cmd = ["curl", "-s", "-S", "-w", r"\nHTTP_CODE:%{http_code}\n", "--max-time", str(timeout)]
    for h in headers:
        cmd.extend(["-H", h])
    cmd.extend(["-d", f"@{payload_path}", url])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout + 20)
    finally:
        os.unlink(payload_path)

    stdout = result.stdout
    lines = stdout.strip().splitlines()
    if not lines:
        raise RuntimeError("Empty response from VLM API")

    http_code_line = lines[-1]
    if http_code_line.startswith("HTTP_CODE:"):
        http_code = int(http_code_line.split(":", 1)[1])
        body = "\n".join(lines[:-1])
    else:
        http_code = 0
        body = stdout

    if http_code != 200:
        raise RuntimeError(f"VLM API error {http_code}: {body[:1000]}")

    data = json.loads(body)
    msg = data["choices"][0]["message"]

    # Try content first (Doubao puts answer here), then reasoning_content (Kimi k2p5)
    for src in [msg.get("content", ""), msg.get("reasoning_content", "")]:
        if not src:
            continue
        parsed = _extract_json(src)
        if parsed is not None:
            return parsed

    raise RuntimeError("Could not extract valid JSON from VLM API response.")


def call_vlm(
    messages: list[dict[str, Any]],
    *,
    temperature: float = 0.3,
    max_tokens: int = 4096,
    provider: str | None = None,
    response_format: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Call VLM chat completions API via curl.

    Defaults to Kimi. If Kimi fails and Doubao credentials are available,
    automatically retries with Doubao.
    """
    if provider is None:
        provider = "kimi"

    last_error: Exception | None = None
    providers_to_try = [provider]
    if provider == "kimi" and DOUBAO_API_KEY:
        providers_to_try.append("doubao")

    for prov in providers_to_try:
        try:
            return _call_provider(
                messages,
                temperature=temperature,
                max_tokens=max_tokens,
                provider=prov,
                response_format=response_format,
            )
        except Exception as exc:
            last_error = exc
            if len(providers_to_try) > 1 and prov != providers_to_try[-1]:
                print(f"[VLM] {prov} failed ({exc}), retrying with fallback...")
            continue

    raise RuntimeError(f"All VLM providers failed. Last error: {last_error}")
