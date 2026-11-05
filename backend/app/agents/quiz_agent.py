"""Quiz generation writes only to the teacher review queue."""

from __future__ import annotations

import json
import re

from sqlalchemy.orm import Session

from app.agents.context import ToolContext
from app.agents.llm import complete
from app.models import QuizQuestion, Topic
from app.rag.search import search_subject
from app.services.grading import grade_answer
from app.services.mistakes import record_mistake, store_confidence
from app.services.quiz_bank import draft_questions, save_pending

_SYSTEM = (
    "Write quiz questions using only the material. "
    "Return a JSON list of objects with keys qtype, prompt, choices, answer, reasoning. "
    "qtype is mcq or short. The answer must be copied from the material. "
    "If you cannot, return an empty list."
)


def generate(ctx: ToolContext, payload: dict) -> dict:
    db: Session = ctx.session
    subject_id = payload["subject_id"]
    title = payload["topic_title"]
    hits = ctx.call("search_subject", search_subject, db, subject_id, title, 4, detail=subject_id)
    pending = ctx.call("generate_quiz", _generate, db, subject_id, title, hits, detail=title)
    ctx.wrote = True
    return {"pending": pending, "message": "Questions are waiting for a teacher to approve them."}


def grade_session(ctx: ToolContext, payload: dict) -> dict:
    db: Session = ctx.session
    ctx.wrote = True
    results = []
    for item in payload["answers"]:
        results.append(
            ctx.call(
                "grade_answer",
                _grade_one,
                db,
                ctx.user_id,
                item["question_id"],
                item["answer"],
                payload.get("topic_id"),
                payload.get("confidence"),
                payload["today"],
                detail=str(item["question_id"]),
            )
        )
    ctx.wrote = True
    return {"results": results}


def _generate(db: Session, subject_id: str, title: str, hits) -> int:
    drafts = draft_questions(hits)
    blob = "\n".join(hit.text for hit in hits)
    for extra in _llm_drafts(title, blob):
        drafts.append(extra)
    saved = save_pending(db, subject_id, title, drafts[:5])
    return len(saved)


def _llm_drafts(title: str, blob: str) -> list[dict]:
    if not blob.strip():
        return []
    raw = complete(_SYSTEM, f"Topic: {title}\n\nMaterial:\n{blob[:4000]}", max_tokens=900)
    if not raw:
        return []
    match = re.search(r"\[.*\]", raw, re.S)
    if not match:
        return []
    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    drafts = []
    for item in parsed:
        if not isinstance(item, dict):
            continue
        answer = str(item.get("answer") or "").strip()
        prompt = str(item.get("prompt") or "").strip()
        if not answer or not prompt or answer.casefold() not in blob.casefold():
            continue
        qtype = "mcq" if item.get("qtype") == "mcq" else "short"
        choices = item.get("choices") if qtype == "mcq" and isinstance(item.get("choices"), list) else None
        drafts.append(
            {
                "qtype": qtype,
                "language": None,
                "prompt": prompt,
                "choices": choices,
                "answer": answer,
                "reasoning": str(item.get("reasoning") or f"The material says: {answer}"),
                "support_text": blob[:4000],
                "citations": [],
                "fixture_sql": None,
            }
        )
    return drafts


def _grade_one(db, user_id, question_id, student_answer, topic_id, confidence, today) -> dict:
    question = db.get(QuizQuestion, question_id)
    if question is None or question.status != "approved":
        return {"question_id": question_id, "error": "Question is not approved"}
    topic = db.get(Topic, topic_id) if topic_id else None
    if topic is not None and (topic.user_id != user_id or topic.subject_id != question.subject_id):
        topic = None
    correct = grade_answer(
        question.qtype,
        question.language,
        question.answer,
        student_answer,
        question.choices,
        question.fixture_sql,
    )
    if question.qtype == "short" and not correct:
        correct = _llm_short_match(question.answer, student_answer, question.support_text)
    from app.models import QuizAttempt

    db.add(
        QuizAttempt(
            user_id=user_id,
            question_id=question.id,
            topic_id=topic.id if topic else None,
            student_answer=student_answer,
            correct=correct,
            confidence=confidence,
        )
    )
    store_confidence(db, topic, confidence)
    if not correct:
        record_mistake(db, user_id, question, student_answer, topic.id if topic else None, today)
    db.flush()
    return {
        "question_id": question.id,
        "correct": correct,
        "correct_answer": question.answer,
        "reasoning": question.reasoning,
    }


def _llm_short_match(expected: str, student: str, support: str) -> bool:
    verdict = complete(
        "Reply yes or no. Say yes only if the student answer states the same fact as the reference "
        "and that fact appears in the material. Do not use outside knowledge.",
        f"Material:\n{support}\n\nReference:\n{expected}\n\nStudent:\n{student}",
        max_tokens=20,
    )
    if not verdict:
        return False
    return verdict.strip().lower().startswith("yes") and expected.casefold() in support.casefold()
