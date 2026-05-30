import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import TIMEZONE
from app.db import get_conn, init_db
from app.schedule_service import generate_future_schedule


RESCHEDULABLE_STATUSES = ("READY", "WAITING_IMAGE", "IMAGE_FAILED")


def parse_limit(args: list[str]) -> int | None:
    for arg in args:
        if arg.startswith("--limit="):
            return int(arg.split("=", 1)[1])
    return None


def fetch_future_posts(now_iso: str, limit: int | None):
    conn = get_conn()
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in RESCHEDULABLE_STATUSES)
    sql = f"""
        SELECT *
        FROM posts
        WHERE status IN ({placeholders})
          AND scheduled_at > ?
        ORDER BY scheduled_at ASC, id ASC
    """
    params = [*RESCHEDULABLE_STATUSES, now_iso]
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return rows


def occupied_schedule_pairs(excluded_post_ids: set[int]) -> set[tuple[str, str]]:
    conn = get_conn()
    cur = conn.cursor()
    if excluded_post_ids:
        placeholders = ",".join("?" for _ in excluded_post_ids)
        cur.execute(
            f"""
            SELECT scheduled_at, slot
            FROM posts
            WHERE id NOT IN ({placeholders})
            """,
            list(excluded_post_ids),
        )
    else:
        cur.execute("SELECT scheduled_at, slot FROM posts")
    pairs = {(row["scheduled_at"], row["slot"]) for row in cur.fetchall()}
    conn.close()
    return pairs


def build_assignments(rows, start_tomorrow: bool):
    excluded_ids = {row["id"] for row in rows}
    occupied = occupied_schedule_pairs(excluded_ids)
    assignments = []
    tz = ZoneInfo(TIMEZONE)
    today = datetime.now(tz).date()
    for slot_name, dt in generate_future_schedule(target_slots=len(rows) + 120, lookahead_days=120):
        if start_tomorrow and dt.date() <= today:
            continue
        scheduled_at = dt.strftime("%Y-%m-%d %H:%M:%S")
        pair = (scheduled_at, slot_name)
        if pair in occupied:
            continue
        row = rows[len(assignments)]
        assignments.append((row, scheduled_at, slot_name))
        if len(assignments) >= len(rows):
            break
    if len(assignments) < len(rows):
        raise RuntimeError(f"Only found {len(assignments)} target slots for {len(rows)} posts.")
    return assignments


def apply_assignments(assignments):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("BEGIN IMMEDIATE")

    for row, _, _ in assignments:
        cur.execute(
            """
            UPDATE posts
            SET scheduled_at = ?,
                slot = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (f"2099-12-31 23:{row['id'] % 60:02d}:59", f"reschedule_{row['id']}", row["id"]),
        )

    for row, scheduled_at, slot_name in assignments:
        cur.execute(
            """
            UPDATE posts
            SET scheduled_at = ?,
                slot = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (scheduled_at, slot_name, row["id"]),
        )

    conn.commit()
    conn.close()


if __name__ == "__main__":
    apply = "--apply" in sys.argv[1:]
    start_tomorrow = "--start-tomorrow" in sys.argv[1:]
    limit = parse_limit(sys.argv[1:])

    init_db()
    tz = ZoneInfo(TIMEZONE)
    now_iso = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    rows = fetch_future_posts(now_iso, limit)

    if not rows:
        print("No future posts to reschedule.")
        sys.exit(0)

    assignments = build_assignments(rows, start_tomorrow=start_tomorrow)
    print(f"Future posts to reschedule: {len(assignments)}")
    for row, scheduled_at, slot_name in assignments:
        print(
            f"ID={row['id']} | {row['status']} | {row['topic_key']} | "
            f"{row['scheduled_at']} {row['slot']} => {scheduled_at} {slot_name}"
        )

    if not apply:
        print("Dry run only. Re-run with --apply to update DB.")
        sys.exit(0)

    apply_assignments(assignments)
    print("Reschedule applied.")
