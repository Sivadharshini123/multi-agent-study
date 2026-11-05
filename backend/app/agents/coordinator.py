"""Runs agents in a fixed order. This is not an open loop."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.agents import critic, planner, quiz_agent, tutor
from app.agents.context import execute
from app.agents.registry import RUN_ORDER

logger = logging.getLogger("study.coordinator")

_HANDLERS = {
    "tutor": {"doubt": tutor.answer},
    "quiz": {
        "quiz_generate": quiz_agent.generate,
        "quiz_grade": quiz_agent.grade_session,
    },
    "planner": {
        "topic_finished_or_skipped": planner.rebuild,
        "evening": planner.rebuild,
    },
    "critic": {
        "quiz_session_done": critic.review,
        "weekly": critic.review,
    },
}


def _run(event: str, session: Session, user_id: int, payload: dict):
    sequence = RUN_ORDER[event]
    agent = sequence[0]
    logger.info("coordinator event=%s agent=%s user=%s", event, agent, user_id)

    def factory(ctx):
        return _HANDLERS[agent][event](ctx, payload)

    return execute(agent, session, user_id, factory)


def run_doubt(session: Session, user_id: int, subject_id: str, question: str, simple: bool = False) -> dict:
    return _run("doubt", session, user_id, {"subject_id": subject_id, "question": question, "simple": simple})


def run_quiz_generation(session: Session, user_id: int, subject_id: str, topic_title: str) -> dict:
    return _run(
        "quiz_generate",
        session,
        user_id,
        {"subject_id": subject_id, "topic_title": topic_title},
    )


def run_quiz_session(session: Session, user_id: int, payload: dict) -> dict:
    graded = _run("quiz_grade", session, user_id, payload)
    critique = _run("quiz_session_done", session, user_id, payload)
    return {"results": graded["results"], "critique": critique}


def run_planner(session: Session, user_id: int, day, *, keep_finished: bool, evening: bool = False) -> dict:
    event = "evening" if evening else "topic_finished_or_skipped"
    return _run(event, session, user_id, {"day": day, "keep_finished": keep_finished})


def run_weekly_critic(session: Session, user_id: int, today) -> dict:
    return _run("weekly", session, user_id, {"today": today, "kind": "weekly"})
