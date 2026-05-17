from pathlib import Path

from app.config import GEMINI_API_KEY, GEMINI_IMAGE_MODEL


def _ensure_api_key():
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing ANIMAL_AGENT_GEMINI_API_KEY")


def _client():
    from google import genai

    return genai.Client(api_key=GEMINI_API_KEY)


def generate_image(image_prompt: str, output_path: str, retries: int = 2) -> str:
    _ensure_api_key()
    client = _client()
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    last_error = None

    for _ in range(retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_IMAGE_MODEL,
                contents=[image_prompt],
            )

            parts = getattr(response, "parts", None)
            if parts:
                for part in parts:
                    if getattr(part, "inline_data", None) is not None:
                        image = part.as_image()
                        image.save(output_path)
                        return output_path

            candidates = getattr(response, "candidates", None)
            if candidates:
                for candidate in candidates:
                    content = getattr(candidate, "content", None)
                    if not content:
                        continue
                    c_parts = getattr(content, "parts", [])
                    for part in c_parts:
                        if getattr(part, "inline_data", None) is not None:
                            image = part.as_image()
                            image.save(output_path)
                            return output_path

            raise RuntimeError("Model did not return an image part.")
        except Exception as exc:
            last_error = exc

    raise RuntimeError(f"Generate image failed: {last_error}")
