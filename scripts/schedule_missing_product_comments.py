import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import TIMEZONE
from app.db import get_conn, init_db
from app.product_comment_service import schedule_product_comments_for_post


def parse_limit(args: list[str]) -> int:
    for arg in args:
        if arg.startswith("--limit="):
            return int(arg.split("=", 1)[1])
    return 20


def parse_post_id(args: list[str]) -> int | None:
    for arg in args:
        if arg.startswith("--post-id="):
            return int(arg.split("=", 1)[1])
    return None


def list_posted_posts_without_product_comments(limit: int, post_id: int | None):
    conn = get_conn()
    cur = conn.cursor()
    params = []
    where = """
        p.status = 'POSTED'
        AND p.fb_post_id IS NOT NULL
        AND p.fb_post_id != ''
        AND NOT EXISTS (
            SELECT 1
            FROM post_product_comments c
            WHERE c.post_id = p.id
        )
    """
    if post_id is not None:
        where += " AND p.id = ?"
        params.append(post_id)
    params.append(limit)
    cur.execute(
        f"""
        SELECT p.*
        FROM posts p
        WHERE {where}
        ORDER BY p.scheduled_at DESC, p.id DESC
        LIMIT ?
        """,
        params,
    )
    rows = cur.fetchall()
    conn.close()
    return rows


if __name__ == "__main__":
    apply = "--apply" in sys.argv[1:]
    immediate = "--immediate" in sys.argv[1:]
    limit = parse_limit(sys.argv[1:])
    post_id = parse_post_id(sys.argv[1:])

    init_db()
    rows = list_posted_posts_without_product_comments(limit=limit, post_id=post_id)
    if not rows:
        print("No POSTED posts missing product comments.")
        sys.exit(0)

    print(f"POSTED posts missing product comments: {len(rows)}")
    for row in rows:
        print(f"ID={row['id']} | {row['scheduled_at']} | {row['topic_key']} | fb_post_id={row['fb_post_id']}")

    if not apply:
        print("Dry run only. Re-run with --apply to create comment queue.")
        sys.exit(0)

    tz = ZoneInfo(TIMEZONE)
    now = datetime.now(tz)
    total = 0
    for row in rows:
        created = schedule_product_comments_for_post(
            row,
            row["fb_post_id"],
            posted_at=now,
            immediate=immediate,
        )
        total += created
        print(f"Scheduled product comments for post ID={row['id']}: {created}")

    print(f"Total scheduled product comments: {total}")
