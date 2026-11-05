from __future__ import annotations

import re

from app.rag.search import Hit
from app.rag.tamil_check import contains_tamil

NOT_FOUND = "not found in the material."

_STOP = {
    "what", "is", "the", "a", "an", "of", "to", "and", "or", "in", "on", "for", "how",
    "does", "do", "with", "this", "that", "from", "your", "about", "source", "chapter",
    "page", "notes", "define", "explain", "state", "tell", "give",
}


def citations_for(hits: list[Hit]) -> list[dict]:
    seen: list[dict] = []
    labels: set[str] = set()
    for hit in hits:
        label = f"{hit.chapter}|{hit.page}"
        if label in labels:
            continue
        labels.add(label)
        seen.append({"chapter": hit.chapter, "page": hit.page, "source": hit.source_path})
    return seen


def format_sources(citations: list[dict]) -> str:
    parts = [f"{item['chapter']}, p. {item['page']}" for item in citations]
    return "; ".join(parts)


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"(?<=[.!?\n])\s+", text) if part.strip() and len(part.strip()) > 10]


def extractive_answer(query: str, hits: list[Hit]) -> tuple[str, list[dict]]:
    if not hits:
        return NOT_FOUND, []
    query_terms = {
        tok
        for tok in re.findall(r"\w+", query.lower(), flags=re.UNICODE)
        if tok not in _STOP and len(tok) > 2
    }
    is_tamil = contains_tamil(query)
    chosen: list[str] = []
    used_hits: list[Hit] = []

    for hit in hits:
        for sentence in _sentences(hit.text):
            words = set(re.findall(r"\w+", sentence.lower(), flags=re.UNICODE))
            matched = bool(words & query_terms) if query_terms else True
            if not matched and is_tamil:
                # Tamil query with English or Tamil text in hit
                matched = contains_tamil(sentence) or hit == hits[0]
            if matched or hit.keyword >= 0.5 or hit.score >= 0.2:
                chosen.append(sentence)
                used_hits.append(hit)
            if len(chosen) >= 3:
                break
        if len(chosen) >= 3:
            break

    if not chosen:
        top_sentences = _sentences(hits[0].text)[:2]
        if top_sentences:
            chosen = top_sentences
            used_hits = [hits[0]]
        else:
            return NOT_FOUND, []

    citations = citations_for(used_hits or hits[:1])
    body = " ".join(chosen)
    return f"{body}\n\nSource: {format_sources(citations)}", citations


def _content_words(text: str) -> list[str]:
    return [
        tok
        for tok in re.findall(r"\w+", text.lower(), flags=re.UNICODE)
        if tok not in _STOP and len(tok) > 3
    ]


def grounded(answer: str, hits: list[Hit], *, tamil_question: bool) -> bool:
    if answer.strip() == NOT_FOUND:
        return True
    if not hits:
        return False
    blob = " ".join(hit.text for hit in hits).lower()
    words = _content_words(answer)
    if tamil_question:
        latin = [word for word in words if re.match(r"^[a-z]", word)]
        if not latin:
            return "Source:" in answer or "p." in answer or contains_tamil(answer)
        overlap = sum(1 for word in latin if word in blob) / len(latin)
        return overlap >= 0.35 and ("p." in answer or "Source:" in answer)
    if not words:
        return False
    overlap = sum(1 for word in words if word in blob) / len(words)
    return overlap >= 0.45


def attach_source(answer: str, citations: list[dict]) -> str:
    if answer.strip() == NOT_FOUND:
        return NOT_FOUND
    if "Source:" in answer:
        return answer
    if not citations:
        return NOT_FOUND
    return f"{answer.rstrip()}\n\nSource: {format_sources(citations)}"


def question_is_tamil(question: str) -> bool:
    return contains_tamil(question)
