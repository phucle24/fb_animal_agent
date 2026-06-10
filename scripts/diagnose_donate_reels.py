import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import (
    DONATE_COMMENT_DELAY_MINUTES,
    DONATE_COMMENT_LOOKBACK_HOURS,
    DONATE_COMMENT_SCAN_LIMIT,
    DONATE_COMMENT_URL,
    TIMEZONE,
)
from app.facebook_service import list_recent_page_posts, list_recent_page_reels, list_recent_page_videos
from app.product_comment_service import (
    is_reel_or_video_post,
    normalize_external_video_objects,
    parse_facebook_time,
    schedule_recent_donate_comments,
)


def print_section(title: str):
    print("=" * 100)
    print(title)


def print_item(source: str, item: dict, is_video_like: bool = True):
    created_at = item.get("created_time", "")
    permalink = item.get("permalink_url", "")
    print(
        f"{source} | id={item.get('id', '-')} | created_time={created_at or '-'} | "
        f"video_like={is_video_like} | permalink={permalink or '-'}"
    )


if __name__ == "__main__":
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    lookback_start = now - timedelta(hours=DONATE_COMMENT_LOOKBACK_HOURS)

    print_section("Donate config")
    print(f"DONATE_COMMENT_URL={DONATE_COMMENT_URL or '-'}")
    print(f"DONATE_COMMENT_DELAY_MINUTES={DONATE_COMMENT_DELAY_MINUTES}")
    print(f"DONATE_COMMENT_SCAN_LIMIT={DONATE_COMMENT_SCAN_LIMIT}")
    print(f"DONATE_COMMENT_LOOKBACK_HOURS={DONATE_COMMENT_LOOKBACK_HOURS}")
    print(f"Now={now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Lookback start={lookback_start.strftime('%Y-%m-%d %H:%M:%S %Z')}")

    for source, loader in (
        ("posts", list_recent_page_posts),
        ("videos", list_recent_page_videos),
        ("video_reels", list_recent_page_reels),
    ):
        print_section(source)
        try:
            rows = loader(limit=DONATE_COMMENT_SCAN_LIMIT)
        except Exception as exc:
            print(f"ERROR: {exc}")
            continue

        if not rows:
            print("No rows.")
            continue

        for row in rows:
            is_video_like = True if source != "posts" else is_reel_or_video_post(row)
            print_item(source, row, is_video_like=is_video_like)
            created_at = parse_facebook_time(row.get("created_time", ""))
            if created_at:
                created_local = created_at.astimezone(tz)
                scheduled_at = created_local + timedelta(minutes=DONATE_COMMENT_DELAY_MINUTES)
                print(
                    f"  local_created={created_local.strftime('%Y-%m-%d %H:%M:%S')} | "
                    f"scheduled={scheduled_at.strftime('%Y-%m-%d %H:%M:%S')} | "
                    f"in_lookback={created_local >= lookback_start}"
                )

    print_section("Normalized candidates")
    candidates = normalize_external_video_objects()
    if not candidates:
        print("No normalized video/reel candidates.")
    for item in candidates:
        created = item["created_at"].astimezone(tz).strftime("%Y-%m-%d %H:%M:%S") if item["created_at"] else "-"
        print(f"{item['source']} | fb_post_id={item['fb_post_id']} | created={created}")

    print_section("Dry-run queue")
    queued = schedule_recent_donate_comments(dry_run=True)
    if not queued:
        print("No donate comments would be queued.")
    for item in queued:
        print(
            f"Would queue donate comment for fb_post_id={item['fb_post_id']} "
            f"at {item['scheduled_at']} | source={item['source']}"
        )
