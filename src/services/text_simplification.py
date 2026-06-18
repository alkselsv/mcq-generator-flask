import logging

from langchain_core.messages import HumanMessage
from langchain_core.prompts import PromptTemplate

from services.llm import invoke_chat
from services.text_chunking import chunk_text

logger = logging.getLogger("llm.simplify")

_PROMPT = PromptTemplate.from_template(
    """Перепиши текст, упростив его, при этом не используй нумерацию абзацев:
    "{text}".
    """
)


def simplify_text(text):
    try:
        chunks = chunk_text(text)
        logger.info(
            "Запрос упрощения текста: text_length=%s, chunks=%s",
            len(text),
            len(chunks),
        )

        if len(chunks) == 1:
            prompt_text = _PROMPT.format(text=chunks[0])
            response = invoke_chat(
                [HumanMessage(content=prompt_text)],
                operation="simplify_text",
                chunk="1/1",
                text_length=len(chunks[0]),
            )
            summary = response.content
        else:
            parts = []
            for index, chunk in enumerate(chunks, start=1):
                prompt_text = _PROMPT.format(text=chunk)
                response = invoke_chat(
                    [HumanMessage(content=prompt_text)],
                    operation="simplify_text",
                    chunk=f"{index}/{len(chunks)}",
                    text_length=len(chunk),
                )
                parts.append(response.content)
            summary = "\n\n".join(parts)

        if not summary:
            raise ValueError("Модель не вернула упрощенного текста")

        logger.info("Текст упрощён: output_length=%s", len(summary))
        return summary, None
    except Exception as error:
        error_message = f"Ошибка при упрощении текста: {str(error)}"
        logger.error(error_message)
        return None, error_message
