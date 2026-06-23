import csv
import json
import re
import unicodedata
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
SOLD_FIELDS = (
    "Doanh thu",
    "doanh thu",
    "Lượt bán",
    "lượt bán",
    "Da ban",
    "Đã bán",
    "đã bán",
    "sold",
    "sales",
    "sold_count",
)

IMPORTANT_SHORT_TOKENS = {"ca", "ga", "bo", "de", "oc"}
PRODUCT_STOPWORDS = {
    "ban",
    "bao",
    "bang",
    "bo",
    "cac",
    "cao",
    "cap",
    "cat",
    "cho",
    "chinh",
    "combo",
    "cua",
    "danh",
    "dong",
    "duoc",
    "dung",
    "goi",
    "hang",
    "kem",
    "khong",
    "loai",
    "mau",
    "moi",
    "nhieu",
    "san",
    "set",
    "si",
    "sieu",
    "tang",
    "theo",
    "thich",
    "thuong",
    "tien",
    "tot",
    "tu",
    "va",
    "voi",
}

CATEGORY_KEYWORDS = {
    "cat": (
        "tiger",
        "su tu",
        "lion",
        "leopard",
        "cheetah",
        "jaguar",
        "lynx",
        "felid",
    ),
    "dog": (
        "cun",
        "dog",
        "soi",
        "wolf",
        "coyote",
        "jackal",
        "mastiff",
        "husky",
        "canid",
    ),
    "pet": ("thu cung", "pet", "cham soc meo", "cham soc cho", "cho meo", "meo cho"),
    "bird": (
        "chim",
        "bird",
        "dai bang",
        "eagle",
        "cu meo",
        "owl",
        "canh cut",
        "penguin",
        "falcon",
        "da dieu",
        "ostrich",
        "weaverbird",
    ),
    "sea": (
        "bien",
        "dai duong",
        "hai san",
        "rong bien",
        "fish",
        "ca map",
        "shark",
        "squid",
        "octopus",
        "bach tuot",
        "shrimp",
        "crab",
        "turtle",
        "jellyfish",
        "seahorse",
        "salmon",
        "arowana",
    ),
    "plant": (
        "plant",
        "flower",
        "oc cho",
        "macca",
        "sachi",
        "oliu",
        "venus",
        "rafflesia",
        "nap am",
    ),
    "insect": (
        "con trung",
        "insect",
        "ant",
        "bee",
        "beetle",
        "fly",
        "worm",
        "termite",
    ),
    "reptile_amphibian": (
        "snake",
        "ran ho mang",
        "crocodile",
        "alligator",
        "frog",
        "thằn lan",
        "than lan",
        "lizard",
        "turtle",
    ),
    "animal_toy": (
        "thu bong",
        "gau bong",
        "do choi",
        "mo hinh",
        "lap rap",
        "xep hinh",
        "khung long",
    ),
}

RELATED_CATEGORY_BONUS = {
    "cat": {"pet": 8, "animal_toy": 5},
    "dog": {"pet": 8, "animal_toy": 5},
    "pet": {"cat": 8, "dog": 8, "animal_toy": 4},
    "bird": {"animal_toy": 5},
    "sea": {"animal_toy": 4},
    "plant": {},
    "insect": {"animal_toy": 5},
    "reptile_amphibian": {"sea": 3, "animal_toy": 5},
    "animal_toy": {"cat": 2, "dog": 2, "bird": 2, "sea": 2, "insect": 2, "reptile_amphibian": 2},
}


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
                    "raw_name": " ".join(name.split()),
                    "link": link.strip(),
                    "sold": compact_sold_count(first_value(row, SOLD_FIELDS)),
                }
            )
    for product in products:
        enrich_product_for_matching(product)
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


def compact_sold_count(value: str) -> str:
    cleaned = " ".join((value or "").replace("+", "").split()).strip()
    cleaned = cleaned.replace("đã bán", "").replace("Đã bán", "").replace("lượt bán", "").replace("Lượt bán", "")
    return cleaned.strip(" :-–—")


def normalize_search_text(text: str) -> str:
    text = (text or "").lower().replace("đ", "d")
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def search_tokens(text: str) -> set[str]:
    tokens = set()
    for token in normalize_search_text(text).split():
        if token in PRODUCT_STOPWORDS:
            continue
        if len(token) >= 3 or token in IMPORTANT_SHORT_TOKENS:
            tokens.add(token)
    return tokens


def contains_keyword(normalized_text: str, keyword: str) -> bool:
    keyword = normalize_search_text(keyword)
    if not keyword:
        return False
    return f" {keyword} " in f" {normalized_text} "


def raw_has_word(text: str, word: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(word)}(?!\w)", text, flags=re.IGNORECASE) is not None


def infer_categories(text: str, product_context: bool = False) -> set[str]:
    raw_lower = (text or "").lower()
    normalized = normalize_search_text(text)
    categories = set()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(contains_keyword(normalized, keyword) for keyword in keywords):
            categories.add(category)

    # Accented Vietnamese words such as "chó", "mèo", "cây", "mối" collide with
    # common unaccented words after normalization, so handle them before scoring.
    if "mèo" in raw_lower or raw_has_word(raw_lower, "cat"):
        categories.add("cat")
    if "cú mèo" in raw_lower and not any(word in raw_lower for word in ("hổ", "báo", "sư tử")):
        categories.discard("cat")
        categories.add("bird")
    if "chó" in raw_lower or "cún" in raw_lower:
        categories.add("dog")
    if not product_context and "cây" in raw_lower:
        categories.add("plant")
    if any(word in raw_lower for word in ("hổ", "báo", "sư tử")):
        categories.add("cat")
    sea_raw_words = (
        "cá",
        "ca",
        "mực",
        "muc",
        "tôm",
        "tom",
        "cua",
        "rùa",
        "rua",
        "sứa",
        "sua",
        "bạch tuộc",
        "hải sản",
        "rong biển",
        "cá hồi",
        "cá ngừ",
    )
    if any(raw_has_word(raw_lower, word) for word in sea_raw_words):
        categories.add("sea")
    plant_raw_words = (
        "hạt",
        "hoa",
        "quả",
        "rau củ",
        "ngũ cốc",
        "đậu",
        "trái cây",
        "thực vật",
        "dầu oliu",
        "dầu óc chó",
    )
    if not product_context:
        plant_raw_words = (*plant_raw_words, "cây")
    if any(raw_has_word(raw_lower, word) for word in plant_raw_words):
        categories.add("plant")
    insect_words = ("bọ", "mối", "ong", "ruồi", "gián")
    if any(raw_has_word(raw_lower, word) for word in insect_words) or (
        raw_has_word(raw_lower, "kiến") and not raw_has_word(raw_lower, "kiến trúc")
    ):
        categories.add("insect")
    reptile_words = ("rắn", "ếch", "cá sấu", "thằn lằn")
    if any(raw_has_word(raw_lower, word) for word in reptile_words):
        categories.add("reptile_amphibian")

    if categories & {"cat", "dog"}:
        categories.add("pet")
    return categories


def sold_count_value(value: str) -> int:
    normalized = normalize_search_text(value)
    match = re.search(r"(\d+(?:[.,]\d+)?)\s*(tr|m|k)?", normalized)
    if not match:
        return 0
    number = float(match.group(1).replace(",", "."))
    unit = match.group(2) or ""
    if unit in {"tr", "m"}:
        number *= 1_000_000
    elif unit == "k":
        number *= 1_000
    return int(number)


def enrich_product_for_matching(product: dict) -> dict:
    match_text = product.get("raw_name") or product.get("name") or ""
    product["match_text"] = normalize_search_text(match_text)
    product["match_tokens"] = search_tokens(match_text)
    product["categories"] = infer_categories(match_text, product_context=True)
    product["sold_value"] = sold_count_value(product.get("sold", ""))
    return product


def flatten_payload_text(value) -> str:
    if not value:
        return ""
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            return value
        return flatten_payload_text(parsed)
    if isinstance(value, dict):
        return " ".join(flatten_payload_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(flatten_payload_text(item) for item in value)
    return str(value)


def category_overlap_score(content_categories: set[str], product_categories: set[str]) -> int:
    score = 0
    for category in content_categories:
        if category in product_categories:
            score += 12
        for related_category, bonus in RELATED_CATEGORY_BONUS.get(category, {}).items():
            if related_category in product_categories:
                score += bonus
    return score


def text_match_score(text: str, product: dict, token_weight: int, category_weight: int) -> int:
    tokens = search_tokens(text)
    token_score = len(tokens & product.get("match_tokens", set())) * token_weight
    categories = infer_categories(text)
    category_score = category_overlap_score(categories, product.get("categories", set())) * category_weight
    return token_score + category_score


def rank_products_for_context(
    products: list[dict],
    seed: int | str,
    title: str = "",
    caption: str = "",
    topic_type: str = "",
    topic_payload: str = "",
) -> list[tuple[int, dict]]:
    topic_text = " ".join([topic_type or "", flatten_payload_text(topic_payload)])
    ranked = []
    for product in products:
        title_score = text_match_score(title, product, token_weight=14, category_weight=2)
        caption_score = text_match_score(caption, product, token_weight=5, category_weight=1)
        topic_score = text_match_score(topic_text, product, token_weight=3, category_weight=1)
        score = title_score or caption_score or topic_score
        ranked.append((score, product))

    def sort_key(item):
        score, product = item
        stable = zlib.crc32(f"{seed}:{product.get('link', '')}".encode("utf-8"))
        return (-score, -int(product.get("sold_value") or 0), stable)

    ranked.sort(key=sort_key)
    return ranked


def product_comment_line(product: dict) -> str:
    sold = product.get("sold", "").strip()
    if sold:
        return f'{product["name"]} với hơn {sold} lượt bán\n{product["link"]}'
    return f'{product["name"]}\n{product["link"]}'


def infer_media_type(final_image_path: str | None) -> str:
    suffix = Path(final_image_path or "").suffix.lower()
    if suffix in {".mp4", ".mov", ".m4v", ".webm"}:
        return "video"
    return "image"


def product_comment_delay_minutes(media_type: str) -> int:
    if media_type == "video":
        return PRODUCT_COMMENT_VIDEO_DELAY_MINUTES
    return PRODUCT_COMMENT_IMAGE_DELAY_MINUTES


def fallback_pick_products(products: list[dict], seed: int | str, count: int) -> list[dict]:
    if not products:
        return []

    seed_value = seed if isinstance(seed, int) else zlib.crc32(str(seed).encode("utf-8"))
    start = (seed_value * count) % len(products)
    selected = []
    for offset in range(min(count, len(products))):
        selected.append(products[(start + offset) % len(products)])
    return selected


def pick_products_for_context(
    seed: int | str,
    count: int,
    title: str = "",
    caption: str = "",
    topic_type: str = "",
    topic_payload: str = "",
) -> list[dict]:
    products = load_products()
    if not products:
        return []

    ranked = rank_products_for_context(
        products,
        seed=seed,
        title=title,
        caption=caption,
        topic_type=topic_type,
        topic_payload=topic_payload,
    )

    if not ranked or ranked[0][0] <= 0:
        return fallback_pick_products(products, seed, count)

    selected = []
    seen_links = set()
    for score, product in ranked:
        if score <= 0:
            break
        link = product.get("link", "")
        if link in seen_links:
            continue
        seen_links.add(link)
        selected.append(product)
        if len(selected) >= count:
            break

    if len(selected) < count:
        for product in fallback_pick_products(products, seed, count):
            link = product.get("link", "")
            if link in seen_links:
                continue
            selected.append(product)
            seen_links.add(link)
            if len(selected) >= count:
                break

    return selected


def pick_products_for_post(post_id: int, count: int) -> list[dict]:
    return pick_products_for_context(post_id, count)


def first_nonempty_line(text: str) -> str:
    for line in (text or "").splitlines():
        line = line.strip()
        if line:
            return line
    return ""


def build_product_comment(product: dict, comment_index: int) -> str:
    product_line = product_comment_line(product)
    if comment_index == 1:
        return (
            "Nếu mọi người thấy nội dung này hữu ích, hãy cho mình xin một like, share và theo dõi kênh nhé! "
            "Mỗi lượt click vào link Shopee của các bạn là một chút hoa hồng giúp team editor mua "
            '"bản quyền phần mềm" và duy trì kênh. Cảm ơn cả nhà yêu rất nhiều! ❤️\n'
            f"{product_line}"
        )
    return product_line


VIEWER_REPLY_TEMPLATES = (
    "Người đâu mà vừa dễ thương lại còn chăm tương tác. Cảm ơn {viewer_name} nhiều nha! Tiện tay bấm Follow kênh và chia sẻ video cho hội bạn cùng xem nhé! 😍",
    "Cảm ơn {viewer_name} đã ghé chơi và để lại bình luận nha! Follow kênh rồi rủ thêm bạn bè vào khám phá thế giới tự nhiên cùng tụi mình nhé!",
    "Bắt gặp một người xem có tâm là {viewer_name} rồi nha! Bấm Follow kênh và chia sẻ cho đứa bạn mê động vật cùng xem nhé! 😄",
    "Bình luận của {viewer_name} làm admin có thêm năng lượng dựng video rồi đó! Follow kênh và gửi video này cho hội bạn thân nha!",
    "Cảm ơn {viewer_name} đã góp vui cho chiếc video này! Nhớ Follow kênh và chia sẻ cho bạn bè để lần sau mình lại gặp nhau nhé!",
    "{viewer_name} tương tác nhiệt tình thế này làm admin vui cả ngày luôn! Follow kênh và kéo thêm đồng đội vào xem chung nha!",
    "Cảm ơn {viewer_name} nhiều nha! Video còn nhiều chuyện thú vị phía sau lắm, Follow kênh rồi chia sẻ cho bạn bè cùng hóng nhé!",
    "Đã ghi nhận một chiếc bình luận siêu có tâm từ {viewer_name}! Follow kênh và gửi ngay cho người bạn hay tò mò của bạn nha!",
    "{viewer_name} xem video lại còn để lại bình luận, quý quá trời! Follow kênh và chia sẻ nhẹ cho hội bạn cùng vui nha! 🥰",
    "Cảm ơn {viewer_name} đã đồng hành cùng kênh! Bấm Follow và chia sẻ video cho bạn bè để không ai bỏ lỡ tập tiếp theo nhé!",
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


def build_viewer_reply_comment(comment_id: str, viewer_name: str = "bạn") -> str:
    index = zlib.crc32(comment_id.encode("utf-8")) % len(VIEWER_REPLY_TEMPLATES)
    display_name = " ".join((viewer_name or "bạn").split())
    return VIEWER_REPLY_TEMPLATES[index].format(viewer_name=display_name)


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
        caption = post.get("message") or ""
        seen.add(fb_post_id)
        objects.append(
            {
                "fb_post_id": fb_post_id,
                "created_at": parse_facebook_time(post.get("created_time", "")),
                "source": "posts",
                "title": first_nonempty_line(caption),
                "caption": caption,
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
        caption = video.get("description") or ""
        seen.add(fb_post_id)
        objects.append(
            {
                "fb_post_id": fb_post_id,
                "created_at": parse_facebook_time(video.get("created_time", "")),
                "source": "videos",
                "title": first_nonempty_line(caption),
                "caption": caption,
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
        caption = reel.get("description") or ""
        seen.add(fb_post_id)
        objects.append(
            {
                "fb_post_id": fb_post_id,
                "created_at": parse_facebook_time(reel.get("created_time", "")),
                "source": "video_reels",
                "title": first_nonempty_line(caption),
                "caption": caption,
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

        products = pick_products_for_context(
            external_id,
            REEL_PRODUCT_COMMENTS_PER_POST,
            title=item.get("title", ""),
            caption=item.get("caption", ""),
        )
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

    products = pick_products_for_context(
        post["id"],
        PRODUCT_COMMENTS_PER_POST,
        title=post["title"],
        caption=post["caption"],
        topic_type=post["topic_type"],
        topic_payload=post["topic_payload"],
    )
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
