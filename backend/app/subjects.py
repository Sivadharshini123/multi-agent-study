from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

import yaml

from app.config import get_settings


@dataclass(frozen=True)
class Subject:
    id: str
    name: str
    source_folder: str
    exam_date: date | None

    def folder(self) -> Path:
        return get_settings().materials_root / self.source_folder


def load_subjects() -> list[Subject]:
    path = get_settings().subjects_config
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    subjects: list[Subject] = []
    for entry in raw.get("subjects", []):
        exam = entry.get("exam_date") or None
        subjects.append(
            Subject(
                id=str(entry["id"]),
                name=str(entry["name"]),
                source_folder=str(entry["source_folder"]),
                exam_date=date.fromisoformat(exam) if isinstance(exam, str) else exam,
            )
        )
    return subjects


def subject_map() -> dict[str, Subject]:
    return {item.id: item for item in load_subjects()}


def require_subject(subject_id: str) -> Subject:
    found = subject_map().get(subject_id)
    if found is None:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail="Unknown subject")
    return found
