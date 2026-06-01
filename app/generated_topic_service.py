import json
import unicodedata
from copy import deepcopy

from app.config import AUTO_GENERATE_TOPICS, GENERATED_TOPICS_PATH
from app.deepseek_service import generate_json
from app.utils import slugify


ALLOWED_COMPARISON_ANGLES = {
    "speed",
    "height",
    "weight",
    "size",
    "special ability",
    "bite force",
    "lifespan",
    "venom",
    "toxicity",
    "camouflage",
    "bioluminescence",
    "building ability",
    "survival",
    "parenting",
}


def load_generated_topics() -> list[dict]:
    if not GENERATED_TOPICS_PATH.exists():
        return []

    topics = []
    for line in GENERATED_TOPICS_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        topics.append(normalize_cached_topic(json.loads(line)))
    return topics


def normalize_cached_topic(topic: dict) -> dict:
    if topic.get("topic_type") == "single_card" and not topic.get("detail_vi"):
        topic["detail_vi"] = topic.get("fact_detail", "")
    return topic


def save_generated_topic(topic: dict):
    GENERATED_TOPICS_PATH.parent.mkdir(parents=True, exist_ok=True)
    with GENERATED_TOPICS_PATH.open("a", encoding="utf-8") as file:
        file.write(json.dumps(topic, ensure_ascii=False) + "\n")


def generated_topics_by_type(topic_type: str) -> list[dict]:
    return [topic for topic in load_generated_topics() if topic.get("topic_type") == topic_type]


def get_generated_topic(topic_type: str, index: int, existing_topics: list[dict]) -> dict:
    topics = generated_topics_by_type(topic_type)
    while len(topics) <= index:
        if not AUTO_GENERATE_TOPICS:
            raise RuntimeError(
                "Topic bank exhausted and ANIMAL_AGENT_AUTO_GENERATE_TOPICS is disabled."
            )
        topic = generate_topic(topic_type, existing_topics + topics)
        save_generated_topic(topic)
        topics.append(topic)
    return deepcopy(topics[index])


def generate_topic(topic_type: str, existing_topics: list[dict]) -> dict:
    existing_summary = "\n".join(
        f"- {topic.get('topic_key')}: {topic.get('subject_vi') or topic.get('subject_en')}"
        for topic in existing_topics[-80:]
    )

    if topic_type == "comparison_top5":
        prompt = f"""
Bạn là biên tập viên nội dung Facebook về thế giới động vật và thực vật.

Hãy sinh 1 topic mới dạng Top 5, dễ viral, dễ gây bình luận, thú vị nhưng không sai sự thật.
Không được trùng hoặc quá giống các topic đã có:
{existing_summary}

Chỉ trả về JSON hợp lệ với schema:
{{
  "topic_type": "comparison_top5",
  "topic_key": "snake_case_english_unique_key",
  "subject_vi": "Top 5 ...",
  "subject_en": "Top 5 ...",
  "comparison_angle": "one of allowed values",
  "items": [
    {{
      "rank": 1,
      "name_vi": "Tên Tiếng Việt Viết Hoa Chữ Cái Đầu",
      "name_en": "English common name",
      "stat": "metric/value very short",
      "detail_vi": "giải thích ngắn bằng tiếng Việt, tối đa 14 từ"
    }}
  ]
}}

Allowed comparison_angle values:
{", ".join(sorted(ALLOWED_COMPARISON_ANGLES))}

Yêu cầu bắt buộc:
- Đúng 5 items, rank từ 1 đến 5.
- name_vi dùng tiếng Việt dễ hiểu, viết hoa chữ cái đầu mỗi từ.
- stat phải ngắn, dễ đọc trên ảnh, không quá 18 ký tự nếu có thể.
- detail_vi làm rõ stat nghĩa là gì, không quá 14 từ.
- Ưu tiên chủ đề thật sự hấp dẫn: kỷ lục lạ, khả năng sinh tồn, vũ khí tự nhiên, chiến thuật săn mồi, thực vật kỳ dị, hành vi khiến người xem muốn comment.
- Không bịa số liệu chính xác nếu không chắc; có thể dùng mô tả định tính ngắn như "Siêu độc", "Tái sinh", "Bẫy dính".
- Không dùng lại chủ đề cũ.
"""
    elif topic_type == "single_card":
        prompt = f"""
Bạn là biên tập viên nội dung Facebook về thế giới động vật và thực vật.

Hãy sinh 1 topic single-card mới, dễ viral, lạ, thú vị và có khả năng kéo bình luận.
Không được trùng hoặc quá giống các topic đã có:
{existing_summary}

Chỉ trả về JSON hợp lệ với schema:
{{
  "topic_type": "single_card",
  "topic_key": "snake_case_english_unique_key_card",
  "subject_vi": "Tên Tiếng Việt Viết Hoa Chữ Cái Đầu",
  "subject_en": "English common name",
  "fact_label": "short english label",
  "fact_value": "giá trị cực ngắn",
  "fact_detail": "English factual detail, one sentence",
  "detail_vi": "giải thích ngắn bằng tiếng Việt, tối đa 16 từ"
}}

Yêu cầu bắt buộc:
- subject nên là động vật hoặc thực vật rất thú vị, ít nhàm chán.
- fact_value tối đa 18 ký tự nếu có thể.
- fact_detail phải thật, dễ hiểu, không giật gân sai sự thật.
- detail_vi giải thích cụ thể fact_value nghĩa là gì, dùng tiếng Việt tự nhiên.
- Không dùng lại chủ đề cũ.
"""
    elif topic_type == "matchup_versus":
        prompt = f"""
Bạn là biên tập viên nội dung Facebook về thế giới động vật theo hướng khoa học, dễ viral.

Hãy sinh 1 topic mới dạng đối đầu giả định 1-vs-1 giữa hai loài động vật, thú vị, gây tranh luận, nhưng không cổ vũ bạo lực thật.
Không được trùng hoặc quá giống các topic đã có:
{existing_summary}

Chỉ trả về JSON hợp lệ với schema:
{{
  "topic_type": "matchup_versus",
  "topic_key": "animal_a_vs_animal_b",
  "subject_vi": "Loài A đối đầu Loài B",
  "subject_en": "Animal A versus Animal B",
  "left": {{
    "name_vi": "Tên Tiếng Việt",
    "name_en": "English common name",
    "height": "short value",
    "weight": "short value",
    "bite_force": "short value or key weapon",
    "edge_vi": "lợi thế ngắn bằng tiếng Việt"
  }},
  "right": {{
    "name_vi": "Tên Tiếng Việt",
    "name_en": "English common name",
    "height": "short value",
    "weight": "short value",
    "bite_force": "short value or key weapon",
    "edge_vi": "lợi thế ngắn bằng tiếng Việt"
  }},
  "verdict_vi": "kết luận ngắn dựa trên số liệu",
  "reality_note_vi": "lưu ý đây là so sánh giả định, không cổ vũ đối đầu thật",
  "debate_question_vi": "câu hỏi kéo bình luận"
}}

Yêu cầu bắt buộc:
- Chọn hai loài có độ tương phản thú vị để người xem muốn tranh luận.
- Không dùng chủ đề chó ngao Tây Tạng vs hổ Bengal nếu đã có.
- Các value trên ảnh phải ngắn, dễ đọc.
- Nếu số liệu chỉ là ước tính phổ biến, viết theo dạng ngắn như "70 kg", "900 PSI", "Nọc độc".
- Không mô tả máu me, thương tích hoặc cổ vũ cho động vật đánh nhau thật.
"""
    else:
        raise ValueError(f"Unsupported generated topic_type: {topic_type}")

    rejected_candidates = []
    for attempt in range(4):
        retry_note = build_retry_note(rejected_candidates)
        candidate = validate_generated_topic(
            generate_json(
                f"{prompt}\n{retry_note}",
                system="Bạn chỉ trả về JSON hợp lệ, không markdown, không giải thích.",
            ),
            topic_type,
            existing_topics,
        )
        duplicate_reason = find_duplicate_reason(candidate, existing_topics)
        if not duplicate_reason:
            return candidate
        rejected_candidates.append(f"{candidate.get('topic_key')}: {duplicate_reason}")

    raise RuntimeError(
        "Could not generate a sufficiently unique topic after retries. "
        f"Rejected: {'; '.join(rejected_candidates)}"
    )


def build_retry_note(rejected_candidates: list[str]) -> str:
    if not rejected_candidates:
        return ""
    rejected_text = "\n".join(f"- {candidate}" for candidate in rejected_candidates)
    return f"""
Các topic sau đã bị hệ thống loại vì quá giống topic cũ. KHÔNG lặp lại ý tưởng này:
{rejected_text}

Hãy chọn một hướng hoàn toàn khác: khác nhóm loài chính, khác năng lực/kỷ lục, khác góc tranh luận.
"""


def normalize_for_similarity(text: str) -> str:
    text = text.lower().replace("đ", "d")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    return "".join(char if char.isalnum() else " " for char in text)


def token_set(text: str) -> set[str]:
    stopwords = {
        "top",
        "5",
        "loai",
        "dong",
        "vat",
        "con",
        "cay",
        "sinh",
        "the",
        "gioi",
        "nhat",
        "doi",
        "dau",
        "versus",
        "vs",
        "animal",
        "animals",
        "plant",
        "plants",
        "in",
        "the",
        "and",
        "with",
    }
    return {token for token in normalize_for_similarity(text).split() if len(token) > 2 and token not in stopwords}


def normalized_key(text: str) -> str:
    return " ".join(normalize_for_similarity(text).split())


def topic_text(topic: dict) -> str:
    parts = [
        topic.get("topic_type", ""),
        topic.get("topic_key", ""),
        topic.get("subject_vi", ""),
        topic.get("subject_en", ""),
        topic.get("comparison_angle", ""),
        topic.get("fact_label", ""),
        topic.get("fact_value", ""),
        topic.get("fact_detail", ""),
        topic.get("detail_vi", ""),
    ]
    for item in topic.get("items", []):
        parts.extend(
            [
                item.get("name_vi", ""),
                item.get("name_en", ""),
                item.get("stat", ""),
                item.get("detail_vi", ""),
            ]
        )
    for side in ("left", "right"):
        animal = topic.get(side, {})
        if isinstance(animal, dict):
            parts.extend([animal.get("name_vi", ""), animal.get("name_en", ""), animal.get("edge_vi", "")])
    return " ".join(parts)


def comparison_entities(topic: dict) -> list[set[str]]:
    entities = []
    for item in topic.get("items", []):
        entity_names = set()
        for key in ("name_vi", "name_en"):
            value = normalized_key(item.get(key, ""))
            if value:
                entity_names.add(value)
        if entity_names:
            entities.append(entity_names)
    return entities


def comparison_entity_overlap(candidate: dict, existing: dict) -> int:
    existing_entities = comparison_entities(existing)
    overlap = 0
    for candidate_entity in comparison_entities(candidate):
        if any(candidate_entity & existing_entity for existing_entity in existing_entities):
            overlap += 1
    return overlap


def single_subject_tokens(topic: dict) -> set[str]:
    return token_set(f"{topic.get('subject_vi', '')} {topic.get('subject_en', '')}")


def matchup_pair_tokens(topic: dict) -> set[str]:
    names = set()
    for side in ("left", "right"):
        animal = topic.get(side, {})
        if isinstance(animal, dict):
            for key in ("name_vi", "name_en"):
                value = normalized_key(animal.get(key, ""))
                if value:
                    names.add(value)
    return names


def jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def find_duplicate_reason(candidate: dict, existing_topics: list[dict]) -> str | None:
    for existing in existing_topics:
        if candidate.get("topic_key") == existing.get("topic_key"):
            return f"trùng topic_key với {existing.get('topic_key')}"
        if candidate.get("topic_type") != existing.get("topic_type"):
            continue

        if candidate["topic_type"] == "comparison_top5":
            item_overlap = comparison_entity_overlap(candidate, existing)
            candidate_subject = token_set(candidate.get("subject_vi", "") + " " + candidate.get("subject_en", ""))
            existing_subject = token_set(existing.get("subject_vi", "") + " " + existing.get("subject_en", ""))
            subject_similarity = jaccard(candidate_subject, existing_subject)
            same_angle = candidate.get("comparison_angle") == existing.get("comparison_angle")
            if item_overlap >= 3:
                return f"trùng nhiều loài với {existing.get('topic_key')}"
            if same_angle and (item_overlap >= 2 or subject_similarity >= 0.35):
                return f"cùng góc nội dung và quá gần {existing.get('topic_key')}"

        elif candidate["topic_type"] == "single_card":
            subject_similarity = jaccard(single_subject_tokens(candidate), single_subject_tokens(existing))
            content_similarity = jaccard(token_set(topic_text(candidate)), token_set(topic_text(existing)))
            if subject_similarity >= 0.5:
                return f"trùng/giống chủ thể với {existing.get('topic_key')}"
            if content_similarity >= 0.45:
                return f"nội dung single-card quá giống {existing.get('topic_key')}"

        elif candidate["topic_type"] == "matchup_versus":
            pair_overlap = len(matchup_pair_tokens(candidate) & matchup_pair_tokens(existing))
            content_similarity = jaccard(token_set(topic_text(candidate)), token_set(topic_text(existing)))
            if pair_overlap >= 2:
                return f"trùng loài trong kèo đối đầu với {existing.get('topic_key')}"
            if content_similarity >= 0.45:
                return f"kèo đối đầu quá giống {existing.get('topic_key')}"

    return None


def validate_generated_topic(topic: dict, expected_type: str, existing_topics: list[dict]) -> dict:
    if topic.get("topic_type") != expected_type:
        raise ValueError(f"Generated topic_type mismatch: {topic.get('topic_type')}")

    existing_keys = {topic.get("topic_key") for topic in existing_topics}
    topic_key = slugify(topic.get("topic_key", ""))
    if not topic_key:
        topic_key = slugify(topic.get("subject_en") or topic.get("subject_vi") or expected_type)
    base_topic_key = topic_key
    suffix = 2
    while topic_key in existing_keys:
        topic_key = f"{base_topic_key}_ai_{suffix}"
        suffix += 1
    topic["topic_key"] = topic_key

    if expected_type == "comparison_top5":
        if topic.get("comparison_angle") not in ALLOWED_COMPARISON_ANGLES:
            topic["comparison_angle"] = "special ability"
        items = topic.get("items")
        if not isinstance(items, list) or len(items) != 5:
            raise ValueError("Generated comparison topic must contain exactly 5 items.")
        for index, item in enumerate(items, start=1):
            item["rank"] = index
            for key in ("name_vi", "name_en", "stat", "detail_vi"):
                value = str(item.get(key, "")).strip()
                if not value:
                    raise ValueError(f"Generated comparison item missing {key}.")
                item[key] = value
        for key in ("subject_vi", "subject_en"):
            if not str(topic.get(key, "")).strip():
                raise ValueError(f"Generated comparison topic missing {key}.")
    elif expected_type == "single_card":
        for key in ("subject_vi", "subject_en", "fact_label", "fact_value", "fact_detail"):
            value = str(topic.get(key, "")).strip()
            if not value:
                raise ValueError(f"Generated single topic missing {key}.")
            topic[key] = value
        topic["detail_vi"] = str(topic.get("detail_vi") or topic["fact_detail"]).strip()
    else:
        for key in ("subject_vi", "subject_en", "verdict_vi", "reality_note_vi", "debate_question_vi"):
            value = str(topic.get(key, "")).strip()
            if not value:
                raise ValueError(f"Generated matchup topic missing {key}.")
            topic[key] = value
        for side in ("left", "right"):
            animal = topic.get(side)
            if not isinstance(animal, dict):
                raise ValueError(f"Generated matchup topic missing {side}.")
            for key in ("name_vi", "name_en", "height", "weight", "bite_force", "edge_vi"):
                value = str(animal.get(key, "")).strip()
                if not value:
                    raise ValueError(f"Generated matchup {side} missing {key}.")
                animal[key] = value

    return topic
