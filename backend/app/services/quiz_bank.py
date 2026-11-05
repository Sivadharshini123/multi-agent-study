"""Questions are built only from retrieved chunks and saved as pending."""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.models import QuizQuestion
from app.rag.search import Hit

_STOP = {
    "that", "with", "from", "this", "have", "were", "been", "their", "about", "which",
    "when", "where", "into", "than", "then", "them", "your", "uses", "used", "does",
}
_UNIX_PATTERNS = (
    (re.compile(r"echo\s+hello\s+\|\s+wc\s+-w", re.I), "echo hello | wc -w"),
    (re.compile(r"\bls\s+-l\b", re.I), "ls -l"),
    (re.compile(r"\bpwd\b", re.I), "pwd"),
)


def _sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.])\s+", text.strip())
    return [part.strip() for part in parts if len(part.split()) >= 6]


def _keyword(sentence: str, reserved: set[str]) -> str | None:
    words = re.findall(r"[A-Za-z][A-Za-z0-9^+-]{4,}", sentence)
    for word in sorted(words, key=len, reverse=True):
        if word.lower() not in _STOP and word.lower() not in reserved:
            return word
    return None


def _fixture(text: str) -> str | None:
    lines = []
    for line in text.splitlines():
        if re.match(r"(?is)^\s*(create\s+table|insert\s+into)\b", line.strip()):
            lines.append(line.strip().rstrip(";"))
    if not lines:
        return None
    return ";\n".join(lines) + ";"


def draft_questions(hits: list[Hit], limit: int = 3) -> list[dict]:
    if not hits:
        return []
    blob = "\n".join(hit.text for hit in hits)
    citations = [
        {"chapter": hit.chapter, "page": hit.page, "source": hit.source_path}
        for hit in hits[:3]
    ]
    questions: list[dict] = []
    used: set[str] = set()

    for line in blob.splitlines():
        stripped = line.strip()
        if re.match(r"(?is)^select\b", stripped):
            questions.append(
                {
                    "qtype": "code",
                    "language": "sql",
                    "prompt": "Enter the SELECT statement written in the notes.",
                    "choices": None,
                    "answer": stripped.rstrip(";"),
                    "reasoning": f"The material includes: {stripped}",
                    "support_text": blob[:4000],
                    "citations": citations,
                    "fixture_sql": _fixture(blob),
                }
            )
            break
    for pattern, command in _UNIX_PATTERNS:
        if pattern.search(blob):
            questions.append(
                {
                    "qtype": "code",
                    "language": "unix",
                    "prompt": f"Enter the command from the notes that matches: {command}",
                    "choices": None,
                    "answer": command,
                    "reasoning": f"The material includes: {command}",
                    "support_text": blob[:4000],
                    "citations": citations,
                    "fixture_sql": None,
                }
            )
            break

    pool: list[str] = []
    for sentence in _sentences(blob):
        word = _keyword(sentence, set())
        if word:
            pool.append(word)
    for sentence in _sentences(blob):
        if len(questions) >= limit:
            break
        word = _keyword(sentence, used)
        if word is None:
            continue
        used.add(word.lower())
        distractors = [item for item in pool if item.lower() != word.lower()]
        extras = ["momentum", "metaphor", "latency", "nucleus"]
        choices = [word]
        for item in distractors + extras:
            if item not in choices:
                choices.append(item)
            if len(choices) == 4:
                break
        stem = re.sub(rf"\b{re.escape(word)}\b", "______", sentence, count=1)
        questions.append(
            {
                "qtype": "mcq",
                "language": None,
                "prompt": stem,
                "choices": choices,
                "answer": word,
                "reasoning": f"The material says: {sentence}",
                "support_text": sentence,
                "citations": citations,
                "fixture_sql": None,
            }
        )
    return questions[:limit]


def save_pending(db: Session, subject_id: str, topic_title: str, drafts: list[dict]) -> list[QuizQuestion]:
    saved: list[QuizQuestion] = []
    for draft in drafts:
        if draft["answer"].casefold() not in draft["support_text"].casefold():
            tokens = [tok for tok in re.findall(r"\w+", draft["answer"].lower()) if len(tok) > 2]
            support = draft["support_text"].lower()
            if tokens and not all(tok in support for tok in tokens):
                continue
        row = QuizQuestion(
            subject_id=subject_id,
            topic_title=topic_title.strip(),
            qtype=draft["qtype"],
            language=draft.get("language"),
            prompt=draft["prompt"],
            choices=draft.get("choices"),
            answer=draft["answer"],
            reasoning=draft["reasoning"],
            support_text=draft["support_text"],
            citations=draft["citations"],
            fixture_sql=draft.get("fixture_sql"),
            status="pending",
        )
        db.add(row)
        saved.append(row)
    db.flush()
    return saved
