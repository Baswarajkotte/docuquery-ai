"""Split page text into overlapping word windows for retrieval."""

import re
from dataclasses import dataclass

_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class TextChunk:
    page: int
    text: str


def clean(text: str) -> str:
    return _WHITESPACE.sub(" ", text).strip()


def chunk_pages(pages: list[str], size: int = 180, overlap: int = 40) -> list[TextChunk]:
    if size <= 0:
        raise ValueError("size must be positive")
    if not 0 <= overlap < size:
        raise ValueError("overlap must be >= 0 and smaller than size")

    step = size - overlap
    chunks: list[TextChunk] = []
    for page_no, page_text in enumerate(pages, start=1):
        words = clean(page_text).split(" ")
        if words == [""]:
            continue
        for start in range(0, len(words), step):
            window = words[start : start + size]
            chunks.append(TextChunk(page=page_no, text=" ".join(window)))
            if start + size >= len(words):
                break
    return chunks
