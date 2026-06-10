import csv
import zlib
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from app.config import (
    DONATE_COMMENT_DELAY_MINUTES,
    DONATE_COMMENT_LOOKBACK_HOURS,
    DONATE_COMMENT_SCAN_LIMIT,
    DONATE_COMMENT_URL,
    PRODUCT_COMMENT_IMAGE_DELAY_MINUTES,
    PRODUCT_COMMENT_VIDEO_DELAY_MINUTES,
    PRODUCT_COMMENTS_PER_POST,
    PRODUCT_LINKS_CSV,
    TIMEZONE,
)
from app.db import (
    insert_product_comment,
    insert_product_comment_once,
    list_due_product_comments,
    mark_product_comment_failed,
    mark_product_comment_posted,
)
from app.facebook_service import FacebookGraphError, list_recent_page_posts, list_recent_page_videos, publish_comment


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


DONATE_COMMENT_TEMPLATES = (
    "Nếu thước phim này làm bạn dừng lướt 3 giây, cứu admin bằng một cú click nhẹ nha:\n{url}",
    "Admin không xin nhiều, chỉ xin một chiếc click bé xíu để nuôi tiếp đam mê cắt video:\n{url}",
    "Bạn xem vui, admin vui lây. Muốn tiếp sức cho kênh thì ghé chiếc link này nha:\n{url}",
    "Góc nạp năng lượng cho admin: một cú click thôi là tinh thần dựng video tăng 200%:\n{url}",
    "Nếu video này ổn áp, cho admin xin ly trà đá tinh thần bằng chiếc link này nha:\n{url}",
    "Không bắt donate đâu, nhưng nếu thương admin thì link này đang ngồi chờ rất ngoan:\n{url}",
    "Cứu ví admin khỏi cảnh mỏng như cánh chuồn bằng một cú ghé nhẹ:\n{url}",
    "Bạn vừa xem miễn phí, admin vừa xin phép thả link tiếp tế cực văn minh ở đây:\n{url}",
    "Nếu thấy kênh còn đáng nuôi, thả cho admin một cú tiếp sức tại đây nha:\n{url}",
    "Một chiếc link nhỏ cho nhân loại, nhưng là động lực khá to cho admin:\n{url}",
)


def build_donate_comment(fb_post_id: str) -> str:
    index = zlib.crc32(fb_post_id.encode("utf-8")) % len(DONATE_COMMENT_TEMPLATES)
    return DONATE_COMMENT_TEMPLATES[index].format(url=DONATE_COMMENT_URL)


def external_post_id(fb_post_id: str) -> int:
    # Keep external/manual Facebook objects out of the positive local posts id range.
    return -int(zlib.crc32(fb_post_id.encode("utf-8")) or 1)


def parse_facebook_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_reel_or_video_post(post: dict) -> bool:
    permalink = (post.get("permalink_url") or "").lower()
    if "/reel/" in permalink or "/reels/" in permalink or "/videos/" in permalink:
        return True

    attachments = ((post.get("attachments") or {}).get("data") or [])
    for attachment in attachments:
        attachment_type = str(attachment.get("type") or "").lower()
        url = str(attachment.get("url") or "").lower()
        if "reel" in attachment_type or "video" in attachment_type:
            return True
        if "/reel/" in url or "/reels/" in url or "/videos/" in url:
            return True
    return False


def normalize_external_video_objects() -> list[dict]:
    objects = []
    seen = set()

    for post in list_recent_page_posts(limit=DONATE_COMMENT_SCAN_LIMIT):
        if not is_reel_or_video_post(post):
            continue
        fb_post_id = post.get("id", "")
        if not fb_post_id or fb_post_id in seen:
            continue
        seen.add(fb_post_id)
        objects.append(
            {
                "fb_post_id": fb_post_id,
                "created_at": parse_facebook_time(post.get("created_time", "")),
                "source": "posts",
            }
        )

    for video in list_recent_page_videos(limit=DONATE_COMMENT_SCAN_LIMIT):
        fb_post_id = video.get("id", "")
        if not fb_post_id or fb_post_id in seen:
            continue
        seen.add(fb_post_id)
        objects.append(
            {
                "fb_post_id": fb_post_id,
                "created_at": parse_facebook_time(video.get("created_time", "")),
                "source": "videos",
            }
        )

    return objects


def schedule_recent_donate_comments(now: datetime | None = None, dry_run: bool = False) -> list[dict]:
    if not DONATE_COMMENT_URL:
        return []

    tz = ZoneInfo(TIMEZONE)
    now = now or datetime.now(tz)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)

    lookback_start = now - timedelta(hours=DONATE_COMMENT_LOOKBACK_HOURS)
    results = []
    for item in normalize_external_video_objects():
        created_at = item["created_at"]
        if created_at is None:
            continue
        created_local = created_at.astimezone(tz)
        if created_local < lookback_start:
            continue

        scheduled_at = created_local + timedelta(minutes=DONATE_COMMENT_DELAY_MINUTES)
        data = {
            "post_id": external_post_id(item["fb_post_id"]),
            "fb_post_id": item["fb_post_id"],
            "comment_index": 1,
            "product_name": "Ủng hộ kênh",
            "product_link": DONATE_COMMENT_URL,
            "message": build_donate_comment(item["fb_post_id"]),
            "scheduled_at": scheduled_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if dry_run:
            inserted = False
        else:
            inserted = insert_product_comment_once(data)
        results.append(
            {
                "fb_post_id": item["fb_post_id"],
                "scheduled_at": data["scheduled_at"],
                "inserted": inserted,
                "source": item["source"],
            }
        )
    return results


def schedule_product_comments_for_post(
    post: dict,
    fb_post_id: str,
    posted_at: datetime | None = None,
    immediate: bool = False,
) -> int:
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
    delay_minutes = 0 if immediate else product_comment_delay_minutes(media_type)

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


def should_try_photo_fallback(exc: Exception) -> bool:
    if not isinstance(exc, FacebookGraphError):
        return False
    return exc.code in {10, 100}


def publish_comment_with_fallback(row) -> dict:
    tried = [row["fb_post_id"]]
    try:
        return publish_comment(row["fb_post_id"], row["message"])
    except Exception as first_exc:
        fb_photo_id = ""
        try:
            fb_photo_id = row["fb_photo_id"] or ""
        except (IndexError, KeyError):
            fb_photo_id = ""

        if fb_photo_id and fb_photo_id not in tried and should_try_photo_fallback(first_exc):
            try:
                return publish_comment(fb_photo_id, row["message"])
            except Exception as second_exc:
                raise RuntimeError(
                    f"post_id target failed: {first_exc}; photo_id fallback failed: {second_exc}"
                ) from second_exc
        raise


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
            result = publish_comment_with_fallback(row)
            fb_comment_id = result.get("id", "")
            mark_product_comment_posted(row["id"], fb_comment_id)
            results.append({"id": row["id"], "status": "POSTED", "fb_comment_id": fb_comment_id})
        except Exception as exc:
            mark_product_comment_failed(row["id"], str(exc))
            results.append({"id": row["id"], "status": "FAILED", "error": str(exc)})
    return results
