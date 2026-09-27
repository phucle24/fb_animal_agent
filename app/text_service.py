from app.deepseek_service import generate_json
from app.utils import matchup_measure_label, matchup_measure_value


STORYTELLING_RULES = """
Nguyên tắc kể chuyện đột phá cho mọi caption (Tối ưu thuật toán & Kéo reach tự nhiên Facebook 2026):
- QUY TẮC 3 DÒNG ĐẦU TIÊN (Above the Fold - Dừng ngón tay lướt feed trong 0.5s):
  + Sức hút từ tiêu đề & chủ đề rộng: Mở đầu bằng sự tò mò tột độ, cảm xúc chạm sâu hoặc một câu chuyện sinh tồn độc đáo (như chim mỏ sừng tự giam mình nuôi con, đại ca lửng mật không sợ trời đất) có tính lan truyền cao, buộc người xem lướt qua phải dừng lại theo dõi.
  + Dòng 1: Cú sốc nhận thức, mâu thuẫn kỳ lạ hoặc khẳng định chạm cảm xúc (Ví dụ: "Vì sao cả sư tử và báo hoa mai đều phải né mặt đại ca lửng mật?", "Có một loài chim chấp nhận tự nhốt mình trong ngục tối suốt 4 tháng vì tình yêu...").
  + Dòng 2: Mở ra bí mật sinh học hoặc câu hỏi kích thích khiến người xem BẮT BUỘC bấm "Xem thêm" (See more).
  + Dòng 3: Dẫn dắt ánh mắt vào chi tiết bức ảnh, gợi mở điều kỳ diệu ẩn giấu.
- Thân bài (Story / Wow / Mechanism):
  + Kể lại câu chuyện sinh tồn độc đáo: Không liệt kê kiến thức khô cứng, mà giải thích cơ chế tiến hóa diệu kỳ đằng sau (vũ khí sinh học, giác quan thần kỳ, sự hy sinh mẫu tử/phụ tử, sự lì lợm không đối thủ).
  + Dùng hình tượng điện ảnh, gần gũi, tạo cảm giác thán phục hoặc xúc động sâu sắc.
- Trình bày trực quan: Chia bài thành các đoạn ngắn (2-3 câu mỗi đoạn), cách nhau bằng 1 dòng trắng. Tuyệt đối không viết thành khối đặc nghẹt gây ngộp mắt trên điện thoại.
- KÍCH HOẠT TRANH LUẬN & CHIA SẺ (Debate Trigger CTA):
  + Cuối bài KHÔNG BAO GIỜ hỏi nhạt nhẽo kiểu "Bạn thấy có hay không?".
  + Phải đưa ra câu hỏi chia phe tranh luận, đánh đố góc nhìn, hoặc chạm vào cảm xúc người xem (ví dụ: "Nếu đối đầu với đại ca lửng mật, bạn nghĩ vũ khí nào của tự nhiên mới khuất phục được nó? Bình luận bên dưới!").
- Giọng văn: Lôi cuốn, sắc bén, giàu cảm xúc, dí dỏm tự nhiên; bảo đảm đúng sự thật khoa học.
"""


CAPTION_STYLE_RULES = """
Khung caption chuẩn Facebook Viral:
- Độ dài: khoảng 130-190 chữ (đủ sâu để giữ chân người xem đọc 10-15s, tối ưu dwell time).
- Bố cục thoáng: Bắt buộc dùng dòng trắng giữa các đoạn để tối ưu trải nghiệm đọc trên điện thoại.
- Cấu trúc 4 phần:
  1. Hook (3 dòng đầu cực mạnh mang tính tò mò, cảm xúc hoặc câu chuyện sinh tồn độc đáo; tuyệt đối không mở bằng "Bạn có biết", "Trong thế giới tự nhiên", "Thiên nhiên luôn").
  2. Story / Mechanism (2-3 câu giải thích cơ chế sinh tồn, vũ khí độc lạ, đức hy sinh hoặc bản lĩnh hoang dã).
  3. Wow Insight (1-2 câu rút ra góc nhìn bất ngờ, chạm vào cảm xúc hoặc sự thán phục về tiến hóa).
  4. Debate CTA (1 câu hỏi kích hoạt người xem bình luận chia phe hoặc chia sẻ cảm xúc).
- Tránh các cụm từ AI sáo rỗng: "đặc điểm thú vị", "khả năng đặc biệt", "vô cùng kỳ diệu", "thiên nhiên luôn ẩn chứa", "minh chứng cho sự kỳ diệu".
- Tiếng Việt tự nhiên, giàu tính hình tượng và cảm xúc; không chèn tiếng Anh nếu đã có từ tiếng Việt tương đương.
"""


ENGAGEMENT_FORMAT_GUIDES = {
    "myth_vs_fact": """
Format: Myth vs Fact.
- Giọng kể chuyện lôi cuốn, phá hiểu lầm bằng một cú twist sinh học chấn động hoặc câu chuyện sinh tồn độc đáo.
- caption mở như một mini-story: người xem tưởng A, nhưng sự thật là cơ chế sinh tồn B khiến ai cũng phải nể phục.
- overlay_title KHÔNG dùng câu chung chung "LỜI ĐỒN HAY SỰ THẬT?" nếu có thể; hãy viết như một câu hook giật ngón tay cụ thể về chủ thể.
- overlay_primary là hiểu lầm cực ngắn, KHÔNG bắt đầu bằng "LỜI ĐỒN:".
- overlay_secondary là cú twist/sự thật cực ngắn, KHÔNG bắt đầu bằng "SỰ THẬT:".
- overlay_primary và overlay_secondary phải khác nhau rõ ràng, không lặp lại cùng cụm từ hoặc cùng ý.
""",
    "guess_quiz": """
Format: Guess / Quiz.
- Giọng đố vui lôi cuốn, kích thích viewer dừng lại comment đoán đáp án.
- caption tiết lộ câu chuyện sinh tồn độc đáo sau 1-2 câu dẫn, đầy bất ngờ.
- overlay_primary là câu đố giật ngón tay.
- overlay_secondary nên là "ĐÁP ÁN Ở CAPTION" hoặc một clue kích thích trí tò mò.
""",
    "one_story": """
Format: One Story / Mini Case.
- Giọng kể chuyện xúc động hoặc kịch tính, có mở đầu giật ngón tay, cao trào và một cú twist sinh tồn khó quên.
- caption như một trích đoạn phim tài liệu thiên nhiên BBC Earth, giàu cảm xúc.
- overlay_primary là sự kiện/hành vi độc lạ nhất.
- overlay_secondary là vì sao chuyện đó lay động hoặc phi thường.
""",
    "before_after": """
Format: Before / After.
- Giọng biến hình, trước-sau đối lập rõ rệt.
- caption giải thích quá trình lột xác, đổi đời hoặc cơ chế sinh tồn kỳ diệu.
- overlay_primary nên bắt đầu bằng "TRƯỚC:".
- overlay_secondary nên bắt đầu bằng "SAU:".
""",
}


def generate_engagement_format_content(topic: dict) -> dict:
    format_guide = ENGAGEMENT_FORMAT_GUIDES[topic["topic_type"]]
    prompt = f"""
Bạn là biên tập viên Facebook về thế giới động vật và hoang dã, chuyên tạo nội dung có sức hút lớn từ tiêu đề và chủ đề rộng: câu chuyện sinh tồn độc đáo, cảm xúc sâu sắc hoặc kỳ tích tự nhiên (như chim mỏ sừng, đại ca lửng mật) có tính lan truyền cao, thu hút người xem lướt qua dừng lại theo dõi.

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
- cực kỳ hấp dẫn, khơi gợi tò mò hoặc cảm xúc mạnh, giật ngón tay lướt feed

2. overlay_title
- 2 đến 6 từ
- cực dễ đọc trên ảnh, viết hoa
- phải là hook cụ thể của topic, tránh title format chung chung
- ví dụ tốt: "ĐẠI CA THẢO NGUYÊN", "TÌNH YÊU TRONG NGỤC TỐI", "KIỆT TÁC DƯỚI ĐÁY CÁT", "BÍ MẬT BẤT TỬ"
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
- viết như đang kể một câu chuyện điện ảnh ngắn, cuốn hút, giàu cảm xúc
- câu 1-2 phải tạo tình huống/mâu thuẫn/nghịch lý khiến người xem tò mò
- câu 3-5 mở cú twist bằng câu chuyện sinh tồn độc đáo và cơ chế thật từ topic
- nói rõ cơ chế sinh học: vũ khí, sự hy sinh, bản lĩnh lì lợm hoặc môi trường sống
- giọng văn cuốn hút, giàu cảm xúc, có một chút duyên ngầm
- câu cuối là câu hỏi kéo bình luận tranh luận sôi nổi
- KHÔNG viết "Ảnh minh họa AI" hoặc nói ảnh là AI

6. image_prompt
- tiếng Anh
- CHỈ mô tả cảnh thiên nhiên, sinh vật, hành động, ánh sáng và chi tiết thị giác
- TUYỆT ĐỐI KHÔNG chứa các từ khóa layout hay poster như: poster, infographic, headline, title, tag, badge, pill, text, visual journalism, visual journalism poster
- không tự mô tả bố cục chữ hay văn bản
- Award-winning wildlife documentary photography (National Geographic / BBC Earth style), 8k resolution, razor-sharp focus
- Capture the decisive moment: subject actively performing its iconic survival behavior or showing its fearless personality (e.g. honey badger glaring boldly, hornbill feeding mate through tree slot, pufferfish sculpting sand circle)
- Intense piercing eye contact with the camera lens, dramatic atmospheric lighting (volumetric god rays, golden rim light, morning mist, deep cinematic chiaroscuro)
- Hyper-detailed organic textures: keratin horn ridges, glistening scales, individual feather barbs, coarse fur
- no watermark, no logo, no fake text, no english labels

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
Bạn là biên tập viên nội dung Facebook chuyên về thế giới động vật và thiên nhiên, chuyên tạo bài viết có sức hút lớn từ tiêu đề và chủ đề rộng: câu chuyện sinh tồn độc đáo, cảm xúc sâu sắc hoặc kỳ tích tự nhiên (như chim mỏ sừng, đại ca lửng mật) có tính lan truyền cao, thu hút người xem lướt qua dừng lại theo dõi.

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
- cực kỳ hấp dẫn, khơi gợi tò mò hoặc cảm xúc mạnh, giật ngón tay lướt feed
- tối đa 14 từ

2. overlay_title
- tiếng Việt, viết hoa
- ngắn, mạnh, 2 đến 4 từ
- ví dụ: "TOP 5 BẢN LĨNH", "TOP 5 TỐC ĐỘ", "TOP 5 ĐỘC TÍNH"

3. overlay_subtitle
- tiếng Việt
- ngắn, 4 đến 8 từ
- giải thích góc độ so sánh gây tò mò, ví dụ: "Những kẻ lì lợm nhất thảo nguyên hoang dã"

4. caption_intro
- 5 đến 8 câu ngắn, khoảng 120-180 chữ
- mở đầu bằng một cảnh nhỏ/nghịch lý hoặc tình huống kịch tính giật ngón tay
- kể lại câu chuyện sinh tồn độc đáo, cú twist "tưởng vậy mà không phải vậy"
- nêu rõ vì sao số liệu/hành vi này phi thường và chạm đến cảm xúc người xem
- dẫn dắt tự nhiên mời viewer mở ảnh xem tiếp bảng xếp hạng
- không cần liệt kê 5 mục vì hệ thống sẽ tự thêm phần đó
- câu cuối là câu hỏi kéo bình luận tranh luận sôi nổi

5. image_prompt
- tiếng Anh
- CHỈ mô tả bối cảnh, ánh sáng, chuyển động, biểu cảm của các sinh vật
- TUYỆT ĐỐI KHÔNG chứa từ khóa layout hay poster như: poster, infographic, headline, title, tag, badge, visual journalism, visual journalism poster
- Award-winning cinematic wildlife photography (BBC Earth / National Geographic style)
- Dynamic wildlife visual story showing animals in action: hunting, sprinting, displaying unique survival tricks, piercing eye contact
- Dramatic natural lighting: volumetric golden hour beams, atmospheric mist, high contrast chiaroscuro
- no watermark, no logo, no fake text, no english labels

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
Bạn là biên tập viên Facebook về sinh học động vật, chuyên tạo nội dung giáo dục bảo tàng cao cấp series "Giải phẫu muôn loài" dễ hiểu, lôi cuốn, có câu chuyện sinh tồn độc đáo.

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
- khơi gợi tò mò, mở ra bí mật cấu tạo sinh học độc đáo của loài vật
- không dùng chữ "Top 5"

2. caption
- 5 đến 8 câu ngắn, khoảng 120-180 chữ
- mở bằng một câu chuyện hoặc tình huống thị giác khiến người xem muốn zoom vào ảnh
- mổ xẻ cơ chế cấu tạo cơ thể của {topic["animal_vi"]} gắn liền với câu chuyện sinh tồn độc đáo
- chỉ dùng dữ kiện được cung cấp ở trên; không tự thêm số liệu hoặc cơ quan ngoài danh sách
- dẫn dắt người xem ngắm nhìn bản vẽ khoa học tinh xảo
- giọng văn cuốn hút, giàu tri thức và cảm xúc nể phục tự nhiên
- câu cuối là câu hỏi tự nhiên để kéo bình luận
- KHÔNG viết "Ảnh minh họa AI" hoặc nói ảnh là AI

3. image_prompt
- tiếng Anh
- CHỈ mô tả thêm visual detail riêng cho chủ thể, không thêm text mới
- TUYỆT ĐỐI KHÔNG chứa các từ khóa layout như: poster, infographic, headline, title, tag, badge, visual journalism
- Museum-quality scientific anatomy plate, ultra-clean educational specimen presentation
- Realistic semi-transparent cutaways showing genuine anatomical systems in place
- no logo, no watermark, no brand name, no english labels

Chỉ trả về JSON, không markdown, không giải thích.
"""
    return generate_json(
        prompt,
        system="Bạn chỉ trả về JSON hợp lệ, không markdown, không giải thích.",
    )


def generate_single_card_content(topic: dict) -> dict:
    detail_vi = topic.get("detail_vi", "").strip()
    prompt = f"""
Bạn là biên tập viên nội dung Facebook chuyên về thế giới động vật và thiên nhiên, chuyên tạo bài viết có sức hút lớn từ tiêu đề và chủ đề rộng: câu chuyện sinh tồn độc đáo, cảm xúc sâu sắc hoặc kỳ tích tự nhiên (như chim mỏ sừng, đại ca lửng mật) có tính lan truyền cao, thu hút người xem lướt qua dừng lại theo dõi.

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
- giật ngón tay, khơi gợi tò mò hoặc cảm xúc mạnh từ danh xưng/câu chuyện sinh tồn độc đáo
- tối đa 14 từ

2. overlay_title
- cực ngắn, viết hoa
- 2 đến 4 từ
- ví dụ: "ĐẠI CA LỬNG MẬT", "CHIM MỎ SỪNG", "SÁT THỦ ĐẠI DƯƠNG", "NGHỆ SĨ ĐÁY CÁT"
- KHÔNG dùng dạng Top/Top 5/xếp hạng
- KHÔNG dùng dấu câu

3. overlay_stat
- lấy trọng tâm từ fact_value
- cực ngắn, tối đa 14 ký tự nếu có thể
- ví dụ: "BẤT TỬ", "MIỄN DỊCH NỌC", "TỰ NHỐT MÌNH", "VẼ MANDALA"
- phải đúng mức độ sự thật trong fact_value/detail_vi, không phóng đại

4. overlay_hook
- 6 đến 10 từ nếu cần, tối đa 44 ký tự
- làm rõ cơ chế, quy mô, hành vi hoặc câu chuyện độc đáo
- ví dụ tốt: "Bị rắn cắn ngủ một giấc dậy ăn tiếp", "Tự giam mình trong bọng cây 4 tháng", "Vẽ mandala cát 2 mét cầu hôn"
- ví dụ không tốt: "Vua tốc độ", "Loài vật thú vị"

5. caption
- 5 đến 8 câu, khoảng 120-180 chữ
- giọng kể chuyện lôi cuốn, chạm vào cảm xúc (nể phục bản lĩnh lì lợm, xúc động trước tình mẫu tử/phụ tử, thán phục vẻ đẹp tiến hóa)
- mở đầu bằng mâu thuẫn nhận thức hoặc câu chuyện kịch tính
- giải thích cơ chế sinh học đặc biệt đằng sau sự thật
- câu cuối là câu hỏi kéo bình luận chia sẻ hoặc tranh luận sôi nổi
- KHÔNG viết "Ảnh minh họa AI", "Ảnh minh hoạ AI", hoặc bất kỳ câu nào nói ảnh là AI

6. image_prompt
- tiếng Anh
- CHỈ mô tả cảnh ảnh, KHÔNG mô tả layout poster hay chữ
- TUYỆT ĐỐI KHÔNG chứa các từ khóa: poster, infographic, headline, title, tag, badge, pill, text, visual journalism, visual journalism poster
- Award-winning wildlife documentary photography (National Geographic / BBC Earth style), razor-sharp 8k resolution
- Hero subject in its authentic natural environment, occupying 75-85% of the frame
- Capture the decisive survival moment: intense fearless posture, piercing eye contact directly facing the camera, dramatic active behavior
- Cinematic lighting: dramatic volumetric rim light, golden hour shafts, morning mist, atmospheric depth, creamy bokeh background
- Hyper-detailed organic textures: keratin horn ridges, glistening scales, coarse fur, wet skin, sharp claws
- no ranking, no list, no top 5, no panel, no table, no grid, no fake text, no extra typography
- no watermark, no logo, no english labels

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
Bạn là biên tập viên nội dung Facebook chuyên về kiến thức động vật theo hướng khoa học, dễ viral, kể chuyện như một màn đặt lên bàn cân hấp dẫn giữa hai kỳ tích tiến hóa.

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
- hấp dẫn, gây tò mò, đặt lên bàn cân cân não, tối đa 14 từ
- không cổ vũ bạo lực thật

2. overlay_title
- tiếng Việt, rất ngắn, viết hoa
- dạng so sánh hai loài bằng tiếng Việt, ví dụ: "LỬNG MẬT VS LINH CẨU", "CÁ VOI SÁT THỦ VS CÁ MẬP TRẮNG"
- tối đa 9 từ
- KHÔNG dùng tên tiếng Anh

3. caption_intro
- 5 đến 8 câu, khoảng 120-180 chữ
- mở đầu bằng một góc nhìn so sánh giả định kịch tính: hai cỗ máy tiến hóa đỉnh cao đại diện cho hai triết lý sinh tồn
- làm rõ mỗi bên mạnh ở tiêu chí nào: thể hình, tốc độ, bản lĩnh lì lợm, lực hàm, giác quan, chiến thuật bầy đàn
- CHỈ dùng tiếng Việt trong caption_intro; không chèn tên tiếng Anh nếu đã có tên tiếng Việt
- không kết luận một bên áp đảo tuyệt đối nếu hai loài khá ngang tầm
- không thay đổi số liệu
- câu cuối là câu hỏi kích hoạt người xem chọn phe tranh luận sôi nổi

4. image_prompt
- tiếng Anh
- CHỈ mô tả cảnh hai sinh vật trong môi trường tự nhiên, KHÔNG mô tả layout hay chữ
- TUYỆT ĐỐI KHÔNG chứa các từ khóa: poster, infographic, headline, title, tag, badge, pill, visual journalism, visual journalism poster
- Award-winning cinematic wildlife comparison scene: two majestic animals facing each other across a split atmospheric divide
- Primal tension created through intense eye contact, posture, scale, and lighting (dust plumes, water spray, dramatic light beams)
- No gore, no blood, no injury, no violent impact
- no watermark, no logo, no english labels

Chỉ trả về JSON, không giải thích thêm.
"""

    return generate_json(
        prompt,
        system="Bạn chỉ trả về JSON hợp lệ, không markdown, không giải thích.",
    )

