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


def metric_label_for_topic(topic: dict) -> str | None:
    labels = {
        "speed": "TỐC ĐỘ",
        "height": "CHIỀU CAO",
        "weight": "CÂN NẶNG",
        "size": "KÍCH THƯỚC",
        "special ability": "ĐẶC ĐIỂM",
        "bite force": "LỰC CẮN",
        "lifespan": "TUỔI THỌ",
        "venom": "NỌC ĐỘC",
        "toxicity": "ĐỘC TÍNH",
    }
    return labels.get(topic.get("comparison_angle", ""))


def compact_text(text: str, max_chars: int) -> str:
    text = " ".join(text.split()).strip()
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def comparison_item_detail(item: dict, topic: dict) -> str:
    detail = item.get("detail_vi", "").strip()
    if detail:
        return detail

    angle = topic.get("comparison_angle", "")
    fallback_details = {
        "speed": "mốc tốc độ nổi bật khi bứt tốc trong môi trường tự nhiên",
        "height": "chiều cao nổi bật giúp nó vượt trội trong nhóm này",
        "weight": "khối lượng lớn khiến nó trở thành một trong những loài nặng nhất",
        "size": "kích thước nổi bật so với phần lớn loài cùng nhóm",
        "special ability": "đặc điểm nổi bật giúp nó săn mồi, sinh tồn hoặc tự vệ",
        "bite force": "lực cắn ước tính rất mạnh, đủ tạo lợi thế khi săn mồi hoặc phòng thủ",
        "lifespan": "tuổi thọ ấn tượng khiến các nhà nghiên cứu đặc biệt chú ý",
        "venom": "cơ chế độc/nọc giúp nó săn mồi hoặc tự vệ cực hiệu quả",
        "toxicity": "độc tính tự nhiên khiến con người phải rất thận trọng",
        "camouflage": "khả năng hòa vào môi trường khiến kẻ thù hoặc con mồi khó nhận ra",
        "bioluminescence": "ánh sáng sinh học giúp giao tiếp, dụ mồi hoặc tự vệ trong bóng tối",
        "building ability": "khả năng xây dựng nơi ở hoặc cấu trúc sống rất tinh vi",
        "survival": "chiến lược sinh tồn giúp nó chịu được điều kiện khắc nghiệt",
        "parenting": "cách chăm con đặc biệt giúp thế hệ sau có cơ hội sống sót cao hơn",
    }
    return fallback_details.get(angle, "đặc điểm nổi bật khiến loài này rất đáng chú ý")


def comparison_item_image_fact_text(item: dict, topic: dict) -> str:
    stat = compact_text(item["stat"], 16)
    detail = compact_text(comparison_item_detail(item, topic), 42)
    return f"{stat} - {detail}"


def comparison_caption_line(item: dict, topic: dict) -> str:
    return (
        f'{item["rank"]}. {item["name_vi"]} ({item["name_en"]}) - '
        f'{item["stat"]}: {comparison_item_detail(item, topic)}'
    )


def comparison_prompt_rows(topic: dict) -> str:
    metric_label = metric_label_for_topic(topic)
    rows = []
    for item in topic["items"]:
        lines = [
            f"Panel {item['rank']}:",
            f"- Rank text: {item['rank']:02d}",
            f"- Animal or plant name text: {item['name_vi'].upper()}",
        ]
        if metric_label:
            lines.append(f"- Metric label text: {metric_label}:")
        lines.extend(
            [
                f"- Metric value text: {comparison_item_image_fact_text(item, topic)}",
                f"- Visual scene: realistic {item['name_en']} showing or strongly suggesting this fact: {comparison_caption_line(item, topic)}",
            ]
        )
        rows.append("\n".join(lines))
    return "\n".join(rows)


def build_model_rendered_infographic_prompt(image_prompt: str, topic: dict, content: dict) -> str:
    if topic["topic_type"] == "comparison_top5":
        title = content.get("overlay_subtitle") or topic["subject_vi"]
        title = title.upper()
        rows = comparison_prompt_rows(topic)
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
            "- Never render generic labels or placeholder labels.\n"
            "- Do not add watermark, logo, captions, brand text, or random symbols.\n"
            "- If text cannot fit inside a panel, reduce font size, tighten spacing, or split into two short lines.\n"
            "- Never crop, truncate, overlap, or replace the listed text; readability is more important than large type.\n\n"
            "Additional photo/style guidance from the text model, use only if it does not conflict with exact text rules:\n"
            f"{image_prompt}"
        )

    title = content.get("overlay_title") or topic["subject_vi"]
    stat = content.get("overlay_stat") or topic.get("fact_value", "")
    hook = content.get("overlay_hook") or ""
    visual_detail = topic.get("detail_vi") or topic.get("fact_detail", "")
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
        f"Visual fact to suggest without rendering as extra text: {visual_detail}\n"
        "Composition: top headline, large hero subject, one copper stat badge, one short hook line near the bottom.\n"
        "Text quality: render Vietnamese diacritics carefully and keep every word readable.\n\n"
        "Additional photo/style guidance from the text model, use only if it does not conflict with exact text rules:\n"
        f"{image_prompt}"
    )


def image_prompt_renders_final_text(image_prompt: str) -> bool:
    return MODEL_RENDERED_TEXT_MARKER in image_prompt


def build_comparison_caption(title: str, caption_intro: str, items: list, topic: dict | None = None) -> str:
    topic = topic or {}
    lines = [
        title,
        "",
        caption_intro.strip(),
        "",
    ]

    for item in items:
        lines.append(comparison_caption_line(item, topic))

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
            topic=topic,
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
