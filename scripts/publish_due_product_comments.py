import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import DONATE_COMMENT_URL
from app.product_comment_service import publish_due_product_comments, schedule_recent_donate_comments


if __name__ == "__main__":
    dry_run = "--dry-run" in sys.argv[1:]
    args = [arg for arg in sys.argv[1:] if arg != "--dry-run"]
    limit = int(args[0]) if args else 5

    if not DONATE_COMMENT_URL:
        schedule_results = []
        if dry_run:
            print("Donate comment scan disabled: missing ANIMAL_AGENT_DONATE_COMMENT_URL")
    else:
        try:
            schedule_results = schedule_recent_donate_comments(dry_run=dry_run)
        except Exception as exc:
            schedule_results = []
            print(f"Schedule donate comments failed: {exc}")
    for result in schedule_results:
        action = "Would queue" if dry_run else ("Queued" if result["inserted"] else "Already queued")
        detail = f" | product={result['product_name']}" if result.get("product_name") else ""
        print(
            f"{action} {result.get('kind', 'donate')} comment for fb_post_id={result['fb_post_id']} "
            f"at {result['scheduled_at']} | source={result['source']}{detail}"
        )

    results = publish_due_product_comments(limit=limit, dry_run=dry_run)
    if not results:
        print("No due product comments.")
        sys.exit(0)

    for result in results:
        if result["status"] == "DRY_RUN":
            print(f"Would comment id={result['id']} on fb_post_id={result['fb_post_id']}")
        elif result["status"] == "POSTED":
            print(f"Posted comment id={result['id']} => fb_comment_id={result['fb_comment_id']}")
        else:
            print(f"Failed comment id={result['id']} => {result['error']}")
