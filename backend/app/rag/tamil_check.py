"""Detect encoding damage in extracted text before it is chunked."""

from __future__ import annotations

import logging
import re

logger = logging.getLogger("study.ingest")

_TAMIL = re.compile(r"[\u0B80-\u0BFF]")
_MOJIBAKE = re.compile(r"(?:à®|à¯|Ã[\x80-\xbf]|â€)")
_CONTROLS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]")


def check_extracted_text(text: str, *, source: str = "") -> list[str]:
    """Return encoding issues. Warnings are always logged. Call this before chunking."""
    issues: list[str] = []
    if "\ufffd" in text:
        issues.append("replacement character U+FFFD")
    if _MOJIBAKE.search(text):
        issues.append("possible mojibake (UTF-8 read as Latin-1)")
    if _CONTROLS.search(text):
        issues.append("unexpected control characters")
    where = f" in {source}" if source else ""
    for issue in issues:
        logger.warning("Encoding issue%s: %s", where, issue)
    return issues


def page_is_unusable(text: str, issues: list[str]) -> bool:
    if not text.strip():
        return True
    if "\ufffd" in text:
        return True
    if any("mojibake" in issue for issue in issues):
        return True
    return False


def contains_tamil(text: str) -> bool:
    return _TAMIL.search(text) is not None
