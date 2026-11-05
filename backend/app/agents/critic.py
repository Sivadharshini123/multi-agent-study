"""Read-only on plans. Flags questions the material does not support."""

from __future__ import annotations

import re
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.context import ToolContext
from app.agents.llm import complete
from app.models import Critique, Mistake, PomodoroLog, QuizAttempt, QuizQuestion
from app.services.progress import progress_snapshot

_SYSTEM = (
    "Rewrite the critique in three short parts labelled "
    "'What went well', 'What is weak', and 'Next steps'. "
    "Use only the notes provided. Do not change the study plan."
)


def review(ctx: ToolContext, payload: dict) -> dict:
    db: Session = ctx.session
    user_id = ctx.user_id
    kind = payload.get("kind", "session")
    since = payload["today"] - timedelta(days=7 if kind == "weekly" else 0)
    attempts = ctx.call("get_quiz_results", _attempts, db, user_id, since, detail=kind)
    mistakes = ctx.call("get_mistake_notebook", _mistakes, db, user_id, detail=kind)
    logs = ctx.call("get_pomodoro_logs", _logs, db, user_id, since, detail=kind)
    questions = _questions_for(db, attempts)
    notes = [_unsupported(question) for question in questions]
    notes = [note for note in notes if note]
    progress = progress_snapshot(db, user_id)
    body, reasons = _compose(progress, mistakes, logs, notes)
    phrased = complete(_SYSTEM, body, max_tokens=400)
    if phrased and "What went well" in phrased:
        body = phrased
    flagged = ctx.call("flag_question", _flag, ctx, db, questions, detail=f"{len(notes)} flags")
    ctx.call("write_critique", _write, ctx, db, user_id, body, reasons + flagged, kind, detail=kind)
    return {"body": body, "reasons": reasons}


def _attempts(db: Session, user_id: int, since):
    rows = db.scalars(select(QuizAttempt).where(QuizAttempt.user_id == user_id))
    return [row for row in rows if row.created_at.date() >= since]


def _mistakes(db: Session, user_id: int):
    return list(db.scalars(select(Mistake).where(Mistake.user_id == user_id)))


def _logs(db: Session, user_id: int, since):
    rows = db.scalars(select(PomodoroLog).where(PomodoroLog.user_id == user_id))
    return [row for row in rows if row.completed_at.date() >= since]


def _questions_for(db: Session, attempts) -> list[QuizQuestion]:
    found: list[QuizQuestion] = []
    seen: set[int] = set()
    for attempt in attempts:
        if attempt.question_id in seen:
            continue
        question = db.get(QuizQuestion, attempt.question_id)
        if question is not None:
            seen.add(question.id)
            found.append(question)
    return found


def _unsupported(question: QuizQuestion) -> str | None:
    support = question.support_text or ""
    answer = (question.answer or "").strip()
    tokens = [tok for tok in re.findall(r"\w+", answer.lower()) if len(tok) > 2]
    supported = answer.casefold() in support.casefold() or (tokens and all(tok in support.lower() for tok in tokens))
    if not supported:
        return f"question {question.id}: retrieved text does not support the answer"
    if question.qtype == "mcq" and question.choices:
        folded = [str(choice).casefold() for choice in question.choices]
        if len(folded) != len(set(folded)):
            return f"question {question.id}: more than one correct answer"
        present = [
            str(choice)
            for choice in question.choices
            if re.search(rf"\b{re.escape(str(choice))}\b", support, flags=re.IGNORECASE)
        ]
        if len(present) > 1:
            return f"question {question.id}: more than one choice is supported by the material"
    return None


def _flag(ctx: ToolContext, db: Session, questions: list[QuizQuestion]) -> list[str]:
    ctx.wrote = True
    reasons = []
    for question in questions:
        reason = _unsupported(question)
        if reason is None:
            continue
        question.status = "flagged"
        question.flag_reason = reason
        reasons.append(reason)
    db.flush()
    return reasons


def _write(ctx: ToolContext, db: Session, user_id: int, body: str, reasons: list[str], kind: str) -> None:
    ctx.wrote = True
    db.add(Critique(user_id=user_id, body=body, reasons=reasons, kind=kind))
    db.flush()


def _compose(progress: dict, mistakes: list, logs: list, notes: list[str]) -> tuple[str, list[str]]:
    accuracy = progress["accuracy"]
    accuracy_text = "no quizzes yet" if accuracy is None else f"{round(accuracy * 100)}% quiz accuracy"
    well = (
        f"You logged {len(logs)} completed pomodoros in this window. "
        f"Coverage is {round(progress['coverage'] * 100)}% and overall accuracy is {accuracy_text}."
    )
    weak_titles = [
        item["title"]
        for item in progress["per_topic"]
        if item["accuracy"] is not None and item["accuracy"] < 0.6
    ]
    if not weak_titles and mistakes:
        weak_titles = list(dict.fromkeys(item.topic_title for item in mistakes))[:3]
    weak = "Weak areas: " + (", ".join(weak_titles) if weak_titles else "none stand out from the scores.")
    gaps = progress["confidence_gaps"]
    if gaps:
        weak += " Confidence looks " + ", ".join(f"{gap['bias']} on {gap['title']}" for gap in gaps[:2]) + "."
    nxt = "Review mistake-notebook items due in 1, 3, and 7 days, then continue the nearest exam topic."
    reasons = [weak, *notes]
    body = f"What went well: {well}\nWhat is weak: {weak}\nNext steps: {nxt}"
    return body, reasons
