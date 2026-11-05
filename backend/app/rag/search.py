"""Hybrid retrieval for one subject. Agents must call search_subject, not this file's helpers."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.models import Chunk
from app.rag.embeddings import cosine, embed_texts

logger = logging.getLogger("study.search")

STOP = {
    "what", "is", "the", "a", "an", "of", "to", "and", "or", "in", "on", "for", "how",
    "does", "do", "explain", "about", "from", "with", "this", "that", "which", "who",
    "why", "when", "where", "it", "its", "be", "are", "was", "were", "can", "could",
    "please", "tell", "me", "define", "what's", "give", "briefly",
}


@dataclass
class Hit:
    chunk_id: int
    subject_id: str
    text: str
    chapter: str
    page: int
    source_path: str
    score: float
    keyword: float
    vector: float
    file_hash: str
    chunk_index: int


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower(), flags=re.UNICODE)


def _squash(text: str) -> str:
    return re.sub(r"\s+", "", text.lower())


_FORMULA = re.compile(r"[A-Za-z][A-Za-z0-9.^]*\s*=\s*[A-Za-z0-9.^+\-/*() ]{1,40}")


def keyword_score(query: str, text: str) -> tuple[float, bool]:
    content = [tok for tok in _tokens(query) if tok not in STOP and len(tok) > 1]
    if not content and not query.strip():
        return 0.0, False
    text_cf = text.lower()
    squashed_text = _squash(text)
    squashed_query = _squash(query)

    hits = 0
    for tok in content:
        is_tamil = any("\u0b80" <= ch <= "\u0bff" for ch in tok)
        if is_tamil:
            # Tamil agglutinative matching
            if tok in text_cf or (len(tok) >= 4 and tok[:len(tok)-2] in text_cf):
                hits += 1
        else:
            if re.search(rf"\b{re.escape(tok)}\b", text_cf, flags=re.IGNORECASE) or (len(tok) >= 5 and tok[:len(tok)-1] in text_cf):
                hits += 1

    ratio = hits / len(content) if content else 0.0
    exact = False
    if len(squashed_query) >= 3 and squashed_query in squashed_text:
        exact = True
    if content and hits == len(content):
        exact = True
    for fragment in _FORMULA.findall(query):
        compact = _squash(fragment)
        if len(compact) >= 3 and compact in squashed_text:
            exact = True
    if any(symbol in query for symbol in "=+-/*") and squashed_query and squashed_query in squashed_text:
        exact = True
    score = 1.0 if exact else ratio
    return score, exact


def hybrid_rerank(
    query: str,
    rows: list[Chunk],
    query_vec: list[float],
    vector_scores: dict[int, float] | None = None,
) -> list[Hit]:
    ranked: list[Hit] = []
    overrides = vector_scores or {}
    for row in rows:
        embedding = row.embedding if isinstance(row.embedding, list) else []
        lexical, exact = keyword_score(query, row.text)
        if row.id in overrides:
            vector = max(0.0, overrides[row.id])
        else:
            vector = max(0.0, cosine(query_vec, embedding))
        if exact:
            combined = 0.25 * vector + 0.75 * lexical
        else:
            combined = 0.55 * vector + 0.45 * lexical
        ranked.append(
            Hit(
                chunk_id=row.id,
                subject_id=row.subject_id,
                text=row.text,
                chapter=row.chapter,
                page=row.page,
                source_path=row.source_path,
                score=combined,
                keyword=lexical,
                vector=vector,
                file_hash=row.file_hash,
                chunk_index=row.chunk_index,
            )
        )
    ranked.sort(key=lambda hit: hit.score, reverse=True)
    return ranked


def is_weak(hit: Hit | None) -> bool:
    if hit is None:
        return True
    if hit.keyword <= 0 and hit.vector < 0.05:
        return True
    if hit.score < 0.03:
        return True
    return False


def _pgvector_scores(db: Session, subject_id: str, query_vec: list[float]) -> dict[int, float]:
    """Use the pgvector column when this database has one. Keyword scoring still sees every row."""
    bind = db.get_bind()
    if bind.dialect.name != "postgresql" or not query_vec:
        return {}
    if not all(isinstance(value, (int, float)) for value in query_vec):
        return {}
    literal = "[" + ",".join(f"{float(value):.8f}" for value in query_vec) + "]"
    try:
        fetched = db.execute(
            text(
                "SELECT id, 1 - (embedding_vec <=> CAST(:query AS vector)) AS score "
                "FROM chunks WHERE subject_id = :subject_id AND embedding_vec IS NOT NULL"
            ),
            {"query": literal, "subject_id": subject_id},
        )
    except Exception:
        logger.warning("pgvector score lookup failed; using stored JSON embeddings")
        return {}
    return {int(row.id): float(row.score) for row in fetched}


def search_subject(db: Session, subject_id: str, query: str, k: int = 4) -> list[Hit]:
    """Single retrieval entry point. Results are limited to one subject collection."""
    rows = list(db.scalars(select(Chunk).where(Chunk.subject_id == subject_id)))
    if not rows:
        return []
    query_vec = embed_texts([query])[0]
    ranked = hybrid_rerank(query, rows, query_vec, _pgvector_scores(db, subject_id, query_vec))
    if not ranked or is_weak(ranked[0]):
        return []
    return ranked[:k]
