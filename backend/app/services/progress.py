from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Mistake, PomodoroLog, QuizAttempt, QuizQuestion, Topic


def progress_snapshot(db: Session, user_id: int) -> dict:
    topics = list(db.scalars(select(Topic).where(Topic.user_id == user_id)))
    attempts = list(db.scalars(select(QuizAttempt).where(QuizAttempt.user_id == user_id)))
    mistakes = list(db.scalars(select(Mistake).where(Mistake.user_id == user_id)))
    logs = list(db.scalars(select(PomodoroLog).where(PomodoroLog.user_id == user_id)))

    done = [topic for topic in topics if topic.status in {"revised", "mastered"}]
    coverage = (len(done) / len(topics)) if topics else 0.0
    accuracy = (sum(item.correct for item in attempts) / len(attempts)) if attempts else None

    missed_titles = {item.topic_title.casefold() for item in mistakes}
    missed_attempts = []
    for attempt in attempts:
        question = db.get(QuizQuestion, attempt.question_id)
        if question and question.topic_title.casefold() in missed_titles:
            missed_attempts.append(attempt)
    missed_accuracy = (
        sum(item.correct for item in missed_attempts) / len(missed_attempts) if missed_attempts else None
    )

    time_map: dict[int, int] = {}
    for log in logs:
        if log.topic_id is not None:
            time_map[log.topic_id] = time_map.get(log.topic_id, 0) + log.minutes

    by_topic: dict[int, list[bool]] = {}
    for attempt in attempts:
        if attempt.topic_id is not None:
            by_topic.setdefault(attempt.topic_id, []).append(bool(attempt.correct))

    gaps = []
    per_topic = []
    for topic in topics:
        flags = by_topic.get(topic.id, [])
        topic_accuracy = (sum(flags) / len(flags)) if flags else None
        bias = "unknown"
        if topic.confidence is not None and topic_accuracy is not None:
            if topic.confidence >= 4 and topic_accuracy < 0.5:
                bias = "overestimated"
            elif topic.confidence <= 2 and topic_accuracy > 0.8:
                bias = "underestimated"
            else:
                bias = "aligned"
        if bias in {"overestimated", "underestimated"}:
            gaps.append(
                {
                    "topic_id": topic.id,
                    "title": topic.title,
                    "bias": bias,
                    "confidence": topic.confidence,
                    "accuracy": topic_accuracy,
                }
            )
        per_topic.append(
            {
                "id": topic.id,
                "subject_id": topic.subject_id,
                "title": topic.title,
                "status": topic.status,
                "difficult": topic.difficult,
                "estimated_minutes": topic.estimated_minutes,
                "minutes_spent": time_map.get(topic.id, 0),
                "accuracy": topic_accuracy,
                "confidence": topic.confidence,
                "bias": bias,
            }
        )

    return {
        "coverage": coverage,
        "topics_total": len(topics),
        "topics_done": len(done),
        "accuracy": accuracy,
        "missed_topic_accuracy": missed_accuracy,
        "time_by_topic": [
            {
                "topic_id": topic.id,
                "title": topic.title,
                "subject_id": topic.subject_id,
                "minutes": time_map.get(topic.id, 0),
            }
            for topic in topics
        ],
        "confidence_gaps": gaps,
        "per_topic": per_topic,
        "pomodoro_count": len(logs),
        "mistake_count": len(mistakes),
    }


def minutes_by_subject(db: Session, user_id: int) -> dict[str, int]:
    rows = db.execute(
        select(PomodoroLog.subject_id, func.sum(PomodoroLog.minutes))
        .where(PomodoroLog.user_id == user_id)
        .group_by(PomodoroLog.subject_id)
    )
    return {subject: int(minutes or 0) for subject, minutes in rows}
