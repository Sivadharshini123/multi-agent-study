from datetime import date, timedelta


def _signup(client, username, role="student"):
    response = client.post(
        "/auth/signup",
        json={
            "username": username,
            "password": "password1",
            "name": username,
            "course": "Class 12",
            "role": role,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert "password" not in body["user"]
    return {"Authorization": f"Bearer {body['token']}"}


def test_students_only_see_their_own_topics(client):
    ada = _signup(client, "ada")
    bes = _signup(client, "bes")
    created = client.post(
        "/topics",
        headers=ada,
        json={"subject_id": "physics", "title": "Ohm's law", "estimated_minutes": 50},
    )
    assert created.status_code == 200
    ada_topics = client.get("/schedule", headers=ada).json()["topics"]
    bes_topics = client.get("/schedule", headers=bes).json()["topics"]
    assert [item["title"] for item in ada_topics] == ["Ohm's law"]
    assert bes_topics == []
    topic_id = ada_topics[0]["id"]
    hidden = client.patch(f"/topics/{topic_id}", headers=bes, json={"difficult": True})
    assert hidden.status_code == 404


def test_quiz_stays_hidden_until_a_teacher_approves_it(client):
    student = _signup(client, "student1")
    teacher = _signup(client, "teacher1", role="teacher")
    topic = client.post(
        "/topics",
        headers=student,
        json={"subject_id": "physics", "title": "Ohm's law", "estimated_minutes": 40},
    ).json()
    generated = client.post("/quiz/generate", headers=student, json={"topic_id": topic["id"]})
    assert generated.status_code == 200, generated.text
    assert generated.json()["pending"] > 0
    assert client.get(f"/quiz?topic_id={topic['id']}", headers=student).json() == []
    blocked = client.get("/review", headers=student)
    assert blocked.status_code == 403
    queue = client.get("/review", headers=teacher).json()
    assert queue
    assert "answer" in queue[0]
    for item in queue:
        approved = client.post(f"/review/{item['id']}", headers=teacher, json={"action": "approve"})
        assert approved.status_code == 200
    visible = client.get(f"/quiz?topic_id={topic['id']}", headers=student).json()
    assert visible
    assert "answer" not in visible[0]
    submitted = client.post(
        "/quiz/submit",
        headers=student,
        json={
            "topic_id": topic["id"],
            "confidence": 5,
            "answers": [{"question_id": visible[0]["id"], "answer": "not-the-answer"}],
        },
    )
    assert submitted.status_code == 200, submitted.text
    body = submitted.json()
    assert body["results"][0]["correct"] is False
    assert "What went well" in body["critique"]["body"]
    mistakes = client.get("/mistakes", headers=student).json()
    assert mistakes
    today = date.today()
    assert mistakes[0]["due_on"] == [
        (today + timedelta(days=1)).isoformat(),
        (today + timedelta(days=3)).isoformat(),
        (today + timedelta(days=7)).isoformat(),
    ]
    assert client.get("/mistakes", headers=teacher).json() == []


def test_plan_updates_when_a_topic_is_skipped(client):
    student = _signup(client, "planner")
    weekday = date.today().weekday()
    saved = client.put(
        "/schedule",
        headers=student,
        json={
            "slots": [{"weekday": weekday, "start_minute": 16 * 60, "end_minute": 18 * 60}],
            "exams": [{"subject_id": "os", "exam_date": (date.today() + timedelta(days=3)).isoformat()}],
        },
    )
    assert saved.status_code == 200, saved.text
    client.post("/topics", headers=student, json={"subject_id": "os", "title": "Processes", "estimated_minutes": 50})
    client.post("/topics", headers=student, json={"subject_id": "dbms", "title": "Queries", "estimated_minutes": 50})
    plan = client.post("/plan/rebuild", headers=student).json()
    assert plan["blocks"]
    assert {block["subject_id"] for block in plan["blocks"]} >= {"os", "dbms"}
    assert all(block["reason"] for block in plan["blocks"])
    first = next(block for block in plan["blocks"] if block["status"] == "planned")
    updated = client.post(f"/plan/blocks/{first['id']}", headers=student, json={"action": "skipped"}).json()
    assert any(block["id"] == first["id"] and block["status"] == "skipped" for block in updated["blocks"])
    logged = client.post(
        "/pomodoro",
        headers=student,
        json={"subject_id": "os", "topic_id": first["topic_id"], "minutes": 25},
    )
    assert logged.status_code == 200
    report = client.get("/reports/weekly.html", headers=student)
    assert report.status_code == 200
    assert "planner" in report.text
    assert "Syllabus coverage" in report.text
