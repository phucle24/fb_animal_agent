# FB Animal Agent

Agent tạo bài Facebook tự động cho fanpage động vật/thực vật:

- Text/topic/caption: `deepseek-v4-flash`
- Image/full infographic: `gemini-2.5-flash-image`
- DeepSeek sinh nội dung và prompt; Gemini image model render ảnh final có chữ theo prompt
- Chủ đạo topic so sánh / Top 5
- Dashboard Flask để preview, tạo lịch tuần, đăng thủ công, reset trạng thái
- Dùng bộ biến môi trường riêng với prefix `ANIMAL_AGENT_`

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Điền các biến trong `.env`:

- `ANIMAL_AGENT_GEMINI_API_KEY`
- `ANIMAL_AGENT_DEEPSEEK_API_KEY`
- `ANIMAL_AGENT_FB_PAGE_ID`
- `ANIMAL_AGENT_FB_PAGE_TOKEN`
- `ANIMAL_AGENT_FB_GRAPH_VERSION`

## Init DB

```bash
python scripts/init_db.py
```

## Chạy website dashboard

```bash
python scripts/run_web.py
```

Mặc định dashboard chạy tại:

```text
http://127.0.0.1:8000
```

## Tạo trước bài viết 7 ngày

Qua dashboard: bấm `Tạo lịch tuần`.

Hoặc chạy CLI:

```bash
python scripts/prepare_weekly_posts.py
```

## Tạo trước bài viết bằng Gemini Batch API

Batch API dùng cho ảnh infographic final bất đồng bộ, rẻ hơn standard image generation nhưng không có kết quả ngay.

Qua dashboard:

1. Bấm `Tạo tuần Batch`
2. Chờ batch xử lý
3. Bấm `Poll Batch ảnh` để tải ảnh final về và chuyển bài sang `READY`

Hoặc chạy CLI:

```bash
python scripts/prepare_weekly_posts_batch.py
python scripts/poll_batch_images.py
```

Cron gợi ý:

```cron
0 2 * * * cd /root/fb_animal_agent && /root/fb_animal_agent/venv/bin/python scripts/ensure_future_posts_batch.py >> logs/agent.log 2>&1
15 */6 * * * cd /root/fb_animal_agent && /root/fb_animal_agent/venv/bin/python scripts/poll_batch_images.py >> logs/agent.log 2>&1
*/15 * * * * cd /root/fb_animal_agent && /root/fb_animal_agent/venv/bin/python scripts/publish_due_posts.py all >> logs/agent.log 2>&1
```

Trạng thái liên quan:

- `WAITING_IMAGE`: đã có caption/prompt, đang chờ ảnh batch
- `READY`: đã có ảnh final, sẵn sàng đăng Facebook
- `IMAGE_FAILED`: batch hoặc lưu ảnh lỗi

Ảnh mới dùng `ANIMAL_AGENT_IMAGE_ASPECT_RATIO=4:5`; đây là tỉ lệ dọc hợp với Facebook feed và infographic Top 5.

### Reset batch/job cũ chưa đăng

Xóa toàn bộ bài chưa đăng (`READY`, `WAITING_IMAGE`, `IMAGE_FAILED`, `FAILED`, `SKIPPED`) và file ảnh liên quan, giữ lại bài `POSTED`:

```bash
python scripts/reset_unposted_posts.py --cancel-batches
```

Sau đó tạo batch mới:

```bash
python scripts/ensure_future_posts_batch.py
```

## Hashtag mặc định

Caption bài mới tự thêm:

```text
#thegioimuonloai #topdongbat #reivewthegioidongvat #khamphatunhien
```

Muốn cập nhật caption các bài đã tạo nhưng chưa đăng:

```bash
python scripts/add_hashtags_to_existing_posts.py
```

## Tạo 1 bài test local

Điền `ANIMAL_AGENT_GEMINI_API_KEY` trong `.env`, sau đó dùng dashboard bấm `Tạo 1 bài test`.

Hoặc chạy CLI:

```bash
python scripts/create_test_post.py
```

Bài test dùng topic index `0` mặc định. Muốn đổi topic:

```bash
python scripts/create_test_post.py 1
```

Nếu chỉ muốn test caption dù Gemini image đang lỗi:

```bash
python scripts/create_test_post.py --allow-placeholder
```

## Preview bài

Qua dashboard: mở từng bài để xem ảnh final, caption, text fields, image prompt.

Hoặc chạy CLI:

```bash
python scripts/preview_posts.py
```

## Đăng bài đến hạn

```bash
python scripts/publish_due_posts.py all
python scripts/publish_due_posts.py morning
python scripts/publish_due_posts.py evening
```

Lịch sinh bài mặc định:

- Thứ 2 đến Thứ 6: `08:15` và `20:30`
- Thứ 7: `09:15` và `21:00`
- Chủ nhật: `09:15` và `20:30`

Nếu đã có bài tương lai đang dùng giờ cũ, xem trước lịch mới:

```bash
python scripts/reschedule_future_posts.py
```

Áp dụng lịch mới cho các bài tương lai chưa đăng:

```bash
python scripts/reschedule_future_posts.py --apply
```

Nếu không muốn dời bài nào vào slot còn lại của hôm nay, dùng:

```bash
python scripts/reschedule_future_posts.py --start-tomorrow --apply
```

## Cron VPS

```cron
0 2 * * * cd /root/fb_animal_agent && /root/fb_animal_agent/venv/bin/python scripts/ensure_future_posts_batch.py >> logs/agent.log 2>&1
15 */6 * * * cd /root/fb_animal_agent && /root/fb_animal_agent/venv/bin/python scripts/poll_batch_images.py >> logs/agent.log 2>&1
*/15 * * * * cd /root/fb_animal_agent && /root/fb_animal_agent/venv/bin/python scripts/publish_due_posts.py all >> logs/agent.log 2>&1
```

## Deploy VPS với Batch API

VPS tối thiểu khuyến nghị:

- Ubuntu 22.04 hoặc 24.04 LTS
- 1 vCPU
- 1 GB RAM
- 10-20 GB SSD
- Python 3.10+

Với agent này, CPU/RAM không quan trọng nhiều vì Gemini/Facebook chạy qua API. VPS rẻ 4-6 USD/tháng là đủ.

### 1. Cài dependencies hệ thống

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip fonts-noto-core
```

### 2. Đặt source vào `/root/fb_animal_agent`

```bash
cd /root/fb_animal_agent
```

Copy source project lên thư mục này bằng `scp`, `rsync`, hoặc `git clone`.

### 3. Tạo venv và env

```bash
cd /root/fb_animal_agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Điền `.env`:

```env
ANIMAL_AGENT_GEMINI_API_KEY=...
ANIMAL_AGENT_GEMINI_IMAGE_MODEL=gemini-2.5-flash-image
ANIMAL_AGENT_IMAGE_FALLBACK_ON_ERROR=false
ANIMAL_AGENT_IMAGE_ASPECT_RATIO=4:5

ANIMAL_AGENT_DEEPSEEK_API_KEY=...
ANIMAL_AGENT_DEEPSEEK_BASE_URL=https://api.deepseek.com
ANIMAL_AGENT_DEEPSEEK_TEXT_MODEL=deepseek-v4-flash
ANIMAL_AGENT_DEEPSEEK_TIMEOUT_SECONDS=120

ANIMAL_AGENT_FB_PAGE_ID=...
ANIMAL_AGENT_FB_PAGE_TOKEN=...
ANIMAL_AGENT_FB_GRAPH_VERSION=v21.0

ANIMAL_AGENT_TIMEZONE=Asia/Ho_Chi_Minh
ANIMAL_AGENT_DB_PATH=data/agent.db
ANIMAL_AGENT_OUTPUT_DIR=assets

ANIMAL_AGENT_FONT_BOLD=/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf
ANIMAL_AGENT_FONT_REGULAR=/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf

ANIMAL_AGENT_WEB_HOST=127.0.0.1
ANIMAL_AGENT_WEB_PORT=8000
ANIMAL_AGENT_WEB_SECRET_KEY=change-me

ANIMAL_AGENT_MIN_FUTURE_POSTS=4
ANIMAL_AGENT_TARGET_FUTURE_POSTS=4
ANIMAL_AGENT_DIRECT_IMAGE_BOOTSTRAP_DAYS=2
ANIMAL_AGENT_DIRECT_IMAGE_BOOTSTRAP_UNTIL=
ANIMAL_AGENT_AUTO_GENERATE_TOPICS=true
ANIMAL_AGENT_GENERATED_TOPICS_PATH=data/generated_topics.jsonl

ANIMAL_AGENT_PRODUCT_LINKS_CSV=data/product_links.csv
ANIMAL_AGENT_PRODUCT_COMMENT_IMAGE_DELAY_MINUTES=15
ANIMAL_AGENT_PRODUCT_COMMENT_VIDEO_DELAY_MINUTES=30
ANIMAL_AGENT_PRODUCT_COMMENTS_PER_POST=2

ANIMAL_AGENT_DONATE_COMMENT_URL=https://nuoieditor.io.vn/
ANIMAL_AGENT_DONATE_COMMENT_DELAY_MINUTES=15
ANIMAL_AGENT_DONATE_COMMENT_SCAN_LIMIT=25
ANIMAL_AGENT_DONATE_COMMENT_LOOKBACK_HOURS=72
```

### 4. Init DB

```bash
venv/bin/python scripts/init_db.py
```

### 5. Chạy ngay tối nay để chuẩn bị tuần mới bằng Batch API

```bash
venv/bin/python scripts/ensure_future_posts_batch.py
```

Lệnh này:

- đếm số bài tương lai `READY + WAITING_IMAGE`
- trong giai đoạn bootstrap `ANIMAL_AGENT_DIRECT_IMAGE_BOOTSTRAP_DAYS=2`, tạo/lấy ảnh trực tiếp bằng API thường để bài có ảnh ngay
- mốc kết thúc bootstrap được lưu ở `data/direct_image_bootstrap_until.txt`; sau mốc này bot tự chuyển sang Batch API hoàn toàn
- nếu muốn tắt direct ngay, đặt `ANIMAL_AGENT_DIRECT_IMAGE_BOOTSTRAP_DAYS=0` và xóa `data/direct_image_bootstrap_until.txt`
- DeepSeek sinh topic/text/caption/prompt ảnh; Gemini chỉ sinh ảnh từ prompt cuối cùng
- nếu topic bank cục bộ đã dùng hết, bot tự sinh topic mới bằng DeepSeek và lưu vào `data/generated_topics.jsonl` để dùng lại

Sau đó poll batch:

```bash
venv/bin/python scripts/poll_batch_images.py
```

Poll batch dùng để hỏi Google xem batch ảnh đã xử lý xong chưa. Khi xong, script tải ảnh final đã có chữ về, rồi chuyển bài từ `WAITING_IMAGE` sang `READY`.

Nếu batch chưa xong, chạy lại sau 6 giờ.

Sinh topic thủ công trước nếu muốn kiểm tra nội dung:

```bash
venv/bin/python scripts/generate_topics.py comparison_top5 5
venv/bin/python scripts/generate_topics.py single_card 2
```

Nếu muốn tự comment link sản phẩm sau khi bài đã đăng, copy file CSV sản phẩm vào VPS, ví dụ:

```bash
mkdir -p data
cp /path/to/products.csv data/product_links.csv
venv/bin/python scripts/publish_due_product_comments.py --dry-run
```

Luồng comment sản phẩm:

- bài ảnh: tạo 2 comment sau khi bài đăng được 15 phút
- bài video: tạo 2 comment sau khi bài đăng được 30 phút
- mỗi bài chỉ tạo 1 lần, tối đa 2 comment, mỗi comment 1 link
- comment không kèm giá, chỉ có mô tả ngắn và link ưu đãi/sản phẩm
- link sản phẩm chỉ tự gắn cho bài do bot publish vì lúc đó bot có `fb_post_id` trong DB

Luồng comment donate cho thước phim/reel:

- timer comment quét Page posts/videos gần đây qua Graph API
- nếu phát hiện reel/video đăng thủ công hoặc hàng loạt, bot queue 1 comment donate sau 15 phút
- mỗi reel/video chỉ queue 1 lần để tránh spam
- cần Page token có quyền đọc Page engagement và comment với tư cách Page

### 6. Bật systemd cho chạy tự động

```bash
sudo bash deploy/install_systemd.sh
```

Các timer được bật:

- `fb-animal-agent-ensure.timer`: 02:00 mỗi ngày, tự bù bài tương lai bằng Batch API
- `fb-animal-agent-poll-batch.timer`: mỗi 6 giờ, poll ảnh batch
- `fb-animal-agent-publish-due.timer`: mỗi 15 phút, đăng mọi bài `READY` đã đến giờ
- `fb-animal-agent-product-comments.timer`: mỗi 5 phút, đăng các comment sản phẩm đã đến hạn
- `fb-animal-agent-web.service`: dashboard local ở `127.0.0.1:8000`

Không bật thêm timer đăng riêng lúc 10:00/15:00 nếu đã dùng `fb-animal-agent-publish-due.timer`, vì hai timer có thể cùng publish một bài ở đúng mốc giờ.

Kiểm tra:

```bash
systemctl status fb-animal-agent-web.service
systemctl list-timers 'fb-animal-agent-*'
journalctl -u fb-animal-agent-ensure.service -n 100 --no-pager
journalctl -u fb-animal-agent-poll-batch.service -n 100 --no-pager
```

Nếu muốn mở dashboard từ máy cá nhân mà không public web:

```bash
ssh -L 8000:127.0.0.1:8000 ubuntu@YOUR_VPS_IP
```

Rồi mở:

```text
http://127.0.0.1:8000
```

## Font tiếng Việt

Trên Ubuntu:

```bash
sudo apt update
sudo apt install -y fonts-noto-core
```

Nếu deploy trên macOS hoặc VPS khác, chỉnh:

```env
ANIMAL_AGENT_FONT_BOLD=/path/to/NotoSans-Bold.ttf
ANIMAL_AGENT_FONT_REGULAR=/path/to/NotoSans-Regular.ttf
```
