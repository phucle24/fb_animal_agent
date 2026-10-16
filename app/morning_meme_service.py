"""
Morning Animal Meme Service - Master Prompt V2.0 for 'Thế Giới Muôn Loài'
Generates and manages daily 07:05 AM morning animal memes for Facebook feed.
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

# Master Prompt V2.0 System Prompt
MASTER_PROMPT_V2_SYSTEM = """
Bạn là Giám đốc sáng tạo nội dung meme, chuyên gia hài hước đời thường Việt Nam, chuyên gia tâm lý người dùng Facebook và chuyên gia viết prompt hình ảnh động vật có biểu cảm nhân hóa.
Bạn phụ trách series meme buổi sáng cho fanpage 'Thế Giới Muôn Loài'.

Mục tiêu cốt lõi:
- Người xem dừng lướt trong 3 giây đầu tiên.
- Nhận ra chính mình hoặc đồng nghiệp trong con vật.
- Bật cười, thấy nhột hoặc muốn gửi/tag người quen.
- Tự nhiên thả cảm xúc, bình luận hoặc chia sẻ.

Đối tượng: Người Việt Nam 22–35 tuổi, dân văn phòng, người đi làm sớm, chịu áp lực công việc.
Ngôn ngữ: Tiếng Việt đời thường, thông minh, dí dỏm, có thể dùng slang công sở (chấm công, deadline dí, kiếp trâu ngựa, cày cuốc, sếp gọi, họp đột xuất) nhưng không gượng ép.

Lịch nội dung theo Thứ:
- Thứ Hai: Khởi động kiếp trâu ngựa (báo thức, thiếu ngủ, mặt sưng, tắc đường, uể oải, quay lại cày cuốc).
- Thứ Ba: Deadline bắt đầu tăng tốc (tin nhắn công việc dồn dập, danh sách việc phát sinh, việc chồng việc).
- Thứ Tư: Đỉnh điểm họp hành (họp đột xuất, báo cáo tiến độ, cười bên ngoài bất lực bên trong).
- Thứ Năm: Pin xã hội còn 5% (cạn năng lượng, thèm cà phê, đếm từng giờ, thân xác online tinh thần offline).
- Thứ Sáu: Tâm hồn đã nghỉ phép (nghĩ đến cuối tuần, đầu óc đi chơi thân xác chấm công).
- Thứ Bảy: Quyền được sống chậm (ngủ nướng, ăn uống, nằm dài, trì hoãn dọn nhà, làm điều mình muốn).
- Chủ Nhật: Lo âu trước thứ Hai (tiếc ngày nghỉ, chuẩn bị đồ, mai chưa đến áp lực đã đến).

Thư viện nhân vật & tính cách:
- Mèo: lạnh lùng, bất cần, ánh mắt phán xét.
- Chó Shiba: biểu cảm tỉnh bơ, tự tin vô lý.
- Trâu: chăm chỉ, gánh việc, biểu tượng kiếp cày cuốc.
- Ngựa: chạy deadline, bận rộn, không có thời gian nghỉ.
- Gà trống: báo thức, dậy sớm, năng lượng quá mức.
- Cú mèo: thiếu ngủ, cà phê, đôi mắt thâm quầng.
- Con lười: trì hoãn, năng lượng thấp, sống chậm.
- Hamster: quay cuồng trong guồng công việc.
- Vịt: vẻ ngoài bình thản, nội tâm hỗn loạn.
- Ếch: mặt ngơ, bất lực, đứng hình.
- Capybara: bình thản trước mọi biến cố.
- Gấu trúc: uể oải, thiếu ngủ.
- Khỉ: nghịch ngợm, phản ứng lém lỉnh.
- Thỏ: cuống cuồng vì công việc.
- Chim cánh cụt: vụng về, lúng túng trong môi trường công sở.

Tiêu chuẩn Caption:
- Tiếng Việt tự nhiên.
- Tối đa 15 từ, ưu tiên 6–12 từ.
- 1 ý chính, 1 cảm xúc chủ đạo, đọc nhanh trên điện thoại.
- Không giải thích punchline.
- Tối đa 2 emoji.

Tiêu chuẩn Image Prompt (tiếng Anh):
- 4:5 vertical aspect ratio for Facebook feed.
- Mô tả chi tiết: Main subject (loài động vật, biểu cảm mắt/mặt nhân hóa rõ rệt), Action, Setting (phòng ngủ, bàn làm việc, văn phòng...), Lighting (ánh sáng tự nhiên buổi sáng hoặc cinematic), Visual style (award-winning wildlife documentary humor, National Geographic comedy wildlife standard, photorealistic textures).
- QUY TẮC BẮT BUỘC VỀ ẢNH: STRICT NO TEXT, NO LETTERS, NO WORDS, NO NUMBERS, NO WATERMARKS, NO SUBTITLES ANYWHERE. Tuyệt đối không có bất kỳ chữ nào trong ảnh. Sự hài hước đến từ biểu cảm và tình huống tự nhiên của con vật.

Quy tắc xuất định dạng JSON:
Bạn PHẢI trả về duy nhất một đối tượng JSON hợp lệ (không kèm markdown ngoài JSON):
{
  "concept": "Một câu mô tả ý tưởng cốt lõi",
  "day_of_week": "Thứ...",
  "animal": "Tên loài động vật tiếng Việt",
  "animal_trait": "Nét tính cách đặc trưng",
  "situation": "Tình huống cụ thể",
  "punchline": "Cú chốt hài hước",
  "caption": "Caption tiếng Việt tối đa 15 từ",
  "hashtags": ["#TheGioiMuonLoai", "#MemeCongSo", "#..."],
  "interactive_prompt": "Một câu hỏi hoặc gợi ý bình luận ngắn (hoặc rỗng nếu không cần)",
  "image_prompt": "Prompt tiếng Anh cực kỳ chi tiết, tỷ lệ 4:5, mô tả chủ thể, biểu cảm hài hước, bối cảnh, ánh sáng, cam kết hoàn toàn không có chữ hay watermark",
  "viral_reason": "Lý do vì sao người xem sẽ đồng cảm và muốn chia sẻ",
  "score": 92
}
""".strip()

WEEKDAY_INFO = [
    {
        "weekday": 0,
        "name": "Thứ Hai",
        "theme": "Khởi động kiếp trâu ngựa",
        "context": "Báo thức reo, thiếu ngủ, mặt sưng, tắc đường, chưa sẵn sàng nhưng vẫn phải đi làm",
        "animals": ["Trâu nước", "Cú mèo", "Gà trống", "Mèo", "Gấu trúc"],
    },
    {
        "weekday": 1,
        "name": "Thứ Ba",
        "theme": "Deadline bắt đầu tăng tốc",
        "context": "Tin nhắn công việc dồn dập, danh sách việc phát sinh, việc chồng việc, deadline dí",
        "animals": ["Ngựa", "Thỏ", "Hamster", "Chó Shiba"],
    },
    {
        "weekday": 2,
        "name": "Thứ Tư",
        "theme": "Đỉnh điểm họp hành",
        "context": "Họp đột xuất, báo cáo tiến độ, sếp hỏi, đồng nghiệp nhờ vả, cười ngoài bất lực trong",
        "animals": ["Vịt", "Ếch", "Capybara", "Chim cánh cụt"],
    },
    {
        "weekday": 3,
        "name": "Thứ Năm",
        "theme": "Pin xã hội còn 5%",
        "context": "Cạn kiệt năng lượng, thèm cà phê, đếm từng giờ trôi qua, cơ thể online tinh thần offline",
        "animals": ["Gấu trúc", "Con lười", "Cú mèo", "Mèo"],
    },
    {
        "weekday": 4,
        "name": "Thứ Sáu",
        "theme": "Tâm hồn đã nghỉ phép",
        "context": "Nghĩ đến cuối tuần trong khi việc chưa xong, ngóng giờ về, tâm hồn bay bổng nhưng thân xác vẫn chấm công",
        "animals": ["Khỉ", "Chó Shiba", "Hamster", "Mèo"],
    },
    {
        "weekday": 5,
        "name": "Thứ Bảy",
        "theme": "Quyền được sống chậm",
        "context": "Ngủ nướng, cuộn tròn trong chăn, ăn uống thoải mái, nằm dài lướt điện thoại, quyền được lười",
        "animals": ["Con lười", "Capybara", "Mèo", "Gấu túi"],
    },
    {
        "weekday": 6,
        "name": "Chủ Nhật",
        "theme": "Lo âu trước thứ Hai",
        "context": "Tối Chủ Nhật, nhìn đồng hồ đếm ngược, tiếc ngày nghỉ, mai chưa đến áp lực đã đến",
        "animals": ["Chim cánh cụt", "Cú mèo", "Mèo", "Chó"],
    },
]

# Curated seed bank of 21 Master Memes (3 per day of week) strictly adhering to Master Prompt V2.0
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
        "punchline": "Thân xác đã ở thứ Hai nhưng linh hồn vẫn kẹt lại chiều Chủ Nhật",
        "caption": "Thân xác đã thứ Hai nhưng linh hồn vẫn ở Chủ Nhật. 🥱",
        "hashtags": ["#TheGioiMuonLoai", "#MemeCongSo", "#KiepTrauNgua"],
        "interactive_prompt": "Sáng nay bạn bấm hoãn báo thức mấy lần rồi?",
        "image_prompt": "A humorous high-definition photograph of a muscular domestic water buffalo standing inside a modern apartment hallway, staring blankly ahead with heavy eyelids and an utterly defeated, sleepy facial expression. Warm early morning light streaming from a doorway. Vertical 4:5 composition, hyper-realistic coarse skin and wet fur textures, shallow depth of field, comedy wildlife documentary photography standard. Absolutely no text, no words, no letters, no numbers, no watermark anywhere.",
        "viral_reason": "Chạm đúng cảm giác choáng váng khi mở mắt sáng Thứ Hai của mọi người đi làm.",
        "score": 93,
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_monday_owl_coffee_first",
        "weekday": 0,
        "day_of_week": "Thứ Hai",
        "animal": "Cú mèo",
        "animal_trait": "thiếu ngủ kinh niên, cần cà phê",
        "situation": "Ngồi cạnh cốc cà phê bốc khói, mắt trợn tròn đờ đẫn",
        "punchline": "Đừng ai nói chuyện với tôi trước ngụm cà phê thứ hai",
        "caption": "Xin đừng nói chuyện với tôi trước ngụm cà phê thứ hai. ☕🦉",
        "hashtags": ["#TheGioiMuonLoai", "#ChaoBuoiSang", "#CanCaPhe"],
        "interactive_prompt": "Hôm nay cần mấy ly cà phê mới mở mắt nổi?",
        "image_prompt": "A comical close-up portrait of a fluffy owl perched beside a large ceramic coffee mug emitting steam on a rustic wooden desk. The owl has enormous, round, wide-open eyes with hilarious dark circles under them, looking completely dazed and exhausted. Soft morning golden sunlight through window blinds. Clean vertical 4:5 frame, ultra-crisp feather details, cinematic chiaroscuro lighting, humorous wildlife standard. Absolutely no text, no letters, no words, no watermark.",
        "viral_reason": "Đại diện chân thực nhất cho hội cú đêm phải dậy sớm sáng đầu tuần.",
        "score": 91,
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_monday_panda_rolling_out_of_bed",
        "weekday": 0,
        "day_of_week": "Thứ Hai",
        "animal": "Gấu trúc",
        "animal_trait": "uể oải, lười vận động",
        "situation": "Rơi từ trên giường xuống sàn nhưng quyết định nằm tiếp trên sàn",
        "punchline": "Đã ngã rồi thì ngủ luôn dưới sàn cho tiện",
        "caption": "Đã lỡ lăn xuống sàn rồi thì ngủ luôn dưới sàn vậy. 🐼😴",
        "hashtags": ["#TheGioiMuonLoai", "#MemeCongSo", "#DiLamSom"],
        "interactive_prompt": "Có ai từng nằm ngơ trên sàn 15 phút trước khi đi tắm không?",
        "image_prompt": "A funny candid photograph of a chubby giant panda lying face down on a soft bedroom rug next to a low bed, completely motionless with paws outstretched in total surrender. Natural morning bedroom daylight, cozy home atmosphere. Vertical 4:5 aspect ratio, hyper-detailed thick black and white fur, humorous documentary storytelling. Absolutely no text, no labels, no watermark.",
        "viral_reason": "Hình ảnh lười biếng đáng yêu mà ai cũng thấy bóng dáng mình trong đó.",
        "score": 90,
    },

    # ==================== THỨ BA ====================
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_tuesday_horse_deadline_gallop",
        "weekday": 1,
        "day_of_week": "Thứ Ba",
        "animal": "Ngựa",
        "animal_trait": "chạy deadline không kịp thở",
        "situation": "Tóc bờm dựng đứng, lao về phía trước với ánh mắt hoảng hốt",
        "punchline": "Tưởng Thứ Ba thư thả, ai ngờ việc gấp từ Thứ Hai vừa rớt xuống",
        "caption": "Tưởng Thứ Ba thong thả, ai ngờ deadline hôm qua vừa ùa tới! 🐴💨",
        "hashtags": ["#TheGioiMuonLoai", "#MemeCongSo", "#DeadlineDi"],
        "interactive_prompt": "Sáng nay hộp thư của bạn đã nổ thông báo chưa?",
        "image_prompt": "An amusing photograph of a brown horse with wild, windblown mane sticking up comically in every direction, galloping with wide panicked eyes and a hilarious open-mouthed expression of rushed urgency. Misty morning meadow setting, dramatic dynamic lighting. Vertical 4:5 layout, razor-sharp focus on the horse's expressive face, award-winning humorous nature photo standard. Absolutely no text, no letters, no watermark.",
        "viral_reason": "Phản ánh đúng nhịp tăng tốc bất ngờ của ngày Thứ Ba khi việc dồn lại.",
        "score": 92,
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_tuesday_shiba_fake_confidence",
        "weekday": 1,
        "day_of_week": "Thứ Ba",
        "animal": "Chó Shiba",
        "animal_trait": "tỉnh bơ, tự tin vô lý",
        "situation": "Ngồi thẳng lưng nở nụ cười gượng gạo trước đống hồ sơ",
        "punchline": "Trong lòng đang hoảng loạn nhưng ngoài mặt vẫn phải giữ phong thái chuyên nghiệp",
        "caption": "Trong lòng đang hoảng nhưng phong thái vẫn phải chuyên nghiệp. 🐕✨",
        "hashtags": ["#TheGioiMuonLoai", "#MemeCongSo", "#BinhTinh"],
        "interactive_prompt": "Tag ngay đứa bạn chuyên làm mặt tỉnh khi việc ngập đầu!",
        "image_prompt": "A hilarious vertical photograph of a Shiba Inu sitting upright on an office chair, wearing an unnaturally stiff, polite smile with squinted eyes, trying to look completely in control despite obvious inner stress. Natural office window light in the background. Vertical 4:5 composition, sharp plush fur texture, charming anthropomorphic expression. Absolutely no text, no words, no signs, no watermark.",
        "viral_reason": "Khuôn mặt 'cười trừ' kinh điển của dân công sở khi sếp hỏi việc.",
        "score": 94,
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_tuesday_rabbit_multitasking",
        "weekday": 1,
        "day_of_week": "Thứ Ba",
        "animal": "Thỏ",
        "animal_trait": "cuống cuồng, hớt hải",
        "situation": "Hai tai vểnh hai hướng khác nhau, hai mắt đảo liên tục",
        "punchline": "Một lúc nhận 4 task ưu tiên số 1",
        "caption": "Khi sếp bảo: 'Tất cả các việc này đều là ưu tiên số 1'. 🐰⚡",
        "hashtags": ["#TheGioiMuonLoai", "#MemeCongSo", "#UuTienSoMot"],
        "interactive_prompt": "Bạn có bao giờ gặp cảnh 'cái gì cũng gấp' chưa?",
        "image_prompt": "A comical close-up shot of a fluffy white rabbit with ears splayed in completely opposite directions, wide bewildered eyes staring in different angles, twitching nose conveying humorous sensory overload. Clean soft morning lighting, vertical 4:5 framing, crisp whisker and fur details. Absolutely zero text, no letters, no words, no watermark.",
        "viral_reason": "Tình huống kinh điển mà bất cứ ai đi làm công ty cũng từng trải qua.",
        "score": 89,
    },

    # ==================== THỨ TƯ ====================
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_wednesday_duck_calm_surface",
        "weekday": 2,
        "day_of_week": "Thứ Tư",
        "animal": "Vịt",
        "animal_trait": "vẻ ngoài bình thản, nội tâm hỗn loạn",
        "situation": "Nổi yên ả trên mặt nước nhưng dưới nước hai chân quạt điên cuồng",
        "punchline": "Bên ngoài nở nụ cười 'dạ vâng', bên trong chân đạp muốn gãy",
        "caption": "Ngoài mặt 'dạ vâng em nghe', bên trong hoảng loạn cực độ. 🦆🌊",
        "hashtags": ["#TheGioiMuonLoai", "#MemeCongSo", "#HopHanh"],
        "interactive_prompt": "Ai đang trong một cuộc họp mà đầu óc trôi dạt tận đâu rồi?",
        "image_prompt": "A humorous photograph of a white duck floating placidly on a calm pond with a smug, stone-faced expression, while subtle water ripples suggest vigorous unseen paddling beneath. Crisp morning light reflecting off the water. Vertical 4:5 composition, sharp feather details, peaceful yet comically secretive atmosphere. Absolutely no text, no subtitles, no watermark.",
        "viral_reason": "Hình ảnh ẩn dụ hoàn hảo cho tâm thế 'bình tĩnh giả tạo' giữa tuần.",
        "score": 95,
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_wednesday_capybara_meeting_zen",
        "weekday": 2,
        "day_of_week": "Thứ Tư",
        "animal": "Capybara",
        "animal_trait": "bình thản trước mọi biến cố, miễn nhiễm drama",
        "situation": "Ngồi thiền giữa đám đông ồn ào hỗn loạn, mắt lim dim",
        "punchline": "Cuộc họp kéo dài tiếng thứ hai và tôi đã đạt cảnh giới giác ngộ",
        "caption": "Cuộc họp kéo dài tiếng thứ hai và tôi đã đạt cảnh giới giác ngộ. 🧘‍♂️🗿",
        "hashtags": ["#TheGioiMuonLoai", "#Capybara", "#KiepCongSo"],
        "interactive_prompt": "Tag đồng nghiệp có khả năng ngồi im như tượng trong mọi cuộc họp!",
        "image_prompt": "A hilarious photograph of a calm, plump capybara sitting completely zen and motionless with eyes closed peacefully, unbothered by surrounding birds and commotion. Gentle morning sunlight, lush grass setting. Clean vertical 4:5 frame, hyper-realistic bristly fur, funny stoic demeanor. Absolutely no text, no labels, no watermark.",
        "viral_reason": "Năng lượng 'bộ trưởng bộ ngoại giao' của Capybara luôn viral mạnh mẽ.",
        "score": 96,
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_wednesday_frog_stare_blank",
        "weekday": 2,
        "day_of_week": "Thứ Tư",
        "animal": "Ếch",
        "animal_trait": "mặt ngơ, bất lực, đứng hình",
        "situation": "Ngồi chồm hổm trên lá sen, mắt lồi nhìn chằm chằm vào khoảng không vô định",
        "punchline": "Đang nghe sếp giao việc nhưng bộ não đã từ chối tiếp nhận dữ liệu",
        "caption": "Bộ não đã tự động bật chế độ từ chối tiếp nhận thông tin. 🐸📴",
        "hashtags": ["#TheGioiMuonLoai", "#MemeCongSo", "#DungHinh"],
        "interactive_prompt": "Có ai vừa bị đứng hình mất 5 giây giống chú ếch này không?",
        "image_prompt": "A funny macro photograph of a green tree frog sitting frozen on a large leaf, with bulging round eyes staring completely blankly into the distance with zero thoughts behind them. Soft morning dew drops, clean natural lighting. Vertical 4:5 aspect ratio, detailed glossy skin texture, humorous catatonic expression. Strictly no text, no letters, no watermark.",
        "viral_reason": "Gương mặt 'đơ toàn tập' cực kỳ dễ thương và dễ đồng cảm.",
        "score": 91,
    },

    # ==================== THỨ NĂM ====================
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_thursday_sloth_low_battery",
        "weekday": 3,
        "day_of_week": "Thứ Năm",
        "animal": "Con lười",
        "animal_trait": "năng lượng thấp, sống chậm, pin 5%",
        "situation": "Treo lơ lửng trên cành cây, với tay lấy chiếc lá nhưng mãi chưa tới",
        "punchline": "Tốc độ xử lý công việc hôm nay phụ thuộc vào lượng pin còn lại",
        "caption": "Pin năng lượng còn 5%, xin vui lòng cắm sạc trước khi giao việc. 🦥🔋",
        "hashtags": ["#TheGioiMuonLoai", "#MemeCongSo", "#PinYeu"],
        "interactive_prompt": "Hôm nay pin năng lượng của bạn còn bao nhiêu %?",
        "image_prompt": "A comical vertical photograph of a three-toed sloth hanging upside down on a branch, reaching one claw forward in extreme slow motion with heavy, half-shut sleepy eyes and a faint resigned smile. Warm morning jungle canopy light, soft bokeh background. Vertical 4:5 composition, hyper-realistic shaggy fur textures, comedy wildlife standard. Absolutely no text, no words, no watermark.",
        "viral_reason": "Trúng tim đen trạng thái cạn pin của người đi làm vào Thứ Năm.",
        "score": 93,
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_thursday_cat_judging_exhaustion",
        "weekday": 3,
        "day_of_week": "Thứ Năm",
        "animal": "Mèo",
        "animal_trait": "lạnh lùng, ánh mắt phán xét",
        "situation": "Nằm bẹp trên bàn phím, mắt lim dim phán xét người đang gõ",
        "punchline": "Nhìn bạn cố cày cuốc nốt Thứ Năm mà tôi thấy mệt giùm",
        "caption": "Nhìn bạn cố cày cuốc nốt hôm nay mà tôi thấy mệt giùm. 🐱😑",
        "hashtags": ["#TheGioiMuonLoai", "#MemeMeo", "#KiepCongSo"],
        "interactive_prompt": "Nuôi mèo để nó an ủi, ai ngờ nó chỉ phán xét!",
        "image_prompt": "A humorous close-up photograph of a chubby British Shorthair cat sprawled completely flat across an office desk, resting its chin on the surface while narrowing its eyes in a condescending, deeply unimpressed gaze. Soft morning ambient window light. Vertical 4:5 frame, ultra-detailed fur, funny judgment expression. Absolutely no text, no letters, no watermark.",
        "viral_reason": "Mèo phán xét luôn là nam châm hút comment và share cực mạnh trên Facebook.",
        "score": 95,
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_thursday_panda_sitting_sigh",
        "weekday": 3,
        "day_of_week": "Thứ Năm",
        "animal": "Gấu trúc",
        "animal_trait": "thở dài, buông xuôi tạm thời",
        "situation": "Ngồi dựa lưng vào tảng đá, hai tay buông thõng thở dài",
        "punchline": "Cố gắng sống sót qua ngày Thứ Năm để đón chào Thứ Sáu",
        "caption": "Ráng sống sót qua nốt hôm nay là thiên đường mở ra rồi. 🐼⏳",
        "hashtags": ["#TheGioiMuonLoai", "#MemeCongSo", "#RangLen"],
        "interactive_prompt": "Đếm ngược còn bao nhiêu tiếng nữa là hết tuần?",
        "image_prompt": "A funny vertical photo of a giant panda sitting slouched against a stone wall, belly sticking out roundly, paws resting lazily on the ground with an expression of existential fatigue. Morning daylight filtering through bamboo leaves. Vertical 4:5 framing, realistic fur textures, humorous relatable posture. Absolutely no text, no letters, no watermark.",
        "viral_reason": "Tâm lý đếm ngược chờ Thứ Sáu của tất cả mọi người.",
        "score": 90,
    },

    # ==================== THỨ SÁU ====================
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_friday_monkey_sneaking_out",
        "weekday": 4,
        "day_of_week": "Thứ Sáu",
        "animal": "Khỉ",
        "animal_trait": "lém lỉnh, ngóng giờ về",
        "situation": "Núp sau thân cây, hé nửa mặt liếc nhìn đồng hồ rồi mỉm cười gian xảo",
        "punchline": "Mới 9 giờ sáng nhưng tâm hồn đã đặt chân vào quán bia",
        "caption": "Mới 9h sáng nhưng tâm hồn đã ngồi ở quán ăn cuối tuần rồi. 🐒🍻",
        "hashtags": ["#TheGioiMuonLoai", "#ThuSauMauChayVeTim", "#MemeCongSo"],
        "interactive_prompt": "Tối nay hẹn hò ở đâu, ai đã lên kèo xong chưa?",
        "image_prompt": "A mischievous, funny photograph of a small monkey peeking out from behind a tree trunk, with a wide cheeky grin and cunning eyes darting sideways as if sneaking away early. Bright sunny morning forest lighting. Vertical 4:5 aspect ratio, sharp facial details, expressive comedic character. Absolutely no text, no letters, no numbers, no watermark.",
        "viral_reason": "Tâm trạng háo hức cuối tuần bùng nổ của ngày Thứ Sáu.",
        "score": 94,
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_friday_hamster_countdown",
        "weekday": 4,
        "day_of_week": "Thứ Sáu",
        "animal": "Hamster",
        "animal_trait": "nhồi nhét cho nhanh để được về",
        "situation": "Hai má phúng phính nhét đầy hạt hướng dương, mắt lấp lánh hy vọng",
        "punchline": "Cố làm cho xong việc nhanh gấp 3 lần bình thường để đúng 5h về",
        "caption": "Tốc độ làm việc ngày Thứ Sáu bỗng nhiên nhanh gấp ba lần. 🐹⚡",
        "hashtags": ["#TheGioiMuonLoai", "#MemeCongSo", "#NgongGioVe"],
        "interactive_prompt": "Đúng 5h chiều nay bạn có đứng dậy ngay lập tức không?",
        "image_prompt": "An adorable, comical photograph of a golden hamster with absurdly stuffed, puffed-out cheeks full of sunflower seeds, sitting upright with sparkling eager eyes and tiny paws clutched together in hopeful excitement. Warm morning indoor light. Vertical 4:5 frame, ultra-macro fluffy fur details. Absolutely no text, no letters, no watermark.",
        "viral_reason": "Sự phấn khích tột cùng của Thứ Sáu được thể hiện qua má bánh bao phúng phính.",
        "score": 92,
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_friday_shiba_happy_walk",
        "weekday": 4,
        "day_of_week": "Thứ Sáu",
        "animal": "Chó Shiba",
        "animal_trait": "hớn hở, tung tăng",
        "situation": "Bước đi nhún nhảy trên vỉa hè với nụ cười rạng rỡ",
        "punchline": "Cùng một con đường đi làm nhưng hôm nay đi nhẹ như bay",
        "caption": "Cùng con đường đi làm mà sao hôm nay bước chân nhẹ như bay. 🐕🌈",
        "hashtags": ["#TheGioiMuonLoai", "#ThuSauVuiVe", "#ChaoBuoiSang"],
        "interactive_prompt": "Năng lượng sáng Thứ Sáu có khác hẳn sáng Thứ Hai không?",
        "image_prompt": "A joyful, hilarious vertical photo of a Shiba Inu happily prancing down a sunny morning street sidewalk, ears perked, tongue out in a goofy beaming smile, paws frozen mid-bounce. Golden morning sunlight, urban park background. Vertical 4:5 layout, crisp fur texture, infectious happy mood. Strictly zero text, no letters, no watermark.",
        "viral_reason": "Truyền năng lượng tích cực, người xem nhìn vào là muốn cười theo.",
        "score": 91,
    },

    # ==================== THỨ BẢY ====================
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_saturday_sloth_bed_burrito",
        "weekday": 5,
        "day_of_week": "Thứ Bảy",
        "animal": "Con lười",
        "animal_trait": "trì hoãn, sống chậm, quyền được lười",
        "situation": "Cuộn tròn như chiếc bánh burrito trong chăn, chỉ thò mỗi mũi và mắt lim dim",
        "punchline": "Thứ Bảy sinh ra là để nằm, không phải để vội",
        "caption": "Thứ Bảy mà bắt dậy sớm là một tội ác. 😴💤",
        "hashtags": ["#TheGioiMuonLoai", "#QuyenDuocSongCham", "#NguNuong"],
        "interactive_prompt": "Hôm nay dự định mấy giờ bạn mới chịu rời khỏi giường?",
        "image_prompt": "An ultra-detailed, humorous photograph of an adorable sloth completely wrapped like a cozy burrito inside a soft knitted blanket on a warm bed. Only its sleepy face with half-closed eyes and peaceful, satisfied smile peeks out. Soft morning golden sunbeams filter through window curtains. Clean vertical 4:5 composition, shallow depth of field, warm cinematic lighting, ultra-realistic fur textures, comedy wildlife documentary photography standard. Absolutely no text, no letters, no words, no numbers, no watermarks anywhere in the image.",
        "viral_reason": "Đánh trúng tâm lý thèm ngủ nướng của tất cả người đi làm vào sáng Thứ Bảy.",
        "score": 97,
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_saturday_capybara_spa_orange",
        "weekday": 5,
        "day_of_week": "Thứ Bảy",
        "animal": "Capybara",
        "animal_trait": "hưởng thụ, thư giãn tuyệt đối",
        "situation": "Ngâm mình trong bồn nước ấm với quả cam đặt ngay ngắn trên đầu",
        "punchline": "Cả tuần cày cuốc, Thứ Bảy là quyền được bất động",
        "caption": "Cả tuần cày cuốc, Thứ Bảy là quyền được nằm im hưởng thụ. 🛀🍊",
        "hashtags": ["#TheGioiMuonLoai", "#Capybara", "#CuoiTuanThuGian"],
        "interactive_prompt": "Hôm nay bạn định dành bao nhiêu tiếng để nằm lướt điện thoại?",
        "image_prompt": "A delightfully funny vertical photograph of a calm, contented capybara soaking in a wooden hot spring tub with gentle steam rising, balancing a bright orange perfectly on top of its head, eyes blissfully shut in absolute luxury. Soft morning mist and serene garden greenery background. Vertical 4:5 framing, realistic wet bristly fur, award-winning comedy wildlife style. Absolutely no text, no labels, no watermark.",
        "viral_reason": "Iconic Capybara onsen meme - biểu tượng tối thượng của sự thảnh thơi cuối tuần.",
        "score": 96,
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_saturday_cat_refusing_alarm",
        "weekday": 5,
        "day_of_week": "Thứ Bảy",
        "animal": "Mèo",
        "animal_trait": "bất cần, ngủ đè lên tất cả",
        "situation": "Nằm ngửa phơi bụng trắng muốt trên giường, hai chân trước duỗi thẳng buông xuôi",
        "punchline": "Hôm nay ai gọi điện thoại cũng là người không biết điều",
        "caption": "Hôm nay ai gọi điện thoại đều là người không biết điều. 🐱🛌",
        "hashtags": ["#TheGioiMuonLoai", "#MemeMeo", "#CuoiTuan"],
        "interactive_prompt": "Tắt chuông báo thức chưa các đồng chí?",
        "image_prompt": "A humorous vertical photograph of a chubby ginger tabby cat sleeping flat on its back in the middle of a messy white bed, belly fully exposed to the ceiling, paws sprawled in total relaxation, mouth slightly open. Warm morning sunlight streaming across the bedsheets. Vertical 4:5 aspect ratio, hyper-detailed soft fur, peaceful funny mood. Strictly no text, no letters, no watermark.",
        "viral_reason": "Tư thế ngủ 'bất chấp đời' của mèo làm người xem thấy nhẹ nhõm ngay tức thì.",
        "score": 93,
    },

    # ==================== CHỦ NHẬT ====================
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_sunday_penguin_staring_horizon",
        "weekday": 6,
        "day_of_week": "Chủ Nhật",
        "animal": "Chim cánh cụt",
        "animal_trait": "vụng về, đứng nhìn xa xăm tiếc nuối",
        "situation": "Đứng một mình bên bờ băng nhìn hoàng hôn buông xuống, cánh buông thõng",
        "punchline": "Chưa kịp làm gì thì 48 tiếng cuối tuần đã chuẩn bị kết thúc",
        "caption": "Chưa kịp làm gì thì cuối tuần đã chuẩn bị trôi qua rồi. 🐧🌅",
        "hashtags": ["#TheGioiMuonLoai", "#ChuNhatBuon", "#LaiSapThuHai"],
        "interactive_prompt": "Có ai thấy 2 ngày cuối tuần trôi nhanh như 2 phút không?",
        "image_prompt": "A comical and poignant vertical photograph of a solitary emperor penguin standing at the edge of an ice shelf, looking pensively out towards the vast ocean as the afternoon sun begins to lower. Its tiny flippers hang limply at its sides in a posture of humorous existential regret. Soft golden hour lighting, cold blue tones. Vertical 4:5 composition, sharp feather details. Absolutely zero text, no letters, no watermark.",
        "viral_reason": "Cảm giác tiếc nuối thời gian cuối tuần là nỗi niềm chung của cả nhân loại.",
        "score": 94,
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_sunday_cat_looking_at_monday",
        "weekday": 6,
        "day_of_week": "Chủ Nhật",
        "animal": "Mèo",
        "animal_trait": "ánh mắt kinh hoàng khi nghĩ về ngày mai",
        "situation": "Hai tai cụp về sau, mắt tròn xoe kinh hãi nhìn vào hư không",
        "punchline": "Khoảnh khắc chợt nhận ra tối nay phải đi ngủ sớm để mai đi cày",
        "caption": "Khoảnh khắc nhận ra tối nay phải ngủ sớm mai đi cày. 🙀⏰",
        "hashtags": ["#TheGioiMuonLoai", "#MemeMeo", "#NoiSoThuHai"],
        "interactive_prompt": "Bạn đã chuẩn bị tinh thần cho sáng mai chưa?",
        "image_prompt": "A hilarious vertical close-up photograph of a fluffy gray cat with ears flattened backwards in shock, eyes dilated to huge dark circles, staring directly at the camera with comical horror and disbelief. Soft cozy indoor lighting. Vertical 4:5 aspect ratio, razor-sharp fur and whisker focus, dramatic lighting. Absolutely no text, no letters, no watermark.",
        "viral_reason": "Biểu cảm sốc kinh điển kích thích bão thả 'Haha' và tag bạn bè.",
        "score": 95,
    },
    {
        "topic_type": "morning_meme",
        "topic_key": "meme_sunday_owl_inspecting_schedule",
        "weekday": 6,
        "day_of_week": "Chủ Nhật",
        "animal": "Cú mèo",
        "animal_trait": "thức đêm, lo âu tương lai",
        "situation": "Đậu trên cành cây ban đêm, đầu nghiêng 90 độ khó hiểu",
        "punchline": "Ước gì một tuần có 5 ngày nghỉ và 2 ngày làm việc",
        "caption": "Ước gì tuần có 5 ngày nghỉ và 2 ngày làm việc thôi. 🦉🌙",
        "hashtags": ["#TheGioiMuonLoai", "#UocMoNhoNhoi", "#CuoiTuan"],
        "interactive_prompt": "Ai đồng ý với thời khóa biểu này giơ tay!",
        "image_prompt": "A humorous photograph of a small screech owl perched on a branch in the dim evening light, tilting its head completely sideways at a ninety-degree angle with a bewildered, questioning expression. Twilight blue atmosphere with subtle warm rim lighting. Vertical 4:5 composition, crisp feather textures, funny inquisitive posture. Strictly no text, no letters, no watermark.",
        "viral_reason": "Ước mơ không của riêng ai, comment kêu gọi tán thành cực cao.",
        "score": 92,
    },
]

for _m in MORNING_MEME_BANK:
    if "concept" not in _m:
        _m["concept"] = f"{_m['animal']}: {_m['situation']}"


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
    conn.close()

    history = []
    for r in rows:
        payload = {}
        if r["topic_payload"]:
            try:
                payload = json.loads(r["topic_payload"])
            except Exception:
                pass
        history.append(
            {
                "scheduled_at": r["scheduled_at"],
                "topic_key": r["topic_key"],
                "animal": payload.get("animal", ""),
                "situation": payload.get("situation", ""),
                "punchline": payload.get("punchline", ""),
                "caption": r["caption"],
            }
        )
    return history


def generate_morning_meme_via_llm(dt: datetime, recent_history: list[dict] | None = None) -> dict | None:
    """
    Calls DeepSeek LLM with Master Prompt V2.0 to dynamically create a new morning meme
    tailored to the specific day of week, strictly avoiding recent animals & situations.
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
            history_pieces.append(f"{idx}. Con vật: {animal} | Tình huống: {h.get('situation', '')} | Caption: {h.get('caption', '')}")
        history_str = "\n".join(history_pieces)

    prompt = f"""
DỮ LIỆU ĐẦU VÀO HÔM NAY:
- Ngày đăng: {weekday_info['name']}, ngày {date_str}.
- Định hướng theo thứ: {weekday_info['theme']} ({weekday_info['context']}).
- Các con vật gợi ý cho ngày này: {', '.join(weekday_info['animals'])}.
- Các con vật hoặc meme gần đây (CẤM LẶP LẠI):
{history_str}

YÊU CẦU:
1. Tạo ĐÚNG MỘT meme mới toanh cho ngày {weekday_info['name']}.
2. Chọn một loài động vật biểu cảm mạnh mẽ, KHÔNG trùng với các con vật gần đây: {', '.join(recent_animals) if recent_animals else 'chưa có'}.
3. Tình huống đời thường, siêu hài hước, trúng tâm lý người xem.
4. Caption tiếng Việt thông minh, tự nhiên, TỐI ĐA 15 TỪ, 1-2 emoji.
5. Image prompt tiếng Anh 4:5 vertical, tả thật chi tiết cử chỉ hài hước nhân hóa, ánh sáng buổi sáng, ĐẶC BIỆT CAM KẾT KHÔNG CÓ BẤT KỲ CHỮ/TEXT/WATERMARK NÀO TRONG ẢNH.
6. Chấm điểm theo hệ thống (phải đạt >= 80/100).
""".strip()

    try:
        data = generate_json(prompt=prompt, system=MASTER_PROMPT_V2_SYSTEM, max_tokens=1500)
        if not data or not isinstance(data, dict):
            return None

        caption = data.get("caption", "").strip()
        image_prompt = data.get("image_prompt", "").strip()
        animal = data.get("animal", "").strip()

        if not caption or not image_prompt or not animal:
            return None

        # Validate caption word count <= 15
        words = caption.split()
        if len(words) > 16:
            # Trim gently if slightly over
            caption = " ".join(words[:15])

        # Enforce zero-text reminder in image prompt
        if "no text" not in image_prompt.lower():
            image_prompt += ". Clean vertical 4:5 aspect ratio. Absolutely no text, no letters, no words, no numbers, no watermarks anywhere."

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
            "punchline": data.get("punchline", ""),
            "caption": caption,
            "hashtags": data.get("hashtags") or ["#TheGioiMuonLoai", "#MemeCongSo"],
            "interactive_prompt": data.get("interactive_prompt", ""),
            "image_prompt": image_prompt,
            "viral_reason": data.get("viral_reason", ""),
            "score": int(data.get("score", 90)),
        }
    except Exception as exc:
        logger.warning("DeepSeek dynamic morning meme generation failed: %s. Using curated bank.", exc)
        return None


def get_morning_meme_topic(dt: datetime | None = None, index: int = 0) -> dict:
    """
    Main entry point to get a Master Prompt V2.0 Morning Meme topic for a scheduled date.
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
