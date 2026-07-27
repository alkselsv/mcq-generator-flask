import os
import threading

from dotenv import load_dotenv

load_dotenv()

from flask import Flask, render_template, request, jsonify, send_file, session, make_response

from logging_config import setup_logging
from services.job_store import cancel_job, create_job, get_job
from services.job_queue import cancel_rq_job, enqueue_generation, enqueue_simplification
from services.file_generator import generate_csv, generate_xlsx
from services.question_storage import cleanup_old_files, load_questions
from services.redis_client import get_redis
from text_limits import (
    MIN_TEXT_LENGTH,
    MAX_TEXT_LENGTH,
    MIN_NUM_QUESTIONS,
    MAX_NUM_QUESTIONS,
    DEFAULT_NUM_QUESTIONS,
    parse_num_questions,
    validate_text_length,
)

setup_logging()
app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY")
app.config["MAX_CONTENT_LENGTH"] = int(
    os.environ.get("MAX_CONTENT_LENGTH", str(256 * 1024))
)
POLL_INTERVAL_MS = int(os.environ.get("POLL_INTERVAL_MS", "2000"))
POLL_MAX_MS = int(os.environ.get("POLL_MAX_MS", str(15 * 60 * 1000)))


@app.context_processor
def inject_text_limits():
    return {
        "min_text_length": MIN_TEXT_LENGTH,
        "max_text_length": MAX_TEXT_LENGTH,
        "min_num_questions": MIN_NUM_QUESTIONS,
        "max_num_questions": MAX_NUM_QUESTIONS,
        "default_num_questions": DEFAULT_NUM_QUESTIONS,
        "poll_interval_ms": POLL_INTERVAL_MS,
        "poll_max_ms": POLL_MAX_MS,
    }


def _schedule_cleanup():
    threading.Thread(target=cleanup_old_files, daemon=True).start()


def _get_request_data():
    if request.is_json:
        return request.get_json(silent=True) or {}
    return request.form


def _parse_text(data):
    return (data.get("text") or "").strip()


def _start_job(enqueue_fn, job_type, *args):
    job_id = create_job(job_type=job_type)
    enqueue_fn(job_id, *args)
    return job_id


@app.route("/health")
def health():
    try:
        get_redis().ping()
    except Exception:
        return jsonify({"status": "error", "redis": "unavailable"}), 503
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    response = make_response(render_template("index.html"))
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/generate", methods=["POST"])
def generate():
    data = _get_request_data()
    text = _parse_text(data)
    validation_error = validate_text_length(text)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    num_questions, num_error = parse_num_questions(data.get("num_questions"))
    if num_error:
        return jsonify({"error": num_error}), 400

    job_id = _start_job(enqueue_generation, "generate", text, num_questions)
    _schedule_cleanup()
    return jsonify({"job_id": job_id})


@app.route("/simplify", methods=["POST"])
def simplify():
    data = _get_request_data()
    text = _parse_text(data)
    validation_error = validate_text_length(text)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    job_id = _start_job(enqueue_simplification, "simplify", text)
    return jsonify({"job_id": job_id})


def _job_questions_payload(job):
    question_id = job.get("question_id")
    if not question_id:
        return None
    questions = load_questions(question_id)
    if not questions:
        return None
    return {
        "questions": questions,
        "question_id": question_id,
    }


@app.route("/jobs/<job_id>")
def job_status(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Задача не найдена"}), 404

    response = {"status": job["status"]}
    if job["status"] in ("pending", "running") and job.get("job_type") == "generate":
        if job.get("progress_total") is not None:
            response["progress_current"] = job.get("progress_current") or 0
            response["progress_total"] = job["progress_total"]
    if job["status"] == "done":
        if job["job_type"] == "simplify":
            response["simplified_text"] = job["simplified_text"]
        else:
            payload = _job_questions_payload(job)
            if payload is None:
                return jsonify({"error": "Результат не найден"}), 404
            response.update(payload)
            session["question_id"] = payload["question_id"]
    elif job["status"] == "cancelled" and job.get("job_type") == "generate":
        payload = _job_questions_payload(job)
        if payload is not None:
            response.update(payload)
            session["question_id"] = payload["question_id"]
        if job.get("progress_total") is not None:
            response["progress_current"] = job.get("progress_current") or 0
            response["progress_total"] = job["progress_total"]
    elif job["status"] == "error":
        response["error"] = job["error"]
    return jsonify(response)


@app.route("/jobs/<job_id>/cancel", methods=["POST"])
def job_cancel(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Задача не найдена"}), 404

    if job["status"] in ("done", "error", "cancelled"):
        response = {"status": job["status"]}
        if job["status"] in ("done", "cancelled") and job.get("job_type") == "generate":
            payload = _job_questions_payload(job)
            if payload is not None:
                response.update(payload)
                session["question_id"] = payload["question_id"]
        return jsonify(response)

    cancelled = cancel_job(job_id)
    if not cancelled:
        return jsonify({"error": "Задача не найдена"}), 404

    cancel_rq_job(cancelled.get("rq_job_id"))
    # Reload: worker may already have saved partial questions.
    job = get_job(job_id) or cancelled
    response = {"status": "cancelled"}
    if job.get("job_type") == "generate":
        payload = _job_questions_payload(job)
        if payload is not None:
            response.update(payload)
            session["question_id"] = payload["question_id"]
        if job.get("progress_total") is not None:
            response["progress_current"] = job.get("progress_current") or 0
            response["progress_total"] = job["progress_total"]
    return jsonify(response)


@app.route("/download")
def download_file():
    question_id = request.args.get("question_id") or session.get("question_id")
    if not question_id:
        return "No questions generated yet", 400

    questions = load_questions(question_id)
    if questions is None:
        return "Questions file not found", 404

    if not questions:
        return "No questions available", 400

    selected_indices_str = request.args.get("questions", "")
    if selected_indices_str:
        try:
            selected_indices = [int(i) for i in selected_indices_str.split(",") if i.strip()]
            valid_indices = [i for i in selected_indices if 0 <= i < len(questions)]
            if valid_indices:
                questions = [questions[i] for i in valid_indices]
            else:
                return "No valid question indices selected", 400
        except ValueError:
            return "Invalid question indices format", 400

    file_format = request.args.get("format", "csv")

    if file_format == "csv":
        file_path = generate_csv(questions)
        mimetype = "text/csv"
        filename = "questions.csv"
    elif file_format == "xlsx":
        file_path = generate_xlsx(questions)
        mimetype = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "questions.xlsx"
    else:
        return "Invalid format specified", 400

    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename,
        mimetype=mimetype,
    )


if __name__ == "__main__":
    app.run(debug=False)
