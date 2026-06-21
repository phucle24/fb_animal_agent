from app.deepseek_service import generate_json
from app.utils import matchup_measure_label, matchup_measure_value


ENGAGEMENT_FORMAT_GUIDES = {
    "myth_vs_fact": """
Format: Myth vs Fact.
- Giọng vui, phá hiểu lầm phổ biến.
- caption phải làm rõ lời đồn sai/chưa đủ và sự thật thú vị.
- overlay_primary nên bắt đầu bằng "LỜI ĐỒN:".
- overlay_secondary nên bắt đầu bằng "SỰ THẬT:".
""",
    "guess_quiz": """
Format: Guess / Quiz.
- Giọng đố vui, kích thích viewer comment đáp án.
- caption có thể tiết lộ đáp án sau 1-2 câu dẫn, không quá khô.
- overlay_primary là câu đố ngắn.
- overlay_secondary nên là "ĐÁP ÁN Ở CAPTION" hoặc một clue cực ngắn.
""",
    "one_story": """
Format: One Story / Mini Case.
- Giọng kể chuyện ngắn, có mở đầu gây tò mò và một cú twist.
- caption phải giống một mẩu chuyện tự nhiên học, không phải bài encyclopedia.
- overlay_primary là sự kiện/cú twist chính.
- overlay_secondary là vì sao chuyện đó đặc biệt.
""",
    "before_after": """
Format: Before / After.
- Giọng biến hình, trước-sau rõ ràng.
- caption phải giải thích quá trình chuyển đổi hoặc khác biệt sinh học.
- overlay_primary nên bắt đầu bằng "TRƯỚC:".
- overlay_secondary nên bắt đầu bằng "SAU:".
""",
}


def generate_engagement_format_content(topic: dict) -> dict:
    format_guide = ENGAGEMENT_FORMAT_GUIDES[topic["topic_type"]]
    prompt = f"""
Bạn là biên tập viên Facebook về thế giới động vật và thực vật, chuyên làm nội dung lạ, vui nhẹ, giàu thông tin, dễ kéo bình luận.

Hãy tạo output JSON hợp lệ với đúng các key sau:
- title
- overlay_title
- overlay_primary
- overlay_secondary
- caption
- image_prompt

Thông tin topic:
- topic_type: {topic["topic_type"]}
- Chủ đề tiếng Việt: {topic["subject_vi"]}
- Chủ đề tiếng Anh: {topic["subject_en"]}
- Chủ thể hình ảnh tiếng Anh: {topic.get("visual_subject_en", topic["subject_en"])}
- Hook: {topic["hook_vi"]}
- Fact chính: {topic["main_fact_vi"]}
- Twist/chi tiết phụ: {topic["twist_vi"]}
- Câu hỏi kéo bình luận: {topic["question_vi"]}

{format_guide}

Yêu cầu:
1. title
- tiếng Việt, tối đa 14 từ
- có tính tò mò, không giật gân sai sự thật

2. overlay_title
- 2 đến 6 từ
- cực dễ đọc trên ảnh
- phải nói rõ format hoặc hook chính, ví dụ: "LỜI ĐỒN HAY SỰ THẬT?", "ĐOÁN XEM?", "CHUYỆN LẠ TỰ NHIÊN", "TRƯỚC VÀ SAU"

3. overlay_primary
- tối đa 42 ký tự nếu có thể
- là thông tin chính khiến người xem dừng lại
- không dùng câu chung chung kiểu "đặc điểm thú vị"

4. overlay_secondary
- tối đa 48 ký tự nếu có thể
- bổ sung cơ chế/quy mô/twist thật sự đặc biệt
- nếu quá dài, tách thành cụm ngắn dễ đọc

5. caption
- 4 đến 6 câu ngắn
- mở đầu vui, có điểm lạ rõ ràng
- giải thích bằng thông tin thật từ topic
- có một chút dí dỏm tự nhiên, không nhảm
- câu cuối là câu hỏi kéo bình luận
- KHÔNG viết "Ảnh minh họa AI" hoặc nói ảnh là AI

6. image_prompt
- tiếng Anh
- chỉ mô tả cảnh ảnh, không tự mô tả layout chữ
- visually striking, cinematic, high contrast, strong subject focus
- phải làm nổi bật cơ chế/quy mô/hành vi đặc biệt của topic
- dùng scale cue, glow, motion trail, macro detail, split transformation, silhouette, mystery lighting nếu phù hợp
- no watermark, no logo, no fake text

Chỉ trả về JSON, không markdown, không giải thích.
"""
    return generate_json(
        prompt,
        system="Bạn chỉ trả về JSON hợp lệ, không markdown, không giải thích.",
    )


def generate_comparison_content(topic: dict) -> dict:
    items_text = "\n".join(
        [
            f'{item["rank"]}. {item["name_vi"]} ({item["name_en"]}) - {item["stat"]}'
            for item in topic["items"]
        ]
    )

    prompt = f"""
Bạn là biên tập viên nội dung Facebook chuyên về kiến thức động vật và thực vật, giọng vui, dễ hiểu, giàu thông tin.

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
- 3 đến 4 câu ngắn
- gần gũi, dễ hiểu, vui nhẹ nhưng không nhảm
- mở đầu bằng hook thật sự đặc biệt khiến người đọc muốn dừng lại
- phải nêu rõ vì sao số liệu/hành vi này đáng "wow", không chỉ nói chung chung
- không cần liệt kê 5 mục vì hệ thống sẽ tự thêm phần đó
- nếu nhắc tên loài cụ thể, ưu tiên tên tiếng Việt đã cho
- có thể dùng một câu hỏi ngắn cuối đoạn để kéo bình luận

5. image_prompt
- tiếng Anh
- mô tả phong cách ảnh động vật hoang dã thực tế cho infographic ranking
- cinematic, sharp, visually striking
- mô tả môi trường sống, ánh sáng, chuyển động, biểu cảm của các sinh vật
- nhấn mạnh khoảnh khắc "wow" hoặc đặc điểm khiến người xem muốn bấm vào ảnh đọc tiếp
- không cần tự viết layout chữ vì hệ thống sẽ dựng prompt infographic cuối cùng
- no watermark
- suitable for ranking infographic

Chỉ trả về JSON, không giải thích thêm.
"""

    return generate_json(
        prompt,
        system="Bạn chỉ trả về JSON hợp lệ, không markdown, không giải thích.",
    )


def generate_single_card_content(topic: dict) -> dict:
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
- phải đúng mức độ sự thật trong fact_value/detail_vi, không phóng đại
- nếu fact_value có "gần như", "có thể", "ước tính", "khoảng" thì overlay_stat cũng phải giữ sắc thái đó, không viết thành tuyệt đối

4. overlay_hook
- 6 đến 10 từ nếu cần, tối đa 44 ký tự
- phải giàu thông tin hơn một nickname chung chung
- nên nói rõ cơ chế, quy mô, hành vi hoặc lợi ích đặc biệt
- ví dụ tốt: "Cả đàn nối nhau lọc phù du", "Săn trong bóng tối gần im lặng"
- ví dụ không tốt: "Vua tốc độ", "Vua lọc sinh vật", "Kẻ bí ẩn"

5. caption
- 3 đến 5 câu
- gần gũi, dễ hiểu, vui nhẹ, có một chút dí dỏm tự nhiên
- có kiến thức thật từ detail_vi và fact_detail
- ưu tiên dùng detail_vi để giải thích bằng tiếng Việt rõ ràng
- mở đầu bằng một câu hook nêu điểm lạ nhất/khó tin nhất, tránh mở đầu kiểu sách giáo khoa
- phải giải thích "vì sao điều này đặc biệt" bằng cơ chế, quy mô, môi trường sống, hoặc lợi ích sinh tồn
- nếu có số liệu như chiều dài/tốc độ/độc tính/thời gian, hãy đặt nó vào ngữ cảnh dễ hình dung
- nên có một câu hỏi ngắn để kéo bình luận, ví dụ: "Bạn nghĩ nó dùng khả năng này để làm gì?"
- không dùng từ ngữ giật gân sai sự thật
- không dùng từ tuyệt đối nếu dữ kiện chỉ nói "gần như", "có thể", "ước tính", hoặc "khoảng"
- KHÔNG viết "Ảnh minh họa AI", "Ảnh minh hoạ AI", hoặc bất kỳ câu nào nói ảnh là AI

6. image_prompt
- tiếng Anh
- chỉ mô tả cảnh ảnh, KHÔNG mô tả layout poster
- single-subject wildlife/nature cinematic scene
- sharp, dramatic, beautiful
- strong subject focus
- mô tả môi trường sống, ánh sáng, chuyển động, biểu cảm của chủ thể
- phản ánh đúng detail_vi/fact_detail bằng hình ảnh, làm rõ quy mô/cơ chế/hành vi đặc biệt để người xem "wow"
- ưu tiên cảnh có chiều sâu, tương phản, scale cue, motion trail, glow, macro detail hoặc môi trường sống đặc trưng nếu phù hợp
- không tự viết text layout, không thêm infographic, ranking, list, panel, table, grid instructions
- no ranking, no list, no top 5, no panel, no table, no grid, no fake text, no extra typography
- no watermark
- suitable for educational social media poster

Chỉ trả về JSON.
"""

    return generate_json(
        prompt,
        system="Bạn chỉ trả về JSON hợp lệ, không markdown, không giải thích.",
    )


def generate_matchup_content(topic: dict) -> dict:
    left = topic["left"]
    right = topic["right"]
    left_measure_label = matchup_measure_label(left).lower()
    right_measure_label = matchup_measure_label(right).lower()
    left_measure_value = matchup_measure_value(left)
    right_measure_value = matchup_measure_value(right)
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
- {left["name_vi"]}: {left_measure_label} {left_measure_value}, trọng lượng {left["weight"]}, lực cắn/vũ khí chính {left["bite_force"]}, lợi thế {left["edge_vi"]}
- {right["name_vi"]}: {right_measure_label} {right_measure_value}, trọng lượng {right["weight"]}, lực cắn/vũ khí chính {right["bite_force"]}, lợi thế {right["edge_vi"]}

Yêu cầu:
1. title
- tiếng Việt
- hấp dẫn, gây tò mò, tối đa 14 từ
- không cổ vũ bạo lực thật
- dùng sắc thái "so tài", "đặt lên bàn cân", "ai nổi bật hơn ở điểm nào" thay vì cổ vũ đánh nhau

2. overlay_title
- tiếng Việt, rất ngắn
- dạng poster so sánh, ví dụ: "JAGUAR VS LEOPARD", "CÁ MẬP TRẮNG VS CÁ MẬP HỔ"
- tối đa 9 từ

3. caption_intro
- 3 đến 5 câu
- mở đầu tươi mới, có chất tranh luận
- giải thích rằng đây là so sánh đặc điểm dựa trên số liệu sinh học/hành vi, không cổ vũ cho động vật đối đầu thật
- làm rõ mỗi bên mạnh ở tiêu chí nào: thể hình, tốc độ, lực hàm, độ bền, giác quan, chiến thuật, môi trường sống
- không kết luận kiểu một bên áp đảo tuyệt đối nếu hai loài khá ngang tầm
- không thay đổi số liệu
- dùng nhãn đo hình thái phù hợp với từng loài: rắn/cá/cá mập/cá voi/mực/cá sấu/thằn lằn dùng "chiều dài"; chim săn mồi dùng "sải cánh"; chó/mèo lớn/gấu/thú bốn chân dùng "chiều cao vai"; linh trưởng hoặc loài đứng thẳng có thể dùng "chiều cao"
- câu cuối nên là câu hỏi kéo bình luận

4. image_prompt
- tiếng Anh
- cinematic wildlife comparison infographic poster
- two similarly sized animals facing forward in split-screen natural habitat scene
- premium dark copper/orange style, dramatic light beams, scientific comparison mood
- no gore, no injury, no blood, no fighting impact, no attack pose
- no watermark
- do not invent extra text layout; system will build final infographic prompt

Chỉ trả về JSON, không giải thích thêm.
"""

    return generate_json(
        prompt,
        system="Bạn chỉ trả về JSON hợp lệ, không markdown, không giải thích.",
    )
