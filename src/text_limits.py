import os

MIN_TEXT_LENGTH = int(os.environ.get("MIN_TEXT_LENGTH", "100"))
MAX_TEXT_LENGTH = int(os.environ.get("MAX_TEXT_LENGTH", "16000"))
MIN_NUM_QUESTIONS = int(os.environ.get("MIN_NUM_QUESTIONS", "1"))
MAX_NUM_QUESTIONS = int(os.environ.get("MAX_NUM_QUESTIONS", "20"))
DEFAULT_NUM_QUESTIONS = int(os.environ.get("DEFAULT_NUM_QUESTIONS", "5"))


def validate_text_length(text):
    stripped = text.strip()
    if not stripped:
        return "Пожалуйста, введите текст"
    length = len(stripped)
    if length < MIN_TEXT_LENGTH:
        return f"Текст слишком короткий. Минимальная длина: {MIN_TEXT_LENGTH} символов"
    if length > MAX_TEXT_LENGTH:
        return f"Текст слишком длинный. Максимальная длина: {MAX_TEXT_LENGTH} символов"
    return None


def parse_num_questions(value, default=None):
    if default is None:
        default = DEFAULT_NUM_QUESTIONS
    try:
        if value is None or value == "":
            num_questions = default
        else:
            num_questions = int(value)
    except (TypeError, ValueError):
        return None, "Количество вопросов должно быть целым числом"

    if num_questions < MIN_NUM_QUESTIONS or num_questions > MAX_NUM_QUESTIONS:
        return (
            None,
            f"Количество вопросов должно быть от {MIN_NUM_QUESTIONS} до {MAX_NUM_QUESTIONS}",
        )
    return num_questions, None
