import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.schedule_service import prepare_weekly_posts


if __name__ == "__main__":
    created = prepare_weekly_posts(days=7)
    for post in created:
        print(
            "Created post "
            f"ID={post['id']} | {post['scheduled_at']} | {post['slot']} | {post['topic_key']}"
        )
    print(f"Done. Created {len(created)} posts.")
