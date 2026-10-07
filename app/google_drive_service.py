import logging
import os
import re
import time
import requests
from pathlib import Path

from app.config import (
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_DRIVE_REELS_FOLDER_ID,
    GOOGLE_REFRESH_TOKEN,
    REELS_DIR,
)

logger = logging.getLogger(__name__)

# Token cache: (access_token, expires_at_timestamp)
_TOKEN_CACHE: tuple[str, float] | None = None


def get_access_token() -> str:
    """Obtains a valid Google OAuth2 access token, caching it until expiry."""
    global _TOKEN_CACHE
    now = time.time()
    if _TOKEN_CACHE and _TOKEN_CACHE[1] > now + 60:
        return _TOKEN_CACHE[0]

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET or not GOOGLE_REFRESH_TOKEN:
        raise RuntimeError(
            "Missing Google OAuth credentials. Ensure GOOGLE_CLIENT_ID, "
            "GOOGLE_CLIENT_SECRET, and GOOGLE_REFRESH_TOKEN are configured."
        )

    url = "https://oauth2.googleapis.com/token"
    data = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": GOOGLE_REFRESH_TOKEN,
        "grant_type": "refresh_token",
    }
    resp = requests.post(url, data=data, timeout=30)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to refresh Google OAuth token ({resp.status_code}): {resp.text}")

    payload = resp.json()
    access_token = payload.get("access_token")
    expires_in = payload.get("expires_in", 3600)
    if not access_token:
        raise RuntimeError(f"No access_token returned by Google OAuth: {payload}")

    _TOKEN_CACHE = (access_token, now + expires_in)
    return access_token


def list_drive_files(folder_id: str | None = None) -> list[dict]:
    """Lists all files in a Google Drive folder, handling pagination."""
    folder = folder_id or GOOGLE_DRIVE_REELS_FOLDER_ID
    if not folder:
        raise ValueError("No folder_id provided and GOOGLE_DRIVE_REELS_FOLDER_ID is empty.")

    token = get_access_token()
    url = "https://www.googleapis.com/drive/v3/files"
    query = f"'{folder}' in parents and trashed = false"

    all_files: list[dict] = []
    page_token: str | None = None

    while True:
        params = {
            "q": query,
            "fields": "nextPageToken, files(id, name, size, mimeType, modifiedTime)",
            "pageSize": 100,
            "supportsAllDrives": "true",
            "includeItemsFromAllDrives": "true",
        }
        if page_token:
            params["pageToken"] = page_token

        headers = {"Authorization": f"Bearer {token}"}
        resp = requests.get(url, headers=headers, params=params, timeout=60)
        if resp.status_code != 200:
            raise RuntimeError(f"Google Drive API error ({resp.status_code}): {resp.text}")

        data = resp.json()
        files = data.get("files", [])
        all_files.extend(files)

        page_token = data.get("nextPageToken")
        if not page_token:
            break

    return all_files


def extract_file_number(filename: str) -> tuple[int, str] | None:
    """Extracts leading number from filename, e.g. '066_The Gioi Muon Loai_vi.mp4' -> (66, '066')."""
    match = re.search(r"^(\d+)", filename.strip())
    if match:
        num_str = match.group(1)
        return int(num_str), num_str
    return None


def get_sorted_reels_from_drive(folder_id: str | None = None) -> list[dict]:
    """
    Finds and groups .mp4 video files and .txt caption files by number prefix.
    Returns list of matched reel items sorted by number ascending.
    """
    files = list_drive_files(folder_id)

    videos_by_num: dict[int, dict] = {}
    captions_by_num: dict[int, dict] = {}

    for f in files:
        name = f.get("name", "")
        num_info = extract_file_number(name)
        if not num_info:
            continue
        num_int, _ = num_info

        lower_name = name.lower()
        if lower_name.endswith(".mp4"):
            # Prefer _vi.mp4 if duplicate exists
            if num_int not in videos_by_num or "_vi." in lower_name:
                videos_by_num[num_int] = f
        elif lower_name.endswith(".txt"):
            captions_by_num[num_int] = f

    reels: list[dict] = []
    for num_int in sorted(videos_by_num.keys()):
        video_file = videos_by_num[num_int]
        caption_file = captions_by_num.get(num_int)
        num_str = extract_file_number(video_file["name"])[1]

        # Clean title from video filename without extension
        base_name = re.sub(r"\.mp4$", "", video_file["name"], flags=re.I)
        clean_title = re.sub(r"_vi$", "", base_name, flags=re.I).replace("_", " ").strip()

        reels.append(
            {
                "number": num_int,
                "number_str": num_str,
                "topic_key": f"reel_{num_str}",
                "title": clean_title,
                "video_file": video_file,
                "caption_file": caption_file,
            }
        )

    return reels


def download_drive_file(file_id: str, dest_path: Path, expected_size: int | None = None) -> Path:
    """Downloads a file from Google Drive to local destination, streaming chunks."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)

    if dest_path.exists():
        actual_size = dest_path.stat().st_size
        if expected_size is not None and actual_size == expected_size and actual_size > 0:
            logger.info("File %s already exists with matching size (%d bytes), skipping download", dest_path, actual_size)
            return dest_path

    token = get_access_token()
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&supportsAllDrives=true"
    headers = {"Authorization": f"Bearer {token}"}

    temp_path = dest_path.with_suffix(dest_path.suffix + ".part")
    with requests.get(url, headers=headers, stream=True, timeout=600) as resp:
        if resp.status_code != 200:
            raise RuntimeError(f"Failed to download Drive file {file_id} ({resp.status_code}): {resp.text}")

        with open(temp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1024 * 1024):  # 1MB chunks
                if chunk:
                    f.write(chunk)

    temp_path.replace(dest_path)
    logger.info("Downloaded %s (%d bytes)", dest_path, dest_path.stat().st_size)
    return dest_path


def download_caption_text(file_id: str) -> str:
    """Downloads a .txt caption file and decodes as UTF-8 string."""
    token = get_access_token()
    url = f"https://www.googleapis.com/drive/v3/files/{file_id}?alt=media&supportsAllDrives=true"
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(url, headers=headers, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"Failed to download caption file {file_id} ({resp.status_code}): {resp.text}")
    return resp.content.decode("utf-8", errors="replace").strip()
