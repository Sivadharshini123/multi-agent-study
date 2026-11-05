"""Split extracted pages into ~500-word chunks with overlap and chapter/page metadata."""

from __future__ import annotations

import re
from dataclasses import dataclass

CHUNK_WORDS = 500
CHUNK_OVERLAP = 50

_CHAPTER = re.compile(
    r"^\s*(?:#{1,3}\s*)?(?:chapter|unit|module)\s+([0-9ivxlcdm]+)\b[:.\-\s]*(.*)$",
    re.IGNORECASE,
)
_TAMIL_CHAPTER = re.compile(
    r"^\s*(?:#{1,3}\s*)?(அத்தியாயம்|அலகு)\s+([0-9]+)\s*[:.\-]?\s*(.*)$"
)
_PAGE = re.compile(r"<!--\s*page:\s*(\d+)\s*-->", re.IGNORECASE)
_WORD = re.compile(r"\S+")


@dataclass
class WordSpan:
    text: str
    page: int
    chapter: str


@dataclass
class TextChunk:
    index: int
    text: str
    chapter: str
    page: int


def _chapter_label(line: str, current: str) -> str:
    tamil = _TAMIL_CHAPTER.match(line)
    if tamil:
        title = tamil.group(3).strip()
        label = f"{tamil.group(1)} {tamil.group(2)}"
        return f"{label}: {title}" if title else label
    match = _CHAPTER.match(line)
    if not match:
        return current
    title = match.group(2).strip(" :-#")
    label = f"Chapter {match.group(1)}"
    return f"{label}: {title}" if title else label


def words_from_pages(pages: list[tuple[int, str]]) -> list[WordSpan]:
    words: list[WordSpan] = []
    chapter = "Notes"
    for page_no, text in pages:
        markers = list(_PAGE.finditer(text))
        current_page = int(markers[0].group(1)) if markers else page_no
        for line in text.splitlines():
            marker = _PAGE.search(line)
            if marker:
                current_page = int(marker.group(1))
                line = _PAGE.sub("", line)
            chapter = _chapter_label(line.strip(), chapter)
            for token in _WORD.findall(line):
                words.append(WordSpan(token, current_page, chapter))
    return words


def chunk_words(
    words: list[WordSpan],
    size: int = CHUNK_WORDS,
    overlap: int = CHUNK_OVERLAP,
) -> list[TextChunk]:
    if not words:
        return []
    step = max(1, size - overlap)
    chunks: list[TextChunk] = []
    start = 0
    while start < len(words):
        window = words[start : start + size]
        if not window:
            break
        chunks.append(
            TextChunk(
                index=len(chunks),
                text=" ".join(word.text for word in window),
                chapter=window[0].chapter,
                page=window[0].page,
            )
        )
        if start + size >= len(words):
            break
        start += step
    return chunks
