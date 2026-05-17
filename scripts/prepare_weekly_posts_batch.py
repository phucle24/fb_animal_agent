import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.batch_service import submit_pending_image_batch
from app.schedule_service import prepare_weekly_posts_for_batch


if __name__ == "__main__":
    days = int(sys.argv[1]) if len(sys.argv) > 1 else 7
    created = prepare_weekly_posts_for_batch(days=days)
    print(f"Created {len(created)} WAITING_IMAGE posts.")
    for post in created:
        print(
            "Created post "
            f"ID={post['id']} | {post['scheduled_at']} | {post['slot']} | {post['topic_key']}"
        )

    result = submit_pending_image_batch(limit=max(len(created), 1))
    if result["submitted"]:
        print(
            "Submitted image batch "
            f"{result['batch_job_name']} | posts={result['submitted']} | state={result['batch_state']}"
        )
    else:
        print("No pending image posts to submit.")

