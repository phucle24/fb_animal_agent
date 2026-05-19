import sqlite3
from collections import Counter
from pathlib import Path

from app.config import DB_PATH


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            scheduled_at TEXT NOT NULL,
            slot TEXT NOT NULL,
            topic_type TEXT NOT NULL,
            topic_key TEXT NOT NULL,
            title TEXT NOT NULL,
            overlay_title TEXT,
            overlay_subtitle TEXT,
            overlay_stat TEXT,
            overlay_hook TEXT,
            caption TEXT NOT NULL,
            image_prompt TEXT NOT NULL,
            topic_payload TEXT,
            raw_image_path TEXT,
            final_image_path TEXT,
            status TEXT NOT NULL DEFAULT 'READY',
            fb_post_id TEXT,
            error_message TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    _ensure_columns(
        cur,
        "posts",
        {
            "batch_job_name": "TEXT",
            "batch_request_key": "TEXT",
            "batch_state": "TEXT",
            "batch_error": "TEXT",
            "batch_submitted_at": "TEXT",
            "batch_completed_at": "TEXT",
        },
    )

    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_schedule_slot
        ON posts (scheduled_at, slot)
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_status ON posts (status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_topic_key ON posts (topic_key)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_batch_job_name ON posts (batch_job_name)")

    conn.commit()
    conn.close()


def _ensure_columns(cur, table_name: str, columns: dict[str, str]):
    cur.execute(f"PRAGMA table_info({table_name})")
    existing = {row["name"] for row in cur.fetchall()}
    for column, definition in columns.items():
        if column not in existing:
            cur.execute(f"ALTER TABLE {table_name} ADD COLUMN {column} {definition}")


def insert_post(data: dict) -> int:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO posts (
            scheduled_at, slot, topic_type, topic_key, title,
            overlay_title, overlay_subtitle, overlay_stat, overlay_hook,
            caption, image_prompt, topic_payload, raw_image_path,
            final_image_path, status, batch_job_name, batch_request_key,
            batch_state, batch_error, batch_submitted_at, batch_completed_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            data["scheduled_at"],
            data["slot"],
            data["topic_type"],
            data["topic_key"],
            data["title"],
            data.get("overlay_title"),
            data.get("overlay_subtitle"),
            data.get("overlay_stat"),
            data.get("overlay_hook"),
            data["caption"],
            data["image_prompt"],
            data.get("topic_payload"),
            data.get("raw_image_path"),
            data.get("final_image_path"),
            data.get("status", "READY"),
            data.get("batch_job_name"),
            data.get("batch_request_key"),
            data.get("batch_state"),
            data.get("batch_error"),
            data.get("batch_submitted_at"),
            data.get("batch_completed_at"),
        ),
    )

    post_id = cur.lastrowid
    conn.commit()
    conn.close()
    return post_id


def exists_schedule(scheduled_at: str, slot: str) -> bool:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT 1 FROM posts
        WHERE scheduled_at = ? AND slot = ?
        LIMIT 1
        """,
        (scheduled_at, slot),
    )
    row = cur.fetchone()
    conn.close()
    return row is not None


def count_posts() -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS total FROM posts")
    total = cur.fetchone()["total"]
    conn.close()
    return total


def count_future_posts(now_iso: str, statuses: tuple[str, ...] = ("READY", "WAITING_IMAGE")) -> int:
    conn = get_conn()
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in statuses)
    cur.execute(
        f"""
        SELECT COUNT(*) AS total
        FROM posts
        WHERE scheduled_at > ?
          AND status IN ({placeholders})
        """,
        (now_iso, *statuses),
    )
    total = cur.fetchone()["total"]
    conn.close()
    return total


def get_due_posts(now_iso: str, slot: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM posts
        WHERE status = 'READY'
          AND slot = ?
          AND scheduled_at <= ?
        ORDER BY scheduled_at ASC
        """,
        (slot, now_iso),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_all_due_posts(now_iso: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM posts
        WHERE status = 'READY'
          AND scheduled_at <= ?
        ORDER BY scheduled_at ASC, id ASC
        """,
        (now_iso,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_post(post_id: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT * FROM posts WHERE id = ?", (post_id,))
    row = cur.fetchone()
    conn.close()
    return row


def mark_posted(post_id: int, fb_post_id: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET status = 'POSTED',
            fb_post_id = ?,
            error_message = NULL,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (fb_post_id, post_id),
    )
    conn.commit()
    conn.close()


def mark_failed(post_id: int, error_message: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET status = 'FAILED',
            error_message = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (error_message[:1000], post_id),
    )
    conn.commit()
    conn.close()


def mark_image_ready(post_id: int, raw_image_path: str, final_image_path: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET status = 'READY',
            raw_image_path = ?,
            final_image_path = ?,
            error_message = NULL,
            batch_error = NULL,
            batch_state = 'JOB_STATE_SUCCEEDED',
            batch_completed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (raw_image_path, final_image_path, post_id),
    )
    conn.commit()
    conn.close()


def mark_image_failed(post_id: int, error_message: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET status = 'IMAGE_FAILED',
            error_message = ?,
            batch_error = ?,
            batch_state = COALESCE(batch_state, 'JOB_STATE_FAILED'),
            batch_completed_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (error_message[:1000], error_message[:1000], post_id),
    )
    conn.commit()
    conn.close()


def update_status(post_id: int, status: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET status = ?,
            error_message = CASE WHEN ? = 'READY' THEN NULL ELSE error_message END,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (status, status, post_id),
    )
    conn.commit()
    conn.close()


def update_post_caption(post_id: int, caption: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET caption = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (caption, post_id),
    )
    conn.commit()
    conn.close()


def list_unposted_posts():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM posts
        WHERE status != 'POSTED'
        ORDER BY id ASC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def delete_posts(post_ids: list[int]) -> int:
    if not post_ids:
        return 0
    conn = get_conn()
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in post_ids)
    cur.execute(f"DELETE FROM posts WHERE id IN ({placeholders})", post_ids)
    deleted = cur.rowcount
    conn.commit()
    conn.close()
    return deleted


def set_batch_for_posts(post_ids: list[int], batch_job_name: str, batch_state: str | None = None):
    if not post_ids:
        return
    conn = get_conn()
    cur = conn.cursor()
    placeholders = ",".join("?" for _ in post_ids)
    params = [batch_job_name, batch_state, *post_ids]
    cur.execute(
        f"""
        UPDATE posts
        SET batch_job_name = ?,
            batch_state = ?,
            batch_submitted_at = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
        WHERE id IN ({placeholders})
        """,
        params,
    )
    conn.commit()
    conn.close()


def update_batch_state(batch_job_name: str, batch_state: str, batch_error: str | None = None):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE posts
        SET batch_state = ?,
            batch_error = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE batch_job_name = ?
          AND status = 'WAITING_IMAGE'
        """,
        (batch_state, batch_error[:1000] if batch_error else None, batch_job_name),
    )
    conn.commit()
    conn.close()


def list_posts_for_batch_submission(limit: int = 100):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM posts
        WHERE status = 'WAITING_IMAGE'
          AND batch_job_name IS NULL
        ORDER BY scheduled_at ASC, id ASC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_posts_for_direct_image_generation(start_after_iso: str, cutoff_iso: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT *
        FROM posts
        WHERE status IN ('WAITING_IMAGE', 'IMAGE_FAILED')
          AND scheduled_at > ?
          AND scheduled_at <= ?
        ORDER BY scheduled_at ASC, id ASC
        """,
        (start_after_iso, cutoff_iso),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_batch_jobs_to_poll():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT batch_job_name
        FROM posts
        WHERE status = 'WAITING_IMAGE'
          AND batch_job_name IS NOT NULL
        GROUP BY batch_job_name
        ORDER BY MIN(batch_submitted_at) ASC
        """
    )
    rows = [row["batch_job_name"] for row in cur.fetchall()]
    conn.close()
    return rows


def batch_publish_overview(now_iso: str) -> dict:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM posts
        WHERE status = 'WAITING_IMAGE'
          AND batch_job_name IS NULL
        """
    )
    waiting_unsubmitted = cur.fetchone()["total"]

    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM posts
        WHERE status = 'WAITING_IMAGE'
          AND batch_job_name IS NOT NULL
        """
    )
    waiting_submitted = cur.fetchone()["total"]

    cur.execute(
        """
        SELECT COUNT(DISTINCT batch_job_name) AS total
        FROM posts
        WHERE status = 'WAITING_IMAGE'
          AND batch_job_name IS NOT NULL
        """
    )
    batch_jobs_to_poll = cur.fetchone()["total"]

    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM posts
        WHERE status = 'READY'
          AND scheduled_at <= ?
        """,
        (now_iso,),
    )
    due_ready = cur.fetchone()["total"]

    cur.execute(
        """
        SELECT COUNT(*) AS total
        FROM posts
        WHERE status = 'READY'
          AND scheduled_at > ?
        """,
        (now_iso,),
    )
    future_ready = cur.fetchone()["total"]

    conn.close()
    return {
        "waiting_unsubmitted": waiting_unsubmitted,
        "waiting_submitted": waiting_submitted,
        "batch_jobs_to_poll": batch_jobs_to_poll,
        "due_ready": due_ready,
        "future_ready": future_ready,
    }


def list_posts_by_batch_job(batch_job_name: str):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM posts
        WHERE batch_job_name = ?
          AND status = 'WAITING_IMAGE'
        ORDER BY id ASC
        """,
        (batch_job_name,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_recent_posts(limit: int = 10):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM posts
        ORDER BY scheduled_at DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def list_posts(status: str | None = None, limit: int = 100):
    conn = get_conn()
    cur = conn.cursor()
    if status:
        cur.execute(
            """
            SELECT * FROM posts
            WHERE status = ?
            ORDER BY scheduled_at ASC, id ASC
            LIMIT ?
            """,
            (status, limit),
        )
    else:
        cur.execute(
            """
            SELECT * FROM posts
            ORDER BY scheduled_at ASC, id ASC
            LIMIT ?
            """,
            (limit,),
        )
    rows = cur.fetchall()
    conn.close()
    return rows


def dashboard_stats() -> dict:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT status, COUNT(*) AS total FROM posts GROUP BY status")
    status_counts = {row["status"]: row["total"] for row in cur.fetchall()}
    cur.execute("SELECT topic_type, COUNT(*) AS total FROM posts GROUP BY topic_type")
    type_counts = {row["topic_type"]: row["total"] for row in cur.fetchall()}
    cur.execute("SELECT COUNT(*) AS total FROM posts")
    total = cur.fetchone()["total"]
    conn.close()

    return {
        "total": total,
        "status_counts": Counter(status_counts),
        "type_counts": Counter(type_counts),
        "db_path": str(Path(DB_PATH)),
    }
