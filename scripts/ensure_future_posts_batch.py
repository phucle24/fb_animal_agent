import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import MIN_FUTURE_POSTS, TARGET_FUTURE_POSTS
from app.schedule_service import ensure_future_posts_for_batch


if __name__ == "__main__":
    min_future = int(sys.argv[1]) if len(sys.argv) > 1 else MIN_FUTURE_POSTS
    posts_to_create = int(sys.argv[2]) if len(sys.argv) > 2 else TARGET_FUTURE_POSTS

    result = ensure_future_posts_for_batch(
        min_future_posts=min_future,
        target_future_posts=posts_to_create,
    )

    print(f"Current future posts before ensure: {result['current_future']}")
    print(f"Created posts: {len(result['created'])}")
    for post in result["created"]:
        print(
            "Created post "
            f"ID={post['id']} | {post['scheduled_at']} | {post['slot']} | {post['topic_key']}"
        )

    batch = result["batch"]
    if batch["submitted"]:
        print(
            "Submitted image batch "
            f"{batch['batch_job_name']} | posts={batch['submitted']} | state={batch['batch_state']}"
        )
    else:
        print("No batch submitted.")
