from app.config import GEMINI_API_KEY, GEMINI_TEXT_MODEL
from app.utils import safe_json_loads


def _ensure_api_key():
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing ANIMAL_AGENT_GEMINI_API_KEY")


def _client_and_types():
    from google import genai
    from google.genai import types

    return genai.Client(api_key=GEMINI_API_KEY), types


def generate_comparison_content(topic: dict) -> dict:
    _ensure_api_key()
    client, types = _client_and_types()
    items_text = "\n".join(
        [
            f'{item["rank"]}. {item["name_vi"]} ({item["name_en"]}) - {item["stat"]}'
            for item in topic["items"]
        ]
    )

    prompt = f"""
Bạn là biên tập viên nội dung Facebook chuyên về kiến thức động vật và thực vật.

Hãy tạo output JSON hợp lệ với đúng các key sau:
- title
- overlay_title
- overlay_subtitle
- caption_intro
- image_prompt

Thông tin bài viết:
- Chủ đề tiếng Việt: {topic["subject_vi"]}
- Chủ đề tiếng Anh: {topic["subject_en"]}
- Kiểu bài: comparison_top5
- Góc nội dung: {topic["comparison_angle"]}

Danh sách xếp hạng cố định (KHÔNG thay đổi thứ tự, KHÔNG thay đổi số liệu):
{items_text}

Yêu cầu:
1. title
- tiếng Việt
- hấp dẫn, dễ đọc
- tối đa 12 từ

2. overlay_title
- tiếng Việt
- ngắn, mạnh
- ví dụ kiểu: "TOP 5 TỐC ĐỘ"

3. overlay_subtitle
- tiếng Việt
- ngắn
- giải thích ngắn cho title
- ví dụ: "Con vật chạy nhanh nhất trên cạn"

4. caption_intro
- 2 đến 3 câu ngắn
- gần gũi, dễ hiểu
- không dài dòng
- không cần liệt kê 5 mục vì hệ thống sẽ tự thêm phần đó
- nếu nhắc tên loài cụ thể, ưu tiên tên tiếng Việt đã cho

5. image_prompt
- tiếng Anh
- ảnh dạng educational social media poster / infographic background
- cinematic, sharp, visually striking
- mô tả các sinh vật liên quan trong cùng một khung hình
- ưu tiên bố cục phù hợp cho poster dọc Facebook
- chừa không gian rõ ràng ở phần trên và phần dưới để overlay text
- no text
- no watermark
- suitable for ranking infographic

Chỉ trả về JSON, không giải thích thêm.
"""

    response = client.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    return safe_json_loads(response.text)


def generate_single_card_content(topic: dict) -> dict:
    _ensure_api_key()
    client, types = _client_and_types()
    prompt = f"""
Bạn là biên tập viên nội dung Facebook chuyên về kiến thức động vật và thực vật.

Hãy tạo output JSON hợp lệ với đúng các key sau:
- title
- overlay_title
- overlay_stat
- overlay_hook
- caption
- image_prompt

Thông tin bài viết:
- Chủ thể tiếng Việt: {topic["subject_vi"]}
- Chủ thể tiếng Anh: {topic["subject_en"]}
- fact_label: {topic["fact_label"]}
- fact_value: {topic["fact_value"]}
- fact_detail: {topic["fact_detail"]}

Yêu cầu:
1. title
- tiếng Việt
- ngắn, hấp dẫn
- tối đa 12 từ

2. overlay_title
- cực ngắn
- 2 đến 5 từ
- viết theo hướng mạnh, dễ đọc

3. overlay_stat
- lấy trọng tâm từ fact_value
- cực ngắn
- ví dụ: "110 KM/H"

4. overlay_hook
- tối đa 6 từ
- tạo tò mò
- ví dụ: "Vua tốc độ thảo nguyên"

5. caption
- 2 đến 4 câu
- gần gũi, dễ hiểu
- có kiến thức
- câu cuối cùng phải là: "Ảnh minh họa AI."

6. image_prompt
- tiếng Anh
- wildlife / nature cinematic
- sharp, dramatic, beautiful
- strong subject focus
- chừa khoảng trống rõ ràng bên trái hoặc phía trên để overlay text
- no text
- no watermark
- suitable for educational social media poster

Chỉ trả về JSON.
"""

    response = client.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    return safe_json_loads(response.text)
