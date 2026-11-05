from datetime import date, timedelta

from sqlalchemy import select

from app.models import QuizQuestion, ReviewItem, Topic, User
from app.security import hash_password
from app.services.grading import grade_sql, grade_unix
from app.services.mistakes import record_mistake


def test_sql_and_unix_are_graded_by_running():
    fixture = "CREATE TABLE students (id INTEGER, name TEXT); INSERT INTO students VALUES (1, 'Ada');"
    assert grade_sql("SELECT name FROM students WHERE id = 1", "select name from students where id=1", fixture)
    assert not grade_sql("SELECT name FROM students WHERE id = 1", "DROP TABLE students", fixture)
    assert grade_unix("echo hello | wc -w", "echo hello | wc -w")
    assert not grade_unix("echo hello | wc -w", "echo goodbye | wc -w")


def test_wrong_answers_are_reviewed_after_one_three_and_seven_days(db):
    user = User(username="sam", password_hash=hash_password("password1"), name="Sam", course="12")
    db.add(user)
    db.flush()
    topic = Topic(user_id=user.id, subject_id="unix", title="Listing files", estimated_minutes=25)
    question = QuizQuestion(
        subject_id="unix",
        topic_title="Listing files",
        qtype="code",
        prompt="Enter the command",
        answer="pwd",
        reasoning="The notes say pwd prints the working directory.",
        support_text="pwd prints the working directory.",
        citations=[],
        status="approved",
    )
    db.add(topic)
    db.add(question)
    db.flush()
    today = date(2026, 11, 5)
    record_mistake(db, user.id, question, "ls", topic.id, today)
    db.commit()
    due = sorted(row.due_on for row in db.scalars(select(ReviewItem)))
    assert due == [today + timedelta(days=1), today + timedelta(days=3), today + timedelta(days=7)]
