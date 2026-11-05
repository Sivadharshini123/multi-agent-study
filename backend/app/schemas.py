from __future__ import annotations

from datetime import date

from pydantic import BaseModel, Field


class SignupIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[A-Za-z0-9_]+$")
    password: str = Field(min_length=8, max_length=128)
    name: str = Field(min_length=1, max_length=80)
    course: str = Field(min_length=1, max_length=80)
    role: str = "student"


class LoginIn(BaseModel):
    username: str
    password: str


class SlotIn(BaseModel):
    weekday: int = Field(ge=0, le=6)
    start_minute: int = Field(ge=0, le=1440)
    end_minute: int = Field(ge=0, le=1440)


class ExamIn(BaseModel):
    subject_id: str
    exam_date: date


class ScheduleIn(BaseModel):
    slots: list[SlotIn]
    exams: list[ExamIn]


class TopicIn(BaseModel):
    subject_id: str
    title: str = Field(min_length=1, max_length=200)
    estimated_minutes: int = Field(ge=10, le=600)


class TopicPatch(BaseModel):
    status: str | None = None
    difficult: bool | None = None
    confidence: int | None = Field(default=None, ge=1, le=5)


class BlockAction(BaseModel):
    action: str


class PomodoroIn(BaseModel):
    subject_id: str
    topic_id: int | None = None
    minutes: int = 25


class DoubtIn(BaseModel):
    question: str = Field(min_length=1, max_length=2000)
    simple: bool = False


class QuizGenIn(BaseModel):
    topic_id: int


class AnswerIn(BaseModel):
    question_id: int
    answer: str = Field(max_length=2000)


class QuizSubmitIn(BaseModel):
    topic_id: int
    answers: list[AnswerIn]
    confidence: int | None = Field(default=None, ge=1, le=5)
