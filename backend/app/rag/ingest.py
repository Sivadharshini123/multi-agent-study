"""Read PDFs, slides, and notes into one collection per subject."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from sqlalchemy import delete, select, text
from sqlalchemy.orm import Session

from app.models import Chunk, EmbeddingCache, IngestIssue
from app.rag.chunking import chunk_words, words_from_pages
from app.rag.embeddings import embed_texts, model_key
from app.rag.tamil_check import check_extracted_text, page_is_unusable

logger = logging.getLogger("study.ingest")
_SUFFIXES = {".pdf", ".txt", ".md", ".pptx"}


def file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def extract_pages(path: Path) -> list[tuple[int, str]]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        import fitz

        doc = fitz.open(path)
        try:
            return [(index, page.get_text()) for index, page in enumerate(doc, start=1)]
        finally:
            doc.close()
    if suffix == ".pptx":
        from pptx import Presentation

        deck = Presentation(str(path))
        pages: list[tuple[int, str]] = []
        for index, slide in enumerate(deck.slides, start=1):
            parts = []
            for shape in slide.shapes:
                if hasattr(shape, "text") and shape.text:
                    parts.append(shape.text)
            pages.append((index, "\n".join(parts)))
        return pages
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        logger.warning("Encoding issue in %s: %s", path, exc)
        text = raw.decode("utf-8", errors="replace")
    return [(1, text)]


def _cache_get(db: Session, file_hash: str, index: int) -> list[float] | None:
    row = db.scalar(
        select(EmbeddingCache).where(
            EmbeddingCache.file_hash == file_hash,
            EmbeddingCache.chunk_index == index,
            EmbeddingCache.model_name == model_key(),
        )
    )
    if row is None:
        return None
    return list(row.embedding)


def ingest_file(db: Session, subject_id: str, path: Path) -> dict:
    digest = file_digest(path)
    pages = extract_pages(path)
    kept: list[tuple[int, str]] = []
    issues = 0
    for page_no, text in pages:
        found = check_extracted_text(text, source=f"{path.name} p.{page_no}")
        if page_is_unusable(text, found):
            if found or not text.strip():
                if found:
                    issues += 1
                    db.add(
                        IngestIssue(
                            subject_id=subject_id,
                            source_path=str(path),
                            detail=f"p.{page_no}: {'; '.join(found)}",
                        )
                    )
            continue
        kept.append((page_no, text))
    pieces = chunk_words(words_from_pages(kept))
    existing = list(
        db.scalars(select(Chunk).where(Chunk.subject_id == subject_id, Chunk.source_path == str(path)))
    )
    unchanged = (
        len(existing) == len(pieces)
        and bool(existing)
        and all(row.file_hash == digest for row in existing)
        and [row.text for row in sorted(existing, key=lambda row: row.chunk_index)]
        == [piece.text for piece in pieces]
    )
    if unchanged:
        _sync_pgvector(db, subject_id, str(path))
        return {"path": str(path), "chunks": 0, "embedded": 0, "unchanged": True, "issues": issues}

    db.execute(delete(Chunk).where(Chunk.subject_id == subject_id, Chunk.source_path == str(path)))
    missing: list[int] = []
    vectors: list[list[float] | None] = []
    for piece in pieces:
        cached = _cache_get(db, digest, piece.index)
        vectors.append(cached)
        if cached is None:
            missing.append(piece.index)
    embedded = 0
    if missing:
        fresh = embed_texts([pieces[index].text for index in missing])
        embedded = len(fresh)
        for index, vector in zip(missing, fresh, strict=True):
            vectors[index] = vector
            db.add(
                EmbeddingCache(
                    file_hash=digest,
                    chunk_index=index,
                    model_name=model_key(),
                    embedding=vector,
                )
            )
    for piece, vector in zip(pieces, vectors, strict=True):
        db.add(
            Chunk(
                subject_id=subject_id,
                source_path=str(path),
                file_hash=digest,
                chunk_index=piece.index,
                chapter=piece.chapter,
                page=piece.page,
                text=piece.text,
                embedding=vector or [],
            )
        )
    db.flush()
    _sync_pgvector(db, subject_id, str(path))
    return {
        "path": str(path),
        "chunks": len(pieces),
        "embedded": embedded,
        "unchanged": False,
        "issues": issues,
    }


def _sync_pgvector(db: Session, subject_id: str, source_path: str) -> None:
    bind = db.get_bind()
    if bind.dialect.name != "postgresql":
        return
    rows = db.scalars(select(Chunk).where(Chunk.subject_id == subject_id, Chunk.source_path == source_path))
    for row in rows:
        if not row.embedding:
            continue
        literal = "[" + ",".join(f"{float(value):.8f}" for value in row.embedding) + "]"
        db.execute(
            text("UPDATE chunks SET embedding_vec = CAST(:vec AS vector) WHERE id = :id"),
            {"vec": literal, "id": row.id},
        )


def ingest_subject(db: Session, subject_id: str, folder: Path) -> dict:
    if not folder.is_dir():
        return {"subject_id": subject_id, "files": [], "missing_folder": True}
    files = sorted(path for path in folder.rglob("*") if path.is_file() and path.suffix.lower() in _SUFFIXES)
    reports = [ingest_file(db, subject_id, path) for path in files]
    db.flush()
    return {"subject_id": subject_id, "files": reports, "missing_folder": False}
