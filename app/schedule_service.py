from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import (
    DB_PATH,
    DIRECT_IMAGE_BOOTSTRAP_DAYS,
    DIRECT_IMAGE_BOOTSTRAP_UNTIL,
    MIN_FUTURE_POSTS,
    TARGET_FUTURE_POSTS,
    TIMEZONE,
)
from app.db import (
    count_future_posts,
    count_posts,
    exists_schedule,
    list_posts_for_direct_image_generation,
    mark_image_failed,
    mark_image_ready,
)
from app.topic_bank import get_topic_by_index


BOOTSTRAP_STATE_PATH = DB_PATH.parent / "direct_image_bootstrap_until.txt"


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


def prepare_future_posts_for_batch(posts_to_create: int, start_after_iso: str | None = None) -> list[dict]:
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
        if start_after_iso and scheduled_at <= start_after_iso:
            continue
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
                "mode": "batch_new",
            }
        )
        offset += 1

        if len(created) >= posts_to_create:
            break

    return created


def parse_local_datetime(value: str, tz: ZoneInfo) -> datetime:
    value = value.strip()
    if not value:
        raise ValueError("empty datetime")

    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        parsed = datetime.strptime(value, "%Y-%m-%d %H:%M:%S")

    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=tz)
    return parsed.astimezone(tz)


def direct_image_bootstrap_until(now: datetime) -> datetime | None:
    if DIRECT_IMAGE_BOOTSTRAP_UNTIL:
        return parse_local_datetime(DIRECT_IMAGE_BOOTSTRAP_UNTIL, ZoneInfo(TIMEZONE))

    if BOOTSTRAP_STATE_PATH.exists():
        value = BOOTSTRAP_STATE_PATH.read_text(encoding="utf-8").strip()
        if value:
            return parse_local_datetime(value, ZoneInfo(TIMEZONE))

    if DIRECT_IMAGE_BOOTSTRAP_DAYS <= 0:
        return None

    until = now + timedelta(days=DIRECT_IMAGE_BOOTSTRAP_DAYS)
    BOOTSTRAP_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BOOTSTRAP_STATE_PATH.write_text(until.isoformat(), encoding="utf-8")
    return until


def generate_direct_images_for_near_term_posts(start_after_iso: str, cutoff_iso: str) -> list[dict]:
    from app.image_service import generate_image

    converted = []
    for post in list_posts_for_direct_image_generation(start_after_iso, cutoff_iso):
        try:
            generate_image(post["image_prompt"], post["final_image_path"])
            mark_image_ready(post["id"], post["final_image_path"], post["final_image_path"])
            converted.append(
                {
                    "id": post["id"],
                    "scheduled_at": post["scheduled_at"],
                    "slot": post["slot"],
                    "topic_key": post["topic_key"],
                    "mode": "direct_existing",
                }
            )
        except Exception as exc:
            mark_image_failed(post["id"], str(exc))

    return converted


def prepare_future_posts_direct(posts_to_create: int, cutoff_iso: str) -> list[dict]:
    from app.post_service import build_post

    if posts_to_create <= 0:
        return []

    base_index = count_posts()
    created = []
    offset = 0

    slots = generate_future_schedule(target_slots=posts_to_create + 60)
    for slot_name, dt in slots:
        scheduled_at = dt.strftime("%Y-%m-%d %H:%M:%S")
        if scheduled_at > cutoff_iso:
            continue
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
                "mode": "direct_new",
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
    now = datetime.now(tz)
    now_iso = now.strftime("%Y-%m-%d %H:%M:%S")
    direct_until = direct_image_bootstrap_until(now)
    direct_enabled = direct_until is not None and now <= direct_until
    direct_cutoff_iso = direct_until.strftime("%Y-%m-%d %H:%M:%S") if direct_until else None

    direct_existing = (
        generate_direct_images_for_near_term_posts(now_iso, direct_cutoff_iso)
        if direct_enabled and direct_cutoff_iso
        else []
    )
    current_future = count_future_posts(now_iso)

    if current_future >= min_future_posts:
        return {
            "current_future": current_future,
            "created": [],
            "direct_existing": direct_existing,
            "direct_cutoff": direct_cutoff_iso,
            "direct_enabled": direct_enabled,
            "batch": {"submitted": 0, "batch_job_name": None, "batch_state": None},
        }

    if direct_enabled and direct_cutoff_iso:
        created = prepare_future_posts_direct(
            posts_to_create=target_future_posts,
            cutoff_iso=direct_cutoff_iso,
        )
        remaining_for_batch = max(target_future_posts - len(created), 0)
        batch_created = prepare_future_posts_for_batch(
            posts_to_create=remaining_for_batch,
            start_after_iso=direct_cutoff_iso,
        )
        created.extend(batch_created)
    else:
        created = prepare_future_posts_for_batch(posts_to_create=target_future_posts)

    batch_created_count = sum(1 for post in created if post.get("mode") == "batch_new")
    batch = submit_pending_image_batch(limit=max(batch_created_count, 1)) if batch_created_count else {
        "submitted": 0,
        "batch_job_name": None,
        "batch_state": None,
    }

    return {
        "current_future": current_future,
        "created": created,
        "direct_existing": direct_existing,
        "direct_cutoff": direct_cutoff_iso,
        "direct_enabled": direct_enabled,
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
