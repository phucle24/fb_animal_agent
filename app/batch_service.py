from datetime import datetime
from zoneinfo import ZoneInfo

from app.config import GEMINI_API_KEY, GEMINI_IMAGE_MODEL, IMAGE_ASPECT_RATIO, TIMEZONE
from app.db import (
    list_batch_jobs_to_poll,
    list_posts_by_batch_job,
    list_posts_for_batch_submission,
    mark_image_failed,
    mark_image_ready,
    set_batch_for_posts,
    update_batch_state,
)
from app.image_service import save_image_from_response
from app.post_service import image_prompt_renders_final_text, overlay_post_image


COMPLETED_STATES = {
    "JOB_STATE_SUCCEEDED",
    "JOB_STATE_FAILED",
    "JOB_STATE_CANCELLED",
    "JOB_STATE_EXPIRED",
}


def _ensure_api_key():
    if not GEMINI_API_KEY:
        raise RuntimeError("Missing ANIMAL_AGENT_GEMINI_API_KEY")


def _client():
    from google import genai

    return genai.Client(api_key=GEMINI_API_KEY)


def _image_batch_request(image_prompt: str) -> dict:
    return {
        "contents": [
            {
                "role": "user",
                "parts": [{"text": image_prompt}],
            }
        ],
        "config": {
            "response_modalities": ["TEXT", "IMAGE"],
            "image_config": {"aspect_ratio": IMAGE_ASPECT_RATIO},
        },
    }


def submit_pending_image_batch(limit: int = 100, display_name: str | None = None) -> dict:
    _ensure_api_key()
    posts = list_posts_for_batch_submission(limit=limit)
    if not posts:
        return {"submitted": 0, "batch_job_name": None}

    client = _client()
    inline_requests = [_image_batch_request(post["image_prompt"]) for post in posts]

    if display_name is None:
        now = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y%m%d-%H%M%S")
        display_name = f"animal-agent-images-{now}"

    batch_job = client.batches.create(
        model=GEMINI_IMAGE_MODEL,
        src=inline_requests,
        config={"display_name": display_name},
    )

    state = getattr(getattr(batch_job, "state", None), "name", None)
    set_batch_for_posts([post["id"] for post in posts], batch_job.name, state)

    return {
        "submitted": len(posts),
        "batch_job_name": batch_job.name,
        "batch_state": state,
    }


def _inline_responses(batch_job) -> list:
    dest = getattr(batch_job, "dest", None)
    if not dest:
        return []
    return list(getattr(dest, "inlined_responses", None) or [])


def _inline_response_error(inline_response) -> str | None:
    error = getattr(inline_response, "error", None)
    if not error:
        return None
    message = getattr(error, "message", None)
    if message:
        return message
    return repr(error)


def process_batch_job(batch_job_name: str) -> dict:
    _ensure_api_key()
    client = _client()
    batch_job = client.batches.get(name=batch_job_name)
    state = getattr(getattr(batch_job, "state", None), "name", str(getattr(batch_job, "state", "")))

    if state != "JOB_STATE_SUCCEEDED":
        error = getattr(batch_job, "error", None)
        error_message = repr(error) if error else None
        update_batch_state(batch_job_name, state, error_message)
        failed = 0
        if state in COMPLETED_STATES:
            message = error_message or f"Batch job finished with state {state}."
            for post in list_posts_by_batch_job(batch_job_name):
                mark_image_failed(post["id"], message)
                failed += 1
        return {
            "batch_job_name": batch_job_name,
            "state": state,
            "ready": 0,
            "failed": failed,
        }

    posts = list_posts_by_batch_job(batch_job_name)
    responses = _inline_responses(batch_job)
    ready = 0
    failed = 0

    if len(responses) != len(posts):
        message = f"Batch response count mismatch: posts={len(posts)} responses={len(responses)}"
        for post in posts:
            mark_image_failed(post["id"], message)
            failed += 1
        return {
            "batch_job_name": batch_job_name,
            "state": state,
            "ready": ready,
            "failed": failed,
        }

    for post, inline_response in zip(posts, responses):
        error = _inline_response_error(inline_response)
        if error:
            mark_image_failed(post["id"], error)
            failed += 1
            continue

        response = getattr(inline_response, "response", None)
        if not response:
            mark_image_failed(post["id"], "Batch inline response has no response payload.")
            failed += 1
            continue

        try:
            if image_prompt_renders_final_text(post["image_prompt"]):
                save_image_from_response(response, post["final_image_path"])
                mark_image_ready(post["id"], post["final_image_path"], post["final_image_path"])
            else:
                # Legacy in-flight jobs created before model-rendered text was enabled.
                save_image_from_response(response, post["raw_image_path"])
                overlay_post_image(post)
                mark_image_ready(post["id"], post["raw_image_path"], post["final_image_path"])
            ready += 1
        except Exception as exc:
            mark_image_failed(post["id"], str(exc))
            failed += 1

    update_batch_state(batch_job_name, state, None)
    return {
        "batch_job_name": batch_job_name,
        "state": state,
        "ready": ready,
        "failed": failed,
    }


def poll_all_image_batches() -> list[dict]:
    results = []
    for batch_job_name in list_batch_jobs_to_poll():
        results.append(process_batch_job(batch_job_name))
    return results
