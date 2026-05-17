# FB Animal Agent

Agent tạo bài Facebook tự động cho fanpage động vật/thực vật:

- Text: `gemini-2.5-flash`
- Image background: `gemini-2.5-flash-image`
- Overlay text bằng Python để chữ tiếng Việt ổn định
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

Batch API dùng cho ảnh nền bất đồng bộ, rẻ hơn standard image generation nhưng không có kết quả ngay.

Qua dashboard:

1. Bấm `Tạo tuần Batch`
2. Chờ batch xử lý
3. Bấm `Poll Batch ảnh` để tải ảnh về, overlay text, chuyển bài sang `READY`

Hoặc chạy CLI:

```bash
python scripts/prepare_weekly_posts_batch.py
python scripts/poll_batch_images.py
```

Cron gợi ý:

```cron
0 2 * * 0 cd /home/ubuntu/fb_animal_agent && /home/ubuntu/fb_animal_agent/venv/bin/python scripts/prepare_weekly_posts_batch.py >> logs/agent.log 2>&1
*/30 * * * * cd /home/ubuntu/fb_animal_agent && /home/ubuntu/fb_animal_agent/venv/bin/python scripts/poll_batch_images.py >> logs/agent.log 2>&1
0 10 * * * cd /home/ubuntu/fb_animal_agent && /home/ubuntu/fb_animal_agent/venv/bin/python scripts/publish_due_posts.py morning >> logs/agent.log 2>&1
0 15 * * * cd /home/ubuntu/fb_animal_agent && /home/ubuntu/fb_animal_agent/venv/bin/python scripts/publish_due_posts.py afternoon >> logs/agent.log 2>&1
```

Trạng thái liên quan:

- `WAITING_IMAGE`: đã có caption/prompt, đang chờ ảnh batch
- `READY`: đã có ảnh final, sẵn sàng đăng Facebook
- `IMAGE_FAILED`: batch hoặc overlay ảnh lỗi

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

Nếu chỉ muốn test overlay/caption dù Gemini image đang lỗi:

```bash
python scripts/create_test_post.py --allow-placeholder
```

## Preview bài

Qua dashboard: mở từng bài để xem ảnh final, caption, overlay, image prompt.

Hoặc chạy CLI:

```bash
python scripts/preview_posts.py
```

## Đăng bài đến hạn

```bash
python scripts/publish_due_posts.py morning
python scripts/publish_due_posts.py afternoon
```

## Cron VPS

```cron
0 2 * * 0 cd /home/ubuntu/fb_animal_agent && /home/ubuntu/fb_animal_agent/venv/bin/python scripts/prepare_weekly_posts.py >> logs/agent.log 2>&1
0 10 * * * cd /home/ubuntu/fb_animal_agent && /home/ubuntu/fb_animal_agent/venv/bin/python scripts/publish_due_posts.py morning >> logs/agent.log 2>&1
0 15 * * * cd /home/ubuntu/fb_animal_agent && /home/ubuntu/fb_animal_agent/venv/bin/python scripts/publish_due_posts.py afternoon >> logs/agent.log 2>&1
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

### 2. Đặt source vào `/opt/fb_animal_agent`

```bash
sudo mkdir -p /opt/fb_animal_agent
sudo chown -R $USER:$USER /opt/fb_animal_agent
cd /opt/fb_animal_agent
```

Copy source project lên thư mục này bằng `scp`, `rsync`, hoặc `git clone`.

### 3. Tạo venv và env

```bash
cd /opt/fb_animal_agent
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Điền `.env`:

```env
ANIMAL_AGENT_GEMINI_API_KEY=...
ANIMAL_AGENT_GEMINI_TEXT_MODEL=gemini-2.5-flash
ANIMAL_AGENT_GEMINI_IMAGE_MODEL=gemini-2.5-flash-image
ANIMAL_AGENT_IMAGE_FALLBACK_ON_ERROR=false

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
- nếu dưới `ANIMAL_AGENT_MIN_FUTURE_POSTS`, tạo thêm `ANIMAL_AGENT_TARGET_FUTURE_POSTS` bài mới
- submit Gemini Batch API cho ảnh

Sau đó poll batch:

```bash
venv/bin/python scripts/poll_batch_images.py
```

Poll batch dùng để hỏi Google xem batch ảnh đã xử lý xong chưa. Khi xong, script tải ảnh raw về, overlay chữ, rồi chuyển bài từ `WAITING_IMAGE` sang `READY`.

Nếu batch chưa xong, chạy lại sau 6 giờ.

### 6. Bật systemd cho chạy tự động

```bash
sudo bash deploy/install_systemd.sh
```

Các timer được bật:

- `fb-animal-agent-ensure.timer`: 02:00 mỗi ngày, tự bù bài tương lai bằng Batch API
- `fb-animal-agent-poll-batch.timer`: mỗi 6 giờ, poll ảnh batch
- `fb-animal-agent-publish-morning.timer`: 10:00 mỗi ngày
- `fb-animal-agent-publish-afternoon.timer`: 15:00 mỗi ngày
- `fb-animal-agent-web.service`: dashboard local ở `127.0.0.1:8000`

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
