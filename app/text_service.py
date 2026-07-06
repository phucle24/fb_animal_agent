from app.deepseek_service import generate_json
from app.utils import matchup_measure_label, matchup_measure_value


STORYTELLING_RULES = """
Nguyên tắc kể chuyện bắt buộc cho mọi caption:
- Mở đầu bằng một cảnh nhỏ hoặc tình huống dễ hình dung, như viewer đang xem một đoạn phim tự nhiên.
- Câu đầu phải làm người xem tò mò hoặc bật cười nhẹ, không mở kiểu "Trong thế giới động vật..." hay "Bạn có biết rằng..." quá sách giáo khoa.
- Sau hook phải có một cú "hóa ra..." hoặc twist sinh học rõ ràng.
- Luôn giải thích vì sao điều đó đáng wow bằng cơ chế, môi trường sống, kẻ săn mồi/con mồi, quy mô, hoặc lợi ích sinh tồn.
- Giọng hóm hỉnh, duyên, gần gũi; tuyệt đối không bịa, không giật gân sai sự thật.
- Tránh văn khô kiểu encyclopedia và tránh câu chung chung như "đặc điểm này rất thú vị".
"""


CAPTION_STYLE_RULES = """
Khung caption bắt buộc:
- Độ dài phần caption/caption_intro do bạn viết: khoảng 120-180 chữ, không tính danh sách item cố định mà hệ thống sẽ tự ghép sau đó.
- Cấu trúc: Hook 1-2 câu -> Story/Wow 2-3 câu -> Value 1-2 câu -> CTA 1 câu.
- Hook phải mở bằng một cảnh, tình huống hoặc hiểu lầm cụ thể; KHÔNG mở bằng "Bạn có biết rằng", "Trong thế giới động vật", "Trong thế giới tự nhiên", "Thiên nhiên luôn...".
- Story/Wow phải có một cú twist sinh học rõ: cơ chế, môi trường sống, kẻ săn mồi/con mồi, quy mô, hoặc lợi ích sinh tồn.
- Value phải giúp viewer học được điều gì đó bằng ngôn ngữ dễ hiểu, không giống sách giáo khoa.
- CTA là một câu hỏi tự nhiên, không ép like/share/comment lộ liễu.
- Chỉ dùng dữ kiện có trong topic, items, detail_vi, fact_detail, main_fact_vi, twist_vi, verdict_vi; KHÔNG tự thêm số liệu, địa danh, hành vi, kẻ thù, hoặc kết luận nếu prompt không cung cấp.
- Nếu dữ kiện không chắc tuyệt đối, dùng wording mềm như "thường", "có thể", "ước tính", "được ghi nhận", tùy đúng dữ liệu đã có.
- Tránh cụm AI/khuôn mẫu: "đặc điểm thú vị", "khả năng đặc biệt", "vô cùng", "khiến ai cũng", "thiên nhiên kỳ diệu".
- Ưu tiên tiếng Việt tự nhiên; không chèn tiếng Anh trong caption nếu đã có tên/thuật ngữ tiếng Việt phổ biến.
- Giọng văn chân thật, duyên nhẹ, có chút hóm hỉnh; không Gen Z quá mạnh, không giật gân sai sự thật.
"""


ENGAGEMENT_FORMAT_GUIDES = {
    "myth_vs_fact": """
Format: Myth vs Fact.
- Giọng kể chuyện vui, phá hiểu lầm bằng một cú twist sinh học.
- caption phải mở như một mini-story: người xem tưởng A, nhưng tự nhiên đang làm B để sinh tồn.
- overlay_title KHÔNG dùng câu chung chung "LỜI ĐỒN HAY SỰ THẬT?" nếu có thể; hãy viết như một câu hook cụ thể về chủ thể.
- overlay_primary là hiểu lầm cực ngắn, KHÔNG bắt đầu bằng "LỜI ĐỒN:".
- overlay_secondary là cú twist/sự thật cực ngắn, KHÔNG bắt đầu bằng "SỰ THẬT:".
- overlay_primary và overlay_secondary phải khác nhau rõ ràng, không lặp lại cùng cụm từ hoặc cùng ý.
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

{STORYTELLING_RULES}
{CAPTION_STYLE_RULES}

Yêu cầu:
1. title
- tiếng Việt, tối đa 14 từ
- có tính tò mò, không giật gân sai sự thật

2. overlay_title
- 2 đến 6 từ
- cực dễ đọc trên ảnh
- phải là hook cụ thể của topic, tránh title format chung chung nếu topic đã có ý hay
- ví dụ tốt: "CUTE ĐỂ SINH TỒN?", "CÁI ĐẦU NHÌN XUYÊN", "BÍ MẬT TRONG BÓNG TỐI"
- ví dụ không tốt: "LỜI ĐỒN HAY SỰ THẬT?", "SỰ THẬT THÚ VỊ"

3. overlay_primary
- tối đa 36 ký tự nếu có thể
- là mồi câu khiến người xem dừng lại, một hiểu lầm/câu hỏi/cú nhìn đầu tiên
- không dùng câu chung chung kiểu "đặc điểm thú vị"
- KHÔNG lặp lại overlay_title
- KHÔNG bắt đầu bằng label chung như "LỜI ĐỒN:", "SỰ THẬT:", "THÔNG TIN:"

4. overlay_secondary
- tối đa 42 ký tự nếu có thể
- bổ sung cơ chế/quy mô/twist thật sự đặc biệt
- nếu quá dài, tách thành cụm ngắn dễ đọc
- KHÔNG lặp lại overlay_primary
- KHÔNG bắt đầu bằng label chung như "LỜI ĐỒN:", "SỰ THẬT:", "THÔNG TIN:"

5. caption
- 5 đến 8 câu ngắn, khoảng 120-180 chữ
- viết như đang kể một câu chuyện nhỏ, không phải đoạn encyclopedia
- câu 1-2 phải tạo tình huống/hiểu lầm khiến người xem tò mò
- câu 3-5 mở cú twist bằng thông tin thật từ topic
- phải nói rõ cơ chế/quy mô/ngữ cảnh: nó dùng khả năng đó ở đâu, để tránh ai, dụ ai, hoặc sinh tồn ra sao
- có một chút dí dỏm tự nhiên, không nhảm
- câu cuối là câu hỏi kéo bình luận
- KHÔNG viết "Ảnh minh họa AI" hoặc nói ảnh là AI

6. image_prompt
- tiếng Anh
- chỉ mô tả cảnh ảnh, không tự mô tả layout chữ
- visually striking, cinematic, high contrast, strong subject focus
- phải làm nổi bật cơ chế/quy mô/hành vi đặc biệt của topic
- tạo một visual story rõ ràng: chủ thể đang làm gì, môi trường nào, mối đe dọa/cơ chế/twist nằm ở đâu
- nếu là myth_vs_fact, hãy mô tả cảnh có "before assumption vs hidden survival function" bằng hình ảnh, không dùng chữ
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
Bạn là biên tập viên nội dung Facebook chuyên về kiến thức động vật và thực vật, giọng vui, dễ hiểu, giàu thông tin, kể chuyện lôi cuốn.

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

{STORYTELLING_RULES}
{CAPTION_STYLE_RULES}

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
- 5 đến 8 câu ngắn, khoảng 120-180 chữ
- gần gũi, dễ hiểu, vui nhẹ nhưng không nhảm
- mở đầu bằng một cảnh nhỏ/tình huống hài nhẹ khiến người đọc muốn dừng lại
- phải có một cú twist kiểu "tưởng vậy mà không phải vậy" hoặc "nhìn nhỏ/hiền/lạ nhưng hóa ra..."
- phải nêu rõ vì sao số liệu/hành vi này đáng "wow", không chỉ nói chung chung
- phải dẫn vào bảng Top 5 tự nhiên, giống đang mời viewer mở ảnh để xem tiếp
- không cần liệt kê 5 mục vì hệ thống sẽ tự thêm phần đó
- nếu nhắc tên loài cụ thể, ưu tiên tên tiếng Việt đã cho
- có thể dùng một câu hỏi ngắn cuối đoạn để kéo bình luận

5. image_prompt
- tiếng Anh
- mô tả phong cách ảnh động vật hoang dã thực tế cho infographic ranking
- cinematic, sharp, visually striking
- mô tả môi trường sống, ánh sáng, chuyển động, biểu cảm của các sinh vật
- có visual story rõ: bối cảnh, hành động, khoảnh khắc căng/tò mò/hài hước, chi tiết khiến viewer muốn zoom ảnh
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


def generate_anatomy_content(topic: dict) -> dict:
    labels_text = "\n".join(
        f'- {part["label_vi"]}: {part["description_vi"]}'
        for part in topic["labels"]
    )
    prompt = f"""
Bạn là biên tập viên Facebook về sinh học động vật, viết nội dung giáo dục dễ hiểu, tự nhiên, có hook nhưng không giật gân.

Hãy tạo output JSON hợp lệ với đúng các key sau:
- title
- caption
- image_prompt

Thông tin bài viết:
- topic_type: anatomy_infographic
- Chủ đề tiếng Việt: {topic["subject_vi"]}
- Chủ đề tiếng Anh: {topic["subject_en"]}
- Chủ thể tiếng Việt: {topic["animal_vi"]}
- Chủ thể tiếng Anh: {topic["animal_en"]}
- Hook chính: {topic["hook_vi"]}
- Fact chính: {topic["main_fact_vi"]}
- Câu hỏi kéo bình luận: {topic["question_vi"]}

Các nhãn giải phẫu sẽ xuất hiện trên ảnh, KHÔNG thay đổi và KHÔNG thêm nhãn mới:
{labels_text}

{STORYTELLING_RULES}
{CAPTION_STYLE_RULES}

Yêu cầu:
1. title
- tiếng Việt, tối đa 14 từ
- có tính tò mò, nhưng không dùng kiểu giật gân sai sự thật
- không dùng chữ "Top 5"

2. caption
- 5 đến 8 câu ngắn, khoảng 120-180 chữ
- mở bằng một cảnh/tình huống khiến người xem muốn zoom vào ảnh, không mở kiểu sách giáo khoa
- kể vì sao cấu tạo cơ thể của {topic["animal_vi"]} đáng xem, gắn với cách nó ăn, bơi, hô hấp, sinh sản hoặc sống sót
- chỉ dùng dữ kiện được cung cấp ở trên; không tự thêm số liệu hoặc cơ quan ngoài danh sách
- không liệt kê lại toàn bộ nhãn theo kiểu khô; hãy dẫn người xem nhìn vào ảnh để khám phá
- giọng chân thật, duyên nhẹ, dễ hiểu
- câu cuối là câu hỏi tự nhiên để kéo bình luận
- KHÔNG viết "Ảnh minh họa AI" hoặc nói ảnh là AI

3. image_prompt
- tiếng Anh
- chỉ mô tả thêm visual detail riêng cho chủ thể, không thêm text mới
- realistic educational anatomy infographic, clean scientific style
- no logo, no watermark, no brand name

Chỉ trả về JSON, không markdown, không giải thích.
"""
    return generate_json(
        prompt,
        system="Bạn chỉ trả về JSON hợp lệ, không markdown, không giải thích.",
    )


def generate_single_card_content(topic: dict) -> dict:
    detail_vi = topic.get("detail_vi", "").strip()
    prompt = f"""
Bạn là biên tập viên nội dung Facebook chuyên về kiến thức động vật và thực vật lạ, dễ viral, kể chuyện ngắn cực cuốn.

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

{STORYTELLING_RULES}
{CAPTION_STYLE_RULES}

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
- 5 đến 8 câu, khoảng 120-180 chữ
- gần gũi, dễ hiểu, vui nhẹ, có một chút dí dỏm tự nhiên
- có kiến thức thật từ detail_vi và fact_detail
- ưu tiên dùng detail_vi để giải thích bằng tiếng Việt rõ ràng
- mở đầu bằng một cảnh nhỏ hoặc tình huống buồn cười/tò mò xoay quanh chủ thể, tránh mở đầu kiểu sách giáo khoa
- phải có một cú twist: nhìn vậy nhưng hóa ra khả năng đó phục vụ săn mồi, phòng vệ, sinh tồn, sinh sản, giao tiếp hoặc kiếm ăn
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
- mô tả một khoảnh khắc như cảnh phim, có hành động hoặc dấu hiệu thị giác khiến viewer muốn bấm vào ảnh
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
Bạn là biên tập viên nội dung Facebook chuyên về kiến thức động vật theo hướng khoa học, dễ viral, kể chuyện như một màn đặt lên bàn cân hấp dẫn.

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

{STORYTELLING_RULES}
{CAPTION_STYLE_RULES}

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
- 5 đến 8 câu, khoảng 120-180 chữ
- mở đầu bằng một cảnh giả định vui/đời thường như "nếu đặt hai cao thủ này lên bàn cân..." nhưng không cổ vũ đánh nhau
- phải dẫn dắt viewer tò mò: bên nào có lợi thế gì, bên nào khiến ta bất ngờ ở điểm nào
- giải thích rằng đây là so sánh đặc điểm dựa trên số liệu sinh học/hành vi, không cổ vũ cho động vật đối đầu thật
- làm rõ mỗi bên mạnh ở tiêu chí nào: thể hình, tốc độ, lực hàm, độ bền, giác quan, chiến thuật, môi trường sống
- CHỈ dùng tiếng Việt trong caption_intro; không chèn tên tiếng Anh nếu đã có tên tiếng Việt
- Dịch thuật ngữ môi trường/hành vi sang tiếng Việt tự nhiên, ví dụ "savanna" -> "thảo nguyên", "urban" -> "đô thị", "canid" -> "họ chó"
- không kết luận kiểu một bên áp đảo tuyệt đối nếu hai loài khá ngang tầm
- không thay đổi số liệu
- dùng nhãn đo hình thái phù hợp với từng loài: rắn/cá/cá mập/cá voi/mực/cá sấu/thằn lằn dùng "chiều dài"; chim săn mồi dùng "sải cánh"; chó/mèo lớn/gấu/thú bốn chân dùng "chiều cao vai"; linh trưởng hoặc loài đứng thẳng có thể dùng "chiều cao"
- Chó, sói, chó rừng, cáo, linh cẩu và các loài thú bốn chân KHÔNG BAO GIỜ dùng "sải cánh"; dùng "chiều cao vai" hoặc "chiều dài" nếu số liệu là chiều dài thân.
- câu cuối nên là câu hỏi kéo bình luận

4. image_prompt
- tiếng Anh
- cinematic wildlife comparison infographic poster
- two similarly sized animals facing forward in split-screen natural habitat scene
- visual story should feel like a scientific face-off poster: tension from posture, habitat, scale, and lighting, not violence
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
