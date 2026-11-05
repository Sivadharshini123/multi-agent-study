"""Fixed agent order. This is not an open tool loop."""

from __future__ import annotations

TUTOR_TOOLS = frozenset({"search_subject", "explain_simply"})
QUIZ_TOOLS = frozenset({"search_subject", "generate_quiz", "grade_answer"})
PLANNER_TOOLS = frozenset({"get_progress", "update_plan", "log_decision"})
CRITIC_TOOLS = frozenset(
    {
        "get_quiz_results",
        "get_mistake_notebook",
        "get_pomodoro_logs",
        "flag_question",
        "write_critique",
    }
)

ALLOWED = {
    "tutor": TUTOR_TOOLS,
    "quiz": QUIZ_TOOLS,
    "planner": PLANNER_TOOLS,
    "critic": CRITIC_TOOLS,
}

CAPS = {"tutor": 6, "quiz": 12, "planner": 8, "critic": 20}

# Coordinator events run these agents and no others.
RUN_ORDER = {
    "doubt": ("tutor",),
    "quiz_generate": ("quiz",),
    "quiz_grade": ("quiz",),
    "quiz_session_done": ("critic",),
    "topic_finished_or_skipped": ("planner",),
    "evening": ("planner",),
    "weekly": ("critic",),
}
