import uuid

from services.job_store import update_job
from services.question_generator import generate_questions
from services.question_storage import save_questions
from services.text_simplification import simplify_text


def run_generation(job_id, text, num_questions):
    update_job(job_id, status="running")
    try:
        questions, error = generate_questions(text, num_questions)
        if error:
            update_job(job_id, status="error", error=error)
            return

        question_id = str(uuid.uuid4())
        save_questions(question_id, questions)
        update_job(job_id, status="done", question_id=question_id)
    except Exception as error:
        update_job(job_id, status="error", error=str(error))


def run_simplification(job_id, text):
    update_job(job_id, status="running")
    try:
        simplified_text, error = simplify_text(text)
        if error:
            update_job(job_id, status="error", error=error)
            return
        update_job(job_id, status="done", simplified_text=simplified_text)
    except Exception as error:
        update_job(job_id, status="error", error=str(error))
