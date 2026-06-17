import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate


def simplify_text(text):
    load_dotenv()

    try:
        chat_model = ChatOpenAI(
            temperature=0,
            model_name="gpt-4o",
            api_key=os.environ.get("OPENAI_API_KEY"),
            timeout=300,  # 5 минут таймаут
            max_retries=3,  # 3 попытки при ошибке
            request_timeout=300,  # 5 минут таймаут запроса
        )

        prompt_template = """Перепиши текст, упростив его, при этом не используй нумерацию абзацев:
        "{text}".
        """
        prompt = PromptTemplate.from_template(prompt_template)
        chain = prompt | chat_model
        response = chain.invoke({"text": text})
        summary = response.content

        if not summary:
            raise ValueError("Модель не вернула упрощенного текста")

        return summary, None
    except Exception as e:
        error_message = f"Ошибка при упрощении текста: {str(e)}"
        return (
            None,
            error_message,
        )
