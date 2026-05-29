import csv
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config import (
    PRODUCT_COMMENT_IMAGE_DELAY_MINUTES,
    PRODUCT_COMMENT_VIDEO_DELAY_MINUTES,
    PRODUCT_COMMENTS_PER_POST,
    PRODUCT_LINKS_CSV,
    TIMEZONE,
)
from app.db import (
    insert_product_comment,
    list_due_product_comments,
    mark_product_comment_failed,
    mark_product_comment_posted,
)
from app.facebook_service import publish_comment


LINK_FIELDS = ("Link ưu đãi", "Link sản phẩm", "link", "url")
NAME_FIELDS = ("Tên sản phẩm", "name", "title")


def load_products() -> list[dict]:
    if not PRODUCT_LINKS_CSV:
        return []

    path = Path(PRODUCT_LINKS_CSV).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"Product CSV not found: {path}")

    products = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            name = first_value(row, NAME_FIELDS)
            link = first_value(row, LINK_FIELDS)
            if not name or not link:
                continue
            products.append(
                {
                    "name": compact_product_name(name),
                    "link": link.strip(),
                }
            )
    return products


def first_value(row: dict, keys: tuple[str, ...]) -> str:
    for key in keys:
        value = row.get(key)
        if value:
            return value.strip()
    return ""


def compact_product_name(name: str, max_chars: int = 72) -> str:
    cleaned = " ".join(name.replace("[", "").replace("]", "").split())
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rstrip() + "…"


def infer_media_type(final_image_path: str | None) -> str:
    suffix = Path(final_image_path or "").suffix.lower()
    if suffix in {".mp4", ".mov", ".m4v", ".webm"}:
        return "video"
    return "image"


def product_comment_delay_minutes(media_type: str) -> int:
    if media_type == "video":
        return PRODUCT_COMMENT_VIDEO_DELAY_MINUTES
    return PRODUCT_COMMENT_IMAGE_DELAY_MINUTES


def pick_products_for_post(post_id: int, count: int) -> list[dict]:
    products = load_products()
    if not products:
        return []

    start = (post_id * count) % len(products)
    selected = []
    for offset in range(min(count, len(products))):
        selected.append(products[(start + offset) % len(products)])
    return selected


def build_product_comment(product: dict, comment_index: int) -> str:
    templates = (
        "Cứu vớt admin khỏi cảnh nói chuyện một mình bằng một cú click nhẹ:\n{product_name}\n{product_link}",
        "Một món nhỏ xinh đi ngang qua, ai thương admin thì ghé xem thử:\n{product_name}\n{product_link}",
        "Không bắt mua đâu, chỉ xin một ánh nhìn cho admin có động lực nuôi page:\n{product_name}\n{product_link}",
        "Nếu bài này làm bạn cười 1 chút, cho admin gửi ké món này nha:\n{product_name}\n{product_link}",
        "Góc tự cứu lấy ví content của admin, xem vui cũng được:\n{product_name}\n{product_link}",
    )
    template = templates[(comment_index - 1) % len(templates)]
    return template.format(product_name=product["name"], product_link=product["link"])


def schedule_product_comments_for_post(post: dict, fb_post_id: str, posted_at: datetime | None = None) -> int:
    if not fb_post_id:
        return 0

    products = pick_products_for_post(post["id"], PRODUCT_COMMENTS_PER_POST)
    if not products:
        return 0

    tz = ZoneInfo(TIMEZONE)
    base_time = posted_at or datetime.now(tz)
    if base_time.tzinfo is None:
        base_time = base_time.replace(tzinfo=tz)

    media_type = infer_media_type(post["final_image_path"])
    delay_minutes = product_comment_delay_minutes(media_type)

    inserted = 0
    for index, product in enumerate(products, start=1):
        scheduled_at = base_time + timedelta(minutes=delay_minutes + ((index - 1) * 2))
        did_insert = insert_product_comment(
            {
                "post_id": post["id"],
                "fb_post_id": fb_post_id,
                "comment_index": index,
                "product_name": product["name"],
                "product_link": product["link"],
                "message": build_product_comment(product, index),
                "scheduled_at": scheduled_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
        )
        if did_insert:
            inserted += 1
    return inserted


def publish_due_product_comments(now: datetime | None = None, limit: int = 5, dry_run: bool = False) -> list[dict]:
    tz = ZoneInfo(TIMEZONE)
    now = now or datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)

    rows = list_due_product_comments(now.strftime("%Y-%m-%d %H:%M:%S"), limit=limit)
    results = []
    for row in rows:
        if dry_run:
            results.append({"id": row["id"], "status": "DRY_RUN", "fb_post_id": row["fb_post_id"]})
            continue
        try:
            result = publish_comment(row["fb_post_id"], row["message"])
            fb_comment_id = result.get("id", "")
            mark_product_comment_posted(row["id"], fb_comment_id)
            results.append({"id": row["id"], "status": "POSTED", "fb_comment_id": fb_comment_id})
        except Exception as exc:
            mark_product_comment_failed(row["id"], str(exc))
            results.append({"id": row["id"], "status": "FAILED", "error": str(exc)})
    return results
