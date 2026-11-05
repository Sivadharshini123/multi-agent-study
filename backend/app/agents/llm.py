from __future__ import annotations

import logging

from app.agents.context import TransientFailure
from app.config import get_settings

logger = logging.getLogger("study.llm")


def complete(system: str, user: str, max_tokens: int = 800) -> str | None:
    settings = get_settings()
    if not settings.anthropic_api_key:
        return None
    import anthropic

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    try:
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=max_tokens,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
    except anthropic.APITimeoutError as exc:
        raise TransientFailure(str(exc)) from exc
    except anthropic.RateLimitError as exc:
        raise TransientFailure(str(exc)) from exc
    parts = []
    for block in response.content:
        text = getattr(block, "text", "")
        if text:
            parts.append(text)
    return "\n".join(parts).strip() or None
