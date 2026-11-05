"""Rebuild a day's plan. Every block stores a short reason."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agents.context import ToolContext
from app.models import DecisionLog, StudyPlan
from app.services.plans import budget_minutes, finished_topic_ids, save_blocks, topic_views
from app.services.planning import build_blocks
from app.services.progress import progress_snapshot


def rebuild(ctx: ToolContext, payload: dict) -> dict:
    db: Session = ctx.session
    user_id = ctx.user_id
    day = payload["day"]
    keep = bool(payload.get("keep_finished"))
    ctx.call("get_progress", progress_snapshot, db, user_id, detail=str(day))
    plan_id, decisions = ctx.call(
        "update_plan",
        _update,
        ctx,
        db,
        user_id,
        day,
        keep,
        detail=str(day),
    )
    ctx.call("log_decision", _log, db, user_id, plan_id, ctx.run_id, decisions, detail=f"{len(decisions)} decisions")
    return {"plan_id": plan_id, "blocks": len(decisions)}


def _update(ctx: ToolContext, db: Session, user_id: int, day, keep: bool):
    ctx.wrote = True
    existing = db.scalar(select(StudyPlan).where(StudyPlan.user_id == user_id, StudyPlan.plan_date == day))
    hidden = finished_topic_ids(db, existing) if keep else set()
    views = topic_views(db, user_id, day, skip_ids=hidden)
    drafts = build_blocks(views, budget_minutes(db, user_id, day), day)
    plan, saved = save_blocks(db, user_id, day, drafts, keep_finished=keep)
    if saved:
        decisions = [(f"Schedule {item.minutes} min on {item.title}", item.reason) for item in saved]
    else:
        decisions = [("No new blocks", "no open topics fit the free time")]
    return plan.id, decisions


def _log(db: Session, user_id: int, plan_id: int, run_id: str, decisions: list[tuple[str, str]]) -> None:
    for summary, reason in decisions:
        db.add(DecisionLog(user_id=user_id, plan_id=plan_id, run_id=run_id, summary=summary, reason=reason))
    db.flush()
