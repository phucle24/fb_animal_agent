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
- mô tả phong cách ảnh động vật hoang dã thực tế cho infographic ranking
- cinematic, sharp, visually striking
- mô tả môi trường sống, ánh sáng, chuyển động, biểu cảm của các sinh vật
- không cần tự viết layout chữ vì hệ thống sẽ dựng prompt infographic cuối cùng
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
    detail_vi = topic.get("detail_vi", "").strip()
    prompt = f"""
Bạn là biên tập viên nội dung Facebook chuyên về kiến thức động vật và thực vật lạ, dễ viral.

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
- detail_vi: {detail_vi}

Yêu cầu:
1. title
- tiếng Việt
- ngắn, hấp dẫn, có tính tò mò hoặc bất ngờ
- tối đa 12 từ

2. overlay_title
- cực ngắn
- 2 đến 4 từ
- viết như headline poster mạnh, dễ đọc
- KHÔNG dùng dạng Top/Top 5/xếp hạng
- KHÔNG dùng dấu câu

3. overlay_stat
- lấy trọng tâm từ fact_value
- cực ngắn
- tối đa 14 ký tự nếu có thể
- ví dụ: "110 KM/H", "SỐC ĐIỆN", "BẤT TỬ"

4. overlay_hook
- tối đa 5 từ
- tạo tò mò
- dễ đọc trên ảnh
- ví dụ: "Vua tốc độ", "Cú đấm sấm sét"

5. caption
- 3 đến 5 câu
- gần gũi, dễ hiểu
- có kiến thức thật từ detail_vi và fact_detail
- ưu tiên dùng detail_vi để giải thích bằng tiếng Việt rõ ràng
- mở đầu bằng một câu hook khiến người đọc muốn dừng lại
- nên có một câu hỏi ngắn để kéo bình luận, ví dụ: "Bạn nghĩ nó dùng khả năng này để làm gì?"
- không dùng từ ngữ giật gân sai sự thật
- KHÔNG viết "Ảnh minh họa AI", "Ảnh minh hoạ AI", hoặc bất kỳ câu nào nói ảnh là AI

6. image_prompt
- tiếng Anh
- single-subject wildlife/nature cinematic poster
- sharp, dramatic, beautiful
- strong subject focus
- mô tả môi trường sống, ánh sáng, chuyển động, biểu cảm của chủ thể
- phản ánh đúng detail_vi/fact_detail bằng hình ảnh, không cần render câu giải thích thành chữ
- không tự viết text layout, không thêm ranking/list/panel instructions
- no ranking, no list, no top 5, no fake text
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


def generate_matchup_content(topic: dict) -> dict:
    _ensure_api_key()
    client, types = _client_and_types()
    left = topic["left"]
    right = topic["right"]
    prompt = f"""
Bạn là biên tập viên nội dung Facebook chuyên về kiến thức động vật theo hướng khoa học, dễ viral.

Hãy tạo output JSON hợp lệ với đúng các key sau:
- title
- overlay_title
- caption_intro
- image_prompt

Thông tin bài viết:
- Chủ đề: {topic["subject_vi"]}
- Bên trái: {left["name_vi"]} ({left["name_en"]})
- Bên phải: {right["name_vi"]} ({right["name_en"]})
- Kết luận khoa học: {topic["verdict_vi"]}
- Lưu ý thực tế: {topic["reality_note_vi"]}
- Câu hỏi kéo bình luận: {topic["debate_question_vi"]}

Số liệu cố định, KHÔNG thay đổi:
- {left["name_vi"]}: chiều cao {left["height"]}, trọng lượng {left["weight"]}, lực cắn {left["bite_force"]}, lợi thế {left["edge_vi"]}
- {right["name_vi"]}: chiều cao {right["height"]}, trọng lượng {right["weight"]}, lực cắn {right["bite_force"]}, lợi thế {right["edge_vi"]}

Yêu cầu:
1. title
- tiếng Việt
- hấp dẫn, gây tò mò, tối đa 14 từ
- không cổ vũ bạo lực thật

2. overlay_title
- tiếng Việt, rất ngắn
- dạng poster đối đầu, ví dụ: "NGẠO TẠNG VS HỔ BENGAL"
- tối đa 9 từ

3. caption_intro
- 3 đến 5 câu
- mở đầu tươi mới, có chất tranh luận
- giải thích rằng đây là so sánh giả định dựa trên số liệu sinh học, không cổ vũ cho động vật đối đầu thật
- không thay đổi số liệu
- câu cuối nên là câu hỏi kéo bình luận

4. image_prompt
- tiếng Anh
- cinematic wildlife face-off infographic poster
- two animals facing forward in split-screen forest/jungle scene
- premium dark copper/orange style, dramatic light beams, scientific comparison mood
- no gore, no injury, no blood, no fighting impact
- no watermark
- do not invent extra text layout; system will build final infographic prompt

Chỉ trả về JSON, không giải thích thêm.
"""

    response = client.models.generate_content(
        model=GEMINI_TEXT_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json"),
    )

    return safe_json_loads(response.text)
