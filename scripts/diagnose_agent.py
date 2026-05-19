import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DB_PATH, TIMEZONE
from app.db import batch_publish_overview, get_all_due_posts, get_conn, init_db


def print_rows(title: str, rows):
    print(f"\n{title}: {len(rows)}")
    for row in rows:
        final_path = row["final_image_path"]
        image_exists = bool(final_path and Path(final_path).exists())
        print(
            f"ID={row['id']} | {row['scheduled_at']} | {row['slot']} | "
            f"{row['status']} | {row['topic_key']} | image_exists={image_exists} | "
            f"batch_state={row['batch_state'] or '-'} | error={row['error_message'] or row['batch_error'] or '-'}"
        )


if __name__ == "__main__":
    init_db()
    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    today = now.date()
    tomorrow = today + timedelta(days=1)
    now_iso = now.strftime("%Y-%m-%d %H:%M:%S")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT status, COUNT(*) AS total FROM posts GROUP BY status")
    status_counts = {row["status"]: row["total"] for row in cur.fetchall()}

    cur.execute(
        """
        SELECT *
        FROM posts
        WHERE scheduled_at BETWEEN ? AND ?
        ORDER BY scheduled_at ASC, id ASC
        """,
        (f"{today} 00:00:00", f"{today} 23:59:59"),
    )
    today_rows = cur.fetchall()

    cur.execute(
        """
        SELECT *
        FROM posts
        WHERE scheduled_at BETWEEN ? AND ?
        ORDER BY scheduled_at ASC, id ASC
        """,
        (f"{tomorrow} 00:00:00", f"{tomorrow} 23:59:59"),
    )
    tomorrow_rows = cur.fetchall()

    cur.execute(
        """
        SELECT batch_job_name, batch_state, COUNT(*) AS total
        FROM posts
        WHERE status = 'WAITING_IMAGE'
          AND batch_job_name IS NOT NULL
        GROUP BY batch_job_name, batch_state
        ORDER BY MIN(id)
        """
    )
    batch_rows = cur.fetchall()

    cur.execute(
        """
        SELECT *
        FROM posts
        WHERE status IN ('FAILED', 'IMAGE_FAILED')
        ORDER BY updated_at DESC, id DESC
        LIMIT 10
        """
    )
    failed_rows = cur.fetchall()

    conn.close()

    due_rows = get_all_due_posts(now_iso)
    overview = batch_publish_overview(now_iso)

    print(f"DB: {DB_PATH}")
    print(f"Now: {now_iso} {TIMEZONE}")
    print(f"Status counts: {dict(Counter(status_counts))}")
    print(f"Batch/publish overview: {overview}")
    print_rows("Due READY posts", due_rows)
    print_rows("Today posts", today_rows)
    print_rows("Tomorrow posts", tomorrow_rows)

    print(f"\nWaiting image batches: {len(batch_rows)}")
    for row in batch_rows:
        print(
            f"batch={row['batch_job_name']} | state={row['batch_state'] or '-'} | "
            f"posts={row['total']}"
        )

    print_rows("Recent failed posts", failed_rows)
