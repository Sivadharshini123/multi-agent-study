import os

os.environ["ENV"] = "test"
os.environ["DATABASE_URL"] = "sqlite://"
os.environ["JWT_SECRET"] = "test-secret"
os.environ["EMBEDDING_BACKEND"] = "hash"
os.environ["SCHEDULER_ENABLED"] = "0"
os.environ["ANTHROPIC_API_KEY"] = ""
os.environ["ALLOW_TEACHER_SIGNUP"] = "1"

import pytest

from app.config import clear_settings_cache
from app.database import SessionLocal, init_db, reset_engine
from app.rag.embeddings import reset_embedder


@pytest.fixture(autouse=True)
def fresh_db():
    clear_settings_cache()
    reset_engine()
    reset_embedder()
    init_db()
    yield
    reset_engine()
    clear_settings_cache()


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
