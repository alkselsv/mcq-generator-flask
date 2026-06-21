import os
import json
import tempfile
import uuid
import time
import threading
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_file, session, make_response

from logging_config import setup_logging
from services.job_store import cleanup_old_jobs, create_job, get_job, update_job
from services.question_generator import generate_questions
from services.file_generator import generate_csv, generate_xlsx
from services.text_simplification import simplify_text
from text_limits import MIN_TEXT_LENGTH, MAX_TEXT_LENGTH, validate_text_length

load_dotenv()
setup_logging()
app = Flask(__name__)
app.secret_key = os.environ.get("APP_SECRET_KEY")
app.config["MAX_CONTENT_LENGTH"] = 256 * 1024

# Директория для временных файлов с вопросами
QUESTIONS_STORAGE_DIR = Path(tempfile.gettempdir()) / "mcq_questions"
QUESTIONS_STORAGE_DIR.mkdir(exist_ok=True)

# Максимальный возраст файла в секундах (24 часа)
MAX_FILE_AGE = 24 * 60 * 60


@app.context_processor
def inject_text_limits():
    return {
        "min_text_length": MIN_TEXT_LENGTH,
        "max_text_length": MAX_TEXT_LENGTH,
    }


def cleanup_old_files():
    """Удаляет временные файлы старше MAX_FILE_AGE"""
    current_time = time.time()
    for file_path in QUESTIONS_STORAGE_DIR.glob("*.json"):
        try:
            if current_time - file_path.stat().st_mtime > MAX_FILE_AGE:
                file_path.unlink()
        except OSError:
            pass


def _schedule_cleanup():
    threading.Thread(target=cleanup_old_files, daemon=True).start()


def _run_generation(job_id, text, num_questions):
    update_job(job_id, status="running")
    try:
        questions, error = generate_questions(text, num_questions)
        if error:
            update_job(job_id, status="error", error=error)
            return

        question_id = str(uuid.uuid4())
        question_file = QUESTIONS_STORAGE_DIR / f"{question_id}.json"
        with open(question_file, "w", encoding="utf-8") as f:
            json.dump(questions, f, ensure_ascii=False)

        update_job(
            job_id,
            status="done",
            questions=questions,
            question_id=question_id,
        )
    except Exception as error:
        update_job(job_id, status="error", error=str(error))


def _run_simplification(job_id, text):
    update_job(job_id, status="running")
    simplified_text, error = simplify_text(text)
    if error:
        update_job(job_id, status="error", error=error)
        return
    update_job(job_id, status="done", simplified_text=simplified_text)


def _start_job(target, job_type, *args):
    job_id = create_job(job_type=job_type)
    threading.Thread(target=target, args=(job_id, *args), daemon=True).start()
    return job_id


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/")
def index():
    response = make_response(render_template("index.html"))
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/generate", methods=["POST"])
def generate():
    cleanup_old_jobs()

    text = request.form.get("text", "").strip()
    validation_error = validate_text_length(text)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    num_questions = int(request.form.get("num_questions", 5))
    job_id = _start_job(_run_generation, "generate", text, num_questions)
    _schedule_cleanup()
    return jsonify({"job_id": job_id})


@app.route("/simplify", methods=["POST"])
def simplify():
    cleanup_old_jobs()

    text = request.form.get("text", "").strip()
    validation_error = validate_text_length(text)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    job_id = _start_job(_run_simplification, "simplify", text)
    return jsonify({"job_id": job_id})


@app.route("/jobs/<job_id>")
def job_status(job_id):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Задача не найдена"}), 404

    response = {"status": job["status"]}
    if job["status"] == "done":
        if job["job_type"] == "simplify":
            response["simplified_text"] = job["simplified_text"]
        else:
            response["questions"] = job["questions"]
            response["question_id"] = job["question_id"]
            session["question_id"] = job["question_id"]
    elif job["status"] == "error":
        response["error"] = job["error"]
    return jsonify(response)


@app.route("/download")
def download_file():
    question_id = request.args.get("question_id") or session.get("question_id")
    if not question_id:
        return "No questions generated yet", 400

    # Загружаем вопросы из временного файла
    question_file = QUESTIONS_STORAGE_DIR / f"{question_id}.json"
    if not question_file.exists():
        return "Questions file not found", 404

    try:
        with open(question_file, "r", encoding="utf-8") as f:
            questions = json.load(f)
    except (json.JSONDecodeError, IOError):
        return "Error reading questions file", 500

    if not questions:
        return "No questions available", 400

    # Получаем индексы выбранных вопросов
    selected_indices_str = request.args.get("questions", "")
    if selected_indices_str:
        try:
            selected_indices = [int(i) for i in selected_indices_str.split(",") if i.strip()]
            # Фильтруем валидные индексы
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
