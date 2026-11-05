from __future__ import annotations

import sqlite3
import re
import shlex

_SQL_LEAD = re.compile(r"(?is)^\s*(select|with)\b")
_UNSAFE_SQL = re.compile(r"(?is)\b(attach|detach|pragma|drop|alter|insert|update|delete|create)\b")
_UNIX_META = re.compile(r"[;&<>`$()]")
_ALLOW = {"echo", "printf", "pwd", "true", "false", "expr", "wc"}


class UnsafeCommand(Exception):
    pass


def normalize_sql(sql: str) -> str:
    text = sql.strip().rstrip(";").lower()
    text = re.sub(r"\s+", " ", text)
    return text.replace("( ", "(").replace(" )", ")")


def _run_select(fixture: str, sql: str) -> list[tuple]:
    statement = sql.strip().rstrip(";")
    if ";" in statement or not _SQL_LEAD.match(statement) or _UNSAFE_SQL.search(statement):
        raise UnsafeCommand("sql")
    connection = sqlite3.connect(":memory:")
    try:
        if fixture:
            connection.executescript(fixture)
        cursor = connection.execute(sql)
        return list(cursor.fetchall())
    finally:
        connection.close()


def grade_sql(expected: str, student: str, fixture: str | None) -> bool:
    if fixture:
        try:
            return _run_select(fixture, expected) == _run_select(fixture, student)
        except Exception:
            return False
    return normalize_sql(expected) == normalize_sql(student)


def _run_argv(argv: list[str], stdin: str) -> str:
    command = argv[0]
    args = argv[1:]
    if command == "echo":
        return " ".join(args) + "\n"
    if command == "printf":
        return " ".join(args)
    if command == "pwd":
        return "/student\n"
    if command == "true":
        return ""
    if command == "false":
        raise UnsafeCommand("false")
    if command == "expr":
        if len(args) == 3 and args[1] in {"+", "-", "*", "/"}:
            left, op, right = int(args[0]), args[1], int(args[2])
            if op == "+":
                return f"{left + right}\n"
            if op == "-":
                return f"{left - right}\n"
            if op == "*":
                return f"{left * right}\n"
            if right == 0:
                raise UnsafeCommand("div0")
            return f"{left // right}\n"
        raise UnsafeCommand("expr")
    if command == "wc":
        flag = args[0] if args else "-w"
        if flag == "-w":
            return f"{len(stdin.split())}\n"
        if flag == "-l":
            return f"{len(stdin.splitlines())}\n"
        if flag == "-c":
            return f"{len(stdin.encode())}\n"
        raise UnsafeCommand("wc")
    raise UnsafeCommand(command)


def run_unix_sandbox(command: str) -> str:
    if _UNIX_META.search(command):
        raise UnsafeCommand("meta")
    data = ""
    for segment in command.split("|"):
        argv = shlex.split(segment.strip())
        if not argv or argv[0] not in _ALLOW:
            raise UnsafeCommand("allow")
        data = _run_argv(argv, data)
    return data


def normalize_command(command: str) -> str:
    return re.sub(r"\s+", " ", command.strip())


def grade_unix(expected: str, student: str) -> bool:
    try:
        return run_unix_sandbox(expected) == run_unix_sandbox(student)
    except UnsafeCommand:
        return normalize_command(expected) == normalize_command(student)
    except Exception:
        return False


def _content_tokens(text: str) -> list[str]:
    return [tok for tok in re.findall(r"\w+", text.lower()) if len(tok) > 2]


def grade_text(expected: str, student: str) -> bool:
    exp = expected.strip().casefold()
    got = student.strip().casefold()
    if not got:
        return False
    if got == exp or got in exp or exp in got:
        return True
    expected_tokens = _content_tokens(exp)
    if not expected_tokens:
        return False
    got_tokens = set(_content_tokens(got))
    overlap = sum(1 for tok in expected_tokens if tok in got_tokens)
    return overlap / len(expected_tokens) >= 0.6


def grade_answer(question_type: str, language: str | None, expected: str, student: str, choices, fixture) -> bool:
    if question_type == "mcq":
        got = student.strip().casefold()
        if choices:
            letters = {chr(ord("a") + index): choice for index, choice in enumerate(choices)}
            if got in letters:
                got = letters[got].strip().casefold()
        return got == expected.strip().casefold()
    if question_type == "code" and language == "sql":
        return grade_sql(expected, student, fixture)
    if question_type == "code":
        return grade_unix(expected, student)
    return grade_text(expected, student)
