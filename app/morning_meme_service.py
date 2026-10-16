"""
Morning Animal Meme Service - Master Prompt V3.0 for 'Thế Giới Muôn Loài'
Hệ thống sáng tạo meme động vật khung giờ vàng (07:05 sáng) trên Facebook.
"""

import json
import logging
import random
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from app.config import TIMEZONE
from app.db import get_conn
from app.deepseek_service import generate_json
from app.prompt_safety import enforce_prompt_language_and_safety
from app.utils import slugify

logger = logging.getLogger(__name__)

# Master Prompt V3.0 System Prompt
MASTER_PROMPT_V3_SYSTEM = """
Bạn là Giám đốc Sáng tạo Meme, Chuyên gia Tâm lý học Hành vi mạng xã hội Việt Nam và Kỹ sư Prompt Hình ảnh AI cao cấp.
Bạn phụ trách series "Meme Động Vật Buổi Sáng" (lên sóng lúc 07:05 sáng hàng ngày) cho fanpage Thế Giới Muôn Loài.

1. VAI TRÒ & MỤC TIÊU CỐT LÕI
Mục tiêu trong mỗi lần chạy là tạo ra ĐÚNG MỘT gói nội dung meme hoàn chỉnh khiến người xem khi vừa mở mắt hoặc đang ăn sáng:
- Dừng ngón tay lướt (Thumb-stopping) trong 1.5 giây đầu tiên nhờ biểu cảm động vật cực kỳ giống người.
- Thấy "nhột" và đồng cảm sâu sắc: Nhận ra ngay bản thân, đứa bạn thân hoặc đồng nghiệp trong bức ảnh.
- Kích hoạt hành vi chia sẻ (Share/Tag): Lưu ảnh gửi ngay vào nhóm chat Zalo/Messenger công ty, hoặc tag đồng nghiệp dưới phần bình luận.
- Tệp khán giả trọng tâm: Người Việt Nam 22–35 tuổi (dân văn phòng, giáo viên, nhân viên kinh doanh, người lao động làm việc theo ca, những người đang gánh áp lực "cơm áo gạo tiền" và "kiếp trâu ngựa").
- Tone & Mood: Đời thường, châm biếm nhẹ nhàng, sắc sảo, "bất ổn một cách bình thản", sử dụng từ lóng Gen Z/Millennial tự nhiên (khum, vãi ò, kiếp trâu ngựa, cày deadline, tâm bất biến, sập nguồn, giao diện...), tuyệt đối không thô tục.

2. QUY TẮC VẬN HÀNH TỨC THỜI (ZERO-FRICTION)
- KHÔNG HỎI LẠI: Tự động lấy theo thứ thực tế trong tuần (hoặc chọn 1 ngày từ Thứ Hai đến Thứ Sáu nếu không rõ) và xuất ngay kết quả hoàn chỉnh.
- Một phát ăn ngay: Mỗi lần chạy chỉ xuất ĐÚNG MỘT phương án xuất sắc nhất. Không liệt kê danh sách lựa chọn, không chào hỏi rườm rà.
- Tạm khóa tính năng cũ: Tuyệt đối KHÔNG tạo các chủ đề về giải phẫu động vật (anatomy), X-quang, hay biểu đồ so sánh kiến thức khoa học. Chỉ tập trung 100% vào Meme Đời Thường Nhân Hóa.

3. LỊCH TÂM TRẠNG THEO THỨ (BỐI CẢNH 07:05 SÁNG)
- Thứ Hai — Khởi động kiếp trâu ngựa: Sốc tâm lý đầu tuần, mắt sưng húp, đấu tranh tư tưởng giữa việc đi làm và nộp đơn nghỉ việc, tắc đường, áo mưa kẹt xe, quên mang thẻ nhân viên.
- Thứ Ba — Cơn lốc việc phát sinh: Tưởng đã quen nhịp nhưng việc từ trên trời rơi xuống, nhóm Zalo công ty nổ tin nhắn từ 6h sáng, giao diện tỉnh táo nhưng hệ điều hành bên trong đã treo.
- Thứ Tư — Đỉnh điểm họp hành & Giao tiếp giả tạo: Cười công nghiệp với sếp/khách hàng nhưng nội tâm gào thét, đồng nghiệp mở miệng nói câu "nhờ tí", lưng và vai gáy bắt đầu biểu tình.
- Thứ Năm — Pin xã hội báo đỏ (5%): Cơ thể vẫn đi chấm công nhưng linh hồn đã xuất thần, sống nhờ hoàn toàn vào caffeine/trà sữa, đếm ngược từng giờ.
- Thứ Sáu — Tâm hồn đi nghỉ phép: Thân xác ngồi trước màn hình nhưng đầu óc đã ở quán nhậu hoặc trên giường ngủ nướng, làm việc với tốc độ rùa bò để chờ 5 giờ chiều.
- Thứ Bảy — Quyền được nằm trương thây: Ngủ tới trưa, đầu bù tóc rối, gọi đồ ăn ship tận giường, hứa dậy chạy bộ/dọn nhà nhưng chỉ nằm lướt điện thoại.
- Chủ Nhật — Nỗi ám ảnh mang tên "Sáng Mai": Chiều tối Chủ Nhật nhìn đồng hồ mà lòng lạnh ngắt, chuẩn bị quần áo đi làm trong sự bất lực.

4. THƯ VIỆN NHÂN VẬT & CHẤT LIỆU BẢN ĐỊA HÓA (HYPER-LOCAL VIBES)
- Nhân vật: Capybara (tâm bất biến), Cú mèo / Gấu trúc (mắt thâm quầng trả thù đời), Mèo (lạnh lùng, phán xét), Chó Shiba/Corgi (ngơ ngác, thảo mai), Con lười (sống chậm, trì hoãn), Chuột Hamster (cuống cuồng), Vịt / Ếch / Chim cánh cụt / Moo Deng (đứng hình, bất lực).
- Đạo cụ & tình huống Việt Nam: Ly cà phê sữa đá treo xe, ổ bánh mì gặm dở, chiếc mũ bảo hiểm lệch làm bẹp lông đầu, ngón tay đặt máy chấm công vân tay báo lỗi "xin thử lại", nhóm Zalo nổ thông báo lúc 6h sáng, đứng đợi thang máy tòa nhà...

5. CẤU TRÚC KÉP: CHỮ TRÊN ẢNH & CAPTION BÀI ĐĂNG
- Chữ chèn lên ảnh (In-Image Text / POV): 6–14 từ, đóng vai trò linh hồn meme (POV:, Khi bạn..., hoặc độc thoại nội tâm), có cú bẻ lái (twist) gây cười hoặc gây nhột ngay lập tức.
- Caption bài đăng (Facebook Status): 4–10 từ, cực ngắn, 1–2 emoji, câu bình luận bồi thêm từ Admin fanpage (không lặp lại chữ trên ảnh).
- Bình luận mồi (First Comment Seeding): 1 câu bình luận hài hước hoặc câu hỏi gợi mở để fanpage tự comment ngay lúc đăng bài (07:05), kích thích tranh luận/tag bạn bè.
- Hashtags: #TheGioiMuonLoai và 2 hashtag chủ đề liên quan.

6. TIÊU CHUẨN KỸ THUẬT IMAGE PROMPT (TIẾNG ANH)
- Phong cách: Candid photorealistic photography, shot on 85mm lens, f/2.8, shallow depth of field, natural early morning window light, ultra-detailed fur texture, raw candid photography.
- Bố cục chừa chỗ chèn chữ (Negative Space): BẮT BUỘC đặt chủ thể ở 2/3 dưới khung hình, chừa 1/3 phía trên làm khoảng trống sạch sẽ (clean, softly blurred background at the top third for text overlay).
- Tỷ lệ: aspect ratio 4:5 (tối ưu Facebook Mobile Feed).
- STRICT NO TEXT: Tuyệt đối no text, no letters, no watermark, no typography, no subtitles in the generated image.

7. BỘ LỌC 3 CỔNG (3-GATE FILTER)
- Cổng 1 (Chống trùng): Khác biệt hoàn toàn về loài vật, đạo cụ và cấu trúc câu đùa so với lịch sử gần đây.
- Cổng 2 (Độ sắc Punchline): Lược bỏ từ thừa, đọc lên trong 2 giây thấy bật cười hoặc nhột.
- Cổng 3 (Độ rõ của Ảnh): Biểu cảm tự nhiên của con vật bộc lộ rõ tâm trạng ngay cả khi chưa có chữ.

8. ĐỊNH DẠNG ĐẦU RA JSON BẮT BUỘC:
Trả về DUY NHẤT một JSON hợp lệ (không kèm markdown ngoài JSON):
{
  "concept": "Tóm tắt tình huống và điểm chạm tâm lý buổi sáng",
  "day_of_week": "Thứ...",
  "animal": "Tên loài động vật tiếng Việt",
  "animal_trait": "Nét tính cách đặc trưng",
  "situation": "Tình huống cụ thể đời thường",
  "in_image_text": "Câu chữ chèn lên khoảng trống trên ảnh (6-14 từ, có twist)",
  "caption": "Câu status Facebook cực ngắn (4-10 từ, 1-2 emoji)",
  "hashtags": ["#TheGioiMuonLoai", "#Hashtag1", "#Hashtag2"],
  "first_comment": "Bình luận mồi của Admin đăng ngay khi lên bài kích thích tương tác",
  "image_prompt": "Prompt tiếng Anh 4:5, 85mm lens, f/2.8, shallow depth of field, natural morning light, top third negative space, no text, no watermark",
  "viral_reason": "Lý do người xem sẽ đồng cảm và chia sẻ",
  "anti_repeat_log": "Tên con vật | Tình huống | Từ khóa Punchline"
}
""".strip()

WEEKDAY_INFO = [
    {
        "weekday": 0,
        "name": "Thứ Hai",
        "theme": "Khởi động kiếp trâu ngựa",
        "context": "Sốc tâm lý đầu tuần, mắt sưng húp, tắc đường, áo mưa kẹt xe, máy chấm công vân tay báo lỗi, chưa sẵn sàng nhưng vẫn phải đi cày",
        "animals": ["Trâu nước", "Cú mèo", "Gà trống", "Mèo", "Gấu trúc"],
    },
    {
        "weekday": 1,
        "name": "Thứ Ba",
        "theme": "Cơn lốc việc phát sinh",
        "context": "Tưởng đã vào guồng ai ngờ việc trên trời rơi xuống, nhóm Zalo nổ tin nhắn từ 6h sáng, giao diện tỉnh táo nhưng hệ điều hành treo",
        "animals": ["Ngựa", "Thỏ", "Hamster", "Chó Shiba"],
    },
    {
        "weekday": 2,
        "name": "Thứ Tư",
        "theme": "Đỉnh điểm họp hành & Giao tiếp giả tạo",
        "context": "Cười công nghiệp với sếp và đối tác, họp đột xuất, đồng nghiệp nhờ vả 'nhờ tí', đau lưng mỏi gáy nhưng vẫn phải thảo mai",
        "animals": ["Vịt", "Ếch", "Capybara", "Chim cánh cụt"],
    },
    {
        "weekday": 3,
        "name": "Thứ Năm",
        "theme": "Pin xã hội báo đỏ (5%)",
        "context": "Cạn kiệt năng lượng, sống nhờ caffeine ly cà phê sữa đá, đếm ngược từng giờ, thân xác online linh hồn offline",
        "animals": ["Gấu trúc", "Con lười", "Cú mèo", "Mèo"],
    },
    {
        "weekday": 4,
        "name": "Thứ Sáu",
        "theme": "Tâm hồn đi nghỉ phép",
        "context": "Thân xác chấm công nhưng đầu óc ở quán nhậu, rùa bò chờ 5h chiều, từ chối nhận việc mới cuối tuần",
        "animals": ["Khỉ", "Chó Shiba", "Hamster", "Mèo"],
    },
    {
        "weekday": 5,
        "name": "Thứ Bảy",
        "theme": "Quyền được nằm trương thây",
        "context": "Ngủ tới trưa, đầu bù tóc rối, ship đồ ăn tận giường, lời thề dậy tập thể dục vs trùm chăn ngủ nướng",
        "animals": ["Mèo Anh lông ngắn", "Con lười", "Capybara", "Gấu túi"],
    },
    {
        "weekday": 6,
        "name": "Chủ Nhật",
        "theme": "Nỗi ám ảnh mang tên 'Sáng Mai'",
        "context": "Chiều tối nhìn đồng hồ lạnh ngắt, tiếc nuối 48 tiếng trôi như 2 phút, chuẩn bị tinh thần sáng mai đi cày",
        "animals": ["Chim cánh cụt", "Cú mèo", "Mèo", "Chó"],
    },
]

# Curated seed bank of 21 Master Memes (3 per day of week) strictly adhering to Master Prompt V3.0
MORNING_MEME_BANK = [
    # ==================== THỨ HAI ====================
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_monday_water_buffalo_alarm",
        "weekday": 0,
        "day_of_week": "Thứ Hai",
        "animal": "Trâu nước",
        "animal_trait": "gánh việc, kiếp cày cuốc",
        "situation": "Đứng bất động trước gương sau khi chuông báo thức reo lần 5",
        "in_image_text": "Thân xác đã ở thứ Hai nhưng linh hồn vẫn kẹt lại chiều Chủ Nhật.",
        "caption": "Giao diện đi làm nhưng hệ điều hành đang lỗi 🥱💼",
        "hashtags": ["#TheGioiMuonLoai", "#KiepTrauNgua", "#ChaoThuHai"],
        "first_comment": "Sáng nay ai bấm hoãn báo thức trên 3 lần điểm danh lẹ để biết mình không cô đơn nào 👇🛌",
        "image_prompt": "A candid, photorealistic vertical portrait of a domestic water buffalo standing slumped in an apartment hallway, leaning against the wall with half-closed heavy eyes and a blank thousand-yard stare. Warm early morning light streaming from an open doorway. Composition places the buffalo in the lower two-thirds of the frame, leaving a clean, softly blurred neutral wall in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, hyper-realistic coarse skin and wet fur textures, natural morning light, aspect ratio 4:5, no text, no watermark, no letters.",
        "viral_reason": "Chạm đúng cảm giác choáng váng khi mở mắt sáng Thứ Hai của mọi người đi làm.",
        "anti_repeat_log": "Trâu nước | Đứng ngơ trước gương sáng thứ Hai | Thân xác vs Linh hồn",
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_monday_owl_coffee_first",
        "weekday": 0,
        "day_of_week": "Thứ Hai",
        "animal": "Cú mèo",
        "animal_trait": "thiếu ngủ kinh niên, sống nhờ caffeine",
        "situation": "Ngồi ôm ly cà phê sữa đá, mắt thâm quầng đờ đẫn",
        "in_image_text": "Xin đừng bắt chuyện với tôi trước khi ly cà phê này phát huy tác dụng.",
        "caption": "Nạp caffeine trước, đạo đức nghề nghiệp tính sau ☕🦉",
        "hashtags": ["#TheGioiMuonLoai", "#CaPheSang", "#CuDemDiLam"],
        "first_comment": "Sáng Thứ Hai này bạn cần mấy ly cà phê mới mở nổi 2 con mắt? 1 hay 2 ly? ☕👇",
        "image_prompt": "A candid, photorealistic vertical close-up of a fluffy brown owl perched beside a traditional takeaway iced milk coffee cup on a wooden work desk. The owl has enormous, round, wide-open eyes with prominent dark under-eye circles, looking utterly dazed and shell-shocked. Soft early morning golden sunlight streaming through window blinds. Composition places the owl in the lower two-thirds of the frame, leaving a clean, softly blurred top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, ultra-crisp feather details, raw candid photography, aspect ratio 4:5, no text, no letters, no watermark.",
        "viral_reason": "Đại diện chân thực nhất cho hội cú đêm phải dậy sớm sáng đầu tuần.",
        "anti_repeat_log": "Cú mèo | Ôm ly cà phê sữa đá | Đừng bắt chuyện trước khi cà phê ngấm",
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_monday_panda_rolling_out_of_bed",
        "weekday": 0,
        "day_of_week": "Thứ Hai",
        "animal": "Gấu trúc",
        "animal_trait": "uể oải, lười vận động",
        "situation": "Rơi từ trên giường xuống sàn nhưng quyết định nằm tiếp trên sàn",
        "in_image_text": "Đã lỡ lăn xuống đất rồi thì ngủ luôn dưới sàn cho tiện.",
        "caption": "Mỗi sáng dậy là một cuộc đấu tranh tư tưởng 🐼😴",
        "hashtags": ["#TheGioiMuonLoai", "#MemeCongSo", "#DiLamSom"],
        "first_comment": "Đã có ai từng ngồi ở mép giường nhìn vào hư không suốt 15 phút chưa? Thú nhận đi nào! 🤣",
        "image_prompt": "A candid, photorealistic vertical photograph of a chubby giant panda lying face down on a cozy bedroom rug next to an unmade bed, limbs completely outstretched in comical total surrender. Natural morning bedroom window light illuminating the room. Composition places the panda in the lower two-thirds of the frame, leaving a clean, softly blurred warm bedroom wall in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, hyper-detailed black and white fur, raw candid photography, aspect ratio 4:5, no text, no watermark, no letters.",
        "viral_reason": "Hình ảnh lười biếng đáng yêu mà ai cũng thấy bóng dáng mình trong đó.",
        "anti_repeat_log": "Gấu trúc | Lăn xuống sàn nằm ngủ tiếp | Đấu tranh tư tưởng dậy đi làm",
    },

    # ==================== THỨ BA ====================
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_tuesday_horse_deadline_gallop",
        "weekday": 1,
        "day_of_week": "Thứ Ba",
        "animal": "Ngựa",
        "animal_trait": "chạy deadline không kịp thở",
        "situation": "Bờm tóc dựng đứng, phi cuống cuồng vì tin nhắn Zalo nổ liên hồi",
        "in_image_text": "Tưởng Thứ Ba thong thả, ai ngờ việc từ Thứ Hai vừa rớt xuống đầu.",
        "caption": "Chưa kịp mở mắt nhóm chat công ty đã nổ 🐴💨",
        "hashtags": ["#TheGioiMuonLoai", "#DeadlineDi", "#ThuBaRoi"],
        "first_comment": "Nhóm Zalo công ty của bạn sáng nay đã nổ bao nhiêu tin nhắn gấp rồi? Kể khổ xem ai nhiều hơn! 👇📱",
        "image_prompt": "A candid, photorealistic vertical photograph of a brown horse with wild, windblown messy mane sticking up comically in every direction, galloping with wide panicked eyes and a hilarious open-mouthed expression of rushed panic. Early morning misty outdoor light. Composition focuses on the horse in the lower two-thirds of the frame, leaving a clean, softly blurred misty sky in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, sharp fur texture, raw candid photography, aspect ratio 4:5, no text, no letters, no watermark.",
        "viral_reason": "Phản ánh đúng nhịp tăng tốc bất ngờ của ngày Thứ Ba khi việc dồn lại.",
        "anti_repeat_log": "Ngựa | Chạy hớt hải sáng thứ Ba | Việc hôm qua rớt xuống đầu hôm nay",
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_tuesday_shiba_fake_confidence",
        "weekday": 1,
        "day_of_week": "Thứ Ba",
        "animal": "Chó Shiba",
        "animal_trait": "tỉnh bơ, thảo mai, tự tin vô lý",
        "situation": "Ngồi thẳng lưng nở nụ cười gượng gạo trước màn hình máy tính",
        "in_image_text": "Trong lòng đang gào thét nhưng ngoài mặt vẫn phải cười thật chuyên nghiệp.",
        "caption": "Nụ cười công nghiệp của nhân viên gương mẫu 🐕✨",
        "hashtags": ["#TheGioiMuonLoai", "#CuoiCongNghiep", "#MemeCongSo"],
        "first_comment": "Tag ngay đứa đồng nghiệp có nụ cười công nghiệp đỉnh chóp nhất công ty vô đây check var lẹ! 👇🤣",
        "image_prompt": "A candid, photorealistic vertical photograph of a Shiba Inu sitting upright on an office mesh chair, displaying an unnaturally stiff, polite squinty-eyed smile, attempting to appear completely professional despite visible inner tension. Soft natural office window lighting. Composition positions the Shiba Inu in the lower two-thirds of the frame, leaving a clean, softly blurred neutral office wall in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, ultra-sharp plush fur texture, candid humor, aspect ratio 4:5, no text, no watermark, no typography.",
        "viral_reason": "Khuôn mặt 'cười trừ' kinh điển của dân công sở khi sếp hỏi việc.",
        "anti_repeat_log": "Chó Shiba | Nụ cười công nghiệp văn phòng | Ngoài cười trong gào thét",
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_tuesday_rabbit_multitasking",
        "weekday": 1,
        "day_of_week": "Thứ Ba",
        "animal": "Thỏ",
        "animal_trait": "cuống cuồng, hớt hải",
        "situation": "Hai tai vểnh hai hướng khác nhau, hai mắt đảo liên tục vì nhiều việc gấp",
        "in_image_text": "Khi sếp nhắn: 'Tất cả các file này đều là ưu tiên số một nhé em'.",
        "caption": "Ưu tiên số 1 nhưng có tận mười cái 🐰⚡",
        "hashtags": ["#TheGioiMuonLoai", "#MemeCongSo", "#UuTienSoMot"],
        "first_comment": "Có ai từng nhận một lúc 5 việc mà sếp bảo 'cái nào cũng gấp làm liền' chưa? Trải nghiệm nhớ đời luôn! 😂",
        "image_prompt": "A comical, photorealistic vertical close-up of a fluffy white rabbit with ears comically pointed in completely opposite directions, wide bewildered eyes staring in different angles, showing hilarious sensory overload. Clean soft morning light indoors. Composition places the rabbit in the lower two-thirds of the frame, leaving a clean, softly blurred pastel wall in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, crisp whisker and fur details, raw candid photography, aspect ratio 4:5, no text, no letters, no watermark.",
        "viral_reason": "Tình huống kinh điển mà bất cứ ai đi làm công ty cũng từng trải qua.",
        "anti_repeat_log": "Thỏ | Tai vểnh hai hướng hoang mang | Sếp bảo mọi việc đều ưu tiên số 1",
    },

    # ==================== THỨ TƯ ====================
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_wednesday_duck_calm_surface",
        "weekday": 2,
        "day_of_week": "Thứ Tư",
        "animal": "Vịt",
        "animal_trait": "bình thản bên trên, đạp nước điên cuồng bên dưới",
        "situation": "Trôi lững lờ trên mặt nước nhưng hai chân quạt điên cuồng",
        "in_image_text": "Bề ngoài bình thản như không có gì, bên trong chèo chống muốn sập nguồn.",
        "caption": "Tâm bất biến giữa dòng đời vạn task 🦆🌊",
        "hashtags": ["#TheGioiMuonLoai", "#GiuaTuan", "#TamBatBien"],
        "first_comment": "Thứ Tư giữa tuần rồi anh em ơi, sạc lại năng lượng hay đang trôi bồng bềnh như bạn vịt này rồi? 👇",
        "image_prompt": "A candid, photorealistic vertical portrait of a white duck floating serenely on a calm morning pond, head held high with a deceptively peaceful, straight-faced expression while underwater bubbles hint at frantic paddling below. Soft early morning water reflection and gentle mist. Composition places the duck in the lower two-thirds of the frame, leaving a clean, softly blurred morning mist in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, crisp feather texture, natural lighting, aspect ratio 4:5, no text, no watermark, no letters.",
        "viral_reason": "Hình tượng 'chú vịt bơi' là phép ẩn dụ hoàn hảo nhất cho dân đi làm.",
        "anti_repeat_log": "Vịt | Mặt bình thản chân đạp nước | Ngoài bình thản trong sắp sập nguồn",
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_wednesday_frog_blank_stare",
        "weekday": 2,
        "day_of_week": "Thứ Tư",
        "animal": "Ếch",
        "animal_trait": "mặt ngơ, bất lực toàn tập",
        "situation": "Ngồi trên lá sen nhìn chằm chằm vào khoảng không vô định",
        "in_image_text": "Ngồi họp 2 tiếng đồng hồ và đọng lại duy nhất một chữ: Hả?",
        "caption": "Họp xong mất toi 2 tiếng cuộc đời 🐸📉",
        "hashtags": ["#TheGioiMuonLoai", "#HopHanh", "#MatNgo"],
        "first_comment": "Cuộc họp sáng nay của bạn thế nào? Giải quyết được vấn đề hay họp để chuẩn bị cho cuộc họp tiếp theo? 🤣",
        "image_prompt": "A candid, photorealistic vertical portrait of a green tree frog sitting frozen on a broad green leaf, staring straight ahead with huge, wide, blank round eyes and an utterly bewildered motionless expression. Dew drops on the leaf in soft early morning light. Composition places the frog in the lower two-thirds of the frame, leaving a clean, softly blurred background foliage in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, glistening skin texture, raw candid photography, aspect ratio 4:5, no text, no words, no watermark.",
        "viral_reason": "Khuôn mặt đần thối sau các cuộc họp vô bổ là trải nghiệm quốc dân.",
        "anti_repeat_log": "Ếch | Mắt tròn xoe đờ đẫn sau họp | Họp 2 tiếng đọng lại chữ Hả",
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_wednesday_capybara_meeting_zen",
        "weekday": 2,
        "day_of_week": "Thứ Tư",
        "animal": "Capybara",
        "animal_trait": "tâm bất biến giữa dòng đời vạn biến",
        "situation": "Ngồi nhắm mắt thiền định mặc kệ xung quanh ồn ào",
        "in_image_text": "Ai cãi nhau cứ cãi, tôi tới giờ ăn trưa là tôi đi ăn.",
        "caption": "Cảnh giới tối cao của sự mặc kệ đời 🧘🦫",
        "hashtags": ["#TheGioiMuonLoai", "#Capybara", "#MacKeDoi"],
        "first_comment": "Ở công ty bạn ai là người đạt cảnh giới 'tâm bất biến' đỉnh nhất như Capybara? Tag vô bái sư liền! 👇",
        "image_prompt": "A candid, photorealistic vertical photograph of a calm Capybara sitting peacefully with eyes gently closed, nose tilted upward with an expression of supreme zen tranquility while sitting near a cozy grassy bank. Soft morning sunlight filtering through trees. Composition places the capybara in the lower two-thirds of the frame, leaving a clean, softly blurred warm bokeh background in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, ultra-detailed bristle fur texture, candid mood, aspect ratio 4:5, no text, no watermark, no letters.",
        "viral_reason": "Capybara là biểu tượng chữa lành số 1 trên mạng xã hội hiện nay.",
        "anti_repeat_log": "Capybara | Nhắm mắt thiền định giữa ồn ào | Ai cãi cứ cãi trưa tôi đi ăn",
    },

    # ==================== THỨ NĂM ====================
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_thursday_sloth_booting_speed",
        "weekday": 3,
        "day_of_week": "Thứ Năm",
        "animal": "Con lười",
        "animal_trait": "chậm chạp, pin xã hội 5%",
        "situation": "Treo lơ lửng trên cành cây, giơ một tay lên mất 5 phút",
        "in_image_text": "Cơ thể đã đến chỗ làm nhưng não bộ vẫn đang tải 1% dữ liệu.",
        "caption": "Đường truyền tín hiệu não sáng nay hơi nghẽn 🦥⏳",
        "hashtags": ["#TheGioiMuonLoai", "#PinXaHoi5PhanTram", "#SongCham"],
        "first_comment": "Pin năng lượng sáng Thứ Năm của bạn còn bao nhiêu %? 5% hay âm phần trăm rồi? 🪫👇",
        "image_prompt": "A candid, photorealistic vertical portrait of a three-toed sloth hanging sluggishly from a sturdy tree branch, lifting one claw at an impossibly slow pace with heavy half-closed eyelids and a hilarious sleepy smile. Gentle morning sunlight filtering through soft forest leaves. Composition places the sloth in the lower two-thirds of the frame, leaving a clean, softly blurred green canopy in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, crisp coarse hair details, raw candid photography, aspect ratio 4:5, no text, no letters, no watermark.",
        "viral_reason": "Đánh trúng tình trạng 'lag não' buổi sáng Thứ Năm khi pin cơ thể cạn kiệt.",
        "anti_repeat_log": "Con lười | Treo cành cây khởi động chậm | Cơ thể đến nơi não tải 1%",
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_thursday_panda_battery_low",
        "weekday": 3,
        "day_of_week": "Thứ Năm",
        "animal": "Gấu trúc",
        "animal_trait": "cạn kiệt pin, thèm nằm",
        "situation": "Ngồi bệt tựa lưng vào tường, bụng tròn xoe phơi ra, đầu gục xuống",
        "in_image_text": "Hôm nay tôi chỉ tồn tại thôi, xin vui lòng đừng giao thêm nhiệm vụ.",
        "caption": "Trạng thái hiện tại: Đang thở là may lắm rồi 🐼🪫",
        "hashtags": ["#TheGioiMuonLoai", "#CanPin", "#ThuNamRoi"],
        "first_comment": "Hôm nay ai có trạng thái 'chỉ thở thôi đừng giao việc' giơ tay đồng cảm cái coi! 🙋‍♂️🐼",
        "image_prompt": "A candid, photorealistic vertical photograph of a chubby giant panda sitting slumped against a smooth stone wall, round belly fully relaxed forward, head tilted comically to one side with droopy eyelids of pure exhaustion. Soft natural morning daylight. Composition places the panda in the lower two-thirds of the frame, leaving a clean, softly blurred neutral wall in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, hyper-realistic fluffy fur texture, candid comedy, aspect ratio 4:5, no text, no watermark, no letters.",
        "viral_reason": "Sự mệt mỏi đáng yêu làm tan chảy và kích thích tương tác mạnh mẽ.",
        "anti_repeat_log": "Gấu trúc | Tựa tường bụng tròn gục đầu | Hôm nay chỉ tồn tại đừng giao task",
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_thursday_owl_counting_hours",
        "weekday": 3,
        "day_of_week": "Thứ Năm",
        "animal": "Cú mèo",
        "animal_trait": "đếm từng giờ để được về",
        "situation": "Nhìn chằm chằm vào chiếc đồng hồ treo tường với ánh mắt van nài",
        "in_image_text": "Thứ Năm là ngày dài nhất trong tuần, dài hơn cả Vạn Lý Trường Thành.",
        "caption": "Mỗi phút sáng nay dài như một thế kỷ 🦉⏰",
        "hashtags": ["#TheGioiMuonLoai", "#ThuNamDaiDangDac", "#NgongCuoiTuan"],
        "first_comment": "Có ai thấy Thứ Năm trôi chậm hơn cả ốc sên bò không? Nhìn đồng hồ mới 9h mà ngỡ 4h chiều! ⏳",
        "image_prompt": "A candid, photorealistic vertical portrait of a small fluffy owl perched on an indoor wooden ledge, tilting its head upwards with wide, intense, pleading circular eyes staring towards an out-of-frame wall clock. Soft morning indoor window lighting. Composition places the owl in the lower two-thirds of the frame, leaving a clean, softly blurred plain wall in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, ultra-sharp feather texture, candid photography, aspect ratio 4:5, no text, no words, no watermark.",
        "viral_reason": "Tâm lý đếm ngược chờ Thứ Sáu là điểm chung của hàng triệu người đi làm.",
        "anti_repeat_log": "Cú mèo | Ngước nhìn đồng hồ van nài | Thứ Năm dài hơn Vạn Lý Trường Thành",
    },

    # ==================== THỨ SÁU ====================
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_friday_monkey_sneaking_out",
        "weekday": 4,
        "day_of_week": "Thứ Sáu",
        "animal": "Khỉ",
        "animal_trait": "tinh ranh, đầu óc đã ở quán nhậu",
        "situation": "Đeo ba lô sẵn trên lưng từ sáng sớm, mắt liếc về phía cửa ra về",
        "in_image_text": "Thân xác ngồi trong công ty nhưng tâm hồn đã đặt bàn ở quán lẩu.",
        "caption": "Mới sáng Thứ Sáu mà đầu óc đã bay bổng 🐒🍻",
        "hashtags": ["#TheGioiMuonLoai", "#ThuSauMauChayVeTim", "#CuoiTuanToiRoi"],
        "first_comment": "Kèo tối Thứ Sáu của anh em hôm nay là gì? Về ngủ bù hay làm vài chai giải ngố? Bình luận bên dưới nào! 🍻🎉",
        "image_prompt": "A candid, photorealistic vertical photograph of a cheeky macaque monkey sitting upright on a bench with a tiny backpack strapped on, glancing slyly toward the side with mischievous sparkling eyes and an impish grin. Warm early morning light with playful shadows. Composition places the monkey in the lower two-thirds of the frame, leaving a clean, softly blurred background in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, sharp fur details, raw candid photography, aspect ratio 4:5, no text, no letters, no watermark.",
        "viral_reason": "Tâm trạng háo hức cuối tuần bùng nổ, cực dễ thu hút bình luận rủ rê.",
        "anti_repeat_log": "Khỉ | Đeo ba lô liếc cửa ra về | Thân xác ở công ty tâm hồn ở quán lẩu",
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_friday_shiba_friday_energy",
        "weekday": 4,
        "day_of_week": "Thứ Sáu",
        "animal": "Chó Shiba",
        "animal_trait": "hớn hở, không giấu nổi niềm vui",
        "situation": "Ngồi trước máy tính nhưng miệng cười toe toét không khép lại được",
        "in_image_text": "Từ chối nhận thêm mọi vấn đề phát sinh sau 10 giờ sáng nay.",
        "caption": "Thứ Sáu rồi, xin đừng làm phiền niềm vui này 🐕🎉",
        "hashtags": ["#TheGioiMuonLoai", "#ThuSauRoi", "#TuChoiNhanTask"],
        "first_comment": "Đố đứa nào dám giao task mới sau 3h chiều Thứ Sáu đấy! Tag đứa bạn hay bị giao task giờ chót vô đây cảnh cáo liền! 😂",
        "image_prompt": "A candid, photorealistic vertical photograph of a joyful Shiba Inu sitting in an office chair, mouth wide open in a genuine, uncontrollable doggy smile with eyes squeezed shut in sheer happiness. Golden morning window sunshine washing over the desk. Composition places the smiling Shiba in the lower two-thirds of the frame, leaving a clean, softly blurred bright wall in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, silky fur texture, joyful candid vibe, aspect ratio 4:5, no text, no watermark, no typography.",
        "viral_reason": "Nụ cười lây lan niềm vui giải phóng cuối tuần.",
        "anti_repeat_log": "Chó Shiba | Cười tít mắt trước máy tính | Từ chối nhận task sau 10h sáng",
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_friday_cat_ready_to_bolt",
        "weekday": 4,
        "day_of_week": "Thứ Sáu",
        "animal": "Mèo",
        "animal_trait": "tư thế sẵn sàng phóng ga về nhà",
        "situation": "Tư thế co chân chuẩn bị nhảy vọt qua rào",
        "in_image_text": "Chỉ cần đồng hồ điểm 5:00 là biến mất không để lại dấu vết.",
        "caption": "Tốc độ về nhà lúc 5h chiều: Nhanh hơn ánh sáng 🐱💨",
        "hashtags": ["#TheGioiMuonLoai", "#TanLamThoi", "#VeNhaNgu"],
        "first_comment": "Hôm nay ai có kế hoạch 5:00:01 là quẹt thẻ biến mất liền điểm danh cái coi nào! 🏃‍♂️💨",
        "image_prompt": "A candid, photorealistic vertical photograph of a sleek ginger tabby cat crouching in high alert crouch posture on a polished floor, eyes locked intensely forward with pupils dilated in focused anticipation, muscles coiled ready to spring. Warm morning ambient light. Composition places the cat in the lower two-thirds of the frame, leaving a clean, softly blurred neutral background in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, crisp whisker and fur textures, raw candid photography, aspect ratio 4:5, no text, no letters, no watermark.",
        "viral_reason": "Cảm giác canh từng giây để quẹt thẻ tan sở sáng Thứ Sáu ai cũng thấu hiểu.",
        "anti_repeat_log": "Mèo | Co chân sẵn sàng phóng | Đúng 5h chiều biến mất không dấu vết",
    },

    # ==================== THỨ BẢY ====================
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_saturday_cat_exercise_vs_bed",
        "weekday": 5,
        "day_of_week": "Thứ Bảy",
        "animal": "Mèo Anh lông ngắn béo",
        "animal_trait": "lười biếng, thất hứa với bản thân về việc dậy sớm",
        "situation": "Ngồi sụp ở mép giường lộn xộn, cạnh chiếc tạ tay nhỏ màu hồng chưa từng động tới",
        "in_image_text": "Tối qua thề sáng nay dậy chạy bộ, sáng nay chỉ thấy... chạy mất dép vào trong chăn.",
        "caption": "Ý chí thì mạnh mẽ nhưng chiếc giường lại dùng bùa ngải 🛌💤",
        "hashtags": ["#TheGioiMuonLoai", "#MemeCuoiTuan", "#ChaoBuoiSang"],
        "first_comment": "Tag ngay cái đứa tối nào cũng rủ 'mai 5h dậy tập thể dục nha' nhưng 10h trưa vẫn chưa thấy mở mắt vô đây check var lẹ anh em ơi 👇🤣",
        "image_prompt": "A candid, photorealistic vertical portrait of a chubby British Shorthair cat sitting slumped on the edge of an unmade cozy bed, leaning heavily against a white pillow like an exhausted human. The cat has extremely messy bedhead fur, half-closed drowsy eyes with a blank thousand-yard stare, and a slightly open mouth mid-yawn. Next to the cat on the bedsheet is a single small pink dumbbell untouched. Soft golden early morning sunlight streaming through sheer bedroom curtains. Composition places the cat in the lower two-thirds of the frame, leaving a clean, softly blurred warm wall in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, hyper-realistic fur texture, natural lighting, aspect ratio 4:5, no text, no watermark, no letters.",
        "viral_reason": "Đánh đúng tâm lý thề thốt tối thứ Sáu và ngủ nướng sáng thứ Bảy của dân văn phòng.",
        "anti_repeat_log": "Mèo Anh lông ngắn béo | Lời hứa tập thể dục sáng cuối tuần vs Thực tế ngủ nướng | Chạy bộ vs Chạy vào chăn",
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_saturday_sloth_doing_nothing",
        "weekday": 5,
        "day_of_week": "Thứ Bảy",
        "animal": "Con lười",
        "animal_trait": "tận hưởng quyền được lười",
        "situation": "Nằm ườn trên cành cây, tay cầm chiếc điều khiển tưởng tượng",
        "in_image_text": "Kế hoạch Thứ Bảy: Không làm gì cả và làm việc đó thật chậm rãi.",
        "caption": "Quyền năng tối thượng của ngày Thứ Bảy: Được lười 🦥🛋️",
        "hashtags": ["#TheGioiMuonLoai", "#CuoiTuanThuGian", "#QuyenDuocSongCham"],
        "first_comment": "Kế hoạch cuối tuần này của bạn là gì? Đi chơi xa hay nằm trương thây trên giường cày phim? 👇🎬",
        "image_prompt": "A candid, photorealistic vertical photograph of a content three-toed sloth sprawled horizontally across a low hammock, completely relaxed with paws dangling and a serene blissful grin on its face. Soft, dappled morning garden sunlight warming the scene. Composition places the sloth in the lower two-thirds of the frame, leaving a clean, softly blurred sunlit foliage in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, crisp coarse hair detail, peaceful candid mood, aspect ratio 4:5, no text, no letters, no watermark.",
        "viral_reason": "Tôn vinh giá trị của việc nghỉ ngơi thực sự sau tuần làm việc mệt mỏi.",
        "anti_repeat_log": "Con lười | Nằm võng cười mãn nguyện | Kế hoạch thứ Bảy là không làm gì",
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_saturday_cat_refusing_alarm",
        "weekday": 5,
        "day_of_week": "Thứ Bảy",
        "animal": "Mèo",
        "animal_trait": "bất cần, ngủ đè lên tất cả",
        "situation": "Nằm ngửa phơi bụng trắng muốt trên giường, hai chân trước duỗi thẳng buông xuôi",
        "in_image_text": "Hôm nay ai gọi điện thoại rủ đi ra đường đều là người không biết điều.",
        "caption": "Đã đóng cửa phòng, xin thế giới đừng làm phiền 🐱🛌",
        "hashtags": ["#TheGioiMuonLoai", "#MemeMeo", "#CuoiTuan"],
        "first_comment": "Sáng nay có ai tắt hết báo thức ngủ một mạch tới giờ này mới dậy mở mắt không? Thả tim điểm danh nào! 💤❤️",
        "image_prompt": "A candid, photorealistic vertical photograph of a chubby ginger tabby cat sleeping flat on its back in the middle of a messy white bed, belly fully exposed to the ceiling, paws sprawled in total relaxation, mouth slightly open. Warm morning sunlight streaming across the bedsheets. Composition places the sleeping cat in the lower two-thirds of the frame, leaving a clean, softly blurred warm headboard in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, hyper-detailed soft fur, peaceful funny mood, aspect ratio 4:5, strictly no text, no letters, no watermark.",
        "viral_reason": "Tư thế ngủ 'bất chấp đời' của mèo làm người xem thấy nhẹ nhõm ngay tức thì.",
        "anti_repeat_log": "Mèo mướp béo | Nằm ngửa phơi bụng trên giường | Ai gọi điện hôm nay là không biết điều",
    },

    # ==================== CHỦ NHẬT ====================
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_sunday_penguin_staring_horizon",
        "weekday": 6,
        "day_of_week": "Chủ Nhật",
        "animal": "Chim cánh cụt",
        "animal_trait": "vụng về, đứng nhìn xa xăm tiếc nuối",
        "situation": "Đứng một mình bên bờ băng nhìn xa xăm, cánh buông thõng tiếc ngày nghỉ",
        "in_image_text": "Chưa kịp làm gì tử tế thì 48 tiếng cuối tuần đã chuẩn bị bay màu.",
        "caption": "Ai bấm nút tua nhanh ngày Chủ Nhật vậy trời 🐧🌅",
        "hashtags": ["#TheGioiMuonLoai", "#ChuNhatTroiNhanh", "#SapLaiThuHai"],
        "first_comment": "Có ai thấy 2 ngày cuối tuần trôi nhanh như 2 phút không? Mới sáng Thứ Bảy chớp mắt đã tối Chủ Nhật! 😭",
        "image_prompt": "A candid, photorealistic vertical photograph of a solitary emperor penguin standing at the edge of an ice shelf, looking pensively out towards the vast ocean as morning light glints off the water. Its tiny flippers hang limply at its sides in a posture of humorous existential regret. Soft morning lighting with gentle golden rim accents. Composition places the penguin in the lower two-thirds of the frame, leaving a clean, softly blurred morning sky in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, sharp feather details, raw candid photography, aspect ratio 4:5, absolutely zero text, no letters, no watermark.",
        "viral_reason": "Cảm giác tiếc nuối thời gian cuối tuần là nỗi niềm chung của cả nhân loại.",
        "anti_repeat_log": "Chim cánh cụt | Đứng bờ băng cánh buông thõng | 48 tiếng cuối tuần bay màu",
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_sunday_cat_looking_at_monday",
        "weekday": 6,
        "day_of_week": "Chủ Nhật",
        "animal": "Mèo",
        "animal_trait": "ánh mắt kinh hoàng khi nghĩ về ngày mai",
        "situation": "Hai tai cụp về sau, mắt tròn xoe kinh hãi nhìn vào chiếc đồng hồ báo thức",
        "in_image_text": "Khoảnh khắc chợt nhận ra tối nay phải đi ngủ sớm để mai đi cày.",
        "caption": "Nỗi sợ mang tên 'Sáng mai lại là Thứ Hai' 🙀⏰",
        "hashtags": ["#TheGioiMuonLoai", "#MemeMeo", "#NoiSoThuHai"],
        "first_comment": "Tối nay mấy giờ bạn dự định đi ngủ? Hứa 10h nhưng lướt TikTok đến 1h sáng đúng không? Thú nhận đi! 🤣📱",
        "image_prompt": "A candid, photorealistic vertical close-up photograph of a fluffy gray cat with ears flattened backwards in comical shock, eyes dilated to huge dark circles, staring directly at the camera with comical horror and disbelief. Soft cozy indoor morning lighting. Composition places the cat in the lower two-thirds of the frame, leaving a clean, softly blurred neutral wall in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, razor-sharp fur and whisker focus, candid photography, aspect ratio 4:5, absolutely no text, no letters, no watermark.",
        "viral_reason": "Biểu cảm sốc kinh điển kích thích bão thả 'Haha' và tag bạn bè.",
        "anti_repeat_log": "Mèo xám | Mắt tròn xoe tai cụp sốc | Nhận ra tối nay phải ngủ sớm mai đi cày",
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_sunday_owl_inspecting_schedule",
        "weekday": 6,
        "day_of_week": "Chủ Nhật",
        "animal": "Cú mèo",
        "animal_trait": "thức đêm, ước mơ thay đổi lịch làm việc",
        "situation": "Đậu trên cành cây nghiêng đầu 90 độ suy tư",
        "in_image_text": "Ước gì lịch làm việc đổi thành 5 ngày nghỉ và 2 ngày đi làm.",
        "caption": "Một ước mơ nhỏ nhoi nhưng cả nhân loại đồng tình 🦉🌙",
        "hashtags": ["#TheGioiMuonLoai", "#UocMoNhoNhoi", "#CuoiTuan"],
        "first_comment": "Ai đồng ý với đề xuất 5 ngày nghỉ 2 ngày làm việc giơ 2 tay 2 chân lên tán thành liền nào! 🙋‍♂️🙋‍♀️",
        "image_prompt": "A candid, photorealistic vertical photograph of a small screech owl perched on a branch in the dim morning light, tilting its head completely sideways at a ninety-degree angle with a bewildered, questioning expression. Twilight blue atmosphere with subtle warm rim lighting. Composition places the owl in the lower two-thirds of the frame, leaving a clean, softly blurred forest canopy in the top third as negative space for text overlay. Shot on 85mm lens, f/2.8, shallow depth of field, crisp feather textures, funny inquisitive posture, aspect ratio 4:5, strictly no text, no letters, no watermark.",
        "viral_reason": "Ước mơ không của riêng ai, comment kêu gọi tán thành cực cao.",
        "anti_repeat_log": "Cú mèo | Nghiêng đầu 90 độ suy tư | Ước 5 ngày nghỉ 2 ngày làm",
    },
]

for _m in MORNING_MEME_BANK:
    if "concept" not in _m:
        _m["concept"] = f"{_m['animal']}: {_m['situation']}"
    if "punchline" not in _m:
        _m["punchline"] = _m.get("in_image_text", "")
    if "interactive_prompt" not in _m:
        _m["interactive_prompt"] = _m.get("first_comment", "")


def get_weekday_info(dt: datetime) -> dict:
    """Returns the weekday dict (0 = Thứ Hai, 6 = Chủ Nhật)."""
    weekday = dt.weekday()
    return WEEKDAY_INFO[weekday]


def get_recent_meme_history(limit: int = 7) -> list[dict]:
    """Queries DB for recent morning_meme posts to prevent repeating animals and punchlines."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT scheduled_at, topic_key, title, caption, topic_payload
        FROM posts
        WHERE topic_type = 'morning_meme'
        ORDER BY scheduled_at DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    history = []
    for r in rows:
        payload = {}
        if r["topic_payload"]:
            try:
                payload = json.loads(r["topic_payload"])
            except Exception:
                payload = {}
        history.append(
            {
                "scheduled_at": r["scheduled_at"],
                "topic_key": r["topic_key"],
                "title": r["title"],
                "caption": r["caption"],
                "animal": payload.get("animal"),
                "situation": payload.get("situation"),
                "punchline": payload.get("punchline") or payload.get("in_image_text"),
            }
        )
    return history


def generate_morning_meme_via_llm(dt: datetime, recent_history: list[dict] | None = None) -> dict | None:
    """
    Generates a single dynamic Master Prompt V3.0 morning meme via LLM (DeepSeek).
    Strictly follows Master Prompt V3.0 dual-text structure, zero-friction, and 3-gate filter.
    """
    weekday_info = get_weekday_info(dt)
    date_str = dt.strftime("%d/%m/%Y")

    history_str = "Chưa có lịch sử meme gần đây."
    recent_animals = set()
    if recent_history:
        history_pieces = []
        for idx, h in enumerate(recent_history[:5], start=1):
            animal = h.get("animal") or "Không rõ"
            recent_animals.add(animal)
            history_pieces.append(f"{idx}. Con vật: {animal} | Tình huống: {h.get('situation', '')} | In-Image: {h.get('punchline', '')}")
        history_str = "\n".join(history_pieces)

    prompt = f"""
DỮ LIỆU ĐẦU VÀO HÔM NAY (07:05 AM):
- Ngày đăng: {weekday_info['name']}, ngày {date_str}.
- Tâm trạng & bối cảnh: {weekday_info['theme']} ({weekday_info['context']}).
- Các con vật gợi ý cho ngày này: {', '.join(weekday_info['animals'])}.
- Lịch sử gần đây (CẤM LẶP LẠI LOÀI VẬT & TÌNH HUỐNG):
{history_str}

YÊU CẦU MASTER PROMPT V3.0 (XUẤT DUY NHẤT 1 PHƯƠNG ÁN XUẤT SẮC):
1. Chọn 1 loài động vật biểu cảm mạnh mẽ, KHÔNG trùng với các con vật gần đây: {', '.join(recent_animals) if recent_animals else 'chưa có'}.
2. Tình huống đời thường, siêu hài hước, mang hơi thở đời sống người đi làm Việt Nam (ly cà phê sữa đá, máy chấm công, kẹt xe, mũ bảo hiểm lệch, nhóm Zalo nổ tin nhắn...).
3. Chữ chèn lên ảnh (in_image_text): 6–14 từ, có twist bất ngờ gây cười hoặc thấy nhột.
4. Caption bài đăng (Facebook status): Cực ngắn 4–10 từ, 1–2 emoji, không lặp lại chữ trên ảnh.
5. Bình luận mồi (first_comment): 1 câu admin tự comment ngay khi đăng bài kích thích người xem tag bạn bè hoặc kể khổ.
6. Image prompt tiếng Anh 4:5 vertical, tả thật chi tiết cử chỉ nhân hóa, 85mm lens, f/2.8, shallow depth of field, raw candid photography, BẮT BUỘC chừa 1/3 phía trên làm khoảng trống sạch (negative space for text overlay). TUYỆT ĐỐI NO TEXT trong prompt.
7. Áp dụng Bộ lọc 3 cổng (chống trùng, độ sắc câu chữ, biểu cảm hài hước tự nhiên của ảnh).
""".strip()

    try:
        data = generate_json(prompt=prompt, system=MASTER_PROMPT_V3_SYSTEM, max_tokens=1500)
        if not data or not isinstance(data, dict):
            return None

        caption = data.get("caption", "").strip()
        in_image_text = data.get("in_image_text") or data.get("punchline") or ""
        in_image_text = in_image_text.strip()
        first_comment = data.get("first_comment") or data.get("interactive_prompt") or ""
        first_comment = first_comment.strip()
        image_prompt = data.get("image_prompt", "").strip()
        animal = data.get("animal", "").strip()

        if not caption or not image_prompt or not animal:
            return None

        # Validate caption word count <= 12 words
        words = caption.split()
        if len(words) > 12:
            caption = " ".join(words[:10])

        # Validate in_image_text word count <= 18 words
        if in_image_text:
            text_words = in_image_text.split()
            if len(text_words) > 20:
                in_image_text = " ".join(text_words[:18])

        # Enforce technical photography keywords & zero-text reminder in image prompt
        prompt_lower = image_prompt.lower()
        if "top third" not in prompt_lower and "negative space" not in prompt_lower:
            image_prompt += ". Composition places the subject in the lower two-thirds of the frame, leaving a clean, softly blurred background in the top third as negative space for text overlay."

        if "no text" not in prompt_lower:
            image_prompt += " Shot on 85mm lens, f/2.8, shallow depth of field, raw candid photography, aspect ratio 4:5, absolutely no text, no letters, no words, no numbers, no watermark anywhere."

        slug = slugify(f"{animal}_{weekday_info['name']}")
        topic_key = f"meme_{slug}_{dt.strftime('%Y%m%d')}"

        return {
            "topic_type": "morning_meme",
            "topic_key": topic_key,
            "weekday": weekday_info["weekday"],
            "day_of_week": weekday_info["name"],
            "animal": animal,
            "animal_trait": data.get("animal_trait", ""),
            "situation": data.get("situation", ""),
            "punchline": in_image_text,
            "in_image_text": in_image_text,
            "caption": caption,
            "hashtags": data.get("hashtags") or ["#TheGioiMuonLoai", "#MemeCongSo"],
            "first_comment": first_comment,
            "interactive_prompt": first_comment,
            "image_prompt": image_prompt,
            "viral_reason": data.get("viral_reason", ""),
            "anti_repeat_log": data.get("anti_repeat_log", f"{animal} | {data.get('situation', '')} | {in_image_text}"),
            "score": int(data.get("score", 95)),
        }
    except Exception as exc:
        logger.warning("DeepSeek dynamic morning meme generation failed: %s. Using curated bank.", exc)
        return None


def get_morning_meme_topic(dt: datetime | None = None, index: int = 0) -> dict:
    """
    Main entry point to get a Master Prompt V3.0 Morning Meme topic for a scheduled date.
    1. Determines day of week.
    2. Queries recent DB history to avoid repeats.
    3. Tries dynamic LLM generation.
    4. If LLM fails/offline, selects the best matching unposted meme from MORNING_MEME_BANK.
    """
    if dt is None:
        dt = datetime.now(ZoneInfo(TIMEZONE))

    weekday = dt.weekday()
    recent_history = get_recent_meme_history(limit=7)
    recent_keys = {h["topic_key"] for h in recent_history}
    recent_animals = {h["animal"].lower() for h in recent_history if h.get("animal")}

    # Try dynamic LLM generation first
    dynamic_topic = generate_morning_meme_via_llm(dt, recent_history)
    if dynamic_topic:
        return dynamic_topic

    # Fallback: Curated bank matched by weekday
    matching_bank = [m for m in MORNING_MEME_BANK if m.get("weekday") == weekday]
    if not matching_bank:
        matching_bank = list(MORNING_MEME_BANK)

    # Prefer items whose animal and key have not been used recently
    candidates = [
        m for m in matching_bank
        if m["topic_key"] not in recent_keys and m["animal"].lower() not in recent_animals
    ]
    if not candidates:
        candidates = [m for m in matching_bank if m["topic_key"] not in recent_keys]
    if not candidates:
        candidates = matching_bank

    chosen = dict(candidates[index % len(candidates)])
    return chosen
