"""Evening planner and weekly critic. A worker queue can replace this later."""

from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import select

from app.agents.coordinator import run_planner, run_weekly_critic
from app.database import SessionLocal
from app.models import User

logger = logging.getLogger("study.jobs")


def run_evening(today: date | None = None) -> int:
    day = (today or date.today()) + timedelta(days=1)
    return _each(lambda db, user: run_planner(db, user.id, day, keep_finished=False, evening=True))


def run_weekly(today: date | None = None) -> int:
    day = today or date.today()
    return _each(lambda db, user: run_weekly_critic(db, user.id, day))


def _each(action) -> int:
    db = SessionLocal()
    count = 0
    try:
        students = list(db.scalars(select(User).where(User.role == "student")))
        for user in students:
            action(db, user)
            count += 1
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("scheduled agent run failed")
        raise
    finally:
        db.close()
    return count
