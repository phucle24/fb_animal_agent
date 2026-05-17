import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import TIMEZONE
from app.db import get_due_posts, mark_failed, mark_posted
from app.facebook_service import publish_photo


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/publish_due_posts.py morning|afternoon")
        sys.exit(1)

    slot = sys.argv[1].strip().lower()
    if slot not in {"morning", "afternoon"}:
        print("slot must be morning or afternoon")
        sys.exit(1)

    tz = ZoneInfo(TIMEZONE)
    now_iso = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    posts = get_due_posts(now_iso, slot)
    if not posts:
        print("No due posts.")
        sys.exit(0)

    for post in posts:
        try:
            result = publish_photo(post["final_image_path"], post["caption"])
            fb_post_id = result.get("post_id") or result.get("id", "")
            mark_posted(post["id"], fb_post_id)
            print(f"Posted local_id={post['id']} => fb_post_id={fb_post_id}")
        except Exception as exc:
            mark_failed(post["id"], str(exc))
            print(f"Failed local_id={post['id']} => {exc}")
