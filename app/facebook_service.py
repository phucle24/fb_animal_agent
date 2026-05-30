import requests

from app.config import FB_GRAPH_VERSION, FB_PAGE_ID, FB_PAGE_TOKEN


class FacebookGraphError(RuntimeError):
    def __init__(self, result: dict, status_code: int):
        super().__init__(str(result))
        self.result = result
        self.status_code = status_code
        self.error = result.get("error", {}) if isinstance(result, dict) else {}

    @property
    def code(self):
        return self.error.get("code")

    @property
    def subcode(self):
        return self.error.get("error_subcode")


def _ensure_facebook_config():
    missing = []
    if not FB_PAGE_ID:
        missing.append("ANIMAL_AGENT_FB_PAGE_ID")
    if not FB_PAGE_TOKEN:
        missing.append("ANIMAL_AGENT_FB_PAGE_TOKEN")
    if missing:
        raise RuntimeError(f"Missing Facebook config: {', '.join(missing)}")


def publish_photo(image_path: str, caption: str) -> dict:
    _ensure_facebook_config()
    url = f"https://graph.facebook.com/{FB_GRAPH_VERSION}/{FB_PAGE_ID}/photos"

    with open(image_path, "rb") as img:
        files = {"source": img}
        data = {
            "caption": caption,
            "published": "true",
            "access_token": FB_PAGE_TOKEN,
        }
        response = requests.post(url, files=files, data=data, timeout=120)

    result = response.json()

    if response.status_code >= 400 or "error" in result:
        raise FacebookGraphError(result, response.status_code)

    return result


def publish_comment(fb_post_id: str, message: str) -> dict:
    _ensure_facebook_config()
    url = f"https://graph.facebook.com/{FB_GRAPH_VERSION}/{fb_post_id}/comments"
    response = requests.post(
        url,
        data={
            "message": message,
            "access_token": FB_PAGE_TOKEN,
        },
        timeout=60,
    )
    result = response.json()

    if response.status_code >= 400 or "error" in result:
        raise FacebookGraphError(result, response.status_code)

    return result
