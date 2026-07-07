import json
import re

from app.config import FINAL_DIR, RAW_DIR
from app.db import insert_post
from app.image_service import generate_image
from app.overlay_service import overlay_comparison_top5, overlay_single_card
from app.text_service import (
    generate_anatomy_content,
    generate_comparison_content,
    generate_engagement_format_content,
    generate_matchup_content,
    generate_single_card_content,
)
from app.utils import matchup_measure_label, matchup_measure_value, slugify, vietnamize_common_terms


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
- every panel should feel like a tiny visual story, showing the animal/plant doing the behavior or revealing the survival trick behind the data
- vertical 4:5 layout with enough height for a header and five stacked panels, all text readable without cropping
- no Python overlay will be used later; all text must be rendered by the image model now
""".strip()

SINGLE_CARD_IMAGE_TEMPLATE = """
FINAL INFOGRAPHIC MUST CONTAIN THE EXACT TEXT BELOW.
Create a finished vertical 4:5 Vietnamese single-subject fact poster for Facebook feed:
- exactly one dramatic photorealistic animal or plant hero image, large and unmistakable
- the hero image must tell a mini-story: the subject is doing something, hiding from something, hunting, defending, transforming, glowing, or revealing the biological trick
- premium dark charcoal editorial poster style with copper/orange accents
- exactly three visible text groups total: headline, main metric, micro-fact hook
- clean single-card layout with open space, not a ranking, not a comparison, not a list
- the main metric and micro-fact hook are the clickable information core; make them visually prominent
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
- make it feel like a scientific story of two different survival strategies, not a static ID card
- data cards under each animal with concise measurements
- no gore, no blood, no injury, no violent impact
- no Python overlay will be used later; all text must be rendered by the image model now
""".strip()

ENGAGEMENT_IMAGE_TEMPLATE = """
FINAL INFOGRAPHIC MUST CONTAIN THE EXACT TEXT BELOW.
Create a finished vertical 4:5 Vietnamese social poster for Facebook feed:
- premium dark charcoal editorial style with copper/orange accents
- one dramatic photorealistic animal/plant/nature hero image
- the image must create curiosity like a story frame: a hidden danger, surprising behavior, transformation, camouflage, scale reveal, or visual twist
- bold condensed Vietnamese typography, clean and highly readable
- exactly three visible text groups total: title, primary hook, secondary hook
- no extra paragraphs, no random labels, no fake UI text
- no Python overlay will be used later; all text must be rendered by the image model now
""".strip()

ANATOMY_IMAGE_TEMPLATE = """
FINAL INFOGRAPHIC MUST CONTAIN THE EXACT TEXT BELOW.
Create an ultra-realistic educational anatomy infographic, vertical portrait 4:5 layout, scientific illustration style mixed with high-end macro photography.
- one large realistic subject in clean side view, occupying about 75-85% of the canvas
- macro close-up, biology laboratory specimen photography mood, extremely sharp focus
- the body should remain natural and realistic, with a semi-transparent cutaway only where needed so important internal anatomy can be seen
- preserve real external texture: eyes, skin/shell/exoskeleton, hairs/scales/veins/segments/legs/fins/wings when relevant
- minimal laboratory-style background: soft light gray or pale blue gradient, no texture, no decoration, no landscape
- no flowers, plants, hive, honeycomb, food styling, plate, hands, tools, or environmental scene unless explicitly required by the subject
- only a soft studio shadow beneath the subject if needed
- leave sufficient clean white space around the subject for educational labels
- use thin black leader lines pointing precisely to each anatomical structure
- Vietnamese labels inside small rounded white rectangles with subtle shadow
- modern sans-serif font, black text, consistent spacing, crisp and readable on mobile
- labels must be neat, balanced around the subject, and must never overlap
- every pointer line must end exactly at the anatomical structure
- no decorative title, no logo, no watermark, no signature, no brand name, no page name, no icon, no mascot, no border
- no Python overlay will be used later; all text must be rendered by the image model now
""".strip()

TEXT_DEDUP_RULES = """
Global text safety rules:
- Render each requested text string exactly once.
- Never duplicate a headline as a second header, background word, watermark, badge, shadow caption, footer, or decorative echo.
- Never repeat the same words in another location just to balance the layout.
- Never add extra labels, subtitles, explanations, UI text, fake text, lorem ipsum, brand text, or watermark.
- If the poster feels empty, use image composition, lighting, borders, shapes, arrows, empty space, texture, or visual contrast instead of extra text.
- Final self-check before output: count visible text groups and remove every duplicate or unrequested text element.
""".strip()

ENGAGEMENT_TOPIC_TYPES = {"myth_vs_fact", "guess_quiz", "one_story", "before_after"}
MODEL_RENDERED_TOPIC_TYPES = {
    "anatomy_infographic",
    "comparison_top5",
    "single_card",
    "matchup_versus",
    *ENGAGEMENT_TOPIC_TYPES,
}

CAPTION_HASHTAGS = "#thegioimuonloai #topdongbat #reivewthegioidongvat #khamphatunhien #thegioidongvat #thucvatdongvat"
MODEL_RENDERED_TEXT_MARKER = "FINAL INFOGRAPHIC MUST CONTAIN THE EXACT TEXT BELOW."
AI_DISCLAIMERS = (
    "Ảnh minh họa AI.",
    "Ảnh minh hoạ AI.",
    "Ảnh AI minh họa.",
    "Ảnh AI minh hoạ.",
    "AI illustration.",
)
DRY_CAPTION_OPENERS = (
    r"^\s*Bạn\s+có\s+biết\s+rằng\s*[,:\-–—]?\s*",
    r"^\s*Bạn\s+có\s+biết\s*[,:\-–—]?\s*",
    r"^\s*Trong\s+thế\s+giới\s+động\s+vật\s*[,:\-–—]?\s*",
    r"^\s*Trong\s+thế\s+giới\s+tự\s+nhiên\s*[,:\-–—]?\s*",
    r"^\s*Thiên\s+nhiên\s+luôn\s+ẩn\s+chứa\s+những\s+điều\s+kỳ\s+diệu\s*[,.\-–—]?\s*",
    r"^\s*Thiên\s+nhiên\s+luôn\s*[,:\-–—]?\s*",
)
CAPTION_CLICHE_REPLACEMENTS = (
    ("là một khả năng đặc biệt", "là một chi tiết"),
    ("Là một khả năng đặc biệt", "Là một chi tiết"),
    ("một khả năng này", "một chi tiết"),
    ("Một khả năng này", "Một chi tiết"),
    ("đặc điểm thú vị", "chi tiết này"),
    ("Đặc điểm thú vị", "Chi tiết này"),
    ("khả năng đặc biệt", "khả năng này"),
    ("Khả năng đặc biệt", "Khả năng này"),
    ("rất thú vị", "đáng chú ý"),
    ("Rất thú vị", "Đáng chú ý"),
    ("đặc điểm nổi bật giúp nó săn mồi, sinh tồn hoặc tự vệ", "chi tiết sinh học gắn với cách nó sống sót"),
    ("Đặc điểm nổi bật giúp nó săn mồi, sinh tồn hoặc tự vệ", "Chi tiết sinh học gắn với cách nó sống sót"),
    (
        "chiến lược sinh tồn giúp nó chịu được điều kiện khắc nghiệt",
        "cách sinh tồn riêng giúp nó vượt qua môi trường khắc nghiệt",
    ),
    (
        "Chiến lược sinh tồn giúp nó chịu được điều kiện khắc nghiệt",
        "Cách sinh tồn riêng giúp nó vượt qua môi trường khắc nghiệt",
    ),
    ("vô cùng", "rất"),
    ("Vô cùng", "Rất"),
    ("khiến ai cũng", "dễ khiến người xem"),
    ("Khiến ai cũng", "Dễ khiến người xem"),
    ("thiên nhiên kỳ diệu", "tự nhiên"),
    ("Thiên nhiên kỳ diệu", "Tự nhiên"),
)
GENERATED_CAPTION_MAX_WORDS = 180
GENERIC_ENGAGEMENT_TITLES = {
    "LỜI ĐỒN HAY SỰ THẬT?",
    "LỜI ĐỒN HAY SỰ THẬT",
    "SỰ THẬT THÚ VỊ",
    "BẠN CÓ BIẾT?",
    "BẠN CÓ BIẾT",
}
ENGAGEMENT_TEXT_LABELS = (
    "LỜI ĐỒN:",
    "LỜI ĐỒN",
    "SỰ THẬT:",
    "SỰ THẬT",
    "THÔNG TIN:",
    "THÔNG TIN",
    "FACT:",
    "MYTH:",
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


def capitalize_first_letter(text: str) -> str:
    for index, char in enumerate(text):
        if char.isalpha():
            return text[:index] + char.upper() + text[index + 1 :]
    return text


def strip_generated_hashtags(text: str) -> str:
    return re.sub(r"(?:^|\s)#\S+", "", text).strip()


def normalize_caption_opening(text: str) -> str:
    cleaned = text.strip()
    for pattern in DRY_CAPTION_OPENERS:
        next_cleaned = re.sub(pattern, "", cleaned, count=1, flags=re.IGNORECASE).lstrip(" ,.:;-–—")
        if next_cleaned != cleaned:
            return capitalize_first_letter(next_cleaned.strip())
    return cleaned


def replace_caption_cliches(text: str) -> str:
    cleaned = text
    for _ in range(2):
        for source, target in CAPTION_CLICHE_REPLACEMENTS:
            cleaned = cleaned.replace(source, target)
    return cleaned


def soft_trim_caption_text(text: str, max_words: int = GENERATED_CAPTION_MAX_WORDS) -> str:
    words = text.split()
    if len(words) <= max_words:
        return text

    sentences = re.split(r"(?<=[.!?…])\s+", text)
    kept: list[str] = []
    kept_words = 0
    for sentence in sentences:
        sentence_words = sentence.split()
        if not sentence_words:
            continue
        if kept and kept_words + len(sentence_words) > max_words:
            break
        kept.append(sentence.strip())
        kept_words += len(sentence_words)

    if kept:
        return " ".join(kept).strip()
    return " ".join(words[:max_words]).rstrip(" ,;:") + "…"


def normalize_generated_caption_text(text: str) -> str:
    cleaned = remove_ai_disclaimer(text)
    cleaned = strip_generated_hashtags(cleaned)
    cleaned = vietnamize_common_terms(cleaned)
    cleaned = "\n".join(" ".join(line.split()) for line in cleaned.splitlines()).strip()
    cleaned = normalize_caption_opening(cleaned)
    cleaned = replace_caption_cliches(cleaned)
    cleaned = soft_trim_caption_text(cleaned)
    return cleaned.strip()


def finalize_caption(caption: str) -> str:
    cleaned = remove_ai_disclaimer(caption)
    cleaned = vietnamize_common_terms(cleaned)
    cleaned = replace_caption_cliches(cleaned)
    cleaned = "\n".join(line.rstrip() for line in cleaned.splitlines()).strip()
    return append_caption_hashtags(cleaned)


def strip_engagement_label(text: str) -> str:
    cleaned = " ".join((text or "").split()).strip()
    upper = cleaned.upper()
    for label in ENGAGEMENT_TEXT_LABELS:
        if upper.startswith(label):
            return cleaned[len(label) :].strip(" :-–—")
    return cleaned


def text_signature(text: str, words: int = 4) -> str:
    normalized = " ".join((text or "").lower().split())
    return " ".join(normalized.split()[:words])


def myth_title_fallback(topic: dict) -> str:
    combined = " ".join(
        [
            topic.get("subject_vi", ""),
            topic.get("hook_vi", ""),
            topic.get("main_fact_vi", ""),
            topic.get("twist_vi", ""),
        ]
    ).lower()
    if any(word in combined for word in ("cute", "dễ thương")) and any(
        word in combined for word in ("ngụy trang", "tàng hình", "lẫn vào", "trốn")
    ):
        return "CUTE ĐỂ TÀNG HÌNH?"
    if any(word in combined for word in ("ngụy trang", "tàng hình", "lẫn vào", "trốn")):
        return "BẬC THẦY TÀNG HÌNH?"
    if any(word in combined for word in ("phát sáng", "ánh sáng", "glow")):
        return "SÁNG LÊN ĐỂ LÀM GÌ?"
    if any(word in combined for word in ("trong suốt", "xuyên thấu")):
        return "TÀNG HÌNH THẬT À?"
    return compact_text(topic["subject_vi"], 32)


def normalize_engagement_content(topic: dict, content: dict) -> dict:
    normalized = dict(content)
    topic_type = topic.get("topic_type")

    normalized["overlay_title"] = compact_text(str(normalized.get("overlay_title") or topic["subject_vi"]), 32)
    normalized["overlay_primary"] = compact_text(str(normalized.get("overlay_primary") or topic["hook_vi"]), 52)
    normalized["overlay_secondary"] = compact_text(str(normalized.get("overlay_secondary") or topic["main_fact_vi"]), 58)

    if topic_type == "myth_vs_fact":
        title = normalized["overlay_title"].strip()
        primary = strip_engagement_label(normalized["overlay_primary"])
        secondary = strip_engagement_label(normalized["overlay_secondary"])

        if title.upper() in GENERIC_ENGAGEMENT_TITLES:
            title = myth_title_fallback(topic)

        primary_sig = text_signature(primary)
        secondary_sig = text_signature(secondary)
        if not primary or primary_sig == secondary_sig or primary.lower() in secondary.lower():
            primary = compact_text(topic["hook_vi"], 36)
        if not secondary or text_signature(primary) == text_signature(secondary) or secondary.lower() in primary.lower():
            secondary = compact_text(topic["main_fact_vi"], 42)

        normalized["overlay_title"] = compact_text(title, 32)
        normalized["overlay_primary"] = compact_text(primary, 36)
        normalized["overlay_secondary"] = compact_text(secondary, 42)

    return normalized


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

    if angle == "special ability":
        special_ability_details = [
            (("cảm điện", "cá mập", "shark"), "cảm nhận tín hiệu điện rất yếu từ cơ thể con mồi"),
            (("định vị âm", "dơi", "bat"), "phát sóng siêu âm rồi nghe tiếng vọng để bay trong tối"),
            (("cảm nhiệt", "hổ lục", "pit viper"), "hố cảm nhiệt giúp phát hiện con mồi máu nóng trong bóng tối"),
            (("mắt siêu xa", "đại bàng", "eagle"), "thị lực sắc bén giúp phát hiện con mồi từ khoảng cách xa"),
            (("khứu giác", "chó", "dog"), "mũi có hàng trăm triệu thụ thể mùi để lần theo dấu vết"),
            (("bẫy kẹp", "venus"), "khép lá cực nhanh khi lông cảm ứng bị chạm hai lần"),
            (("bẫy hố", "nắp ấm", "pitcher"), "dụ côn trùng trượt xuống bình chứa dịch tiêu hóa"),
            (("lá dính", "gọng vó", "sundew"), "giọt keo trên lá giữ con mồi rồi cuộn lại tiêu hóa"),
            (("bẫy hút", "bladderwort"), "túi bẫy hút sinh vật nhỏ trong nước chỉ trong chớp mắt"),
            (("lá nhớt", "butterwort"), "lá phủ chất nhầy giữ côn trùng nhỏ làm nguồn dinh dưỡng"),
            (("mùi xác", "corpse"), "tỏa mùi thịt thối để dụ ruồi và bọ đến thụ phấn"),
            (("hoa khổng lồ", "rafflesia"), "bông hoa ký sinh cực lớn, có thể rộng gần một mét"),
            (("nhựa đỏ", "máu rồng", "dragon blood"), "nhựa đỏ như máu chảy ra khi thân cây bị tổn thương"),
            (("cụp lá", "trinh nữ", "sensitive"), "lá cụp lại rất nhanh khi bị chạm hoặc rung động"),
            (("sống lâu", "welwitschia"), "hai lá lớn tiếp tục mọc trong điều kiện sa mạc khắc nghiệt"),
        ]
        lookup = f"{stat} {name_text}"
        for keywords, mapped_detail in special_ability_details:
            if any(keyword in lookup for keyword in keywords):
                return mapped_detail

    if angle == "survival":
        survival_details = [
            (("cực hạn", "gấu nước", "tardigrade"), "rút gần hết nước khỏi cơ thể rồi chuyển sang trạng thái ngủ"),
            (("bức xạ", "deinococcus"), "sửa chữa ADN bị phá hỏng sau liều bức xạ rất cao"),
            (("chịu khát", "lạc đà", "camel"), "giữ nước cực tốt và chịu mất nước cơ thể lâu hơn"),
            (("ngủ bùn", "cá phổi", "lungfish"), "vùi mình trong bùn khô và giảm trao đổi chất nhiều tháng"),
            (("băng giá", "cánh cụt", "penguin"), "tụ thành đàn giữ nhiệt qua mùa đông Nam Cực khắc nghiệt"),
        ]
        lookup = f"{stat} {name_text}"
        for keywords, mapped_detail in survival_details:
            if any(keyword in lookup for keyword in keywords):
                return mapped_detail

    fallback_details = {
        "speed": "mốc tốc độ nổi bật khi bứt tốc trong môi trường tự nhiên",
        "height": "chiều cao nổi bật giúp nó vượt trội trong nhóm này",
        "weight": "khối lượng lớn khiến nó trở thành một trong những loài nặng nhất",
        "size": "kích thước nổi bật so với phần lớn loài cùng nhóm",
        "special ability": "khả năng đặc biệt gắn với giác quan, vận động, phòng vệ hoặc kiếm ăn",
        "bite force": "lực cắn ước tính rất mạnh, đủ tạo lợi thế khi săn mồi hoặc phòng thủ",
        "lifespan": "tuổi thọ ấn tượng khiến các nhà nghiên cứu đặc biệt chú ý",
        "venom": "nọc độc tác động lên thần kinh, máu hoặc mô để săn mồi/tự vệ",
        "toxicity": "chứa hợp chất độc có thể ảnh hưởng nghiêm trọng đến cơ thể",
        "camouflage": "khả năng hòa vào môi trường khiến kẻ thù hoặc con mồi khó nhận ra",
        "bioluminescence": "ánh sáng sinh học giúp giao tiếp, dụ mồi hoặc tự vệ trong bóng tối",
        "building ability": "xây cấu trúc sống bằng vật liệu tự nhiên theo cách rất chuyên biệt",
        "survival": "giảm trao đổi chất, giữ nước/nhiệt hoặc sửa chữa cơ thể để sống sót",
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
    measure_label = matchup_measure_label(animal)
    measure_value = matchup_measure_value(animal)
    return [
        f"{measure_label}: {measure_value}",
        f"Trọng lượng: {animal['weight']}",
        f"Lực cắn: {animal['bite_force']}",
        f"Lợi thế: {animal['edge_vi']}",
    ]


def anatomy_label_rows(topic: dict) -> str:
    rows = []
    for index, part in enumerate(topic["labels"], start=1):
        rows.append(
            "\n".join(
                [
                    f"Label {index}:",
                    f"- Visible label text: {part['label_vi']}",
                    f"- Pointer target: {part['target_en']}",
                    f"- Anatomy guidance: {part['description_vi']}",
                ]
            )
        )
    return "\n".join(rows)


def build_anatomy_image_prompt(topic: dict, content: dict) -> str:
    scene_prompt = " ".join((content.get("image_prompt") or "").split()).strip()
    return (
        f"{ANATOMY_IMAGE_TEMPLATE}\n\n"
        "Main subject:\n"
        f"- Subject: one large realistic {topic['animal_en']} ({topic['animal_vi']}).\n"
        f"- Composition: {topic['composition_en']}.\n"
        f"- Transparency/anatomy: {topic['transparency_en']}.\n"
        f"- External appearance: {topic.get('appearance_en', 'preserve the natural appearance, real body texture, realistic proportions, and accurate visible anatomy')}.\n"
        f"- Internal organ colors: {topic.get('organ_colors_en', 'use subtle realistic biological colors; keep organs natural, not neon or cartoon-like')}.\n"
        f"- Background: {topic.get('background_en', 'simple light grey-blue background, clean and minimal')}.\n\n"
        "Vietnamese labels to render exactly, with pointer lines to the correct body part:\n"
        f"{anatomy_label_rows(topic)}\n\n"
        "Strict text rules:\n"
        "- Render Vietnamese diacritics correctly.\n"
        "- Render every visible label text exactly once.\n"
        "- Do not add a title, subtitle, corner text, logo, watermark, page name, brand name, icon, mascot, caption, or decorative text.\n"
        "- Do not translate, uppercase, paraphrase, duplicate, mirror, or restate any label.\n"
        "- Do not add fake labels, placeholder labels, random symbols, numbers, UI text, or lorem ipsum.\n"
        "- If label space is tight, reduce font size, move labels outward, or shorten pointer lines; never crop or overlap labels.\n"
        "- Pointer lines must be thin black lines and must connect to the correct body part.\n"
        "- Final self-check before output: visible text must be only the exact Vietnamese labels listed above.\n\n"
        "Negative prompt:\n"
        "logo, watermark, brand name, page name, text in the corner, decorative title, blurry text, misspelled Vietnamese, "
        "overlapping labels, messy lines, cartoon style, anime, 3D toy style, fantasy animal, exaggerated anatomy, duplicate limbs, "
        "duplicate wings, duplicate legs, extra organs, food photo, cooked animal, plate, chopsticks, sauce, flowers, plants, hive, honeycomb, "
        "beekeeper, kitchen background, landscape background, dark background, colorful background, excessive shadows, low resolution, "
        "cropped body, distorted body, distorted anatomy, wrong labels, cluttered composition\n\n"
        "Style:\n"
        "Ultra high resolution, scientific museum quality, biology textbook illustration, National Geographic style macro realism, "
        "accurate anatomy, clean layout, balanced typography, perfect readability, viewer-friendly, suitable for Facebook educational posts and science learning.\n\n"
        "Additional visual guidance from text model, use only if it does not conflict with exact label rules:\n"
        f"{scene_prompt}"
    )


def matchup_caption(topic: dict, content: dict) -> str:
    left = topic["left"]
    right = topic["right"]
    caption_intro = normalize_generated_caption_text(content["caption_intro"])
    lines = [
        vietnamize_common_terms(content["title"]),
        "",
        caption_intro,
        "",
        left["name_vi"],
        f"- {matchup_measure_label(left)}: {matchup_measure_value(left)}",
        f"- Trọng lượng: {vietnamize_common_terms(left['weight'])}",
        f"- Lực cắn: {vietnamize_common_terms(left['bite_force'])}",
        f"- Lợi thế: {vietnamize_common_terms(left['edge_vi'])}",
        "",
        right["name_vi"],
        f"- {matchup_measure_label(right)}: {matchup_measure_value(right)}",
        f"- Trọng lượng: {vietnamize_common_terms(right['weight'])}",
        f"- Lực cắn: {vietnamize_common_terms(right['bite_force'])}",
        f"- Lợi thế: {vietnamize_common_terms(right['edge_vi'])}",
        "",
        f"Kết luận: {vietnamize_common_terms(topic['verdict_vi'])}",
        vietnamize_common_terms(topic["reality_note_vi"]),
        vietnamize_common_terms(topic["debate_question_vi"]),
    ]
    return finalize_caption("\n".join(lines))


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
            f"{TEXT_DEDUP_RULES}\n"
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
            f"{TEXT_DEDUP_RULES}\n"
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
        "- Do NOT render long explanatory body text or full sentences beyond the exact hook string.\n"
        "- Do NOT render placeholder words such as Stat, data, label, thông tin, mô tả, lorem ipsum, UI text, or fake text.\n"
        "- Do NOT add watermark, logo, captions, brand text, random symbols, or extra subtitles.\n"
        f"{TEXT_DEDUP_RULES}\n"
        "- Count the visible text groups: exactly 3 groups total. If anything else would appear as text, remove it.\n"
        "- If text cannot fit, reduce font size; never invent or paraphrase additional text.\n\n"
        "Render exactly these 3 visible text strings, and no other text anywhere:\n"
        f"\"{title.upper()}\"\n"
        f"\"{stat.upper()}\"\n"
        f"\"{hook}\"\n\n"
        "Recommended composition:\n"
        "- Top: the headline as one large readable Vietnamese line or two lines.\n"
        "- Center: one dramatic realistic hero subject occupying most of the image, showing the unusual fact clearly.\n"
        "- Lower area: one oversized copper/orange fact badge containing only the main fact text.\n"
        "- Put the hook as a readable micro-fact line near the badge; it should explain why the metric matters, not feel like a generic slogan.\n"
        "- Keep generous margins and make Vietnamese diacritics accurate.\n\n"
        f"Hero image: realistic {topic['subject_en']} in its natural habitat, cinematic, sharp, dramatic, visually striking.\n"
        f"Visual fact to make obvious without rendering as extra text: {visual_detail}\n"
        "- Make the viewer immediately understand the scale, mechanism, behavior, or biological trick behind the fact.\n"
        f"{'Scene/photo guidance only: ' + scene_prompt if scene_prompt else ''}"
    )


def image_prompt_renders_final_text(image_prompt: str) -> bool:
    return MODEL_RENDERED_TEXT_MARKER in image_prompt


def build_comparison_caption(title: str, caption_intro: str, items: list, topic: dict | None = None) -> str:
    topic = topic or {}
    caption_intro = normalize_generated_caption_text(caption_intro)
    lines = [
        title,
        "",
        caption_intro.strip(),
        "",
    ]

    for item in items:
        lines.append(comparison_caption_line(item, topic))

    return finalize_caption("\n".join(lines))


def build_single_caption(title: str, caption: str) -> str:
    return finalize_caption(f"{title}\n\n{normalize_generated_caption_text(caption)}")


def build_engagement_caption(content: dict) -> str:
    return finalize_caption(f"{content['title']}\n\n{normalize_generated_caption_text(content['caption'])}")


def build_anatomy_caption(content: dict) -> str:
    return finalize_caption(f"{content['title']}\n\n{normalize_generated_caption_text(content['caption'])}")


def build_engagement_image_prompt(topic: dict, content: dict) -> str:
    title = compact_text(content.get("overlay_title") or topic["subject_vi"], 32).upper()
    primary = compact_text(content.get("overlay_primary") or topic["hook_vi"], 52)
    secondary = compact_text(content.get("overlay_secondary") or topic["main_fact_vi"], 58)
    visual_subject = topic.get("visual_subject_en") or topic["subject_en"]
    scene_prompt = " ".join((content.get("image_prompt") or "").split()).strip()
    if topic["topic_type"] == "myth_vs_fact":
        format_direction = (
            "- Use a visual twist composition: the subject looks cute at first glance, but the environment reveals the hidden survival function.\n"
            "- Show the story visually through camouflage, threat silhouette, habitat contrast, scale cue, or behavior; do not explain with extra text.\n"
            "- Do not render labels like LỜI ĐỒN, SỰ THẬT, FACT, MYTH unless they appear in the exact strings above.\n"
        )
    else:
        format_direction = ""
    return (
        f"{ENGAGEMENT_IMAGE_TEMPLATE}\n\n"
        "Render exactly these 3 visible text strings, and no other text anywhere:\n"
        f"\"{title}\"\n"
        f"\"{primary}\"\n"
        f"\"{secondary}\"\n\n"
        "Fixed text placement map:\n"
        "- TEXT GROUP 1 / TITLE: top area only, one copy, large bold headline.\n"
        "- TEXT GROUP 2 / PRIMARY HOOK: middle or lower-left callout only, one copy.\n"
        "- TEXT GROUP 3 / SECONDARY HOOK: bottom callout or badge only, one copy.\n"
        "- The hero image area must not contain any additional text, duplicated headline, small caption, label, or decorative word.\n\n"
        "Strict text repetition rules:\n"
        "- Each exact text string above may appear ONCE only.\n"
        "- Do not repeat, duplicate, mirror, paraphrase, translate, or restate any text string.\n"
        "- The title must appear only in TEXT GROUP 1 and nowhere else.\n"
        "- The primary hook must appear only in TEXT GROUP 2 and nowhere else.\n"
        "- The secondary hook must appear only in TEXT GROUP 3 and nowhere else.\n"
        "- Do not add category labels such as LỜI ĐỒN, SỰ THẬT, THÔNG TIN, FACT, MYTH, STAT, DATA.\n"
        f"{TEXT_DEDUP_RULES}\n"
        "- If the design needs visual balance, use shapes, shadows, image crops, arrows, or empty space instead of extra text.\n\n"
        "Format direction:\n"
        f"- Topic type: {topic['topic_type']}.\n"
        "- Make the primary and secondary hooks large enough to be readable on mobile.\n"
        "- Create a poster people want to tap: strong mystery, clear scale, unusual behavior, or visual twist.\n"
        "- Do not add watermark, logo, brand text, decorative random symbols, or extra captions.\n"
        "- If text cannot fit, reduce font size or split line breaks; never paraphrase or crop text.\n\n"
        f"{format_direction}"
        f"Hero visual subject: realistic {visual_subject}, cinematic, sharp, dramatic, visually striking.\n"
        "PRIVATE VISUAL GUIDANCE ONLY - DO NOT RENDER THIS GUIDANCE AS TEXT:\n"
        f"- Story hook for image planning only: {topic['hook_vi']}.\n"
        f"- Biological fact for image planning only: {topic['main_fact_vi']}.\n"
        f"- Visual twist for image planning only: {topic['twist_vi']}.\n"
        f"{'Scene/photo guidance only: ' + scene_prompt if scene_prompt else ''}"
    )


def build_post_payload(topic: dict, scheduled_at: str, slot: str) -> dict:
    base_name = slugify(f"{scheduled_at}_{slot}_{topic['topic_key']}")
    final_path = str(FINAL_DIR / f"{base_name}.jpg")

    if topic["topic_type"] == "anatomy_infographic":
        content = generate_anatomy_content(topic)
        image_prompt = build_anatomy_image_prompt(topic, content)
        caption = build_anatomy_caption(content)
        return {
            "scheduled_at": scheduled_at,
            "slot": slot,
            "topic_type": topic["topic_type"],
            "topic_key": topic["topic_key"],
            "title": content["title"],
            "overlay_title": None,
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
        content["title"] = vietnamize_common_terms(content["title"])
        content["caption_intro"] = vietnamize_common_terms(content["caption_intro"])
        content["overlay_title"] = vietnamize_common_terms(content["overlay_title"])
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

    if topic["topic_type"] in ENGAGEMENT_TOPIC_TYPES:
        content = normalize_engagement_content(topic, generate_engagement_format_content(topic))
        image_prompt = build_engagement_image_prompt(topic, content)
        caption = build_engagement_caption(content)
        return {
            "scheduled_at": scheduled_at,
            "slot": slot,
            "topic_type": topic["topic_type"],
            "topic_key": topic["topic_key"],
            "title": content["title"],
            "overlay_title": content["overlay_title"],
            "overlay_subtitle": content["overlay_primary"],
            "overlay_stat": content["overlay_secondary"],
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

    if post_data["topic_type"] in MODEL_RENDERED_TOPIC_TYPES:
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
