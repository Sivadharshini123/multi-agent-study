"""Hybrid retrieval for one subject using BM25 and vector embeddings."""

from __future__ import annotations

import logging
import math
import re
from collections import Counter
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
    "please", "tell", "me", "define", "what's", "give", "briefly", "describe", "discuss",
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


def _stem(token: str) -> str:
    """Lightweight stemmer for English and Tamil to capture roots."""
    token = token.lower()
    is_tamil = any("\u0b80" <= ch <= "\u0bff" for ch in token)
    if is_tamil:
        if len(token) >= 5:
            return token[:len(token) - 2]
        return token
    # English suffix stripping
    for suffix in ("ing", "tion", "tions", "ness", "ment", "s", "es", "ed", "al"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 3:
            return token[:-len(suffix)]
    return token


class BM25:
    """Okapi BM25 implementation for lexical keyword ranking."""

    def __init__(self, corpus: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.corpus_size = len(corpus)
        self.doc_lens = [len(doc) for doc in corpus]
        self.avgdl = sum(self.doc_lens) / (self.corpus_size or 1.0)
        self.doc_freqs: list[Counter] = [Counter(doc) for doc in corpus]
        self.idf: dict[str, float] = {}
        self._compute_idf()

    def _compute_idf(self) -> None:
        df: dict[str, int] = {}
        for freqs in self.doc_freqs:
            for term in freqs:
                df[term] = df.get(term, 0) + 1
        for term, freq in df.items():
            self.idf[term] = math.log(1.0 + (self.corpus_size - freq + 0.5) / (freq + 0.5))

    def get_scores(self, query_terms: list[str]) -> list[float]:
        scores = [0.0] * self.corpus_size
        for term in query_terms:
            if term not in self.idf:
                continue
            idf_val = self.idf[term]
            for i, freqs in enumerate(self.doc_freqs):
                tf = freqs[term]
                if tf <= 0:
                    continue
                doc_len = self.doc_lens[i]
                numerator = tf * (self.k1 + 1.0)
                denominator = tf + self.k1 * (1.0 - self.b + self.b * (doc_len / (self.avgdl or 1.0)))
                scores[i] += idf_val * (numerator / denominator)
        return scores


def keyword_score(query: str, text: str) -> tuple[float, bool]:
    content = [tok for tok in _tokens(query) if tok not in STOP and len(tok) > 1]
    if not content and not query.strip():
        return 0.0, False
    text_cf = text.lower()
    squashed_text = _squash(text)
    squashed_query = _squash(query)

    hits = 0
    for tok in content:
        stem = _stem(tok)
        is_tamil = any("\u0b80" <= ch <= "\u0bff" for ch in tok)
        if is_tamil:
            if tok in text_cf or stem in text_cf:
                hits += 1
        else:
            if re.search(rf"\b{re.escape(tok)}\b", text_cf) or (stem in text_cf and len(stem) >= 3):
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
    if not rows:
        return []

    # 1. Prepare BM25 corpus: unigrams + stems + bigrams
    corpus_tokens: list[list[str]] = []
    for r in rows:
        tokens = [t for t in _tokens(r.text) if t not in STOP]
        stems = [_stem(t) for t in tokens]
        bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens) - 1)]
        corpus_tokens.append(tokens + stems + bigrams)

    bm25 = BM25(corpus_tokens)

    # Prepare query terms: unigrams + stems + bigrams
    q_tokens = [t for t in _tokens(query) if t not in STOP and len(t) > 1]
    q_stems = [_stem(t) for t in q_tokens]
    q_bigrams = [f"{q_tokens[i]}_{q_tokens[i+1]}" for i in range(len(q_tokens) - 1)]
    all_query_terms = q_tokens + q_stems + q_bigrams

    bm25_raw_scores = bm25.get_scores(all_query_terms)
    max_bm25 = max(bm25_raw_scores) if bm25_raw_scores else 0.0

    overrides = vector_scores or {}
    ranked: list[Hit] = []

    for i, row in enumerate(rows):
        bm25_score = bm25_raw_scores[i]
        # Normalize BM25 score to 0..1
        norm_bm25 = (bm25_score / max_bm25) if max_bm25 > 0 else 0.0

        lexical, exact = keyword_score(query, row.text)

        embedding = row.embedding if isinstance(row.embedding, list) else []
        if row.id in overrides:
            vector = max(0.0, overrides[row.id])
        else:
            vector = max(0.0, cosine(query_vec, embedding))

        # Hybrid formula:
        # If BM25 has direct matches, BM25 heavily anchors the ranking (0.7 BM25 + 0.3 Vector)
        # If exact match found, combined is boosted to guarantee top ranking
        if exact:
            combined = 1.0 + 0.5 * norm_bm25 + 0.1 * vector
        elif norm_bm25 > 0:
            combined = 0.70 * norm_bm25 + 0.15 * lexical + 0.15 * vector
        else:
            combined = 0.40 * lexical + 0.60 * vector

        ranked.append(
            Hit(
                chunk_id=row.id,
                subject_id=row.subject_id,
                text=row.text,
                chapter=row.chapter,
                page=row.page,
                source_path=row.source_path,
                score=combined,
                keyword=max(lexical, norm_bm25),
                vector=vector,
                file_hash=row.file_hash,
                chunk_index=row.chunk_index,
            )
        )

    # Sort descending by combined score
    ranked.sort(key=lambda hit: hit.score, reverse=True)
    return ranked


def is_weak(hit: Hit | None) -> bool:
    if hit is None:
        return True
    if hit.keyword <= 0 and hit.vector < 0.04:
        return True
    if hit.score < 0.01:
        return True
    return False


def _pgvector_scores(db: Session, subject_id: str, query_vec: list[float]) -> dict[int, float]:
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
