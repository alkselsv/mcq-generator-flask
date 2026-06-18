MIN_TEXT_LENGTH = 100
MAX_TEXT_LENGTH = 16000


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
