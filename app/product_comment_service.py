import csv
import re
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
    REEL_PRODUCT_COMMENTS_PER_POST,
    TIMEZONE,
)
from app.db import (
    claim_due_product_comments,
    insert_product_comment,
    insert_product_comment_once,
    list_due_product_comments,
    mark_product_comment_failed,
    mark_product_comment_posted,
)
from app.facebook_service import (
    FacebookGraphError,
    list_recent_page_posts,
    list_recent_page_reels,
    list_recent_page_videos,
    publish_comment,
)


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
    if comment_index == 1:
        return (
            "Nếu mọi người thấy nội dung này hữu ích, hãy cho mình xin một like, share và theo dõi kênh nhé! "
            "Mỗi lượt click vào link Shopee của các bạn là một chút hoa hồng giúp team editor mua "
            '"bản quyền phần mềm" và duy trì kênh. Cảm ơn cả nhà yêu rất nhiều! ❤️\n'
            f'{product["name"]}\n'
            f'{product["link"]}'
        )
    return f'{product["name"]}\n{product["link"]}'


VIEWER_REPLY_TEMPLATES = (
    "Cảm ơn bạn đã ghé xem. Follow kênh để khỏi lạc mất mấy thước phim vui vui tiếp theo nha!",
    "Xem tới đây là có gu rồi đó. Bấm follow để lần sau thuật toán khỏi giấu video của tụi mình nha.",
    "Cảm ơn bạn đã dừng chân ở chiếc video này. Follow kênh để còn gặp lại nhau ở tập sau nha!",
    "Nếu video này làm bạn nhướng mày nhẹ, follow kênh để nhận thêm mấy pha thiên nhiên khó tin nha.",
    "Đội xem vui vẻ điểm danh. Follow kênh để lần sau khỏi đi tìm trong vô vọng nha!",
    "Cảm ơn bạn đã xem. Kênh còn nhiều cú twist của tự nhiên lắm, follow để không bỏ lỡ nha!",
    "Bạn vừa mở khóa một mẩu chuyện nhỏ của thế giới tự nhiên. Follow để nhặt tiếp mấy mẩu hay ho nha!",
    "Video này hết nhưng drama thiên nhiên còn dài. Follow kênh để xem tiếp phần sau nha!",
    "Cảm ơn bạn đã ở lại tới đây. Follow một cái cho thuật toán biết mình còn gặp nhau nha!",
    "Nếu thấy vui vui, follow kênh để lần sau video tự tìm tới bạn, khỏi mất công săn lùng nha!",
)


DONATE_COMMENT_TEMPLATES = (
    "Góc hậu trường của kênh, ai tò mò thì ghé chơi ở đây:\n{url}",
    "Khu vực bí mật của admin nằm ở đây, vào tham quan cho vui:\n{url}",
    "Nếu bạn thích mấy chiếc video kiểu này, đây là góc nhỏ phía sau kênh:\n{url}",
    "Đường hầm nhỏ dẫn về căn cứ của admin, đi ngang thì ghé nha:\n{url}",
    "Một chiếc link ngoài lề cho ai muốn xem kênh vận hành phía sau màn hình:\n{url}",
    "Góc chill của admin sau mỗi lần dựng video, để đây cho ai cần:\n{url}",
    "Bản đồ kho báu mini của kênh nằm ở đây, mở hay không tùy tâm trạng:\n{url}",
    "Ai đang rảnh tay thì có thể ghé căn cứ nhỏ này của admin:\n{url}",
    "Link này không cắn, chỉ nằm đây cho video bớt cô đơn:\n{url}",
    "Một trạm dừng chân nho nhỏ cho người xem hệ thích khám phá:\n{url}",
)


def build_viewer_reply_comment(comment_id: str) -> str:
    index = zlib.crc32(comment_id.encode("utf-8")) % len(VIEWER_REPLY_TEMPLATES)
    return VIEWER_REPLY_TEMPLATES[index]


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


def extract_video_id_from_url(url: str) -> str:
    if not url:
        return ""
    match = re.search(r"/(?:reel|reels|videos)/(\d+)", url)
    if match:
        return match.group(1)
    match = re.search(r"[?&](?:v|video_id|story_fbid)=(\d+)", url)
    if match:
        return match.group(1)
    return ""


def canonical_video_object_id(item: dict) -> str:
    permalink_id = extract_video_id_from_url(str(item.get("permalink_url") or ""))
    if permalink_id:
        return permalink_id

    for attachment in ((item.get("attachments") or {}).get("data") or []):
        target_id = str((attachment.get("target") or {}).get("id") or "")
        if target_id:
            return target_id
        attachment_id = extract_video_id_from_url(str(attachment.get("url") or ""))
        if attachment_id:
            return attachment_id

    return str(item.get("id") or "")


def normalize_external_video_objects() -> list[dict]:
    objects = []
    seen = set()

    try:
        posts = list_recent_page_posts(limit=DONATE_COMMENT_SCAN_LIMIT)
    except Exception:
        posts = []
    for post in posts:
        if not is_reel_or_video_post(post):
            continue
        fb_post_id = canonical_video_object_id(post)
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

    try:
        videos = list_recent_page_videos(limit=DONATE_COMMENT_SCAN_LIMIT)
    except Exception:
        videos = []
    for video in videos:
        fb_post_id = canonical_video_object_id(video)
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

    try:
        reels = list_recent_page_reels(limit=DONATE_COMMENT_SCAN_LIMIT)
    except Exception:
        reels = []
    for reel in reels:
        fb_post_id = canonical_video_object_id(reel)
        if not fb_post_id or fb_post_id in seen:
            continue
        seen.add(fb_post_id)
        objects.append(
            {
                "fb_post_id": fb_post_id,
                "created_at": parse_facebook_time(reel.get("created_time", "")),
                "source": "video_reels",
            }
        )

    def sort_key(item: dict):
        return item["created_at"] or datetime.min.replace(tzinfo=ZoneInfo(TIMEZONE))

    objects.sort(key=sort_key, reverse=True)
    return objects[:DONATE_COMMENT_SCAN_LIMIT]


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
        created_at = item["created_at"] or now
        created_local = created_at.astimezone(tz)
        if created_local < lookback_start:
            continue

        scheduled_at = created_local + timedelta(minutes=DONATE_COMMENT_DELAY_MINUTES)
        external_id = external_post_id(item["fb_post_id"])
        donate_data = {
            "post_id": external_id,
            "fb_post_id": item["fb_post_id"],
            "comment_index": 1,
            "product_name": "Ủng hộ kênh",
            "product_link": DONATE_COMMENT_URL,
            "message": build_donate_comment(item["fb_post_id"]),
            "scheduled_at": scheduled_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        if dry_run:
            donate_inserted = False
        else:
            donate_inserted = insert_product_comment_once(donate_data)
        results.append(
            {
                "fb_post_id": item["fb_post_id"],
                "scheduled_at": donate_data["scheduled_at"],
                "inserted": donate_inserted,
                "source": item["source"],
                "kind": "donate",
            }
        )

        products = pick_products_for_post(external_id, REEL_PRODUCT_COMMENTS_PER_POST)
        for offset, product in enumerate(products, start=1):
            product_scheduled_at = scheduled_at + timedelta(minutes=offset * 2)
            product_data = {
                "post_id": external_id,
                "fb_post_id": item["fb_post_id"],
                "comment_index": offset + 1,
                "product_name": product["name"],
                "product_link": product["link"],
                "message": build_product_comment(product, offset),
                "scheduled_at": product_scheduled_at.strftime("%Y-%m-%d %H:%M:%S"),
            }
            if dry_run:
                product_inserted = False
            else:
                product_inserted = insert_product_comment_once(product_data)
            results.append(
                {
                    "fb_post_id": item["fb_post_id"],
                    "scheduled_at": product_data["scheduled_at"],
                    "inserted": product_inserted,
                    "source": item["source"],
                    "kind": "product",
                    "product_name": product["name"],
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

    now_iso = now.strftime("%Y-%m-%d %H:%M:%S")
    if dry_run:
        rows = list_due_product_comments(now_iso, limit=limit)
    else:
        rows = claim_due_product_comments(now_iso, limit=limit)

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
