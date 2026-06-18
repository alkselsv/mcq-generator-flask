import logging
import os
import time
from contextlib import contextmanager

logger = logging.getLogger("llm")

PREVIEW_LENGTH = int(os.environ.get("LOG_LLM_PREVIEW_LENGTH", "300"))


def preview_text(text):
    if text is None:
        return ""

    if logger.isEnabledFor(logging.DEBUG) or PREVIEW_LENGTH < 0:
        return text

    if PREVIEW_LENGTH == 0:
        return f"[{len(text)} chars]"

    if len(text) <= PREVIEW_LENGTH:
        return text

    return f"{text[:PREVIEW_LENGTH]}... [{len(text)} chars total]"


def _format_context(context):
    return ", ".join(f"{key}={value}" for key, value in context.items())


@contextmanager
def log_llm_call(operation, **context):
    started_at = time.perf_counter()
    context_str = _format_context(context)
    logger.info("LLM start: %s (%s)", operation, context_str)

    try:
        yield
    except Exception:
        duration = time.perf_counter() - started_at
        logger.exception(
            "LLM failed: %s after %.2fs (%s)", operation, duration, context_str
        )
        raise
    else:
        duration = time.perf_counter() - started_at
        logger.info("LLM done: %s in %.2fs (%s)", operation, duration, context_str)


def log_llm_prompt(prompt_text):
    logger.debug("LLM prompt: %s", preview_text(prompt_text))


def log_llm_response(response_text, **extra):
    extra_str = _format_context(extra)
    suffix = f" ({extra_str})" if extra_str else ""
    logger.debug("LLM response%s: %s", suffix, preview_text(response_text))
