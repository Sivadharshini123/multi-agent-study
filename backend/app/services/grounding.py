from __future__ import annotations

import re

from app.rag.search import Hit
from app.rag.tamil_check import contains_tamil

NOT_FOUND = "not found in the material."

_STOP = {
    "what", "is", "the", "a", "an", "of", "to", "and", "or", "in", "on", "for", "how",
    "does", "do", "with", "this", "that", "from", "your", "about", "source", "chapter",
    "page", "notes", "define", "explain", "state", "tell", "give", "describe", "discuss",
    "are", "can", "briefly",
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
    # Split on sentence boundaries, colons, or numbered list items
    raw_parts = re.split(r"(?<=[.!?\n])\s+", text)
    cleaned = []
    for part in raw_parts:
        p = part.strip()
        if p and len(p) > 10:
            cleaned.append(p)
    return cleaned


def _stem_word(w: str) -> str:
    w = w.lower()
    for s in ("ing", "tion", "tions", "ness", "ment", "s", "es", "ed", "al", "ic"):
        if w.endswith(s) and len(w) - len(s) >= 3:
            return w[:-len(s)]
    return w


def extractive_answer(query: str, hits: list[Hit]) -> tuple[str, list[dict]]:
    if not hits:
        return NOT_FOUND, []

    query_terms = [
        tok.lower()
        for tok in re.findall(r"\w+", query.lower(), flags=re.UNICODE)
        if tok not in _STOP and len(tok) > 1
    ]
    query_stems = {_stem_word(t) for t in query_terms}
    is_tamil = contains_tamil(query)

    scored_sentences: list[tuple[float, str, Hit]] = []

    # Score each sentence in the top retrieved hits against the query keywords
    for rank_idx, hit in enumerate(hits[:4]):
        sentences = _sentences(hit.text)
        hit_bonus = max(0.0, 1.0 - (rank_idx * 0.25))

        for s_idx, sentence in enumerate(sentences):
            s_lower = sentence.lower()
            s_tokens = set(re.findall(r"\w+", s_lower, flags=re.UNICODE))
            s_stems = {_stem_word(w) for w in s_tokens}

            exact_count = sum(1 for t in query_terms if t in s_lower or t in s_tokens)
            stem_count = len(query_stems & s_stems)

            score = (exact_count * 3.0) + (stem_count * 1.5)

            # High bonus if multiple query terms appear in the same sentence (e.g. cardiac + arrest + symptoms)
            if query_terms and exact_count >= 2:
                score += 5.0
            if query_terms and exact_count == len(query_terms):
                score += 8.0

            if is_tamil and contains_tamil(sentence):
                score += 3.0

            if score > 0:
                final_score = (score * 2.0) + hit_bonus
                scored_sentences.append((final_score, sentence, hit))
            elif rank_idx == 0:
                # Fallback baseline for leading sentences of top hit
                scored_sentences.append((0.05 - (s_idx * 0.005), sentence, hit))

    if not scored_sentences:
        return NOT_FOUND, []

    # Sort descending by relevance score
    scored_sentences.sort(key=lambda x: x[0], reverse=True)

    chosen: list[str] = []
    used_hits: list[Hit] = []
    seen_texts: set[str] = set()

    for score, sentence, hit in scored_sentences:
        if sentence in seen_texts:
            continue
        seen_texts.add(sentence)
        chosen.append(sentence)
        if hit not in used_hits:
            used_hits.append(hit)
        if len(chosen) >= 3:
            break

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
    return overlap >= 0.40


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
