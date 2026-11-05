from __future__ import annotations

from datetime import date, datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.agents.coordinator import run_doubt, run_planner, run_quiz_generation, run_quiz_session
from app.config import get_settings
from app.database import get_db
from app.models import (
    Critique,
    Doubt,
    Mistake,
    PlanBlock,
    PomodoroLog,
    QuizAttempt,
    QuizQuestion,
    ReviewItem,
    StudyPlan,
    TimeSlot,
    Topic,
    User,
    UserExam,
)
from app.rag.ingest import ingest_subject
from app.reports import render_weekly_html, render_weekly_pdf, weekly_context
from app.schemas import (
    BlockAction,
    DoubtIn,
    LoginIn,
    PomodoroIn,
    QuizGenIn,
    QuizSubmitIn,
    ScheduleIn,
    SignupIn,
    TopicIn,
    TopicPatch,
)
from app.security import create_token, get_current_user, hash_password, require_teacher, user_by_username, verify_password
from app.services.mistakes import due_topic_ids
from app.services.progress import progress_snapshot
from app.subjects import load_subjects, require_subject

router = APIRouter()

_STATUSES = {"not_started", "learning", "revised", "mastered"}


def _user_out(user: User) -> dict:
    return {
        "id": user.id,
        "username": user.username,
        "name": user.name,
        "course": user.course,
        "role": user.role,
    }


def _owned_topic(db: Session, user: User, topic_id: int) -> Topic:
    topic = db.get(Topic, topic_id)
    if topic is None or topic.user_id != user.id:
        raise HTTPException(status_code=404, detail="Topic not found")
    return topic


def _plan_out(db: Session, user: User, day: date) -> dict:
    plan = db.scalar(select(StudyPlan).where(StudyPlan.user_id == user.id, StudyPlan.plan_date == day))
    if plan is None:
        return {"date": day.isoformat(), "blocks": []}
    blocks = db.scalars(select(PlanBlock).where(PlanBlock.plan_id == plan.id).order_by(PlanBlock.position))
    items = []
    for block in blocks:
        topic = db.get(Topic, block.topic_id)
        items.append(
            {
                "id": block.id,
                "subject_id": block.subject_id,
                "topic_id": block.topic_id,
                "title": topic.title if topic else "",
                "minutes": block.minutes,
                "status": block.status,
                "reason": block.reason,
            }
        )
    return {"date": day.isoformat(), "blocks": items}


@router.get("/health")
def health() -> dict:
    return {"ok": True}


@router.post("/auth/signup")
def signup(body: SignupIn, db: Session = Depends(get_db)) -> dict:
    if user_by_username(db, body.username):
        raise HTTPException(status_code=409, detail="That username is taken")
    role = "student"
    if body.role == "teacher" and get_settings().allow_teacher_signup:
        role = "teacher"
    user = User(
        username=body.username,
        password_hash=hash_password(body.password),
        name=body.name.strip(),
        course=body.course.strip(),
        role=role,
    )
    db.add(user)
    db.flush()
    return {"token": create_token(user), "user": _user_out(user)}


@router.post("/auth/login")
def login(body: LoginIn, db: Session = Depends(get_db)) -> dict:
    user = user_by_username(db, body.username)
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Sign in required")
    return {"token": create_token(user), "user": _user_out(user)}


@router.get("/auth/me")
def me(user: User = Depends(get_current_user)) -> dict:
    return _user_out(user)


@router.get("/subjects")
def subjects(user: User = Depends(get_current_user)) -> list[dict]:
    del user
    return [
        {
            "id": item.id,
            "name": item.name,
            "exam_date": item.exam_date.isoformat() if item.exam_date else None,
        }
        for item in load_subjects()
    ]


@router.get("/schedule")
def get_schedule(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    slots = db.scalars(select(TimeSlot).where(TimeSlot.user_id == user.id))
    exams = db.scalars(select(UserExam).where(UserExam.user_id == user.id))
    topics = db.scalars(select(Topic).where(Topic.user_id == user.id))
    return {
        "slots": [
            {"weekday": slot.weekday, "start_minute": slot.start_minute, "end_minute": slot.end_minute}
            for slot in slots
        ],
        "exams": [{"subject_id": exam.subject_id, "exam_date": exam.exam_date.isoformat()} for exam in exams],
        "topics": [
            {
                "id": topic.id,
                "subject_id": topic.subject_id,
                "title": topic.title,
                "estimated_minutes": topic.estimated_minutes,
                "status": topic.status,
                "difficult": topic.difficult,
                "confidence": topic.confidence,
            }
            for topic in topics
        ],
    }


@router.put("/schedule")
def put_schedule(body: ScheduleIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    for slot in body.slots:
        if slot.end_minute <= slot.start_minute:
            raise HTTPException(status_code=422, detail="A time slot must end after it starts")
    known = {item.id for item in load_subjects()}
    for exam in body.exams:
        if exam.subject_id not in known:
            raise HTTPException(status_code=404, detail="Unknown subject")
    db.execute(delete(TimeSlot).where(TimeSlot.user_id == user.id))
    for slot in body.slots:
        db.add(
            TimeSlot(
                user_id=user.id,
                weekday=slot.weekday,
                start_minute=slot.start_minute,
                end_minute=slot.end_minute,
            )
        )
    db.execute(delete(UserExam).where(UserExam.user_id == user.id))
    for exam in body.exams:
        db.add(UserExam(user_id=user.id, subject_id=exam.subject_id, exam_date=exam.exam_date))
    db.flush()
    run_planner(db, user.id, date.today(), keep_finished=True)
    return get_schedule(user, db)


@router.post("/topics")
def add_topic(body: TopicIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    require_subject(body.subject_id)
    topic = Topic(
        user_id=user.id,
        subject_id=body.subject_id,
        title=body.title.strip(),
        estimated_minutes=body.estimated_minutes,
    )
    db.add(topic)
    db.flush()
    run_planner(db, user.id, date.today(), keep_finished=True)
    return {"id": topic.id}


@router.patch("/topics/{topic_id}")
def patch_topic(
    topic_id: int,
    body: TopicPatch,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    topic = _owned_topic(db, user, topic_id)
    if body.status is not None:
        if body.status not in _STATUSES:
            raise HTTPException(status_code=422, detail="Unknown topic status")
        topic.status = body.status
    if body.difficult is not None:
        topic.difficult = body.difficult
    if body.confidence is not None:
        topic.confidence = body.confidence
    db.flush()
    if body.status in {"revised", "mastered"} or body.difficult:
        run_planner(db, user.id, date.today(), keep_finished=True)
    return {"id": topic.id, "status": topic.status, "difficult": topic.difficult}


@router.delete("/topics/{topic_id}")
def delete_topic(topic_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    topic = _owned_topic(db, user, topic_id)
    db.execute(delete(PlanBlock).where(PlanBlock.topic_id == topic.id))
    db.execute(update(Mistake).where(Mistake.topic_id == topic.id).values(topic_id=None))
    db.execute(update(QuizAttempt).where(QuizAttempt.topic_id == topic.id).values(topic_id=None))
    db.execute(update(PomodoroLog).where(PomodoroLog.topic_id == topic.id).values(topic_id=None))
    db.delete(topic)
    return {"ok": True}


@router.get("/plan")
def get_plan(
    day: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    target = day or date.today()
    existing = db.scalar(select(StudyPlan).where(StudyPlan.user_id == user.id, StudyPlan.plan_date == target))
    if existing is None:
        run_planner(db, user.id, target, keep_finished=target == date.today(), evening=target != date.today())
    return _plan_out(db, user, target)


@router.post("/plan/rebuild")
def rebuild_plan(
    day: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    target = day or date.today()
    run_planner(db, user.id, target, keep_finished=target == date.today(), evening=target != date.today())
    return _plan_out(db, user, target)


@router.post("/plan/blocks/{block_id}")
def act_on_block(
    block_id: int,
    body: BlockAction,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    block = db.get(PlanBlock, block_id)
    plan = db.get(StudyPlan, block.plan_id) if block else None
    if block is None or plan is None or plan.user_id != user.id:
        raise HTTPException(status_code=404, detail="Block not found")
    topic = _owned_topic(db, user, block.topic_id)
    if body.action == "done":
        block.status = "done"
        topic.completions += 1
        topic.status = "mastered" if topic.status == "revised" else "revised"
    elif body.action == "skipped":
        block.status = "skipped"
        if topic.status == "not_started":
            topic.status = "learning"
    elif body.action == "difficult":
        topic.difficult = True
        if topic.status == "not_started":
            topic.status = "learning"
    else:
        raise HTTPException(status_code=422, detail="Use done, skipped, or difficult")
    db.flush()
    run_planner(db, user.id, plan.plan_date, keep_finished=True)
    return _plan_out(db, user, plan.plan_date)


@router.post("/pomodoro")
def log_pomodoro(body: PomodoroIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    require_subject(body.subject_id)
    if body.minutes != 25:
        raise HTTPException(status_code=422, detail="A completed block is 25 minutes")
    topic = None
    if body.topic_id is not None:
        topic = _owned_topic(db, user, body.topic_id)
        if topic.subject_id != body.subject_id:
            raise HTTPException(status_code=422, detail="Topic is in a different subject")
        if topic.status == "not_started":
            topic.status = "learning"
    db.add(
        PomodoroLog(
            user_id=user.id,
            subject_id=body.subject_id,
            topic_id=topic.id if topic else None,
            minutes=25,
            completed_at=datetime.now(timezone.utc),
        )
    )
    return {"ok": True}


@router.post("/tutor/{subject_id}")
def ask_tutor(
    subject_id: str,
    body: DoubtIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    require_subject(subject_id)
    return run_doubt(db, user.id, subject_id, body.question, body.simple)


@router.get("/tutor/{subject_id}/history")
def doubt_history(
    subject_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    require_subject(subject_id)
    rows = db.scalars(
        select(Doubt)
        .where(Doubt.user_id == user.id, Doubt.subject_id == subject_id)
        .order_by(Doubt.created_at.desc())
    )
    return [
        {
            "id": row.id,
            "question": row.question,
            "answer": row.answer,
            "citations": row.citations,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.post("/quiz/generate")
def generate_quiz(body: QuizGenIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    topic = _owned_topic(db, user, body.topic_id)
    return run_quiz_generation(db, user.id, topic.subject_id, topic.title)


@router.get("/quiz")
def list_quiz(
    topic_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    topic = _owned_topic(db, user, topic_id)
    rows = db.scalars(
        select(QuizQuestion).where(
            QuizQuestion.subject_id == topic.subject_id,
            QuizQuestion.topic_title == topic.title,
            QuizQuestion.status == "approved",
        )
    )
    return [
        {
            "id": row.id,
            "qtype": row.qtype,
            "language": row.language,
            "prompt": row.prompt,
            "choices": row.choices,
        }
        for row in rows
    ]


@router.post("/quiz/submit")
def submit_quiz(body: QuizSubmitIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    topic = _owned_topic(db, user, body.topic_id)
    if not body.answers:
        raise HTTPException(status_code=422, detail="Add at least one answer")
    for item in body.answers:
        question = db.get(QuizQuestion, item.question_id)
        if question is None or question.status != "approved" or question.subject_id != topic.subject_id:
            raise HTTPException(status_code=404, detail="Question is not available")
    return run_quiz_session(
        db,
        user.id,
        {
            "topic_id": topic.id,
            "answers": [{"question_id": item.question_id, "answer": item.answer} for item in body.answers],
            "confidence": body.confidence,
            "today": date.today(),
            "kind": "session",
        },
    )


@router.get("/mistakes")
def mistakes(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Mistake).where(Mistake.user_id == user.id).order_by(Mistake.created_at.desc()))
    items = []
    for row in rows:
        reviews = db.scalars(select(ReviewItem).where(ReviewItem.mistake_id == row.id).order_by(ReviewItem.due_on))
        items.append(
            {
                "id": row.id,
                "subject_id": row.subject_id,
                "topic_title": row.topic_title,
                "prompt": row.prompt,
                "student_answer": row.student_answer,
                "correct_answer": row.correct_answer,
                "reasoning": row.reasoning,
                "due_on": [review.due_on.isoformat() for review in reviews],
            }
        )
    return items


@router.get("/reviews/due")
def reviews_due(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return {"topic_ids": sorted(due_topic_ids(db, user.id, date.today()))}


@router.get("/progress")
def progress(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    return progress_snapshot(db, user.id)


@router.get("/critiques")
def critiques(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[dict]:
    rows = db.scalars(select(Critique).where(Critique.user_id == user.id).order_by(Critique.created_at.desc()))
    return [
        {"id": row.id, "kind": row.kind, "body": row.body, "reasons": row.reasons, "created_at": row.created_at.isoformat()}
        for row in rows
    ]


@router.get("/reports/weekly.pdf")
def weekly_pdf(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    html = render_weekly_html(weekly_context(db, user, date.today()))
    try:
        pdf = render_weekly_pdf(html)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return Response(
        content=pdf,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=weekly-report.pdf"},
    )


@router.get("/reports/weekly.html")
def weekly_html(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Response:
    html = render_weekly_html(weekly_context(db, user, date.today()))
    return Response(content=html, media_type="text/html")


@router.get("/review")
def review_queue(
    status: str = "pending",
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> list[dict]:
    del teacher
    if status not in {"pending", "flagged", "approved", "rejected"}:
        raise HTTPException(status_code=422, detail="Unknown review status")
    rows = db.scalars(select(QuizQuestion).where(QuizQuestion.status == status).order_by(QuizQuestion.created_at))
    return [
        {
            "id": row.id,
            "subject_id": row.subject_id,
            "topic_title": row.topic_title,
            "qtype": row.qtype,
            "prompt": row.prompt,
            "choices": row.choices,
            "answer": row.answer,
            "reasoning": row.reasoning,
            "citations": row.citations,
            "flag_reason": row.flag_reason,
            "status": row.status,
        }
        for row in rows
    ]


@router.post("/review/{question_id}")
def review_question(
    question_id: int,
    body: BlockAction,
    teacher: User = Depends(require_teacher),
    db: Session = Depends(get_db),
) -> dict:
    del teacher
    question = db.get(QuizQuestion, question_id)
    if question is None:
        raise HTTPException(status_code=404, detail="Question not found")
    if body.action == "approve":
        question.status = "approved"
        question.flag_reason = None
    elif body.action == "reject":
        question.status = "rejected"
    else:
        raise HTTPException(status_code=422, detail="Use approve or reject")
    return {"id": question.id, "status": question.status}


@router.post("/materials/ingest")
def ingest(teacher: User = Depends(require_teacher), db: Session = Depends(get_db)) -> dict:
    del teacher
    reports = []
    for subject in load_subjects():
        reports.append(ingest_subject(db, subject.id, subject.folder()))
    return {"subjects": reports}
