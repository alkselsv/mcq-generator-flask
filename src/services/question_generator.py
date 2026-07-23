import re
import json
import logging
import os
from functools import lru_cache

from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

from services.llm import invoke_chat
from services.text_chunking import chunk_text
from text_limits import DEFAULT_NUM_QUESTIONS, MAX_NUM_QUESTIONS, MIN_NUM_QUESTIONS

logger = logging.getLogger("llm.questions")

MAX_TOPUP_ROUNDS = int(os.environ.get("MAX_TOPUP_ROUNDS", "2"))

# Названия нормативных документов — первую букву оставляем заглавной.
_NORMATIVE_DOC_PREFIXES = (
    "федеральный конституционный закон",
    "федеральный закон",
    "технический регламент",
    "методические указания",
    "методические рекомендации",
    "постановление",
    "распоряжение",
    "положение",
    "регламент",
    "инструкция",
    "конституция",
    "конвенция",
    "соглашение",
    "стандарт",
    "правила",
    "приказ",
    "закон",
    "кодекс",
    "устав",
    "указ",
    "декрет",
    "нормы",
    "письмо",
    "договор",
    "гост",
    "снип",
    "санпин",
)

# Аббревиатуры с особым регистром (не просто заглавная первая буква).
_NORMATIVE_ABBREVIATIONS = {
    "гост": "ГОСТ",
    "снип": "СНиП",
    "санпин": "СанПиН",
}


def _is_normative_document_name(text):
    normalized = " ".join((text or "").lower().split())
    return any(
        normalized == prefix or normalized.startswith(prefix + " ")
        for prefix in _NORMATIVE_DOC_PREFIXES
    )


def _normalize_option_casing(text):
    """Фолбэк: поправить регистр, если модель не соблюла правило из промпта."""
    if not text or not isinstance(text, str):
        return text

    stripped = text.strip()
    if not stripped:
        return text

    if not _is_normative_document_name(stripped):
        if stripped[0].islower():
            return stripped
        return stripped[0].lower() + stripped[1:]

    first_word, *rest_parts = stripped.split(None, 1)
    abbreviation = _NORMATIVE_ABBREVIATIONS.get(first_word.lower())
    if abbreviation:
        return abbreviation if not rest_parts else f"{abbreviation} {rest_parts[0]}"

    if stripped[0].isupper():
        return stripped
    return stripped[0].upper() + stripped[1:]


def _normalize_question_options(question):
    """Применить фолбэк-нормализацию регистра к вариантам и ответу."""
    options = [_normalize_option_casing(option) for option in question["options"]]
    answer = _normalize_option_casing(question["answer"])

    # Сохраняем совпадение правильного ответа с одним из вариантов после нормализации.
    answer_key = _normalize_question_text(answer)
    for option in options:
        if _normalize_question_text(option) == answer_key:
            answer = option
            break

    question["options"] = options
    question["answer"] = answer
    return question


def parse_result(result):
    json_objects = re.findall(r"\{[^}]+\}", result)
    questions = []

    for json_str in json_objects:
        try:
            question_data = json.loads(json_str)
            question = {
                "question": question_data["question"],
                "options": [
                    question_data["option_1"],
                    question_data["option_2"],
                    question_data["option_3"],
                ],
                "answer": question_data["answer"],
                "topic_number": question_data["topic_number"],
                "topic": question_data["topic"],
            }
            questions.append(_normalize_question_options(question))
        except json.JSONDecodeError:
            logger.warning("Ошибка при разборе JSON: %s", json_str)
        except KeyError as error:
            logger.warning("Отсутствует ключ в JSON объекте: %s", error)

    return questions


def _normalize_question_text(text):
    return " ".join((text or "").lower().split())


def _dedupe_questions(questions, seen=None):
    if seen is None:
        seen = set()

    unique = []
    for question in questions:
        key = _normalize_question_text(question.get("question", ""))
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(question)
    return unique, seen


@lru_cache(maxsize=32)
def _get_prompt(num_questions, with_exclusions=False):
    response_schemas = [
        ResponseSchema(
            name="question",
            description="Вопрос с множественным выбором ответов, созданный на основе фрагмента входного текста.",
        ),
        ResponseSchema(
            name="option_1",
            description="Первый вариант ответа (см. правило регистра в инструкции).",
        ),
        ResponseSchema(
            name="option_2",
            description="Второй вариант ответа (см. правило регистра в инструкции).",
        ),
        ResponseSchema(
            name="option_3",
            description="Третий вариант ответа (см. правило регистра в инструкции).",
        ),
        ResponseSchema(
            name="answer",
            description=(
                "Правильный ответ — должен дословно совпадать с одним из вариантов."
            ),
        ),
        ResponseSchema(
            name="topic_number", description="Номер пункта исходного документа."
        ),
        ResponseSchema(
            name="topic",
            description="Текст пункта исходного документа с номером topic_number",
        ),
    ]
    output_parser = StructuredOutputParser.from_response_schemas(response_schemas)
    format_instructions = output_parser.get_format_instructions()
    exclusion_block = (
        "\nНе повторяй и не перефразируй следующие уже созданные вопросы:\n{excluded_questions}\n"
        if with_exclusions
        else ""
    )
    input_variables = ["user_prompt"]
    if with_exclusions:
        input_variables.append("excluded_questions")

    return ChatPromptTemplate(
        messages=[
            HumanMessagePromptTemplate.from_template(
                """Получив текст нормативного документа, сгенерируй из него {number_of_questions} вопросов с несколькими вариантами ответов с правильным ответом.

Правило регистра вариантов ответа (option_1, option_2, option_3 и answer):
- пиши вариант со строчной буквы, например: «ознакомление с требованиями»;
- исключение: если вариант — название нормативного документа, начинай с заглавной буквы, например: «Закон…», «Положение…», «Приказ…», «Федеральный закон…», «ГОСТ…».
                """
                + exclusion_block
                + """\n{format_instructions}\n{user_prompt}"""
            )
        ],
        input_variables=input_variables,
        partial_variables={
            "number_of_questions": num_questions,
            "format_instructions": format_instructions,
        },
    )


def _generate_questions_for_chunk(
    text,
    num_questions,
    chunk_index=1,
    chunks_total=1,
    excluded_questions=None,
):
    excluded_questions = excluded_questions or []
    with_exclusions = bool(excluded_questions)
    prompt = _get_prompt(num_questions, with_exclusions=with_exclusions)
    format_kwargs = {"user_prompt": text}
    if with_exclusions:
        format_kwargs["excluded_questions"] = "\n".join(
            f"- {question}" for question in excluded_questions
        )
    user_query = prompt.format_prompt(**format_kwargs)
    user_query_output = invoke_chat(
        user_query.to_messages(),
        operation="generate_questions",
        chunk=f"{chunk_index}/{chunks_total}",
        text_length=len(text),
        num_questions=num_questions,
    )

    if not user_query_output or not user_query_output.content:
        raise ValueError("Модель не вернула ответа")

    questions = parse_result(user_query_output.content)
    if not questions:
        raise ValueError("Не удалось получить вопросы из ответа модели")

    logger.info(
        "Сгенерировано вопросов: %s (chunk %s/%s)",
        len(questions),
        chunk_index,
        chunks_total,
    )
    return questions


def _clamp_num_questions(num_questions):
    try:
        value = int(num_questions)
    except (TypeError, ValueError):
        value = DEFAULT_NUM_QUESTIONS
    return max(MIN_NUM_QUESTIONS, min(value, MAX_NUM_QUESTIONS))


def generate_questions(text, num_questions=None):
    if num_questions is None:
        num_questions = DEFAULT_NUM_QUESTIONS
    try:
        num_questions = _clamp_num_questions(num_questions)
        chunks = chunk_text(text)
        logger.info(
            "Запрос генерации вопросов: text_length=%s, chunks=%s, num_questions=%s",
            len(text),
            len(chunks),
            num_questions,
        )

        questions = []
        seen = set()

        def add_unique(new_questions):
            unique, _ = _dedupe_questions(new_questions, seen)
            questions.extend(unique)
            return len(unique)

        remaining = num_questions
        for index, chunk in enumerate(chunks):
            if remaining <= 0:
                break
            chunks_left = len(chunks) - index
            chunk_questions_count = max(1, remaining // chunks_left)
            chunk_questions = _generate_questions_for_chunk(
                chunk,
                chunk_questions_count,
                chunk_index=index + 1,
                chunks_total=len(chunks),
            )
            added = add_unique(chunk_questions)
            if added < len(chunk_questions):
                logger.info(
                    "Отброшено дублей: %s (chunk %s/%s)",
                    len(chunk_questions) - added,
                    index + 1,
                    len(chunks),
                )
            remaining = num_questions - len(questions)

        topup_round = 0
        while len(questions) < num_questions and topup_round < MAX_TOPUP_ROUNDS:
            topup_round += 1
            needed = num_questions - len(questions)
            logger.info(
                "Добор вопросов: round=%s, needed=%s, have=%s",
                topup_round,
                needed,
                len(questions),
            )
            excluded = [item["question"] for item in questions]
            progress = False

            for index, chunk in enumerate(chunks):
                if len(questions) >= num_questions:
                    break
                ask = num_questions - len(questions)
                try:
                    chunk_questions = _generate_questions_for_chunk(
                        chunk,
                        ask,
                        chunk_index=index + 1,
                        chunks_total=len(chunks),
                        excluded_questions=excluded,
                    )
                except ValueError as error:
                    logger.warning(
                        "Добор не удался (chunk %s/%s): %s",
                        index + 1,
                        len(chunks),
                        error,
                    )
                    continue

                added = add_unique(chunk_questions)
                if added:
                    progress = True
                    excluded = [item["question"] for item in questions]

            if not progress:
                logger.warning(
                    "Добор остановлен: нет новых уникальных вопросов (have=%s, need=%s)",
                    len(questions),
                    num_questions,
                )
                break

        if not questions:
            return [], "Не удалось получить вопросы из ответа модели"

        if len(questions) < num_questions:
            logger.warning(
                "Собрано меньше вопросов, чем запрошено: have=%s, need=%s",
                len(questions),
                num_questions,
            )

        return questions[:num_questions], None
    except Exception as error:
        error_message = f"Ошибка при генерации вопросов: {str(error)}"
        logger.error(error_message)
        return [], error_message
