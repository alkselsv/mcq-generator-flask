from langchain_core.prompts import PromptTemplate

from services.llm import get_chat_model
from services.text_chunking import chunk_text

_PROMPT = PromptTemplate.from_template(
    """Перепиши текст, упростив его, при этом не используй нумерацию абзацев:
    "{text}".
    """
)


def simplify_text(text):
    try:
        chat_model = get_chat_model()
        chain = _PROMPT | chat_model
        chunks = chunk_text(text)

        if len(chunks) == 1:
            response = chain.invoke({"text": chunks[0]})
            summary = response.content
        else:
            parts = []
            for chunk in chunks:
                response = chain.invoke({"text": chunk})
                parts.append(response.content)
            summary = "\n\n".join(parts)

        if not summary:
            raise ValueError("Модель не вернула упрощенного текста")

        return summary, None
    except Exception as e:
        error_message = f"Ошибка при упрощении текста: {str(e)}"
        return None, error_message
