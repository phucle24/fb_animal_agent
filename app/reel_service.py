import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config import REELS_DIR, TIMEZONE
from app.db import exists_schedule, get_conn, insert_post
from app.google_drive_service import (
    download_caption_text,
    download_drive_file,
    get_sorted_reels_from_drive,
)

logger = logging.getLogger(__name__)


def reel_slots_for_date(day) -> list[tuple[str, int, int]]:
    """
    Daily video reels schedule:
    1. 12:15 PM (noon): Reel 1
    2. 20:00 PM (night): Reel 2
    """
    return [("reel_1", 12, 15), ("reel_2", 20, 0)]


def generate_future_reel_schedule(target_slots: int = 14, lookahead_days: int = 30) -> list[tuple[str, datetime]]:
    """Generates future datetime slots for video reels."""
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    slots = []

    for i in range(lookahead_days):
        day = now.date() + timedelta(days=i)
        for slot_name, hour, minute in reel_slots_for_date(day):
            dt = datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)
            if dt > now:
                slots.append((slot_name, dt))
            if len(slots) >= target_slots:
                return slots

    return slots


def get_existing_reel_keys() -> set[str]:
    """Queries DB for topic_keys of reels that are already scheduled, posted, or claimed."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT topic_key FROM posts WHERE topic_type = 'reel'")
    rows = cur.fetchall()
    conn.close()
    return {row["topic_key"] for row in rows}


def get_unposted_drive_reels(folder_id: str | None = None) -> list[dict]:
    """
    Returns sorted list of reels from Google Drive that have NOT yet been scheduled or posted.
    Guarantees no duplicate uploads of videos.
    """
    all_reels = get_sorted_reels_from_drive(folder_id)
    existing_keys = get_existing_reel_keys()

    unposted = [r for r in all_reels if r["topic_key"] not in existing_keys]
    logger.info("Found %d total reels on Drive, %d unposted", len(all_reels), len(unposted))
    return unposted


def prepare_reel_media(reel: dict) -> tuple[Path, str]:
    """
    Downloads the reel's video and caption from Google Drive if not already downloaded locally.
    Returns (local_video_path, caption_text).
    """
    video_file = reel["video_file"]
    video_name = video_file["name"]
    video_id = video_file["id"]
    expected_size = int(video_file.get("size", 0)) if video_file.get("size") else None

    dest_video_path = REELS_DIR / video_name
    download_drive_file(video_id, dest_video_path, expected_size=expected_size)

    caption_file = reel.get("caption_file")
    if caption_file and caption_file.get("id"):
        caption = download_caption_text(caption_file["id"])
    else:
        caption = f"{reel['title']}\n#thegioimuonloai #reviewdongvat #thegioidongvat"

    return dest_video_path, caption


def ensure_future_reels(max_reels: int | None = None, folder_id: str | None = None) -> dict:
    """
    Checks Google Drive for unposted reels, downloads videos and captions,
    and schedules them into the next available 12:15 and 20:00 slots.
    """
    unposted_reels = get_unposted_drive_reels(folder_id)
    if not unposted_reels:
        return {"scheduled": 0, "items": [], "message": "No unposted reels found on Drive."}

    if max_reels is not None and max_reels > 0:
        reels_to_schedule = unposted_reels[:max_reels]
    else:
        reels_to_schedule = unposted_reels

    # Generate enough future slots for the reels
    slots = generate_future_reel_schedule(target_slots=len(reels_to_schedule) + 20)

    scheduled_items = []
    reel_idx = 0

    for slot_name, dt in slots:
        if reel_idx >= len(reels_to_schedule):
            break

        scheduled_at = dt.strftime("%Y-%m-%d %H:%M:%S")
        if exists_schedule(scheduled_at, slot_name):
            continue

        reel = reels_to_schedule[reel_idx]
        try:
            local_video_path, caption = prepare_reel_media(reel)

            post_data = {
                "scheduled_at": scheduled_at,
                "slot": slot_name,
                "topic_type": "reel",
                "topic_key": reel["topic_key"],
                "title": reel["title"],
                "overlay_title": "",
                "overlay_subtitle": "",
                "overlay_stat": "",
                "overlay_hook": "",
                "caption": caption,
                "image_prompt": "",
                "topic_payload": json.dumps(
                    {
                        "drive_video_id": reel["video_file"]["id"],
                        "drive_caption_id": reel.get("caption_file", {}).get("id"),
                        "video_number": reel["number"],
                        "filename": reel["video_file"]["name"],
                    }
                ),
                "raw_image_path": "",
                "final_image_path": str(local_video_path),
                "status": "READY",
            }

            post_id = insert_post(post_data)
            scheduled_items.append(
                {
                    "id": post_id,
                    "scheduled_at": scheduled_at,
                    "slot": slot_name,
                    "topic_key": reel["topic_key"],
                    "title": reel["title"],
                    "video_path": str(local_video_path),
                }
            )
            logger.info(
                "Scheduled reel ID=%d: %s | slot=%s | at %s",
                post_id,
                reel["topic_key"],
                slot_name,
                scheduled_at,
            )
            reel_idx += 1
        except Exception as exc:
            logger.error("Failed to prepare/schedule reel %s: %s", reel.get("topic_key"), exc, exc_info=True)

    return {
        "scheduled": len(scheduled_items),
        "items": scheduled_items,
        "message": f"Successfully scheduled {len(scheduled_items)} reels.",
    }
