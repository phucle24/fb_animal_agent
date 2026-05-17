import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import list_recent_posts


if __name__ == "__main__":
    rows = list_recent_posts(limit=10)

    for row in rows:
        print("=" * 100)
        print("ID:", row["id"])
        print("Scheduled:", row["scheduled_at"])
        print("Slot:", row["slot"])
        print("Topic:", row["topic_key"])
        print("Type:", row["topic_type"])
        print("Title:", row["title"])
        print("Status:", row["status"])
        print("Image:", row["final_image_path"])
        print("Caption:")
        print(row["caption"])
