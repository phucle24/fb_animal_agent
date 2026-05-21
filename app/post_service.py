import json

from app.config import FINAL_DIR, RAW_DIR
from app.db import insert_post
from app.image_service import generate_image
from app.overlay_service import overlay_comparison_top5, overlay_single_card
from app.text_service import generate_comparison_content, generate_single_card_content
from app.utils import slugify


INFOGRAPHIC_IMAGE_TEMPLATE = """
FINAL INFOGRAPHIC MUST CONTAIN THE EXACT TEXT BELOW.
Create a finished vertical 4:5 Vietnamese infographic poster for Facebook feed, in the same visual direction as a premium wildlife ranking graphic:
- black/dark charcoal background panels
- copper/orange border and separators
- bold condensed white Vietnamese typography
- large copper/orange rank numbers
- stacked horizontal ranking panels
- left black text block, right realistic wildlife photo block
- dramatic photorealistic animal images, sharp eyes, motion, cinematic lighting
- vertical 4:5 layout with enough height for a header and five stacked panels, all text readable without cropping
- no Python overlay will be used later; all text must be rendered by the image model now
""".strip()

SINGLE_CARD_IMAGE_TEMPLATE = """
FINAL INFOGRAPHIC MUST CONTAIN THE EXACT TEXT BELOW.
Create a finished vertical 4:5 Vietnamese single-subject fact poster for Facebook feed:
- one dramatic photorealistic animal or plant hero image, large and unmistakable
- premium dark charcoal poster style with copper/orange accents
- bold readable Vietnamese headline at the top
- one large metric/stat badge
- one short hook line
- clean editorial layout, not a ranking, not a comparison, not a list
- no Python overlay will be used later; all text must be rendered by the image model now
""".strip()

CAPTION_HASHTAGS = "#thegioimuonloai #topdongbat #reivewthegioidongvat #khamphatunhien"
MODEL_RENDERED_TEXT_MARKER = "FINAL INFOGRAPHIC MUST CONTAIN THE EXACT TEXT BELOW."
AI_DISCLAIMERS = (
    "Ảnh minh họa AI.",
    "Ảnh minh hoạ AI.",
    "Ảnh AI minh họa.",
    "Ảnh AI minh hoạ.",
    "AI illustration.",
)


def append_caption_hashtags(caption: str) -> str:
    caption = caption.strip()
    if CAPTION_HASHTAGS in caption:
        return caption
    return f"{caption}\n\n{CAPTION_HASHTAGS}"


def remove_ai_disclaimer(caption: str) -> str:
    cleaned = caption.strip()
    for disclaimer in AI_DISCLAIMERS:
        cleaned = cleaned.replace(disclaimer, "").strip()
    return "\n".join(line.rstrip() for line in cleaned.splitlines()).strip()


def metric_label_for_topic(topic: dict) -> str:
    labels = {
        "speed": "TỐC ĐỘ",
        "height": "CHIỀU CAO",
        "weight": "CÂN NẶNG",
        "size": "KÍCH THƯỚC",
        "special ability": "ĐẶC ĐIỂM",
    }
    return labels.get(topic.get("comparison_angle", ""), "THÔNG TIN")


def stat_for_image(stat: str) -> str:
    return stat.upper().replace("KM/H", "KM/H")


def build_model_rendered_infographic_prompt(image_prompt: str, topic: dict, content: dict) -> str:
    if topic["topic_type"] == "comparison_top5":
        title = content.get("overlay_subtitle") or topic["subject_vi"]
        title = title.upper()
        metric_label = metric_label_for_topic(topic)
        rows = "\n".join(
            "\n".join(
                [
                    f"Panel {item['rank']}:",
                    f"- Rank text: {item['rank']:02d}",
                    f"- Animal name text: {item['name_vi'].upper()}",
                    f"- Metric label text: {metric_label}:",
                    f"- Metric value text: {stat_for_image(item['stat'])}",
                    f"- Animal photo: realistic {item['name_en']} in its natural habitat, dynamic motion, visible face and body",
                ]
            )
            for item in topic["items"]
        )
        return (
            f"{INFOGRAPHIC_IMAGE_TEMPLATE}\n\n"
            "Reference visual style:\n"
            "- Reference layout: header title on top, numbered panels below, text column left, animal image right.\n"
            "- Vertical 4:5 canvas for Facebook feed. Use compact spacing; do not crop or hide any panel.\n"
            "- Use strong black and copper/orange theme, thin copper border, clean separators.\n"
            "- Use realistic animal photography inside each right panel.\n\n"
            "Header text to render exactly:\n"
            f"{title}\n\n"
            "Panel text and image content to render exactly:\n"
            f"{rows}\n\n"
            "Strict text rules:\n"
            "- Render Vietnamese diacritics correctly.\n"
            "- Use the exact text strings above, no extra words, no English labels, no fake text.\n"
            "- Do not add watermark, logo, captions, brand text, or random symbols.\n"
            "- If text cannot fit, reduce font size but keep all listed text readable.\n\n"
            "Additional photo/style guidance from the text model, use only if it does not conflict with exact text rules:\n"
            f"{image_prompt}"
        )

    title = content.get("overlay_title") or topic["subject_vi"]
    stat = content.get("overlay_stat") or topic.get("fact_value", "")
    hook = content.get("overlay_hook") or ""
    return (
        f"{SINGLE_CARD_IMAGE_TEMPLATE}\n\n"
        "Critical layout rules:\n"
        "- This is a single-card poster, not a ranking and not a multi-panel list.\n"
        "- Do not render rank numbers such as 01, 02, 03, 1, 2, 5.\n"
        "- Do not render placeholder words such as Stat, data, label, lorem ipsum, UI text, or fake text.\n"
        "- Do not add any extra captions, labels, subtitles, watermark, logo, or random symbols.\n"
        "- Use only the exact text strings listed below.\n"
        "- If text cannot fit, reduce font size; never invent additional text.\n\n"
        "Text to render exactly, and only these text strings:\n"
        f"HEADLINE: {title.upper()}\n"
        f"STAT: {stat.upper()}\n"
        f"HOOK: {hook}\n\n"
        f"Hero image: realistic {topic['subject_en']} in its natural habitat, cinematic, sharp, dramatic, visually striking.\n"
        "Composition: top headline, large hero subject, one copper stat badge, one short hook line near the bottom.\n"
        "Text quality: render Vietnamese diacritics carefully and keep every word readable.\n\n"
        "Additional photo/style guidance from the text model, use only if it does not conflict with exact text rules:\n"
        f"{image_prompt}"
    )


def image_prompt_renders_final_text(image_prompt: str) -> bool:
    return MODEL_RENDERED_TEXT_MARKER in image_prompt


def build_comparison_caption(title: str, caption_intro: str, items: list) -> str:
    lines = [
        title,
        "",
        caption_intro.strip(),
        "",
    ]

    for item in items:
        lines.append(f'{item["rank"]}. {item["name_vi"]} ({item["name_en"]}) - {item["stat"]}')

    return append_caption_hashtags(remove_ai_disclaimer("\n".join(lines)))


def build_single_caption(title: str, caption: str) -> str:
    return append_caption_hashtags(remove_ai_disclaimer(f"{title}\n\n{caption.strip()}"))


def build_post_payload(topic: dict, scheduled_at: str, slot: str) -> dict:
    base_name = slugify(f"{scheduled_at}_{slot}_{topic['topic_key']}")
    final_path = str(FINAL_DIR / f"{base_name}.jpg")

    if topic["topic_type"] == "comparison_top5":
        content = generate_comparison_content(topic)
        image_prompt = build_model_rendered_infographic_prompt(content["image_prompt"], topic, content)
        caption = build_comparison_caption(
            title=content["title"],
            caption_intro=content["caption_intro"],
            items=topic["items"],
        )
        return {
            "scheduled_at": scheduled_at,
            "slot": slot,
            "topic_type": topic["topic_type"],
            "topic_key": topic["topic_key"],
            "title": content["title"],
            "overlay_title": content["overlay_title"],
            "overlay_subtitle": content["overlay_subtitle"],
            "overlay_stat": None,
            "overlay_hook": None,
            "caption": caption,
            "image_prompt": image_prompt,
            "topic_payload": json.dumps(topic, ensure_ascii=False),
            "raw_image_path": final_path,
            "final_image_path": final_path,
            "status": "READY",
        }

    if topic["topic_type"] == "single_card":
        content = generate_single_card_content(topic)
        image_prompt = build_model_rendered_infographic_prompt(content["image_prompt"], topic, content)
        caption = build_single_caption(content["title"], content["caption"])
        return {
            "scheduled_at": scheduled_at,
            "slot": slot,
            "topic_type": topic["topic_type"],
            "topic_key": topic["topic_key"],
            "title": content["title"],
            "overlay_title": content["overlay_title"],
            "overlay_subtitle": None,
            "overlay_stat": content["overlay_stat"],
            "overlay_hook": content["overlay_hook"],
            "caption": caption,
            "image_prompt": image_prompt,
            "topic_payload": json.dumps(topic, ensure_ascii=False),
            "raw_image_path": final_path,
            "final_image_path": final_path,
            "status": "READY",
        }

    raise ValueError(f"Unsupported topic_type: {topic['topic_type']}")


def overlay_post_image(post_data: dict) -> str:
    topic = json.loads(post_data["topic_payload"])
    if post_data["topic_type"] == "comparison_top5":
        return overlay_comparison_top5(
            raw_path=post_data["raw_image_path"],
            final_path=post_data["final_image_path"],
            overlay_title=post_data["overlay_title"],
            overlay_subtitle=post_data["overlay_subtitle"],
            items=topic["items"],
        )

    if post_data["topic_type"] == "single_card":
        return overlay_single_card(
            raw_path=post_data["raw_image_path"],
            final_path=post_data["final_image_path"],
            overlay_title=post_data["overlay_title"],
            overlay_stat=post_data["overlay_stat"],
            overlay_hook=post_data["overlay_hook"],
        )

    raise ValueError(f"Unsupported topic_type: {post_data['topic_type']}")


def build_post(topic: dict, scheduled_at: str, slot: str, image_fallback_on_error: bool | None = None) -> int:
    post_data = build_post_payload(topic, scheduled_at, slot)
    generate_image(
        post_data["image_prompt"],
        post_data["final_image_path"],
        fallback_on_error=image_fallback_on_error,
    )
    return insert_post(post_data)


def build_post_for_batch(topic: dict, scheduled_at: str, slot: str) -> int:
    post_data = build_post_payload(topic, scheduled_at, slot)
    post_data["status"] = "WAITING_IMAGE"
    post_data["batch_request_key"] = f"{post_data['scheduled_at']}_{post_data['slot']}_{post_data['topic_key']}"
    return insert_post(post_data)
