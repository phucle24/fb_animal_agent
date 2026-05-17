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
