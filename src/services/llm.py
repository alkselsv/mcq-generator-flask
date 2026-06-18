import os
from functools import lru_cache

from langchain_openai import ChatOpenAI

from services.llm_logging import log_llm_call, log_llm_prompt, log_llm_response


@lru_cache(maxsize=1)
def get_chat_model():
    return ChatOpenAI(
        temperature=0,
        model_name="gpt-4o",
        api_key=os.environ.get("OPENAI_API_KEY"),
        timeout=300,
        max_retries=2,
        request_timeout=300,
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
