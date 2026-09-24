import re

FORBIDDEN_SCENE_TERMS = (
    "row",
    "rows",
    "panel",
    "panels",
    "list",
    "ranking",
    "rank",
    "top 5",
    "table",
    "grid",
    "text",
    "typography",
    "infographic",
    "poster layout",
    "visual journalism",
    "journalism",
    "headline",
    "badge",
    "pill tag",
    "header pill",
    "thu bat",
    "thủ bạt",
    "đề bạt",
    "banner",
)

MODEL_RENDERED_TEXT_MARKER = "FINAL INFOGRAPHIC MUST CONTAIN THE EXACT TEXT BELOW."


def sanitize_scene_prompt(image_prompt: str) -> str:
    """
    Strips scene prompts of forbidden layout, typography, or styling keywords
    that could lead the image generation model to produce unwanted text or UI elements.
    """
    prompt = " ".join((image_prompt or "").split()).strip()
    if not prompt:
        return ""
    lowered = prompt.lower()
    if any(term in lowered for term in FORBIDDEN_SCENE_TERMS):
        return ""
    return prompt


clean_single_scene_prompt = sanitize_scene_prompt


def enforce_prompt_language_and_safety(image_prompt: str) -> str:
    """
    Central safety enforcer applied to ALL image prompts across the project.
    Guarantees that:
    1. The forbidden phrase 'visual journalism poster' or related layout tags are removed.
    2. Strict anti-English, anti-thu-bat, and Vietnamese-only rules are preserved on model-rendered prompts.
    """
    if not image_prompt:
        return image_prompt

    # Replace forbidden stylistic names that Gemini models love to render as literal text
    cleaned = re.sub(r"(?i)\bvisual\s+journalism\s+poster\b", "wildlife documentary photo feature", image_prompt)
    cleaned = re.sub(r"(?i)\bvisual\s+journalism\b", "documentary feature", cleaned)

    # For any model-rendered text prompt, ensure the critical safety override is present
    if MODEL_RENDERED_TEXT_MARKER in cleaned:
        if "STRICT ZERO ENGLISH TEXT" not in cleaned:
            cleaned = (
                f"{cleaned}\n\n"
                "FINAL CRITICAL TEXT SAFETY OVERRIDE:\n"
                "- STRICT ZERO ENGLISH TEXT: Every visible word and character must be in Vietnamese only. Absolutely NO English words, NO English labels anywhere on the image.\n"
                "- STRICT NO 'THỦ BẠT': Absolutely DO NOT render the word 'Thủ bạt', 'thủ bạt', or any placeholder tag.\n"
                "- NO TOP PILLS OR CORNER TAGS: Do not render any pill buttons, category badges, or header tags at the top edges."
            )

    return cleaned
