import os
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:
    def load_dotenv():
        return False


load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DB_PATH = BASE_DIR / os.getenv("ANIMAL_AGENT_DB_PATH", "data/agent.db")
OUTPUT_DIR = BASE_DIR / os.getenv("ANIMAL_AGENT_OUTPUT_DIR", "assets")
RAW_DIR = OUTPUT_DIR / "raw"
FINAL_DIR = OUTPUT_DIR / "final"
LOG_DIR = BASE_DIR / "logs"
GENERATED_TOPICS_PATH = BASE_DIR / os.getenv(
    "ANIMAL_AGENT_GENERATED_TOPICS_PATH",
    "data/generated_topics.jsonl",
)
PRODUCT_LINKS_CSV = os.getenv("ANIMAL_AGENT_PRODUCT_LINKS_CSV", "").strip()
PRODUCT_COMMENT_IMAGE_DELAY_MINUTES = int(os.getenv("ANIMAL_AGENT_PRODUCT_COMMENT_IMAGE_DELAY_MINUTES", "15"))
PRODUCT_COMMENT_VIDEO_DELAY_MINUTES = int(os.getenv("ANIMAL_AGENT_PRODUCT_COMMENT_VIDEO_DELAY_MINUTES", "30"))
PRODUCT_COMMENTS_PER_POST = int(os.getenv("ANIMAL_AGENT_PRODUCT_COMMENTS_PER_POST", "2"))

for path in [DB_PATH.parent, OUTPUT_DIR, RAW_DIR, FINAL_DIR, LOG_DIR, GENERATED_TOPICS_PATH.parent]:
    path.mkdir(parents=True, exist_ok=True)

GEMINI_API_KEY = os.getenv("ANIMAL_AGENT_GEMINI_API_KEY", "").strip()
GEMINI_TEXT_MODEL = os.getenv("ANIMAL_AGENT_GEMINI_TEXT_MODEL", "gemini-2.5-flash").strip()
GEMINI_IMAGE_MODEL = os.getenv(
    "ANIMAL_AGENT_GEMINI_IMAGE_MODEL",
    "gemini-2.5-flash-image",
).strip()
IMAGE_FALLBACK_ON_ERROR = os.getenv("ANIMAL_AGENT_IMAGE_FALLBACK_ON_ERROR", "false").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
IMAGE_ASPECT_RATIO = os.getenv("ANIMAL_AGENT_IMAGE_ASPECT_RATIO", "4:5").strip()

FB_PAGE_ID = os.getenv("ANIMAL_AGENT_FB_PAGE_ID", "").strip()
FB_PAGE_TOKEN = os.getenv("ANIMAL_AGENT_FB_PAGE_TOKEN", "").strip()
FB_GRAPH_VERSION = os.getenv("ANIMAL_AGENT_FB_GRAPH_VERSION", "v21.0").strip()
TIMEZONE = os.getenv("ANIMAL_AGENT_TIMEZONE", "Asia/Ho_Chi_Minh").strip()

FONT_BOLD = os.getenv(
    "ANIMAL_AGENT_FONT_BOLD",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
).strip()

FONT_REGULAR = os.getenv(
    "ANIMAL_AGENT_FONT_REGULAR",
    "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
).strip()

WEB_HOST = os.getenv("ANIMAL_AGENT_WEB_HOST", "127.0.0.1").strip()
WEB_PORT = int(os.getenv("ANIMAL_AGENT_WEB_PORT", "8000"))
WEB_SECRET_KEY = os.getenv("ANIMAL_AGENT_WEB_SECRET_KEY", "change-me-local-dashboard")

MIN_FUTURE_POSTS = int(os.getenv("ANIMAL_AGENT_MIN_FUTURE_POSTS", "4"))
TARGET_FUTURE_POSTS = int(os.getenv("ANIMAL_AGENT_TARGET_FUTURE_POSTS", "4"))
DIRECT_IMAGE_BOOTSTRAP_DAYS = int(
    os.getenv(
        "ANIMAL_AGENT_DIRECT_IMAGE_BOOTSTRAP_DAYS",
        os.getenv("ANIMAL_AGENT_DIRECT_IMAGE_DAYS", "2"),
    )
)
DIRECT_IMAGE_BOOTSTRAP_UNTIL = os.getenv("ANIMAL_AGENT_DIRECT_IMAGE_BOOTSTRAP_UNTIL", "").strip()
AUTO_GENERATE_TOPICS = os.getenv("ANIMAL_AGENT_AUTO_GENERATE_TOPICS", "true").lower() in {
    "1",
    "true",
    "yes",
    "on",
}
