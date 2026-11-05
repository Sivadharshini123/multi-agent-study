from datetime import date, timedelta

import pytest
from sqlalchemy import select

from app.agents.context import StepCapExceeded, execute
from app.agents.coordinator import run_doubt, run_planner
from app.agents.registry import CRITIC_TOOLS, RUN_ORDER
from app.models import DecisionLog, Topic, User
from app.rag.ingest import ingest_subject
from app.security import hash_password
from app.services.grounding import NOT_FOUND
from app.subjects import subject_map


def test_critic_cannot_update_the_plan():
    assert "update_plan" not in CRITIC_TOOLS

    def factory(ctx):
        ctx.call("update_plan", lambda: None)

    with pytest.raises(PermissionError):
        execute("critic", None, None, factory)


def test_step_cap_stops_the_agent():
    def factory(ctx):
        ctx.call("search_subject", lambda: "one")
        ctx.call("explain_simply", lambda: "two")

    with pytest.raises(StepCapExceeded):
        execute("tutor", None, None, factory, max_steps=1)


def test_run_order_is_fixed():
    assert RUN_ORDER["doubt"] == ("tutor",)
    assert RUN_ORDER["quiz_session_done"] == ("critic",)
    assert RUN_ORDER["evening"] == ("planner",)
    assert RUN_ORDER["weekly"] == ("critic",)


def test_tutor_cites_material_or_says_not_found(db):
    ingest_subject(db, "physics", subject_map()["physics"].folder())
    user = User(username="ada", password_hash=hash_password("password1"), name="Ada", course="12")
    db.add(user)
    db.commit()
    found = run_doubt(db, user.id, "physics", "What is V = IR?", simple=True)
    assert "Source:" in found["answer"]
    assert "p. 5" in found["answer"]
    assert len(found["answer"]) < 500
    missing = run_doubt(db, user.id, "physics", "xylophone orchestra rehearsal")
    assert missing["answer"] == NOT_FOUND
    again = run_doubt(db, user.id, "physics", "What is V = IR?", simple=True)
    assert again["cached"] is True


def test_tamil_question_keeps_english_terms_in_brackets(db):
    ingest_subject(db, "tamil", subject_map()["tamil"].folder())
    user = User(username="kala", password_hash=hash_password("password1"), name="Kala", course="12")
    db.add(user)
    db.commit()
    result = run_doubt(db, user.id, "tamil", "பெயர்ச்சொல் என்றால் என்ன?")
    assert "பெயர்ச்சொல்" in result["answer"]
    assert "(noun)" in result["answer"]
    assert "Source:" in result["answer"]


def test_planner_logs_a_reason_for_each_block(db):
    user = User(username="lin", password_hash=hash_password("password1"), name="Lin", course="BSc")
    db.add(user)
    db.flush()
    db.add(Topic(user_id=user.id, subject_id="os", title="Processes", estimated_minutes=50))
    db.add(Topic(user_id=user.id, subject_id="dbms", title="Queries", estimated_minutes=50, difficult=True))
    db.commit()
    today = date.today()
    run_planner(db, user.id, today, keep_finished=False)
    db.commit()
    logs = list(db.scalars(select(DecisionLog)))
    assert logs
    assert all(row.reason for row in logs)
    assert today <= date.today() + timedelta(days=0)
