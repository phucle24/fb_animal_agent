import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schedule_service import prepare_one_test_post


if __name__ == "__main__":
    topic_index = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    post = prepare_one_test_post(topic_index=topic_index)
    print(
        "Created test post "
        f"ID={post['id']} | {post['scheduled_at']} | {post['slot']} | {post['topic_key']}"
    )
