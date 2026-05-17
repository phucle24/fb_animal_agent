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

    cur.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_posts_schedule_slot
        ON posts (scheduled_at, slot)
        """
    )
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_status ON posts (status)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_posts_topic_key ON posts (topic_key)")

    conn.commit()
    conn.close()


def insert_post(data: dict) -> int:
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO posts (
            scheduled_at, slot, topic_type, topic_key, title,
            overlay_title, overlay_subtitle, overlay_stat, overlay_hook,
            caption, image_prompt, topic_payload, raw_image_path,
            final_image_path, status
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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

