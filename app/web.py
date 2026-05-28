from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

from flask import Flask, abort, flash, redirect, render_template, request, send_file, url_for

from app.batch_service import poll_all_image_batches, submit_pending_image_batch
from app.config import BASE_DIR, TIMEZONE, WEB_HOST, WEB_PORT, WEB_SECRET_KEY
from app.db import (
    batch_publish_overview,
    dashboard_stats,
    get_post,
    init_db,
    list_posts,
    mark_failed,
    mark_posted,
    update_status,
)
from app.facebook_service import publish_photo
from app.product_comment_service import schedule_product_comments_for_post
from app.schedule_service import prepare_one_test_post, prepare_weekly_posts, prepare_weekly_posts_for_batch


def create_app() -> Flask:
    flask_app = Flask(
        __name__,
        template_folder=str(BASE_DIR / "templates"),
        static_folder=str(BASE_DIR / "static"),
    )
    flask_app.secret_key = WEB_SECRET_KEY

    @flask_app.route("/")
    def index():
        init_db()
        status = request.args.get("status") or None
        posts = list_posts(status=status, limit=200)
        stats = dashboard_stats()
        now_iso = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
        overview = batch_publish_overview(now_iso)
        return render_template(
            "index.html",
            posts=posts,
            stats=stats,
            overview=overview,
            active_status=status,
        )

    @flask_app.route("/posts/<int:post_id>")
    def post_detail(post_id: int):
        post = get_post(post_id)
        if not post:
            abort(404)
        return render_template("post_detail.html", post=post)

    @flask_app.post("/actions/init-db")
    def action_init_db():
        init_db()
        flash("Database initialized.", "success")
        return redirect(url_for("index"))

    @flask_app.post("/actions/prepare-week")
    def action_prepare_week():
        try:
            days = int(request.form.get("days", "7"))
            created = prepare_weekly_posts(days=days)
            flash(f"Created {len(created)} posts for {days} days.", "success")
        except Exception as exc:
            flash(f"Prepare failed: {exc}", "error")
        return redirect(url_for("index"))

    @flask_app.post("/actions/prepare-week-batch")
    def action_prepare_week_batch():
        try:
            days = int(request.form.get("days", "7"))
            created = prepare_weekly_posts_for_batch(days=days)
            if created:
                result = submit_pending_image_batch(limit=len(created))
                flash(
                    f"Created {len(created)} posts and submitted batch {result['batch_job_name']}.",
                    "success",
                )
            else:
                flash("No new posts created; existing schedule was kept.", "success")
        except Exception as exc:
            flash(f"Batch prepare failed: {exc}", "error")
        return redirect(url_for("index"))

    @flask_app.post("/actions/poll-batch-images")
    def action_poll_batch_images():
        try:
            results = poll_all_image_batches()
            if not results:
                now_iso = datetime.now(ZoneInfo(TIMEZONE)).strftime("%Y-%m-%d %H:%M:%S")
                overview = batch_publish_overview(now_iso)
                if overview["waiting_unsubmitted"]:
                    flash(
                        "No batch jobs to poll. "
                        f"{overview['waiting_unsubmitted']} WAITING_IMAGE posts have not been submitted yet; "
                        "click Submit pending Batch.",
                        "error",
                    )
                elif overview["due_ready"]:
                    flash(
                        "No batch jobs to poll. "
                        f"{overview['due_ready']} READY posts are due; run publish_due_posts.py all or wait for publish timer.",
                        "success",
                    )
                elif overview["future_ready"]:
                    flash(
                        "No batch jobs to poll. "
                        f"{overview['future_ready']} posts are already READY for future scheduled time.",
                        "success",
                    )
                else:
                    flash("No batch image jobs to poll and no READY future posts found.", "error")
            else:
                ready = sum(result["ready"] for result in results)
                failed = sum(result["failed"] for result in results)
                flash(f"Polled {len(results)} batch jobs. READY={ready}, failed={failed}.", "success")
        except Exception as exc:
            flash(f"Poll batch failed: {exc}", "error")
        return redirect(url_for("index"))

    @flask_app.post("/actions/submit-pending-batch")
    def action_submit_pending_batch():
        try:
            limit = int(request.form.get("limit", "100"))
            result = submit_pending_image_batch(limit=limit)
            if result["submitted"]:
                flash(
                    f"Submitted {result['submitted']} posts to batch {result['batch_job_name']}.",
                    "success",
                )
            else:
                flash("No pending image posts to submit.", "success")
        except Exception as exc:
            flash(f"Submit pending batch failed: {exc}", "error")
        return redirect(url_for("index"))

    @flask_app.post("/actions/prepare-one-test")
    def action_prepare_one_test():
        try:
            topic_index = int(request.form.get("topic_index", "0"))
            post = prepare_one_test_post(topic_index=topic_index)
            flash(f"Created test post #{post['id']}.", "success")
            return redirect(url_for("post_detail", post_id=post["id"]))
        except Exception as exc:
            flash(f"Create test post failed: {exc}", "error")
            return redirect(url_for("index"))

    @flask_app.post("/posts/<int:post_id>/publish")
    def action_publish(post_id: int):
        post = get_post(post_id)
        if not post:
            abort(404)

        try:
            result = publish_photo(post["final_image_path"], post["caption"])
            fb_post_id = result.get("post_id") or result.get("id", "")
            mark_posted(post_id, fb_post_id)
            scheduled_comments = schedule_product_comments_for_post(post, fb_post_id)
            flash(f"Published post #{post_id}. Scheduled {scheduled_comments} product comments.", "success")
        except Exception as exc:
            mark_failed(post_id, str(exc))
            flash(f"Publish failed: {exc}", "error")
        return redirect(url_for("post_detail", post_id=post_id))

    @flask_app.post("/posts/<int:post_id>/status")
    def action_status(post_id: int):
        post = get_post(post_id)
        if not post:
            abort(404)
        status = request.form.get("status", "").strip().upper()
        if status not in {"READY", "FAILED", "SKIPPED", "WAITING_IMAGE", "IMAGE_FAILED"}:
            flash("Unsupported status.", "error")
            return redirect(url_for("post_detail", post_id=post_id))
        update_status(post_id, status)
        flash(f"Updated post #{post_id} to {status}.", "success")
        return redirect(url_for("post_detail", post_id=post_id))

    @flask_app.route("/media/post/<int:post_id>/<kind>")
    def media_post(post_id: int, kind: str):
        post = get_post(post_id)
        if not post:
            abort(404)

        if kind == "final":
            image_path = post["final_image_path"]
        elif kind == "raw":
            image_path = post["raw_image_path"]
        else:
            abort(404)

        if not image_path:
            abort(404)
        path = Path(image_path)
        if not path.exists():
            abort(404)
        return send_file(path)

    return flask_app


app = create_app()


def run():
    app.run(host=WEB_HOST, port=WEB_PORT, debug=False)
