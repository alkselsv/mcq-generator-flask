import os
from functools import lru_cache

from langchain_openai import ChatOpenAI


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
