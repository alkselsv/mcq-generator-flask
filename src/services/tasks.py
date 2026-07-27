import uuid

from services.job_store import JobCancelled, get_job, is_cancelled, update_job
from services.question_generator import generate_questions
from services.question_storage import load_questions, save_questions
from services.text_simplification import simplify_text


def _save_partial_questions(job_id, questions, num_questions, question_id=None):
    if not questions:
        return None

    job = get_job(job_id)
    if not job:
        return None

    qid = question_id or job.get("question_id") or str(uuid.uuid4())
    save_questions(qid, questions)
    update_job(
        job_id,
        question_id=qid,
        progress_current=len(questions),
        progress_total=num_questions,
    )
    return qid


def run_generation(job_id, text, num_questions):
    if is_cancelled(job_id):
        return

    question_id = str(uuid.uuid4())
    update_job(
        job_id,
        status="running",
        progress_current=0,
        progress_total=num_questions,
        question_id=question_id,
    )
    if is_cancelled(job_id):
        return

    def on_progress(current, total, questions=None):
        fields = {
            "progress_current": current,
            "progress_total": total,
        }
        if questions:
            save_questions(question_id, questions)
            fields["question_id"] = question_id

        if is_cancelled(job_id):
            if questions:
                update_job(job_id, **fields)
            raise JobCancelled(partial_questions=questions or [])

        update_job(job_id, **fields)

    try:
        questions, error = generate_questions(
            text,
            num_questions,
            should_cancel=lambda: is_cancelled(job_id),
            on_progress=on_progress,
        )
        if is_cancelled(job_id):
            _save_partial_questions(job_id, questions, num_questions, question_id)
            return
        if error:
            update_job(job_id, status="error", error=error)
            return

        save_questions(question_id, questions)
        update_job(
            job_id,
            status="done",
            question_id=question_id,
            progress_current=len(questions),
            progress_total=num_questions,
        )
    except JobCancelled as cancelled:
        partial = cancelled.partial_questions
        if not partial:
            job = get_job(job_id)
            if job and job.get("question_id"):
                partial = load_questions(job["question_id"]) or []
        _save_partial_questions(job_id, partial, num_questions, question_id)
    except Exception as error:
        update_job(job_id, status="error", error=str(error))


def run_simplification(job_id, text):
    if is_cancelled(job_id):
        return

    update_job(job_id, status="running")
    if is_cancelled(job_id):
        return

    try:
        simplified_text, error = simplify_text(
            text,
            should_cancel=lambda: is_cancelled(job_id),
        )
        if is_cancelled(job_id):
            return
        if error:
            update_job(job_id, status="error", error=error)
            return
        update_job(job_id, status="done", simplified_text=simplified_text)
    except JobCancelled:
        return
    except Exception as error:
        update_job(job_id, status="error", error=str(error))
