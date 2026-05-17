from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import MIN_FUTURE_POSTS, TARGET_FUTURE_POSTS, TIMEZONE
from app.db import count_future_posts, count_posts, exists_schedule
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


def generate_future_schedule(target_slots: int, lookahead_days: int = 60):
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    slots = []

    for i in range(lookahead_days):
        day = now.date() + timedelta(days=i)
        for slot_name, hour in [("morning", 10), ("afternoon", 15)]:
            dt = datetime(day.year, day.month, day.day, hour, 0, tzinfo=tz)
            if dt > now:
                slots.append((slot_name, dt))
            if len(slots) >= target_slots:
                return slots

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


def prepare_weekly_posts_for_batch(days: int = 7) -> list[dict]:
    from app.post_service import build_post_for_batch

    slots = generate_schedule(days=days)
    base_index = count_posts()
    created = []
    offset = 0

    for slot_name, dt in slots:
        scheduled_at = dt.strftime("%Y-%m-%d %H:%M:%S")

        if exists_schedule(scheduled_at, slot_name):
            continue

        topic = get_topic_by_index(base_index + offset)
        post_id = build_post_for_batch(topic, scheduled_at, slot_name)
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


def prepare_future_posts_for_batch(posts_to_create: int) -> list[dict]:
    from app.post_service import build_post_for_batch

    if posts_to_create <= 0:
        return []

    base_index = count_posts()
    created = []
    offset = 0

    # Scan more slots than needed because some future slots may already exist.
    slots = generate_future_schedule(target_slots=posts_to_create + 60)
    for slot_name, dt in slots:
        scheduled_at = dt.strftime("%Y-%m-%d %H:%M:%S")
        if exists_schedule(scheduled_at, slot_name):
            continue

        topic = get_topic_by_index(base_index + offset)
        post_id = build_post_for_batch(topic, scheduled_at, slot_name)
        created.append(
            {
                "id": post_id,
                "scheduled_at": scheduled_at,
                "slot": slot_name,
                "topic_key": topic["topic_key"],
            }
        )
        offset += 1

        if len(created) >= posts_to_create:
            break

    return created


def ensure_future_posts_for_batch(
    min_future_posts: int = MIN_FUTURE_POSTS,
    target_future_posts: int = TARGET_FUTURE_POSTS,
) -> dict:
    from app.batch_service import submit_pending_image_batch

    tz = ZoneInfo(TIMEZONE)
    now_iso = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    current_future = count_future_posts(now_iso)

    if current_future >= min_future_posts:
        return {
            "current_future": current_future,
            "created": [],
            "batch": {"submitted": 0, "batch_job_name": None, "batch_state": None},
        }

    created = prepare_future_posts_for_batch(posts_to_create=target_future_posts)
    batch = submit_pending_image_batch(limit=max(len(created), 1)) if created else {
        "submitted": 0,
        "batch_job_name": None,
        "batch_state": None,
    }

    return {
        "current_future": current_future,
        "created": created,
        "batch": batch,
    }


def prepare_one_test_post(topic_index: int = 0) -> dict:
    from app.post_service import build_post

    tz = ZoneInfo(TIMEZONE)
    scheduled_at = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    topic = get_topic_by_index(topic_index)
    post_id = build_post(topic, scheduled_at, "test", image_fallback_on_error=False)
    return {
        "id": post_id,
        "scheduled_at": scheduled_at,
        "slot": "test",
        "topic_key": topic["topic_key"],
    }
