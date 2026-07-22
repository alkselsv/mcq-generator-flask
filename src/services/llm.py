import os
from functools import lru_cache

from langchain_openai import ChatOpenAI

from services.llm_logging import log_llm_call, log_llm_prompt, log_llm_response


@lru_cache(maxsize=1)
def get_chat_model():
    timeout = float(os.environ.get("OPENAI_TIMEOUT", "300"))
    return ChatOpenAI(
        temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0")),
        model_name=os.environ.get("OPENAI_MODEL", "gpt-4o"),
        api_key=os.environ.get("OPENAI_API_KEY"),
        timeout=timeout,
        max_retries=int(os.environ.get("OPENAI_MAX_RETRIES", "2")),
        request_timeout=timeout,
    )


def _messages_to_text(messages):
    parts = []
    for message in messages:
        content = getattr(message, "content", str(message))
        role = getattr(message, "type", getattr(message, "role", "message"))
        parts.append(f"[{role}] {content}")
    return "\n".join(parts)


def invoke_chat(messages, operation, **context):
    prompt_text = _messages_to_text(messages)
    log_llm_prompt(prompt_text)

    with log_llm_call(operation, **context):
        response = get_chat_model().invoke(messages)

    content = response.content if response else ""
    log_llm_response(content, **context)
    return response
