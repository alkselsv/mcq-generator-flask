import os

DEFAULT_CHUNK_SIZE = int(os.environ.get("TEXT_CHUNK_SIZE", "4000"))


def chunk_text(text, max_chunk_size=None):
    max_chunk_size = max_chunk_size or DEFAULT_CHUNK_SIZE
    if len(text) <= max_chunk_size:
        return [text]

    paragraphs = text.split("\n\n")
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

    return chunks
