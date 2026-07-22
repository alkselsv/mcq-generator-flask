import os
import re

DEFAULT_CHUNK_SIZE = int(os.environ.get("TEXT_CHUNK_SIZE", "4000"))
MIN_CHUNK_SIZE = int(os.environ.get("TEXT_MIN_CHUNK_SIZE", "200"))


def _normalize_text(text):
    text = text.replace("\x0c", "\n")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


def _hard_split(text, max_size):
    parts = []
    remaining = text.strip()
    while remaining:
        if len(remaining) <= max_size:
            parts.append(remaining)
            break

        cut = remaining.rfind(" ", 0, max_size)
        if cut < max_size // 2:
            cut = max_size
        part = remaining[:cut].strip()
        if part:
            parts.append(part)
        remaining = remaining[cut:].strip()
    return parts


def _split_long_paragraph(paragraph, max_chunk_size):
    if len(paragraph) <= max_chunk_size:
        return [paragraph]

    sentences = [
        s.strip() for s in re.split(r"(?<=[.!?…])\s+", paragraph) if s.strip()
    ]
    if len(sentences) <= 1:
        return _hard_split(paragraph, max_chunk_size)

    parts = []
    current = []
    current_len = 0

    for sentence in sentences:
        if len(sentence) > max_chunk_size:
            if current:
                parts.append(" ".join(current))
                current = []
                current_len = 0
            parts.extend(_hard_split(sentence, max_chunk_size))
            continue

        separator = 1 if current else 0
        if current and current_len + separator + len(sentence) > max_chunk_size:
            parts.append(" ".join(current))
            current = [sentence]
            current_len = len(sentence)
        else:
            current.append(sentence)
            current_len += separator + len(sentence)

    if current:
        parts.append(" ".join(current))
    return parts


def _merge_small_chunks(chunks, min_chunk_size, max_chunk_size):
    if len(chunks) <= 1:
        return chunks

    merged = []
    for chunk in chunks:
        if merged and (
            len(merged[-1]) < min_chunk_size or len(chunk) < min_chunk_size
        ):
            candidate = merged[-1] + "\n\n" + chunk
            if len(candidate) <= max_chunk_size:
                merged[-1] = candidate
                continue
        merged.append(chunk)

    return merged


def chunk_text(text, max_chunk_size=None):
    max_chunk_size = max_chunk_size or DEFAULT_CHUNK_SIZE
    text = _normalize_text(text)
    if len(text) <= max_chunk_size:
        return [text]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces = []
    for paragraph in paragraphs:
        pieces.extend(_split_long_paragraph(paragraph, max_chunk_size))

    chunks = []
    current = []
    current_len = 0

    for piece in pieces:
        piece_len = len(piece) + (2 if current else 0)
        if current and current_len + piece_len > max_chunk_size:
            chunks.append("\n\n".join(current))
            current = [piece]
            current_len = len(piece)
        else:
            current.append(piece)
            current_len += piece_len

    if current:
        chunks.append("\n\n".join(current))

    return _merge_small_chunks(chunks, MIN_CHUNK_SIZE, max_chunk_size)
