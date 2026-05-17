import json

from app.config import FINAL_DIR, RAW_DIR
from app.db import insert_post
from app.image_service import generate_image
from app.overlay_service import overlay_comparison_top5, overlay_single_card
from app.text_service import generate_comparison_content, generate_single_card_content
from app.utils import slugify


def build_comparison_caption(title: str, caption_intro: str, items: list) -> str:
    lines = [
        title,
        "",
        caption_intro.strip(),
        "",
    ]

    for item in items:
        lines.append(f'{item["rank"]}. {item["name_vi"]} - {item["stat"]}')

    lines += ["", "Ảnh minh họa AI."]

    return "\n".join(lines)


def build_single_caption(title: str, caption: str) -> str:
    return f"{title}\n\n{caption.strip()}"


def build_post(topic: dict, scheduled_at: str, slot: str) -> int:
    base_name = slugify(f"{scheduled_at}_{slot}_{topic['topic_key']}")
    raw_path = str(RAW_DIR / f"{base_name}.png")
    final_path = str(FINAL_DIR / f"{base_name}.jpg")

    if topic["topic_type"] == "comparison_top5":
        content = generate_comparison_content(topic)
        generate_image(content["image_prompt"], raw_path)

        overlay_comparison_top5(
            raw_path=raw_path,
            final_path=final_path,
            overlay_title=content["overlay_title"],
            overlay_subtitle=content["overlay_subtitle"],
            items=topic["items"],
        )

        caption = build_comparison_caption(
            title=content["title"],
            caption_intro=content["caption_intro"],
            items=topic["items"],
        )

        post_data = {
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
            "image_prompt": content["image_prompt"],
            "topic_payload": json.dumps(topic, ensure_ascii=False),
            "raw_image_path": raw_path,
            "final_image_path": final_path,
            "status": "READY",
        }
        return insert_post(post_data)

    if topic["topic_type"] == "single_card":
        content = generate_single_card_content(topic)
        generate_image(content["image_prompt"], raw_path)

        overlay_single_card(
            raw_path=raw_path,
            final_path=final_path,
            overlay_title=content["overlay_title"],
            overlay_stat=content["overlay_stat"],
            overlay_hook=content["overlay_hook"],
        )

        caption = build_single_caption(content["title"], content["caption"])

        post_data = {
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
            "image_prompt": content["image_prompt"],
            "topic_payload": json.dumps(topic, ensure_ascii=False),
            "raw_image_path": raw_path,
            "final_image_path": final_path,
            "status": "READY",
        }
        return insert_post(post_data)

    raise ValueError(f"Unsupported topic_type: {topic['topic_type']}")

