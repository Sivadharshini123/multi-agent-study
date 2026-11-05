"""Load planner state and replace plan blocks. The planner agent is the only writer."""

from __future__ import annotations

from datetime import date

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import PlanBlock, PomodoroLog, StudyPlan, TimeSlot, Topic, UserExam
from app.services.mistakes import due_topic_ids, topic_accuracy
from app.services.planning import BlockDraft, TopicView, build_blocks
from app.subjects import subject_map


def budget_minutes(db: Session, user_id: int, day: date) -> int:
    slots = db.scalars(select(TimeSlot).where(TimeSlot.user_id == user_id, TimeSlot.weekday == day.weekday()))
    total = sum(max(0, slot.end_minute - slot.start_minute) for slot in slots)
    return total or 120


def topic_views(db: Session, user_id: int, day: date, *, skip_ids: set[int] | None = None) -> list[TopicView]:
    topics = list(db.scalars(select(Topic).where(Topic.user_id == user_id)))
    accuracy = topic_accuracy(db, user_id)
    due = due_topic_ids(db, user_id, day)
    exams = {
        row.subject_id: row.exam_date
        for row in db.scalars(select(UserExam).where(UserExam.user_id == user_id))
    }
    config_exams = {item.id: item.exam_date for item in subject_map().values()}
    spent = _spent_minutes(db, user_id, day)
    hidden = skip_ids or set()
    views: list[TopicView] = []
    for topic in topics:
        if topic.id in hidden:
            continue
        remaining = max(0, topic.estimated_minutes - spent.get(topic.id, 0))
        views.append(
            TopicView(
                id=topic.id,
                subject_id=topic.subject_id,
                title=topic.title,
                estimated_minutes=remaining if topic.status != "mastered" else 0,
                status=topic.status,
                difficult=topic.difficult,
                accuracy=accuracy.get(topic.id),
                review_due=topic.id in due,
                exam_date=exams.get(topic.subject_id) or config_exams.get(topic.subject_id),
            )
        )
    return views


def _spent_minutes(db: Session, user_id: int, day: date) -> dict[int, int]:
    logs = db.scalars(select(PomodoroLog).where(PomodoroLog.user_id == user_id))
    spent: dict[int, int] = {}
    for log in logs:
        if log.topic_id is None or log.completed_at.date() != day:
            continue
        spent[log.topic_id] = spent.get(log.topic_id, 0) + log.minutes
    return spent


def finished_topic_ids(db: Session, plan: StudyPlan | None) -> set[int]:
    if plan is None:
        return set()
    blocks = db.scalars(select(PlanBlock).where(PlanBlock.plan_id == plan.id, PlanBlock.status == "done"))
    return {block.topic_id for block in blocks}


def save_blocks(
    db: Session,
    user_id: int,
    day: date,
    drafts: list[BlockDraft],
    *,
    keep_finished: bool,
) -> tuple[StudyPlan, list[BlockDraft]]:
    plan = db.scalar(select(StudyPlan).where(StudyPlan.user_id == user_id, StudyPlan.plan_date == day))
    if plan is None:
        plan = StudyPlan(user_id=user_id, plan_date=day)
        db.add(plan)
        db.flush()
    if keep_finished:
        db.execute(delete(PlanBlock).where(PlanBlock.plan_id == plan.id, PlanBlock.status == "planned"))
        position = db.scalar(
            select(PlanBlock.position)
            .where(PlanBlock.plan_id == plan.id)
            .order_by(PlanBlock.position.desc())
            .limit(1)
        )
        next_pos = 0 if position is None else int(position) + 1
    else:
        db.execute(delete(PlanBlock).where(PlanBlock.plan_id == plan.id))
        next_pos = 0
    for offset, draft in enumerate(drafts):
        db.add(
            PlanBlock(
                plan_id=plan.id,
                subject_id=draft.subject_id,
                topic_id=draft.topic_id,
                minutes=draft.minutes,
                position=next_pos + offset,
                status="planned",
                reason=draft.reason,
            )
        )
    db.flush()
    return plan, drafts
