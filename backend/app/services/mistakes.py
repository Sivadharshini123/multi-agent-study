from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Mistake, QuizAttempt, QuizQuestion, ReviewItem, Topic


def record_mistake(
    db: Session,
    user_id: int,
    question: QuizQuestion,
    student_answer: str,
    topic_id: int | None,
    today: date,
) -> Mistake:
    mistake = Mistake(
        user_id=user_id,
        question_id=question.id,
        subject_id=question.subject_id,
        topic_title=question.topic_title,
        topic_id=topic_id,
        prompt=question.prompt,
        student_answer=student_answer,
        correct_answer=question.answer,
        reasoning=question.reasoning,
    )
    db.add(mistake)
    db.flush()
    for offset in (1, 3, 7):
        db.add(
            ReviewItem(
                user_id=user_id,
                mistake_id=mistake.id,
                due_on=today + timedelta(days=offset),
            )
        )
    return mistake


def due_topic_ids(db: Session, user_id: int, day: date) -> set[int]:
    rows = db.scalars(
        select(ReviewItem).where(
            ReviewItem.user_id == user_id,
            ReviewItem.done.is_(False),
            ReviewItem.due_on <= day,
        )
    )
    ids: set[int] = set()
    for review in rows:
        mistake = db.get(Mistake, review.mistake_id)
        if mistake and mistake.topic_id is not None:
            ids.add(mistake.topic_id)
    return ids


def topic_accuracy(db: Session, user_id: int) -> dict[int, float]:
    attempts = list(db.scalars(select(QuizAttempt).where(QuizAttempt.user_id == user_id)))
    buckets: dict[int, list[bool]] = {}
    for attempt in attempts:
        if attempt.topic_id is None:
            continue
        buckets.setdefault(attempt.topic_id, []).append(attempt.correct)
    return {topic_id: sum(flags) / len(flags) for topic_id, flags in buckets.items() if flags}


def store_confidence(db: Session, topic: Topic | None, confidence: int | None) -> None:
    if topic is not None and confidence is not None:
        topic.confidence = confidence
