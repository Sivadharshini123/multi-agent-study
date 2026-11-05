"""FastAPI entrypoint."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from apscheduler.schedulers.background import BackgroundScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import router
from app.config import get_settings
from app.database import SessionLocal, init_db
from app.jobs import run_evening, run_weekly
from app.rag.ingest import ingest_subject
from app.subjects import load_subjects

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("study")


@asynccontextmanager
async def lifespan(app: FastAPI):
    del app
    init_db()
    db = SessionLocal()
    try:
        for subject in load_subjects():
            report = ingest_subject(db, subject.id, subject.folder())
            logger.info("ingested %s files=%s", subject.id, len(report["files"]))
        db.commit()
    finally:
        db.close()
    settings = get_settings()
    scheduler = None
    if settings.scheduler_enabled and not settings.testing:
        scheduler = BackgroundScheduler()
        scheduler.add_job(run_evening, "cron", hour=21, minute=0, id="evening", replace_existing=True)
        scheduler.add_job(run_weekly, "cron", day_of_week="sun", hour=20, minute=5, id="weekly", replace_existing=True)
        scheduler.start()
    yield
    if scheduler is not None:
        scheduler.shutdown(wait=False)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="Study planner", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
