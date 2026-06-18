import re
import json
import logging
from functools import lru_cache

from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate

from services.llm import invoke_chat
from services.text_chunking import chunk_text

logger = logging.getLogger("llm.questions")


def parse_result(result):
    json_objects = re.findall(r"\{[^}]+\}", result)
    questions = []

    for json_str in json_objects:
        try:
            question_data = json.loads(json_str)
            questions.append(
                {
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
            )
        except json.JSONDecodeError:
            logger.warning("Ошибка при разборе JSON: %s", json_str)
        except KeyError as error:
            logger.warning("Отсутствует ключ в JSON объекте: %s", error)

    return questions


@lru_cache(maxsize=32)
def _get_prompt(num_questions):
    response_schemas = [
        ResponseSchema(
            name="question",
            description="Вопрос с множественным выбором ответов, созданный на основе фрагмента входного текста.",
        ),
        ResponseSchema(
            name="option_1",
            description="Первый вариант ответа на вопрос с множественным выбором. Используйте этот формат: 'вариант ответа'",
        ),
        ResponseSchema(
            name="option_2",
            description="Второй вариант ответа на вопрос с множественным выбором. Используйте этот формат: 'вариант ответа''",
        ),
        ResponseSchema(
            name="option_3",
            description="Третий вариант ответа на вопрос с множественным выбором. Используйте этот формат: 'вариант ответа''",
        ),
        ResponseSchema(
            name="answer",
            description="Правильный ответ на вопрос. Используйте этот формат: 'вариант ответа' ",
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
    return ChatPromptTemplate(
        messages=[
            HumanMessagePromptTemplate.from_template(
                """Получив текст нормативного документа, сгенерируй из него {number_of_questions} вопросов с несколькими вариантами ответов с правильным ответом.
                \n{format_instructions}\n{user_prompt}"""
            )
        ],
        input_variables=["user_prompt"],
        partial_variables={
            "number_of_questions": num_questions,
            "format_instructions": format_instructions,
        },
    )


def _generate_questions_for_chunk(text, num_questions, chunk_index=1, chunks_total=1):
    prompt = _get_prompt(num_questions)
    user_query = prompt.format_prompt(user_prompt=text)
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


def generate_questions(text, num_questions=5):
    try:
        chunks = chunk_text(text)
        logger.info(
            "Запрос генерации вопросов: text_length=%s, chunks=%s, num_questions=%s",
            len(text),
            len(chunks),
            num_questions,
        )

        if len(chunks) == 1:
            return _generate_questions_for_chunk(chunks[0], num_questions), None

        questions = []
        remaining = num_questions
        for index, chunk in enumerate(chunks):
            chunks_left = len(chunks) - index
            chunk_questions_count = max(1, remaining // chunks_left)
            chunk_questions = _generate_questions_for_chunk(
                chunk,
                chunk_questions_count,
                chunk_index=index + 1,
                chunks_total=len(chunks),
            )
            questions.extend(chunk_questions)
            remaining = num_questions - len(questions)
            if remaining <= 0:
                break

        return questions[:num_questions], None
    except Exception as error:
        error_message = f"Ошибка при генерации вопросов: {str(error)}"
        logger.error(error_message)
        return [], error_message
