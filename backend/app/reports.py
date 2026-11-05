"""Weekly PDF built from an HTML template."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Critique, User
from app.services.progress import progress_snapshot


def weekly_context(db: Session, user: User, today: date) -> dict:
    progress = progress_snapshot(db, user.id)
    start = today - timedelta(days=6)
    critiques = [
        row
        for row in db.scalars(select(Critique).where(Critique.user_id == user.id).order_by(Critique.created_at.desc()))
        if row.created_at.date() >= start
    ]
    accuracy = "n/a" if progress["accuracy"] is None else f"{round(progress['accuracy'] * 100)}%"
    missed = "n/a" if progress["missed_topic_accuracy"] is None else f"{round(progress['missed_topic_accuracy'] * 100)}%"
    return {
        "name": user.name,
        "course": user.course,
        "start": start.isoformat(),
        "end": today.isoformat(),
        "coverage": round(progress["coverage"] * 100),
        "topics_done": progress["topics_done"],
        "topics_total": progress["topics_total"],
        "accuracy": accuracy,
        "missed": missed,
        "pomodoros": progress["pomodoro_count"],
        "mistakes": progress["mistake_count"],
        "topics": progress["per_topic"],
        "critiques": [
            {"kind": item.kind, "body": item.body, "created_at": item.created_at.date().isoformat()}
            for item in critiques
        ],
    }


def render_weekly_html(context: dict) -> str:
    folder = Path(__file__).resolve().parent / "templates"
    env = Environment(loader=FileSystemLoader(folder), autoescape=select_autoescape(["html"]))
    return env.get_template("weekly.html").render(**context)


def render_weekly_pdf(html: str) -> bytes:
    try:
        from weasyprint import HTML
    except Exception as exc:
        raise RuntimeError("WeasyPrint is not installed in this environment") from exc
    return HTML(string=html).write_pdf()
