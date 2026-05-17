import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.post_service import build_post
from app.schedule_service import prepare_one_test_post
from app.topic_bank import get_topic_by_index
from app.config import TIMEZONE

from datetime import datetime
from zoneinfo import ZoneInfo


if __name__ == "__main__":
    args = [arg for arg in sys.argv[1:] if arg != "--allow-placeholder"]
    topic_index = int(args[0]) if args else 0
    allow_placeholder = "--allow-placeholder" in sys.argv[1:]

    if allow_placeholder:
        tz = ZoneInfo(TIMEZONE)
        scheduled_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
        topic = get_topic_by_index(topic_index)
        post_id = build_post(topic, scheduled_at, "test", image_fallback_on_error=True)
        post = {
            "id": post_id,
            "scheduled_at": scheduled_at,
            "slot": "test",
            "topic_key": topic["topic_key"],
        }
    else:
        post = prepare_one_test_post(topic_index=topic_index)
    print(
        "Created test post "
        f"ID={post['id']} | {post['scheduled_at']} | {post['slot']} | {post['topic_key']}"
    )
