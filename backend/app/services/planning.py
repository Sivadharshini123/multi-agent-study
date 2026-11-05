"""Deterministic daily plans. The planner agent calls this; it does not invent times."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass
class TopicView:
    id: int
    subject_id: str
    title: str
    estimated_minutes: int
    status: str
    difficult: bool
    accuracy: float | None
    review_due: bool
    exam_date: date | None


@dataclass
class BlockDraft:
    subject_id: str
    topic_id: int
    title: str
    minutes: int
    reason: str


def priority(topic: TopicView, today: date) -> tuple[float, str]:
    if topic.status == "mastered":
        return 0.0, "already mastered"
    score = 1.0
    reasons: list[str] = []
    if topic.difficult:
        score += 2.0
        reasons.append("marked difficult")
    if topic.accuracy is not None and topic.accuracy < 0.6:
        score += 1.5
        reasons.append("low quiz accuracy")
    if topic.review_due:
        score += 1.5
        reasons.append("mistake review due")
    if topic.exam_date is not None:
        days = (topic.exam_date - today).days
        if days <= 7:
            score += 3.0
            reasons.append("exam is near")
        elif days <= 21:
            score += 1.0
            reasons.append("exam is approaching")
    if topic.status == "not_started":
        score += 0.3
        reasons.append("not started")
    if not reasons:
        reasons.append("keeps subjects rotating")
    return score, "; ".join(reasons)


def build_blocks(topics: list[TopicView], budget_minutes: int, today: date) -> list[BlockDraft]:
    active = [topic for topic in topics if topic.status != "mastered" and topic.estimated_minutes > 0]
    if budget_minutes < 10 or not active:
        return []
    ranked = sorted(active, key=lambda topic: priority(topic, today)[0], reverse=True)
    queues: dict[str, list[TopicView]] = {}
    for topic in ranked:
        copy = TopicView(**{**topic.__dict__})
        queues.setdefault(copy.subject_id, []).append(copy)
    order = sorted(queues, key=lambda subject: priority(queues[subject][0], today)[0], reverse=True)
    remaining = budget_minutes
    blocks: list[BlockDraft] = []
    guard = 0
    while remaining >= 10 and guard < 80:
        guard += 1
        moved = False
        for subject in order:
            queue = [item for item in queues[subject] if item.estimated_minutes > 0]
            queues[subject] = queue
            if not queue or remaining < 10:
                continue
            topic = queue[0]
            score, reason = priority(topic, today)
            slice_len = 50 if score >= 3 else 25
            slice_len = min(slice_len, remaining, topic.estimated_minutes)
            if slice_len < 10:
                queue.pop(0)
                continue
            blocks.append(
                BlockDraft(
                    subject_id=topic.subject_id,
                    topic_id=topic.id,
                    title=topic.title,
                    minutes=slice_len,
                    reason=reason,
                )
            )
            topic.estimated_minutes -= slice_len
            remaining -= slice_len
            moved = True
            if topic.estimated_minutes <= 0:
                queue.pop(0)
            elif len(queue) > 1:
                queue.append(queue.pop(0))
        if not moved:
            break
    return blocks
