import os
import json
import tempfile
import uuid
import time
from pathlib import Path
from dotenv import load_dotenv
from flask import Flask, render_template, request, jsonify, send_file, session

from logging_config import setup_logging
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
        except (OSError, IOError):
            pass  # Игнорируем ошибки при удалении


@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        # Очищаем старые файлы при каждом запросе генерации
        cleanup_old_files()
        
        text = request.form["text"].strip()
        validation_error = validate_text_length(text)
        if validation_error:
            return jsonify({"questions": None, "error": validation_error}), 400

        num_questions = int(request.form.get("num_questions", 5))
        questions, error = generate_questions(text, num_questions)
        
        if not error and questions:
            # Сохраняем вопросы во временный файл вместо сессии
            question_id = str(uuid.uuid4())
            question_file = QUESTIONS_STORAGE_DIR / f"{question_id}.json"
            with open(question_file, "w", encoding="utf-8") as f:
                json.dump(questions, f, ensure_ascii=False)
            # Храним только ID файла в сессии
            session["question_id"] = question_id
        
        return jsonify({"questions": questions, "error": error})
    return render_template("index.html")


@app.route("/download")
def download_file():
    question_id = session.get("question_id")
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


@app.route("/simplify", methods=["POST"])
def simplify():
    text = request.form["text"].strip()
    validation_error = validate_text_length(text)
    if validation_error:
        return jsonify({"error": validation_error}), 400

    simplified_text, error = simplify_text(text)
    if error:
        return jsonify({"error": error}), 400
    return jsonify({"simplified_text": simplified_text})


if __name__ == "__main__":
    app.run(debug=False)
