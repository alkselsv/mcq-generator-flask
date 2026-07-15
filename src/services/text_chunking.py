import os
import re

DEFAULT_CHUNK_SIZE = int(os.environ.get("TEXT_CHUNK_SIZE", "4000"))
MIN_CHUNK_SIZE = int(os.environ.get("TEXT_MIN_CHUNK_SIZE", "200"))


def _normalize_text(text):
    text = text.replace("\x0c", "\n")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def _merge_small_chunks(chunks, min_chunk_size):
    if len(chunks) <= 1:
        return chunks

    merged = []
    for chunk in chunks:
        if merged and (
            len(merged[-1]) < min_chunk_size or len(chunk) < min_chunk_size
        ):
            merged[-1] = merged[-1] + "\n\n" + chunk
        else:
            merged.append(chunk)

    return merged


def chunk_text(text, max_chunk_size=None):
    max_chunk_size = max_chunk_size or DEFAULT_CHUNK_SIZE
    text = _normalize_text(text)
    if len(text) <= max_chunk_size:
        return [text]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks = []
    current = []
    current_len = 0

    for paragraph in paragraphs:
        paragraph_len = len(paragraph) + (2 if current else 0)
        if current and current_len + paragraph_len > max_chunk_size:
            chunks.append("\n\n".join(current))
            current = [paragraph]
            current_len = len(paragraph)
        else:
            current.append(paragraph)
            current_len += paragraph_len

    if current:
        chunks.append("\n\n".join(current))

    return _merge_small_chunks(chunks, MIN_CHUNK_SIZE)
