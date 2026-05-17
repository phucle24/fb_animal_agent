from pathlib import Path

from PIL import Image, ImageDraw

from app.config import GEMINI_API_KEY, GEMINI_IMAGE_MODEL, IMAGE_FALLBACK_ON_ERROR


def _ensure_api_key():
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing ANIMAL_AGENT_GEMINI_API_KEY")


def _client():
    from google import genai

    return genai.Client(api_key=GEMINI_API_KEY)


def _types():
    from google.genai import types

    return types


def _describe_response(response) -> str:
    pieces = []

    prompt_feedback = getattr(response, "prompt_feedback", None)
    if prompt_feedback:
        pieces.append(f"prompt_feedback={prompt_feedback!r}")

    text = getattr(response, "text", None)
    if text:
        pieces.append(f"text={text[:500]!r}")

    candidates = getattr(response, "candidates", None) or []
    for index, candidate in enumerate(candidates):
        finish_reason = getattr(candidate, "finish_reason", None)
        safety_ratings = getattr(candidate, "safety_ratings", None)
        pieces.append(
            f"candidate[{index}].finish_reason={finish_reason!r}, "
            f"safety_ratings={safety_ratings!r}"
        )

    return "; ".join(pieces) or "empty response details"


def create_placeholder_image(output_path: str) -> str:
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    width, height = 1080, 1350
    img = Image.new("RGB", (width, height), (28, 42, 56))
    draw = ImageDraw.Draw(img)

    for y in range(height):
        ratio = y / height
        r = int(24 + ratio * 34)
        g = int(54 + ratio * 74)
        b = int(68 + ratio * 42)
        draw.line((0, y, width, y), fill=(r, g, b))

    for x, y, radius, color in [
        (160, 180, 180, (255, 196, 30)),
        (880, 360, 250, (15, 118, 110)),
        (280, 1040, 320, (36, 64, 98)),
    ]:
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)

    img.save(output_path)
    return output_path


def generate_image(
    image_prompt: str,
    output_path: str,
    retries: int = 2,
    fallback_on_error: bool | None = None,
) -> str:
    _ensure_api_key()
    client = _client()
    types = _types()
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    last_error = "unknown error"

    for _ in range(retries):
        try:
            response = client.models.generate_content(
                model=GEMINI_IMAGE_MODEL,
                contents=[image_prompt],
                config=types.GenerateContentConfig(response_modalities=["TEXT", "IMAGE"]),
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

            raise RuntimeError(f"Model did not return an image part: {_describe_response(response)}")
        except Exception as exc:
            last_error = repr(exc)

    should_fallback = IMAGE_FALLBACK_ON_ERROR if fallback_on_error is None else fallback_on_error
    if should_fallback:
        return create_placeholder_image(output_path)

    raise RuntimeError(
        f"Generate image failed with model {GEMINI_IMAGE_MODEL!r}: {last_error}. "
        "For low-cost Gemini image generation, try ANIMAL_AGENT_GEMINI_IMAGE_MODEL=gemini-2.5-flash-image."
    )
