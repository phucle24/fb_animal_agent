import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import list_posts, update_post_caption
from app.post_service import append_caption_hashtags


if __name__ == "__main__":
    updated = 0
    rows = list_posts(limit=10000)

    for row in rows:
        if row["status"] == "POSTED":
            continue
        new_caption = append_caption_hashtags(row["caption"])
        if new_caption != row["caption"]:
            update_post_caption(row["id"], new_caption)
            updated += 1

    print(f"Updated {updated} posts.")
