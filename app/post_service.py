import json

from app.config import FINAL_DIR, RAW_DIR
from app.db import insert_post
from app.image_service import generate_image
from app.overlay_service import overlay_comparison_top5, overlay_single_card
from app.text_service import generate_comparison_content, generate_single_card_content
from app.utils import slugify


INFOGRAPHIC_IMAGE_TEMPLATE = """
Universal infographic image template:
Create a professionally designed vertical stacked-panel infographic background for a ranking or list.
The style must be clean, modern data visualization combined with natural wildlife photography.

Layout:
- Vertical 4:5 social media poster composition.
- A clear header area at the top.
- Exactly five horizontal item panels stacked one above another for ranking items 1 to 5.
- Each panel should feel like it has a left data area and a right image area.
- The left data areas must be clean, low-detail, and suitable for later text overlay.
- The right image area should contain the subject animal in realistic motion.
- Use blurred natural landscape backgrounds appropriate to the habitat.
- Add subtle motion lines, data glow, and dynamic flourishes.

Important rendering rules:
- Do not render any readable text, letters, numbers, labels, fake UI text, logos, watermarks, or captions.
- Do not render ranking numbers; these will be added later by Python.
- Do not render animal names; these will be added later by Python.
- Leave clean space for text overlay in the header and left side of each panel.
- Keep the animal photo areas clear, realistic, sharp, and visually dominant.
""".strip()

CAPTION_HASHTAGS = "#thegioimuonloai #topdongvat #reivewthegioidongvat #khamphatunhien"


def append_caption_hashtags(caption: str) -> str:
    caption = caption.strip()
    if CAPTION_HASHTAGS in caption:
        return caption
    return f"{caption}\n\n{CAPTION_HASHTAGS}"


def reinforce_image_prompt(image_prompt: str, topic: dict) -> str:
    if topic["topic_type"] == "comparison_top5":
        animals = ", ".join(item["name_en"] for item in topic["items"])
        item_list = "\n".join(
            f"- Rank {item['rank']}: {item['name_en']} in dynamic natural motion"
            for item in topic["items"]
        )
        return (
            f"{image_prompt}\n\n"
            f"{INFOGRAPHIC_IMAGE_TEMPLATE}\n\n"
            "Specific subject for this instance:\n"
            f"- Topic: {topic['subject_en']}\n"
            f"- Animals that must appear clearly and recognizably: {animals}\n"
            f"{item_list}\n\n"
            "Design adaptation:\n"
            "- Use warm orange, amber, and earth-tone accents for land animals.\n"
            "- Use an open savanna or grassland habitat where appropriate.\n"
            "- Show each animal as a real full-body wildlife photo element, not an illustration or abstract symbol.\n"
            "- Add a subtle thematic emblem or compass-star detail in the bottom corner, without text."
        )

    return (
        f"{image_prompt}\n\n"
        "Single-card wildlife poster background:\n"
        f"- Main subject: one real, recognizable {topic['subject_en']}.\n"
        "- Use photorealistic wildlife or nature photography style.\n"
        "- Keep one clean low-detail area for later text overlay.\n"
        "- The animal must be visually dominant and shown clearly in its natural habitat.\n"
        "- Do not render any readable text, letters, numbers, logos, watermarks, or fake UI text."
    )


def build_comparison_caption(title: str, caption_intro: str, items: list) -> str:
    lines = [
        title,
        "",
        caption_intro.strip(),
        "",
    ]

    for item in items:
        lines.append(f'{item["rank"]}. {item["name_vi"]} ({item["name_en"]}) - {item["stat"]}')

    lines += ["", "Ảnh minh họa AI."]

    return append_caption_hashtags("\n".join(lines))


def build_single_caption(title: str, caption: str) -> str:
    return append_caption_hashtags(f"{title}\n\n{caption.strip()}")


def build_post_payload(topic: dict, scheduled_at: str, slot: str) -> dict:
    base_name = slugify(f"{scheduled_at}_{slot}_{topic['topic_key']}")
    raw_path = str(RAW_DIR / f"{base_name}.png")
    final_path = str(FINAL_DIR / f"{base_name}.jpg")

    if topic["topic_type"] == "comparison_top5":
        content = generate_comparison_content(topic)
        image_prompt = reinforce_image_prompt(content["image_prompt"], topic)
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
            "raw_image_path": raw_path,
            "final_image_path": final_path,
            "status": "READY",
        }

    if topic["topic_type"] == "single_card":
        content = generate_single_card_content(topic)
        image_prompt = reinforce_image_prompt(content["image_prompt"], topic)
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
            "raw_image_path": raw_path,
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
        post_data["raw_image_path"],
        fallback_on_error=image_fallback_on_error,
    )
    overlay_post_image(post_data)
    return insert_post(post_data)


def build_post_for_batch(topic: dict, scheduled_at: str, slot: str) -> int:
    post_data = build_post_payload(topic, scheduled_at, slot)
    post_data["status"] = "WAITING_IMAGE"
    post_data["batch_request_key"] = f"{post_data['scheduled_at']}_{post_data['slot']}_{post_data['topic_key']}"
    return insert_post(post_data)
