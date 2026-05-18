import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import delete_posts, list_unposted_posts
from app.config import GEMINI_API_KEY


def delete_asset(path_value: str | None, seen: set[str]) -> bool:
    if not path_value:
        return False
    path = Path(path_value)
    key = str(path)
    if key in seen:
        return False
    seen.add(key)
    if not path.exists() or not path.is_file():
        return False
    path.unlink()
    return True


if __name__ == "__main__":
    cancel_batches = "--cancel-batches" in sys.argv[1:]
    rows = list_unposted_posts()
    post_ids = [row["id"] for row in rows]
    batch_jobs = sorted({row["batch_job_name"] for row in rows if row["batch_job_name"]})
    seen_assets = set()
    deleted_assets = 0

    cancelled = 0
    if cancel_batches and batch_jobs:
        if not GEMINI_API_KEY:
            print("Skip batch cancellation: missing ANIMAL_AGENT_GEMINI_API_KEY")
        else:
            from google import genai

            client = genai.Client(api_key=GEMINI_API_KEY)
            for batch_job_name in batch_jobs:
                try:
                    client.batches.cancel(name=batch_job_name)
                    cancelled += 1
                    print(f"Cancelled batch: {batch_job_name}")
                except Exception as exc:
                    print(f"Could not cancel batch {batch_job_name}: {exc}")

    for row in rows:
        if delete_asset(row["raw_image_path"], seen_assets):
            deleted_assets += 1
        if delete_asset(row["final_image_path"], seen_assets):
            deleted_assets += 1

    deleted_posts = delete_posts(post_ids)
    print(f"Batch jobs found: {len(batch_jobs)}")
    print(f"Batch jobs cancelled: {cancelled}")
    print(f"Deleted posts: {deleted_posts}")
    print(f"Deleted asset files: {deleted_assets}")
