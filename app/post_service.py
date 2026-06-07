import json

from app.config import FINAL_DIR, RAW_DIR
from app.db import insert_post
from app.image_service import generate_image
from app.overlay_service import overlay_comparison_top5, overlay_single_card
from app.text_service import generate_comparison_content, generate_matchup_content, generate_single_card_content
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
- exactly one dramatic photorealistic animal or plant hero image, large and unmistakable
- premium dark charcoal editorial poster style with copper/orange accents
- exactly three visible text groups total: headline, main fact, short hook
- clean single-card layout with open space, not a ranking, not a comparison, not a list
- no rows, no repeated subject thumbnails, no numbered panels, no table, no grid
- no Python overlay will be used later; all text must be rendered by the image model now
""".strip()

MATCHUP_IMAGE_TEMPLATE = """
FINAL INFOGRAPHIC MUST CONTAIN THE EXACT TEXT BELOW.
Create a finished vertical 4:5 Vietnamese scientific animal face-off infographic poster for Facebook feed:
- premium split-screen layout with left animal versus right animal
- dark forest/jungle background, copper/orange accents, cinematic shafts of light
- bold condensed Vietnamese typography, clean science infographic mood
- two realistic full-body or half-body animal portraits facing forward, separated by a thin vertical divider
- data cards under each animal with concise measurements
- no gore, no blood, no injury, no violent impact
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


def concise_single_fact(fact_value: str) -> str:
    fact = " ".join(fact_value.split()).strip()
    normalized = fact.lower()
    if "gần như" in normalized and "im lặng" in normalized:
        return "GẦN IM LẶNG"
    return compact_text(fact.upper(), 18)


def normalize_single_card_content(topic: dict, content: dict) -> dict:
    normalized = dict(content)
    fact_value = topic.get("fact_value", "")
    fact_context = " ".join(
        [
            fact_value,
            topic.get("fact_detail", ""),
            topic.get("detail_vi", ""),
        ]
    ).lower()
    stat = str(normalized.get("overlay_stat") or "").strip()
    if "tuyệt đối" in stat.lower() and any(
        hedge in fact_context for hedge in ("gần như", "nearly", "almost", "có thể", "ước tính", "khoảng")
    ):
        normalized["overlay_stat"] = concise_single_fact(fact_value)
    elif len(stat) > 22:
        normalized["overlay_stat"] = compact_text(stat.upper(), 18)
    return normalized


def clean_single_scene_prompt(image_prompt: str) -> str:
    prompt = " ".join((image_prompt or "").split()).strip()
    forbidden_terms = (
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
    )
    lowered = prompt.lower()
    if any(term in lowered for term in forbidden_terms):
        return ""
    return prompt


def comparison_item_detail(item: dict, topic: dict) -> str:
    detail = item.get("detail_vi", "").strip()
    if detail:
        return detail

    angle = topic.get("comparison_angle", "")
    stat = item.get("stat", "").lower()
    name_text = f"{item.get('name_vi', '')} {item.get('name_en', '')}".lower()

    if angle == "toxicity":
        toxicity_details = [
            (("ricin", "thầu dầu", "castor"), "hạt chứa ricin, chất độc có thể ức chế tế bào tạo protein"),
            (("aconitine", "phụ tử", "monkshood"), "aconitine tác động lên kênh natri, dễ gây rối loạn nhịp tim"),
            (("độc tim", "trúc đào", "oleander"), "glycoside tim có thể làm rối loạn nhịp và co bóp tim"),
            (("ảo giác", "cà độc dược", "jimsonweed"), "alkaloid tropane có thể gây mê sảng, ảo giác và tim đập nhanh"),
            (("nhựa độc", "manchineel"), "nhựa cây gây bỏng rát da, quả và khói đốt cũng nguy hiểm"),
        ]
        lookup = f"{stat} {name_text}"
        for keywords, mapped_detail in toxicity_details:
            if any(keyword in lookup for keyword in keywords):
                return mapped_detail

    if angle == "venom":
        venom_details = [
            (("neurotoxin", "thần kinh"), "độc tố thần kinh có thể làm tê liệt tín hiệu giữa dây thần kinh và cơ"),
            (("hemotoxin", "máu"), "độc tố tác động lên máu và mô, làm vết thương nguy hiểm hơn"),
            (("cardiotoxin", "tim"), "độc tố có thể ảnh hưởng trực tiếp đến hoạt động của tim"),
        ]
        lookup = f"{stat} {name_text}"
        for keywords, mapped_detail in venom_details:
            if any(keyword in lookup for keyword in keywords):
                return mapped_detail

    if angle == "building ability":
        building_details = [
            (("đập", "hải ly", "beaver"), "chặt cây, xếp cành và bùn để đổi dòng chảy"),
            (("tháp", "mối", "termite"), "xây tháp có hệ thống thông gió tự nhiên rất ổn định"),
            (("tổ dệt", "sẻ dòng dọc", "weaver"), "đan cỏ thành tổ treo chắc chắn để thu hút bạn tình"),
            (("lục giác", "ong mật", "honeybee"), "xây ô sáp lục giác để tiết kiệm vật liệu và diện tích"),
            (("trang trại nấm", "kiến cắt lá", "leafcutter"), "cắt lá mang về tổ để nuôi nấm làm thức ăn"),
        ]
        lookup = f"{stat} {name_text}"
        for keywords, mapped_detail in building_details:
            if any(keyword in lookup for keyword in keywords):
                return mapped_detail

    fallback_details = {
        "speed": "mốc tốc độ nổi bật khi bứt tốc trong môi trường tự nhiên",
        "height": "chiều cao nổi bật giúp nó vượt trội trong nhóm này",
        "weight": "khối lượng lớn khiến nó trở thành một trong những loài nặng nhất",
        "size": "kích thước nổi bật so với phần lớn loài cùng nhóm",
        "special ability": "đặc điểm nổi bật giúp nó săn mồi, sinh tồn hoặc tự vệ",
        "bite force": "lực cắn ước tính rất mạnh, đủ tạo lợi thế khi săn mồi hoặc phòng thủ",
        "lifespan": "tuổi thọ ấn tượng khiến các nhà nghiên cứu đặc biệt chú ý",
        "venom": "nọc độc tác động lên thần kinh, máu hoặc mô để săn mồi/tự vệ",
        "toxicity": "chứa hợp chất độc có thể ảnh hưởng nghiêm trọng đến cơ thể",
        "camouflage": "khả năng hòa vào môi trường khiến kẻ thù hoặc con mồi khó nhận ra",
        "bioluminescence": "ánh sáng sinh học giúp giao tiếp, dụ mồi hoặc tự vệ trong bóng tối",
        "building ability": "xây cấu trúc sống bằng vật liệu tự nhiên theo cách rất chuyên biệt",
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


def matchup_stat_lines(animal: dict) -> list[str]:
    return [
        f"Chiều cao: {animal['height']}",
        f"Trọng lượng: {animal['weight']}",
        f"Lực cắn: {animal['bite_force']}",
        f"Lợi thế: {animal['edge_vi']}",
    ]


def matchup_caption(topic: dict, content: dict) -> str:
    left = topic["left"]
    right = topic["right"]
    lines = [
        content["title"],
        "",
        content["caption_intro"].strip(),
        "",
        f"{left['name_vi']} ({left['name_en']})",
        f"- Chiều cao: {left['height']}",
        f"- Trọng lượng: {left['weight']}",
        f"- Lực cắn: {left['bite_force']}",
        f"- Lợi thế: {left['edge_vi']}",
        "",
        f"{right['name_vi']} ({right['name_en']})",
        f"- Chiều cao: {right['height']}",
        f"- Trọng lượng: {right['weight']}",
        f"- Lực cắn: {right['bite_force']}",
        f"- Lợi thế: {right['edge_vi']}",
        "",
        f"Kết luận: {topic['verdict_vi']}",
        topic["reality_note_vi"],
        topic["debate_question_vi"],
    ]
    return append_caption_hashtags(remove_ai_disclaimer("\n".join(lines)))


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

    if topic["topic_type"] == "matchup_versus":
        left = topic["left"]
        right = topic["right"]
        title = content.get("overlay_title") or topic["subject_vi"]
        left_text = "\n".join([left["name_vi"].upper(), *matchup_stat_lines(left)])
        right_text = "\n".join([right["name_vi"].upper(), *matchup_stat_lines(right)])
        return (
            f"{MATCHUP_IMAGE_TEMPLATE}\n\n"
            "Header text to render exactly:\n"
            f"{title.upper()}\n\n"
            "Left side visible text lines to render exactly:\n"
            f"{left_text}\n\n"
            "Right side visible text lines to render exactly:\n"
            f"{right_text}\n\n"
            "Bottom note text to render exactly:\n"
            "Số liệu ước tính, có thể thay đổi theo cá thể\n\n"
            "Strict text rules:\n"
            "- Render Vietnamese diacritics correctly.\n"
            "- Use the exact text strings above, no extra words, no English labels, no fake text.\n"
            "- Keep labels and values readable; reduce font size or split into two lines if needed.\n"
            "- Never crop, truncate, overlap, or replace the listed text.\n"
            "- Do not add watermark, logo, captions, brand text, random symbols, blood, or injury.\n\n"
            "Visual direction:\n"
            f"- Left animal: realistic {left['name_en']}, dignified, alert, no aggression impact.\n"
            f"- Right animal: realistic {right['name_en']}, powerful, alert, no aggression impact.\n"
            "- Create tension through posture, lighting, scale, and composition, not violence.\n\n"
            "Additional photo/style guidance from the text model, use only if it does not conflict with exact text rules:\n"
            f"{image_prompt}"
        )

    title = content.get("overlay_title") or topic["subject_vi"]
    stat = content.get("overlay_stat") or topic.get("fact_value", "")
    hook = content.get("overlay_hook") or ""
    visual_detail = topic.get("detail_vi") or topic.get("fact_detail", "")
    scene_prompt = clean_single_scene_prompt(content.get("image_prompt", ""))
    return (
        f"{SINGLE_CARD_IMAGE_TEMPLATE}\n\n"
        "ABSOLUTE SINGLE-CARD RULES:\n"
        "- This poster has ONE subject and ONE scene only.\n"
        "- Do NOT create rows, stacked panels, numbered sections, step lists, comparison blocks, ranking blocks, or repeated animal thumbnails.\n"
        "- Do NOT render any number used as a rank: 01, 02, 03, 04, 05, 1, 2, 3, 4, 5.\n"
        "- Do NOT render explanatory body text or sentences.\n"
        "- Do NOT render placeholder words such as Stat, data, label, thông tin, mô tả, lorem ipsum, UI text, or fake text.\n"
        "- Do NOT add watermark, logo, captions, brand text, random symbols, or extra subtitles.\n"
        "- Count the visible text groups: exactly 3 groups total. If anything else would appear as text, remove it.\n"
        "- If text cannot fit, reduce font size; never invent or paraphrase additional text.\n\n"
        "Render exactly these 3 visible text strings, and no other text anywhere:\n"
        f"\"{title.upper()}\"\n"
        f"\"{stat.upper()}\"\n"
        f"\"{hook}\"\n\n"
        "Recommended composition:\n"
        "- Top: the headline as one large readable Vietnamese line or two lines.\n"
        "- Center: one large realistic hero subject occupying most of the image.\n"
        "- Lower area: one copper/orange fact badge containing only the main fact text, plus one short hook line.\n"
        "- Keep generous margins and make Vietnamese diacritics accurate.\n\n"
        f"Hero image: realistic {topic['subject_en']} in its natural habitat, cinematic, sharp, dramatic, visually striking.\n"
        f"Visual fact to suggest without rendering as extra text: {visual_detail}\n"
        f"{'Scene/photo guidance only: ' + scene_prompt if scene_prompt else ''}"
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
        content = normalize_single_card_content(topic, generate_single_card_content(topic))
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

    if topic["topic_type"] == "matchup_versus":
        content = generate_matchup_content(topic)
        image_prompt = build_model_rendered_infographic_prompt(content["image_prompt"], topic, content)
        caption = matchup_caption(topic, content)
        return {
            "scheduled_at": scheduled_at,
            "slot": slot,
            "topic_type": topic["topic_type"],
            "topic_key": topic["topic_key"],
            "title": content["title"],
            "overlay_title": content["overlay_title"],
            "overlay_subtitle": None,
            "overlay_stat": None,
            "overlay_hook": None,
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

    if post_data["topic_type"] == "matchup_versus":
        return post_data["final_image_path"]

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
