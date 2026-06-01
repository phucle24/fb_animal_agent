import requests

from app.config import (
    DEEPSEEK_API_KEY,
    DEEPSEEK_BASE_URL,
    DEEPSEEK_TEXT_MODEL,
    DEEPSEEK_TIMEOUT_SECONDS,
)
from app.utils import safe_json_loads


class DeepSeekError(RuntimeError):
    pass


def ensure_deepseek_config():
    if not DEEPSEEK_API_KEY:
        raise RuntimeError("Missing ANIMAL_AGENT_DEEPSEEK_API_KEY")


def generate_json(prompt: str, system: str | None = None, max_tokens: int = 4096) -> dict:
    ensure_deepseek_config()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    response = requests.post(
        f"{DEEPSEEK_BASE_URL}/chat/completions",
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": DEEPSEEK_TEXT_MODEL,
            "messages": messages,
            "response_format": {"type": "json_object"},
            "thinking": {"type": "disabled"},
            "stream": False,
            "max_tokens": max_tokens,
        },
        timeout=DEEPSEEK_TIMEOUT_SECONDS,
    )

    try:
        result = response.json()
    except ValueError as exc:
        raise DeepSeekError(f"DeepSeek returned non-JSON response: {response.text[:500]}") from exc

    if response.status_code >= 400 or "error" in result:
        raise DeepSeekError(str(result))

    choices = result.get("choices") or []
    if not choices:
        raise DeepSeekError(f"DeepSeek returned no choices: {result}")

    content = (choices[0].get("message") or {}).get("content", "")
    if not content:
        raise DeepSeekError(f"DeepSeek returned empty content: {result}")

    return safe_json_loads(content)
