import json
import tempfile
import time
from pathlib import Path

QUESTIONS_STORAGE_DIR = Path(tempfile.gettempdir()) / "mcq_questions"
QUESTIONS_STORAGE_DIR.mkdir(exist_ok=True)

MAX_FILE_AGE = 24 * 60 * 60


def question_file_path(question_id):
    return QUESTIONS_STORAGE_DIR / f"{question_id}.json"


def save_questions(question_id, questions):
    path = question_file_path(question_id)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(questions, file, ensure_ascii=False)


def load_questions(question_id):
    path = question_file_path(question_id)
    if not path.exists():
        return None
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except (json.JSONDecodeError, OSError):
        return None


def cleanup_old_files():
    current_time = time.time()
    for file_path in QUESTIONS_STORAGE_DIR.glob("*.json"):
        try:
            if current_time - file_path.stat().st_mtime > MAX_FILE_AGE:
                file_path.unlink()
        except OSError:
            pass
