import time
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


def generate_json(
    prompt: str,
    system: str | None = None,
    max_tokens: int = 4096,
    retries: int = 3,
) -> dict:
    ensure_deepseek_config()
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    last_error = None
    for attempt in range(retries):
        try:
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
            result = response.json()
        except (requests.RequestException, ValueError, TimeoutError) as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(3 * (2 ** attempt))
                continue
            raise DeepSeekError(f"DeepSeek request failed: {exc}") from exc

        if response.status_code >= 400 or "error" in result:
            err_msg = str(result.get("error") or result)
            last_error = DeepSeekError(err_msg)
            if attempt < retries - 1:
                time.sleep(3 * (2 ** attempt))
                continue
            raise DeepSeekError(err_msg)

        choices = result.get("choices") or []
        if not choices:
            last_error = DeepSeekError(f"DeepSeek returned no choices: {result}")
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise last_error

        content = (choices[0].get("message") or {}).get("content", "")
        if not content:
            last_error = DeepSeekError(f"DeepSeek returned empty content: {result}")
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise last_error

        try:
            return safe_json_loads(content)
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2)
                continue
            raise

    if last_error:
        raise last_error
    raise DeepSeekError("Failed to generate content from DeepSeek")
