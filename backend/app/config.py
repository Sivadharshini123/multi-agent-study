"""Runtime settings. Environment variables win. A local .env is read outside tests."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _load_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    env: str
    database_url: str
    jwt_secret: str
    embedding_backend: str
    anthropic_api_key: str
    anthropic_model: str
    scheduler_enabled: bool
    allow_teacher_signup: bool
    cors_origins: list[str]
    subjects_config: Path
    materials_root: Path

    @property
    def testing(self) -> bool:
        return self.env == "test"


def _flag(name: str, default: str) -> bool:
    return os.getenv(name, default).strip().lower() not in {"0", "false", "no"}


@lru_cache
def get_settings() -> Settings:
    if os.getenv("ENV") != "test":
        _load_dotenv(repo_root() / ".env")
    root = repo_root()
    return Settings(
        env=os.getenv("ENV", "development"),
        database_url=os.getenv(
            "DATABASE_URL",
            "postgresql+psycopg://study:study@localhost:5432/study",
        ),
        jwt_secret=os.getenv("JWT_SECRET", "dev-only-change-me"),
        embedding_backend=os.getenv("EMBEDDING_BACKEND", "auto"),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5"),
        scheduler_enabled=_flag("SCHEDULER_ENABLED", "1"),
        allow_teacher_signup=_flag("ALLOW_TEACHER_SIGNUP", "1"),
        cors_origins=[
            item.strip()
            for item in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
            if item.strip()
        ],
        subjects_config=Path(os.getenv("SUBJECTS_CONFIG", str(root / "config" / "subjects.yaml"))),
        materials_root=Path(os.getenv("MATERIALS_ROOT", str(root / "materials"))),
    )


def clear_settings_cache() -> None:
    get_settings.cache_clear()
