import json
import unicodedata
from copy import deepcopy

from app.config import AUTO_GENERATE_TOPICS, GENERATED_TOPICS_PATH
from app.deepseek_service import generate_json
from app.utils import matchup_measure_label, slugify, vietnamize_common_terms


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

ENGAGEMENT_TOPIC_TYPES = {"myth_vs_fact", "guess_quiz", "one_story", "before_after"}

ENGAGEMENT_TOPIC_GUIDES = {
    "myth_vs_fact": "Myth vs Fact: phá hiểu lầm phổ biến bằng sự thật bất ngờ, dễ khiến người xem bình luận 'hóa ra là vậy'.",
    "guess_quiz": "Guess / Quiz: đố viewer đoán loài hoặc hiện tượng trước khi đọc đáp án, ưu tiên hình ảnh bí ẩn.",
    "one_story": "One Story: kể một mẩu chuyện tự nhiên học ngắn, có hook, twist và chi tiết đáng nhớ.",
    "before_after": "Before / After: nhấn mạnh biến đổi trước-sau, vòng đời, lột xác, biến thái hoặc đổi trạng thái sinh tồn.",
}

STORY_TOPIC_RULES = """
Nguyên tắc chọn topic bắt buộc:
- Topic phải có "mầm câu chuyện": một cảnh nhỏ, mâu thuẫn, hiểu lầm, cú twist, hành vi lạ, hoặc khoảnh khắc khiến viewer muốn bấm vào ảnh.
- Ưu tiên các góc có thể kể như mini-story: tưởng vô hại nhưng nguy hiểm, nhìn dễ thương nhưng là chiến thuật sinh tồn, nhỏ bé nhưng có vũ khí, chậm chạp nhưng sống dai, cây đứng yên nhưng biết lừa.
- Tránh topic chỉ là danh sách khô hoặc fact rời rạc; mỗi topic phải gợi được câu hỏi "Ủa vì sao nó làm được vậy?".
- Nội dung phải vừa thật vừa có tính wow: có cơ chế, môi trường sống, kẻ săn mồi/con mồi, quy mô, hoặc lợi ích sinh tồn cụ thể.
- Giọng định hướng hóm hỉnh, duyên, dễ comment; không nhảm, không sai sự thật.
"""


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

    if topic_type == "anatomy_infographic":
        prompt = f"""
Bạn là biên tập viên nội dung Facebook về sinh học động vật, chuyên tạo topic infographic giải phẫu sạch, dễ hiểu, có giá trị giáo dục và hình ảnh đẹp.

Hãy sinh 1 topic mới dạng anatomy infographic, thay thế cho format Top 5.
Không được trùng hoặc quá giống các topic đã có:
{existing_summary}

Chỉ trả về JSON hợp lệ với schema:
{{
  "topic_type": "anatomy_infographic",
  "topic_key": "snake_case_english_unique_key",
  "subject_vi": "Giải phẫu ...",
  "subject_en": "English anatomy infographic subject",
  "animal_vi": "tên con vật tiếng Việt",
  "animal_en": "English common name",
  "hook_vi": "hook cụ thể, khiến viewer muốn zoom vào ảnh",
  "main_fact_vi": "fact chính về cấu tạo cơ thể, đúng dữ kiện phổ biến",
  "question_vi": "câu hỏi kéo bình luận",
  "composition_en": "side view/diagonal/centered composition instruction in English",
  "transparency_en": "transparency/internal anatomy instruction in English",
  "background_en": "simple light grey-blue background, clean and minimal",
  "labels": [
    {{
      "label_vi": "nhãn tiếng Việt ngắn",
      "target_en": "exact body part target in English",
      "description_vi": "giải thích ngắn bằng tiếng Việt"
    }}
  ]
}}

{STORY_TOPIC_RULES}

Yêu cầu bắt buộc:
- Chủ thể nên là động vật có cấu tạo dễ nhìn và đủ hấp dẫn: cua, cá, mực, bạch tuộc, ong, bướm, ếch, cá ngựa, rùa, chim, rắn, sứa.
- Không chọn tôm/shrimp vì topic đó đã đăng rồi.
- Ưu tiên loài có cơ thể/giải phẫu dễ làm viewer tò mò: trong suốt, nhiều chân, mang, xúc tu, túi trứng, mai/vỏ, cánh, vòi, dạ dày, tim, đường ruột, cơ quan sinh sản.
- labels phải có 8 đến 12 nhãn, mỗi label_vi tối đa 4 từ nếu có thể.
- label_vi phải là tiếng Việt thường, rõ nghĩa, không viết hoa toàn bộ.
- target_en phải chỉ đúng vị trí cơ thể để model nối pointer line chính xác.
- description_vi phải cụ thể, không chung chung kiểu "bộ phận quan trọng".
- Không chọn chủ thể quá khó render anatomy hoặc dễ gây phản cảm.
- Không thêm logo, watermark, page name, title trong image; ảnh chỉ có nhãn giải phẫu.
- Không bịa cơ quan không phổ biến; nếu không chắc thì chọn bộ phận ngoài cơ thể dễ xác định.
- Không dùng lại chủ thể/góc anatomy cũ.
"""
    elif topic_type == "comparison_top5":
        prompt = f"""
Bạn là biên tập viên nội dung Facebook về thế giới động vật và thực vật, ưu tiên topic có "điểm wow" rõ ràng và có thể kể thành một câu chuyện cuốn hút.

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

{STORY_TOPIC_RULES}

Yêu cầu bắt buộc:
- Đúng 5 items, rank từ 1 đến 5.
- name_vi dùng tiếng Việt dễ hiểu, viết hoa chữ cái đầu mỗi từ.
- stat phải ngắn, dễ đọc trên ảnh, không quá 18 ký tự nếu có thể.
- detail_vi làm rõ stat nghĩa là gì bằng thông tin cụ thể, không quá 14 từ.
- detail_vi phải giúp người xem hiểu ngay vì sao item đó đáng kinh ngạc, có cơ chế/quy mô/hành vi cụ thể.
- subject_vi phải gợi cảm giác muốn đọc tiếp, không chỉ là nhãn phân loại khô; ví dụ "Top 5 sinh vật nhìn hiền nhưng có chiêu cực gắt" tốt hơn "Top 5 sinh vật đặc biệt".
- Các item nên cùng tạo thành một "mạch chuyện" hoặc một cú tò mò chung: ai cũng có chiêu riêng, ai cũng có cơ chế wow riêng.
- Tuyệt đối không dùng detail_vi chung chung kiểu "đặc điểm nổi bật giúp nó săn mồi, sinh tồn hoặc tự vệ".
- Nếu comparison_angle là "special ability", detail_vi phải nói rõ cơ chế/khoảng cách/cách dùng/lợi ích cụ thể của khả năng đó.
- Nếu comparison_angle là "survival", detail_vi phải nói rõ cơ chế sống sót: ngủ đông, giảm trao đổi chất, giữ nước/nhiệt, sửa ADN, chịu mặn/nóng/lạnh.
- Nếu comparison_angle là "parenting", detail_vi phải nói rõ hành vi chăm con cụ thể, không viết chung chung "chăm con tận tụy".
- Nếu comparison_angle là "camouflage" hoặc "bioluminescence", detail_vi phải nói rõ môi trường/cách dùng/ngữ cảnh cụ thể.
- Nếu comparison_angle là "toxicity" hoặc "venom", detail_vi phải nói rõ cơ chế/tác động cụ thể của độc/nọc, không được viết chung chung kiểu "độc tính tự nhiên khiến con người phải thận trọng".
- Nếu comparison_angle là "building ability", detail_vi phải nói rõ loài đó xây gì, dùng vật liệu/cách xây nào, lợi ích là gì; không được viết chung chung kiểu "xây dựng cấu trúc sống tinh vi".
- Ưu tiên chủ đề thật sự hấp dẫn: kỷ lục lạ, khả năng sinh tồn, vũ khí tự nhiên, chiến thuật săn mồi, thực vật kỳ dị, hành vi khiến người xem muốn comment hoặc bấm vào ảnh để đọc kỹ.
- Không bịa số liệu chính xác nếu không chắc; có thể dùng mô tả định tính ngắn như "Siêu độc", "Tái sinh", "Bẫy dính".
- Không dùng lại chủ đề cũ.
"""
    elif topic_type == "single_card":
        prompt = f"""
Bạn là biên tập viên nội dung Facebook về thế giới động vật và thực vật, ưu tiên các fact có hình ảnh rất "wow" và kể được thành một mẩu chuyện ngắn.

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

{STORY_TOPIC_RULES}

Yêu cầu bắt buộc:
- subject nên là động vật hoặc thực vật rất thú vị, ít nhàm chán.
- fact_value tối đa 18 ký tự nếu có thể, nên là số liệu/hành vi/khả năng đủ mạnh để làm text lớn trên ảnh.
- fact_detail phải thật, dễ hiểu, không giật gân sai sự thật, và phải nêu được cơ chế/quy mô/hành vi đặc biệt.
- detail_vi giải thích cụ thể fact_value nghĩa là gì, dùng tiếng Việt tự nhiên, tối đa 16 từ.
- fact_value/detail_vi phải đủ tạo cú twist khi kể chuyện: nhìn vậy nhưng hóa ra có vũ khí/cơ chế/sinh tồn/cạm bẫy/kỹ năng kỳ lạ.
- Tránh fact quá phẳng kiểu "rất thông minh", "rất nhanh", "rất đặc biệt" nếu không có cơ chế cụ thể.
- detail_vi không được chung chung kiểu "khả năng đặc biệt", "rất thú vị", "giúp sinh tồn"; phải nói rõ đặc biệt ở đâu.
- Ưu tiên fact có thể tạo hình ảnh ấn tượng: phát sáng, trong suốt, kích thước lạ, chiến thuật săn mồi, cấu trúc cơ thể, cộng sinh, ngụy trang, tái sinh, siêu giác quan.
- Không dùng lại chủ đề cũ.
"""
    elif topic_type in ENGAGEMENT_TOPIC_TYPES:
        prompt = f"""
Bạn là biên tập viên nội dung Facebook về thế giới động vật và thực vật, chuyên tạo format mới lạ, dễ kéo comment, mở đầu từ một câu chuyện khiến viewer tò mò.

Hãy sinh 1 topic mới cho format: {topic_type}
Định hướng format: {ENGAGEMENT_TOPIC_GUIDES[topic_type]}
Không được trùng hoặc quá giống các topic đã có:
{existing_summary}

Chỉ trả về JSON hợp lệ với schema:
{{
  "topic_type": "{topic_type}",
  "topic_key": "snake_case_english_unique_key",
  "subject_vi": "Tiêu đề/chủ đề tiếng Việt",
  "subject_en": "English subject",
  "visual_subject_en": "English visual subject for image generation",
  "hook_vi": "hook chính bằng tiếng Việt, cụ thể và gây tò mò",
  "main_fact_vi": "fact chính bằng tiếng Việt, đúng sự thật, giàu thông tin",
  "twist_vi": "twist/cơ chế/chi tiết phụ khiến câu chuyện đáng nhớ",
  "question_vi": "câu hỏi kéo bình luận"
}}

{STORY_TOPIC_RULES}

Yêu cầu bắt buộc:
- Chủ đề phải thật, không bịa số liệu chính xác nếu không chắc.
- Ưu tiên động vật/thực vật có hình ảnh mạnh: biển sâu, phát sáng, trong suốt, biến hình, cộng sinh, ngụy trang, săn mồi lạ, cây lừa côn trùng, vòng đời kỳ dị.
- hook_vi không được chung chung; phải chứa mâu thuẫn, hành vi lạ, cơ chế hiếm hoặc số liệu dễ hình dung.
- main_fact_vi phải giải thích rõ điểm đặc biệt bằng ngôn ngữ dễ hiểu.
- twist_vi phải bổ sung cơ chế/quy mô/ngữ cảnh, không lặp lại main_fact_vi.
- question_vi ngắn, tự nhiên, làm người xem muốn trả lời.
- subject_vi/hook_vi phải có cảm giác như mở cảnh: viewer nhìn thấy gì trước, hiểu lầm gì, hoặc chi tiết nào làm họ muốn xem tiếp.
- hook_vi + main_fact_vi + twist_vi khi ghép lại phải thành một mini-story rõ ràng: mở cảnh -> sự thật -> cú wow.
- Với myth_vs_fact: hook_vi phải là hiểu lầm/cú nhìn đầu tiên cụ thể, main_fact_vi là sự thật đảo chiều, twist_vi là cơ chế sinh tồn hoặc ngữ cảnh làm người xem "ồ".
- Với myth_vs_fact: tránh các câu khô kiểu "loài này có đặc điểm thú vị"; hãy tạo cảm giác như một cảnh phim ngắn: ai tưởng gì, tự nhiên đang giấu bí mật gì, vì sao đáng bấm vào ảnh.
- Không dùng lại chủ thể/góc nội dung cũ.
- Không mô tả máu me, tra tấn, cổ vũ động vật đánh nhau thật.
"""
    elif topic_type == "matchup_versus":
        prompt = f"""
Bạn là biên tập viên nội dung Facebook về thế giới động vật theo hướng khoa học, dễ viral, biến so sánh thành một câu chuyện đặt lên bàn cân.

Hãy sinh 1 topic mới dạng so sánh 1-vs-1 giữa hai loài động vật cùng nhóm hoặc gần tương đương kích cỡ, thú vị, gây tranh luận, nhưng không cổ vũ bạo lực thật.
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
    "measure_label": "Chiều cao vai | Chiều dài | Sải cánh | Chiều cao",
    "height": "short numeric value only, without label",
    "weight": "short value",
    "bite_force": "short value or key weapon",
    "edge_vi": "lợi thế ngắn bằng tiếng Việt"
  }},
  "right": {{
    "name_vi": "Tên Tiếng Việt",
    "name_en": "English common name",
    "measure_label": "Chiều cao vai | Chiều dài | Sải cánh | Chiều cao",
    "height": "short numeric value only, without label",
    "weight": "short value",
    "bite_force": "short value or key weapon",
    "edge_vi": "lợi thế ngắn bằng tiếng Việt"
  }},
  "verdict_vi": "kết luận ngắn dựa trên số liệu",
  "reality_note_vi": "lưu ý đây là so sánh giả định, không cổ vũ đối đầu thật",
  "debate_question_vi": "câu hỏi kéo bình luận"
}}

{STORY_TOPIC_RULES}

Yêu cầu bắt buộc:
- Chọn hai loài cùng nhóm hoặc rất gần nhau về kích cỡ: 2 giống chó, 2 loài cá, 2 loài mèo lớn gần cân, 2 loài chim săn mồi, 2 loài bò sát tương đương, 2 loài linh trưởng tương đương.
- Tránh tuyệt đối các cặp quá lệch kích cỡ/sức mạnh như chó vs hổ, chim vs báo, khỉ nhỏ vs gấu lớn, rắn nhỏ vs cá mập.
- Mục tiêu là làm rõ đặc điểm nổi bật, điểm mạnh riêng, hành vi, môi trường sống, chiến thuật sinh tồn của mỗi loài.
- Cặp so sánh phải có "câu chuyện tranh luận" rõ: hai loài nhìn có vẻ ngang nhau nhưng mỗi bên có chiêu khác nhau khiến viewer muốn chọn phe.
- edge_vi của mỗi bên phải là lợi thế cụ thể, giàu hình ảnh, không viết chung chung kiểu "mạnh mẽ", "nhanh nhẹn".
- Kết luận không được viết kiểu một bên "áp đảo tuyệt đối"; hãy nêu bên nào nhỉnh ở tiêu chí nào và bên kia mạnh ở tiêu chí nào.
- Ưu tiên chủ đề vui và dễ bình luận: 2 giống chó bảo vệ, 2 loài cá săn mồi, 2 loài mèo lớn gần cân, 2 loài chim săn mồi, 2 loài rắn độc tương đương.
- measure_label phải phù hợp với cơ thể loài: rắn/cá/cá mập/cá voi/mực/cá sấu/thằn lằn dùng "Chiều dài"; chim săn mồi dùng "Sải cánh"; chó/mèo lớn/gấu/thú bốn chân dùng "Chiều cao vai"; linh trưởng hoặc loài đứng thẳng có thể dùng "Chiều cao".
- Chó, sói, chó rừng, cáo, linh cẩu và các loài thú bốn chân KHÔNG BAO GIỜ dùng "Sải cánh"; dùng "Chiều cao vai" hoặc "Chiều dài" nếu số liệu là chiều dài thân.
- Các field tiếng Việt như subject_vi, edge_vi, verdict_vi, reality_note_vi, debate_question_vi phải dùng tiếng Việt tự nhiên; không chèn thuật ngữ tiếng Anh như "savanna", "urban", "canid", "Coyote" khi đã có tên Việt.
- height chỉ chứa giá trị ngắn như "2.5 m", "76 cm", "1.8 m"; không viết lặp nhãn như "Dài 2.5 m" nếu đã có measure_label.
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
        topic.get("hook_vi", ""),
        topic.get("main_fact_vi", ""),
        topic.get("twist_vi", ""),
        topic.get("question_vi", ""),
        topic.get("visual_subject_en", ""),
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
    for label in topic.get("labels", []):
        parts.extend(
            [
                label.get("label_vi", ""),
                label.get("target_en", ""),
                label.get("description_vi", ""),
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

        if candidate["topic_type"] == "anatomy_infographic":
            subject_similarity = jaccard(
                token_set(
                    " ".join(
                        [
                            candidate.get("subject_vi", ""),
                            candidate.get("subject_en", ""),
                            candidate.get("animal_vi", ""),
                            candidate.get("animal_en", ""),
                        ]
                    )
                ),
                token_set(
                    " ".join(
                        [
                            existing.get("subject_vi", ""),
                            existing.get("subject_en", ""),
                            existing.get("animal_vi", ""),
                            existing.get("animal_en", ""),
                        ]
                    )
                ),
            )
            content_similarity = jaccard(token_set(topic_text(candidate)), token_set(topic_text(existing)))
            if subject_similarity >= 0.45:
                return f"trùng/giống chủ thể anatomy với {existing.get('topic_key')}"
            if content_similarity >= 0.5:
                return f"nội dung anatomy quá giống {existing.get('topic_key')}"

        elif candidate["topic_type"] == "comparison_top5":
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

        elif candidate["topic_type"] in ENGAGEMENT_TOPIC_TYPES:
            subject_similarity = jaccard(token_set(candidate.get("subject_vi", "") + " " + candidate.get("subject_en", "")), token_set(existing.get("subject_vi", "") + " " + existing.get("subject_en", "")))
            content_similarity = jaccard(token_set(topic_text(candidate)), token_set(topic_text(existing)))
            if subject_similarity >= 0.45:
                return f"trùng/giống chủ đề với {existing.get('topic_key')}"
            if content_similarity >= 0.42:
                return f"nội dung format mới quá giống {existing.get('topic_key')}"

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

    if expected_type == "anatomy_infographic":
        for key in (
            "subject_vi",
            "subject_en",
            "animal_vi",
            "animal_en",
            "hook_vi",
            "main_fact_vi",
            "question_vi",
            "composition_en",
            "transparency_en",
            "background_en",
        ):
            value = str(topic.get(key, "")).strip()
            if not value:
                raise ValueError(f"Generated anatomy topic missing {key}.")
            topic[key] = value
        labels = topic.get("labels")
        if not isinstance(labels, list) or not 8 <= len(labels) <= 12:
            raise ValueError("Generated anatomy topic must contain 8 to 12 labels.")
        seen_labels = set()
        for label in labels:
            if not isinstance(label, dict):
                raise ValueError("Generated anatomy label must be an object.")
            for key in ("label_vi", "target_en", "description_vi"):
                value = str(label.get(key, "")).strip()
                if not value:
                    raise ValueError(f"Generated anatomy label missing {key}.")
                label[key] = value
            normalized_label = normalized_key(label["label_vi"])
            if normalized_label in seen_labels:
                raise ValueError(f"Duplicate anatomy label: {label['label_vi']}")
            seen_labels.add(normalized_label)

    elif expected_type == "comparison_top5":
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
    elif expected_type in ENGAGEMENT_TOPIC_TYPES:
        for key in (
            "subject_vi",
            "subject_en",
            "visual_subject_en",
            "hook_vi",
            "main_fact_vi",
            "twist_vi",
            "question_vi",
        ):
            value = str(topic.get(key, "")).strip()
            if not value:
                raise ValueError(f"Generated {expected_type} topic missing {key}.")
            topic[key] = value
    else:
        for key in ("subject_vi", "subject_en", "verdict_vi", "reality_note_vi", "debate_question_vi"):
            value = str(topic.get(key, "")).strip()
            if not value:
                raise ValueError(f"Generated matchup topic missing {key}.")
            if key != "subject_en":
                value = vietnamize_common_terms(value)
            topic[key] = value
        for side in ("left", "right"):
            animal = topic.get(side)
            if not isinstance(animal, dict):
                raise ValueError(f"Generated matchup topic missing {side}.")
            for key in ("name_vi", "name_en", "height", "weight", "bite_force", "edge_vi"):
                value = str(animal.get(key, "")).strip()
                if not value:
                    raise ValueError(f"Generated matchup {side} missing {key}.")
                if key not in {"name_en"}:
                    value = vietnamize_common_terms(value)
                animal[key] = value
            animal["measure_label"] = matchup_measure_label(animal)

    return topic
