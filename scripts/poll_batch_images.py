import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.batch_service import poll_all_image_batches, process_batch_job


if __name__ == "__main__":
    if len(sys.argv) > 1:
        results = [process_batch_job(sys.argv[1])]
    else:
        results = poll_all_image_batches()

    if not results:
        print("No image batch jobs to poll.")

    for result in results:
        print(
            f"{result['batch_job_name']} | state={result['state']} | "
            f"ready={result['ready']} | failed={result['failed']}"
        )
        for error in result.get("errors", []):
            print(
                "  ERROR "
                f"post_id={error['post_id']} | topic={error['topic_key']} | "
                f"{error['error']}"
            )
