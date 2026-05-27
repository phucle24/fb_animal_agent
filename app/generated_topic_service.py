import json
from copy import deepcopy

from app.config import AUTO_GENERATE_TOPICS, GENERATED_TOPICS_PATH, GEMINI_TEXT_MODEL
from app.text_service import _client_and_types, _ensure_api_key
from app.utils import safe_json_loads, slugify


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
    _ensure_api_key()
    client, types = _client_and_types()

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
    else:
        raise ValueError(f"Unsupported generated topic_type: {topic_type}")

    response = client.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )
    return validate_generated_topic(safe_json_loads(response.text), topic_type, existing_topics)


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
    else:
        for key in ("subject_vi", "subject_en", "fact_label", "fact_value", "fact_detail"):
            value = str(topic.get(key, "")).strip()
            if not value:
                raise ValueError(f"Generated single topic missing {key}.")
            topic[key] = value
        topic["detail_vi"] = str(topic.get("detail_vi") or topic["fact_detail"]).strip()

    return topic
