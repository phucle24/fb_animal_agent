import time
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

    @property
    def is_transient(self) -> bool:
        # Transient Facebook errors: 5xx server errors or transient API codes (1: unknown/service error, 2: temp unavailable, 4/17: rate limit)
        return self.status_code >= 500 or self.code in {1, 2, 4, 17}


def _request_with_retry(method: str, url: str, retries: int = 3, **kwargs) -> requests.Response:
    last_exc = None
    for attempt in range(retries):
        try:
            response = requests.request(method, url, **kwargs)
            if response.status_code >= 500 and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            return response
        except (requests.RequestException, TimeoutError) as exc:
            last_exc = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
    if last_exc:
        raise last_exc
    raise RuntimeError("Unexpected request failure")


def _ensure_facebook_config():
    missing = []
    if not FB_PAGE_ID:
        missing.append("ANIMAL_AGENT_FB_PAGE_ID")
    if not FB_PAGE_TOKEN:
        missing.append("ANIMAL_AGENT_FB_PAGE_TOKEN")
    if missing:
        raise RuntimeError(f"Missing Facebook config: {', '.join(missing)}")


def publish_photo(image_path: str, caption: str, retries: int = 3) -> dict:
    _ensure_facebook_config()
    url = f"https://graph.facebook.com/{FB_GRAPH_VERSION}/{FB_PAGE_ID}/photos"

    last_error = None
    for attempt in range(retries):
        with open(image_path, "rb") as img:
            files = {"source": img}
            data = {
                "caption": caption,
                "published": "true",
                "access_token": FB_PAGE_TOKEN,
            }
            try:
                response = _request_with_retry("POST", url, retries=1, files=files, data=data, timeout=120)
                result = response.json()
            except Exception as exc:
                last_error = exc
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                raise

        if response.status_code >= 400 or "error" in result:
            err = FacebookGraphError(result, response.status_code)
            if err.is_transient and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise err

        return result

    if last_error:
        raise last_error
    raise RuntimeError("Failed to publish photo after retries")


def publish_comment(fb_post_id: str, message: str, retries: int = 3) -> dict:
    _ensure_facebook_config()
    url = f"https://graph.facebook.com/{FB_GRAPH_VERSION}/{fb_post_id}/comments"

    last_error = None
    for attempt in range(retries):
        try:
            response = _request_with_retry(
                "POST",
                url,
                retries=1,
                data={
                    "message": message,
                    "access_token": FB_PAGE_TOKEN,
                },
                timeout=60,
            )
            result = response.json()
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise

        if response.status_code >= 400 or "error" in result:
            err = FacebookGraphError(result, response.status_code)
            if err.is_transient and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise err

        return result

    if last_error:
        raise last_error
    raise RuntimeError("Failed to publish comment after retries")


def graph_get(path: str, params: dict | None = None, retries: int = 3) -> dict:
    _ensure_facebook_config()
    path = path.strip("/")
    request_params = dict(params or {})
    request_params["access_token"] = FB_PAGE_TOKEN

    last_error = None
    for attempt in range(retries):
        try:
            response = _request_with_retry(
                "GET",
                f"https://graph.facebook.com/{FB_GRAPH_VERSION}/{path}",
                retries=1,
                params=request_params,
                timeout=60,
            )
            result = response.json()
        except Exception as exc:
            last_error = exc
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise

        if response.status_code >= 400 or "error" in result:
            err = FacebookGraphError(result, response.status_code)
            if err.is_transient and attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise err

        return result

    if last_error:
        raise last_error
    raise RuntimeError("Failed to get Graph API data after retries")


def list_recent_page_posts(limit: int = 25) -> list[dict]:
    fields = "id,created_time,message,permalink_url,attachments{target,type,url,media}"
    result = graph_get(
        f"{FB_PAGE_ID}/posts",
        {"fields": fields, "limit": limit},
    )
    return result.get("data", [])


def list_recent_page_videos(limit: int = 25) -> list[dict]:
    result = graph_get(
        f"{FB_PAGE_ID}/videos",
        {"fields": "id,created_time,description,permalink_url", "limit": limit},
    )
    return result.get("data", [])


def list_recent_page_reels(limit: int = 25) -> list[dict]:
    result = graph_get(
        f"{FB_PAGE_ID}/video_reels",
        {"fields": "id,created_time,description,permalink_url", "limit": limit},
    )
    return result.get("data", [])
