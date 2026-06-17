import os
import re
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate


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
            print(f"Ошибка при разборе JSON: {json_str}")
        except KeyError as e:
            print(f"Отсутствует ключ в JSON объекте: {e}")

    return questions


def generate_questions(text, num_questions=5):
    load_dotenv()

    chat_model = ChatOpenAI(
        temperature=0,
        model_name="gpt-4o",
        api_key=os.environ.get("OPENAI_API_KEY"),
        timeout=300,  # 5 минут таймаут
        max_retries=3,  # 3 попытки при ошибке
        request_timeout=300,  # 5 минут таймаут запроса
    )

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
    prompt = ChatPromptTemplate(
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
    user_query = prompt.format_prompt(user_prompt=text)

    try:
        user_query_output = chat_model.invoke(user_query.to_messages())
        if not user_query_output or not user_query_output.content:
            raise ValueError("Модель не вернула ответа")

        result = user_query_output.content
        questions = parse_result(result)

        if not questions:
            raise ValueError("Не удалось получить вопросы из ответа модели")

        return questions, None
    except Exception as e:
        error_message = f"Ошибка при генерации вопросов: {str(e)}"
        return (
            [],
            error_message,
        )
