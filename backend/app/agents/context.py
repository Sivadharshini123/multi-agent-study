from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from app.agents.registry import ALLOWED, CAPS
from app.models import AgentLog

logger = logging.getLogger("study.agents")


class StepCapExceeded(Exception):
    def __init__(self, agent: str):
        super().__init__(f"{agent} reached its step cap")
        self.agent = agent


class TransientFailure(Exception):
    pass


class ToolContext:
    def __init__(self, agent: str, session: Session | None, user_id: int | None, max_steps: int | None = None):
        self.agent = agent
        self.session = session
        self.user_id = user_id
        self.run_id = str(uuid.uuid4())
        self.max_steps = CAPS[agent] if max_steps is None else max_steps
        self.steps = 0
        self.wrote = False

    def call(self, name: str, fn, *args, detail: str = "", **kwargs):
        if name not in ALLOWED[self.agent]:
            self._log(name, "denied")
            raise PermissionError(f"{self.agent} cannot call {name}")
        if self.steps >= self.max_steps:
            raise StepCapExceeded(self.agent)
        self.steps += 1
        self._log(name, detail or "ok")
        return fn(*args, **kwargs)

    def _log(self, tool: str, detail: str) -> None:
        logger.info("agent=%s run=%s step=%s tool=%s %s", self.agent, self.run_id, self.steps, tool, detail)
        if self.session is None:
            return
        self.session.add(
            AgentLog(
                run_id=self.run_id,
                user_id=self.user_id,
                agent=self.agent,
                step=self.steps,
                tool=tool,
                detail=detail[:500],
            )
        )


def execute(agent: str, session: Session | None, user_id: int | None, factory, max_steps: int | None = None):
    """Run one agent function. Retry once only when the attempt has not written yet."""
    error: Exception | None = None
    for _attempt in (1, 2):
        ctx = ToolContext(agent, session, user_id, max_steps=max_steps)
        try:
            return factory(ctx)
        except TransientFailure as exc:
            error = exc
            logger.warning("transient failure in %s (wrote=%s)", agent, ctx.wrote)
            if ctx.wrote:
                raise
        except StepCapExceeded:
            raise
    assert error is not None
    raise error
