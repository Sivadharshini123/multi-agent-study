from datetime import date

from app.models import User
from app.reports import render_weekly_html, weekly_context
from app.security import hash_password


def test_weekly_report_uses_only_that_student(db):
    ada = User(username="ada", password_hash=hash_password("password1"), name="Ada Lovelace", course="Class 12")
    bes = User(username="bes", password_hash=hash_password("password1"), name="Bea Secret", course="Class 12")
    db.add_all([ada, bes])
    db.commit()
    html = render_weekly_html(weekly_context(db, ada, date.today()))
    assert "Ada Lovelace" in html
    assert "Bea Secret" not in html
    assert "Syllabus coverage" in html
