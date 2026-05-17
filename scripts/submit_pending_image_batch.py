import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.batch_service import submit_pending_image_batch


if __name__ == "__main__":
    limit = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    result = submit_pending_image_batch(limit=limit)
    if result["submitted"]:
        print(
            "Submitted image batch "
            f"{result['batch_job_name']} | posts={result['submitted']} | state={result['batch_state']}"
        )
    else:
        print("No pending image posts to submit.")

