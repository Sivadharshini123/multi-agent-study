"""Tutor answers only from chunks returned by search_subject."""

from __future__ import annotations

import hashlib
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.context import ToolContext
from app.agents.llm import complete
from app.models import AnswerCache, Chunk, Doubt
from app.rag.search import search_subject
from app.rag.tamil_check import contains_tamil
from app.services.grounding import (
    NOT_FOUND,
    attach_source,
    citations_for,
    extractive_answer,
    grounded,
    question_is_tamil,
)

_SYSTEM = (
    "Answer only with facts that appear in the material below. "
    "Do not add outside knowledge. Keep the Source line exactly as given. "
    "If the material does not answer the question, reply with exactly: not found in the material. "
    "If the question contains Tamil, write the explanation in Tamil and place English technical terms in brackets."
)


def answer(ctx: ToolContext, payload: dict) -> dict:
    db: Session = ctx.session
    subject_id = payload["subject_id"]
    question = payload["question"].strip()
    simple = bool(payload.get("simple"))
    cached = _cached(db, subject_id, question, simple)
    if cached is not None:
        ctx.wrote = True
        _remember(db, ctx.user_id, subject_id, question, cached["answer"], cached["citations"])
        return cached

    hits = ctx.call("search_subject", search_subject, db, subject_id, question, 4, detail=subject_id)
    text, citations = extractive_answer(question, hits)
    if text != NOT_FOUND:
        proposed = _llm_answer(question, text)
        if proposed and grounded(proposed, hits, tamil_question=question_is_tamil(question)):
            text = attach_source(proposed, citations or citations_for(hits))
            citations = citations or citations_for(hits)
        if simple:
            text = ctx.call("explain_simply", simplify, text, question, detail="simpler reading level")
            if not grounded(text, hits, tamil_question=question_is_tamil(question)):
                text, citations = extractive_answer(question, hits)
                text = simplify(text, question)
    ctx.wrote = True
    _store_cache(db, subject_id, question, simple, text, citations)
    _remember(db, ctx.user_id, subject_id, question, text, citations)
    return {"answer": text, "citations": citations, "cached": False}


def simplify(answer_text: str, question: str) -> str:
    if answer_text.strip() == NOT_FOUND:
        return NOT_FOUND
    body, marker, source = answer_text.partition("\n\nSource:")
    short = _shorten(body)
    if question_is_tamil(question):
        short = _tamil_frame(short)
    if marker:
        return f"{short}\n\nSource:{source}"
    return short


def _shorten(body: str) -> str:
    sentences = [part.strip() for part in body.replace("\n", " ").split(".") if part.strip()]
    kept: list[str] = []
    for sentence in sentences[:2]:
        words = sentence.split()
        if len(words) > 18:
            sentence = " ".join(words[:18])
        kept.append(sentence)
    return ". ".join(kept) + ("." if kept else body)


def _tamil_frame(body: str) -> str:
    if contains_tamil(body):
        return body
    return f"பாடக்குறிப்பிலிருந்து: {body}"


def _llm_answer(question: str, grounded_text: str) -> str | None:
    return complete(_SYSTEM, f"Question:\n{question}\n\nMaterial:\n{grounded_text}")


def _stamp(db: Session, subject_id: str) -> str:
    hashes = sorted(set(db.scalars(select(Chunk.file_hash).where(Chunk.subject_id == subject_id))))
    return hashlib.sha256("|".join(hashes).encode()).hexdigest()


def _cache_key(subject_id: str, question: str, simple: bool, stamp: str) -> str:
    raw = json.dumps(
        {"s": subject_id, "q": question.casefold().strip(), "simple": simple, "stamp": stamp},
        sort_keys=True,
    )
    return hashlib.sha256(raw.encode()).hexdigest()


def _cached(db: Session, subject_id: str, question: str, simple: bool) -> dict | None:
    row = db.get(AnswerCache, _cache_key(subject_id, question, simple, _stamp(db, subject_id)))
    if row is None:
        return None
    return {"answer": row.answer, "citations": row.citations, "cached": True}


def _store_cache(db: Session, subject_id: str, question: str, simple: bool, answer_text: str, citations: list) -> None:
    key = _cache_key(subject_id, question, simple, _stamp(db, subject_id))
    row = db.get(AnswerCache, key)
    if row is None:
        db.add(AnswerCache(key=key, subject_id=subject_id, answer=answer_text, citations=citations))
    else:
        row.answer = answer_text
        row.citations = citations


def _remember(db: Session, user_id: int | None, subject_id: str, question: str, answer_text: str, citations: list) -> None:
    if user_id is None:
        return
    db.add(
        Doubt(
            user_id=user_id,
            subject_id=subject_id,
            question=question,
            answer=answer_text,
            citations=citations,
        )
    )
