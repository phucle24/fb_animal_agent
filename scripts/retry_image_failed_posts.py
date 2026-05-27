import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.batch_service import submit_pending_image_batch
from app.db import get_post, mark_image_failed, mark_image_ready, reset_posts_for_image_retry
from app.image_service import generate_image


def parse_post_ids(args: list[str]) -> list[int]:
    post_ids = []
    for arg in args:
        if arg in {"--submit", "--direct"}:
            continue
        post_ids.extend(int(value) for value in arg.split(",") if value.strip())
    return post_ids


if __name__ == "__main__":
    submit = "--submit" in sys.argv[1:]
    direct = "--direct" in sys.argv[1:]
    post_ids = parse_post_ids(sys.argv[1:])

    if not post_ids or (submit and direct):
        print("Usage: python scripts/retry_image_failed_posts.py POST_ID[,POST_ID...] [--submit|--direct]")
        sys.exit(1)

    updated = reset_posts_for_image_retry(post_ids)
    print(f"Reset IMAGE_FAILED posts to WAITING_IMAGE: {updated}")

    if direct and updated:
        ready = 0
        failed = 0
        for post_id in post_ids:
            post = get_post(post_id)
            if not post or post["status"] != "WAITING_IMAGE":
                continue
            try:
                generate_image(post["image_prompt"], post["final_image_path"])
                mark_image_ready(post_id, post["final_image_path"], post["final_image_path"])
                ready += 1
                print(f"Generated direct image for post ID={post_id}")
            except Exception as exc:
                mark_image_failed(post_id, str(exc))
                failed += 1
                print(f"Direct image failed for post ID={post_id}: {exc}")
        print(f"Direct image retry done. ready={ready} failed={failed}")

    if submit and updated:
        result = submit_pending_image_batch(limit=updated)
        if result["submitted"]:
            print(
                "Submitted image batch "
                f"{result['batch_job_name']} | posts={result['submitted']} | state={result['batch_state']}"
            )
        else:
            print("No pending image posts to submit.")
