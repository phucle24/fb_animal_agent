import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import TIMEZONE
from app.db import claim_due_posts_for_publish, get_all_due_posts, get_due_posts, mark_failed, mark_posted
from app.facebook_service import publish_photo, publish_reel
from app.product_comment_service import schedule_product_comments_for_post


if __name__ == "__main__":
    args = [arg for arg in sys.argv[1:] if arg != "--dry-run"]
    dry_run = "--dry-run" in sys.argv[1:]
    slot = args[0].strip().lower() if args else "all"
    valid_slots = {"all", "morning", "afternoon", "evening", "night", "reel_1", "reel_2"}
    if slot not in valid_slots:
        print(f"Usage: python scripts/publish_due_posts.py [{'|'.join(sorted(valid_slots))}] [--dry-run]")
        sys.exit(1)

    tz = ZoneInfo(TIMEZONE)
    now_iso = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")

    if dry_run:
        if slot == "all":
            posts = get_all_due_posts(now_iso)
        else:
            posts = get_due_posts(now_iso, slot)
    else:
        posts = claim_due_posts_for_publish(now_iso, slot)

    if not posts:
        print("No due posts.")
        sys.exit(0)

    print(f"Found {len(posts)} due posts for slot={slot} at {now_iso}.")

    for post in posts:
        if dry_run:
            print(
                "Would post "
                f"local_id={post['id']} | scheduled_at={post['scheduled_at']} | "
                f"slot={post['slot']} | type={post['topic_type']} | file={post['final_image_path']}"
            )
            continue

        try:
            if post.get("topic_type") == "reel":
                result = publish_reel(post["final_image_path"], post["caption"])
                fb_video_id = result.get("video_id") or result.get("id", "")
                fb_post_id = fb_video_id
                mark_posted(post["id"], fb_post_id, "")
            else:
                result = publish_photo(post["final_image_path"], post["caption"])
                fb_photo_id = result.get("id", "")
                fb_post_id = result.get("post_id") or result.get("id", "")
                mark_posted(post["id"], fb_post_id, fb_photo_id)
        except Exception as exc:
            mark_failed(post["id"], str(exc))
            print(f"Failed local_id={post['id']} => {exc}")
            continue

        try:
            scheduled_comments = schedule_product_comments_for_post(post, fb_post_id)
            print(
                f"Posted local_id={post['id']} => fb_post_id={fb_post_id} | fb_photo_id={fb_photo_id} | "
                f"scheduled_product_comments={scheduled_comments}"
            )
        except Exception as exc:
            print(
                f"Posted local_id={post['id']} => fb_post_id={fb_post_id} | fb_photo_id={fb_photo_id} | "
                f"scheduled_product_comments failed: {exc}"
            )
