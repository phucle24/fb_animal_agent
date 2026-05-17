from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import TIMEZONE
from app.db import count_posts, exists_schedule
from app.topic_bank import get_topic_by_index


def generate_schedule(days: int = 7):
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    start_date = now.date()

    slots = []
    for i in range(days):
        day = start_date + timedelta(days=i)
        morning = datetime(day.year, day.month, day.day, 10, 0, tzinfo=tz)
        afternoon = datetime(day.year, day.month, day.day, 15, 0, tzinfo=tz)
        slots.append(("morning", morning))
        slots.append(("afternoon", afternoon))
    return slots


def prepare_weekly_posts(days: int = 7) -> list[dict]:
    from app.post_service import build_post

    slots = generate_schedule(days=days)
    base_index = count_posts()
    created = []
    offset = 0

    for slot_name, dt in slots:
        scheduled_at = dt.strftime("%Y-%m-%d %H:%M:%S")

        if exists_schedule(scheduled_at, slot_name):
            continue

        topic = get_topic_by_index(base_index + offset)
        post_id = build_post(topic, scheduled_at, slot_name)
        created.append(
            {
                "id": post_id,
                "scheduled_at": scheduled_at,
                "slot": slot_name,
                "topic_key": topic["topic_key"],
            }
        )
        offset += 1

    return created


def prepare_one_test_post(topic_index: int = 0) -> dict:
    from app.post_service import build_post

    tz = ZoneInfo(TIMEZONE)
    scheduled_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    topic = get_topic_by_index(topic_index)
    post_id = build_post(topic, scheduled_at, "test")
    return {
        "id": post_id,
        "scheduled_at": scheduled_at,
        "slot": "test",
        "topic_key": topic["topic_key"],
    }
