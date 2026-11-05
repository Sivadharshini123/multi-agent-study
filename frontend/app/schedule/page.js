"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { STATUS_LABELS, WEEKDAYS, minutesToTime, subjectName, timeToMinutes, todayWeekday } from "../../lib/time";

function blankSlot() {
  return {
    key: crypto.randomUUID(),
    weekday: todayWeekday(),
    start: "16:00",
    end: "18:00",
  };
}

export default function SchedulePage() {
  const [subjects, setSubjects] = useState([]);
  const [slots, setSlots] = useState([]);
  const [exams, setExams] = useState({});
  const [topics, setTopics] = useState([]);
  const [draft, setDraft] = useState({ subject_id: "", title: "", estimated_minutes: 50 });
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    async function load() {
      const [subjectRows, schedule] = await Promise.all([api("/subjects"), api("/schedule")]);
      setSubjects(subjectRows);
      setSlots(
        schedule.slots.length
          ? schedule.slots.map((slot) => ({
              key: crypto.randomUUID(),
              weekday: slot.weekday,
              start: minutesToTime(slot.start_minute),
              end: minutesToTime(slot.end_minute),
            }))
          : [blankSlot()]
      );
      const examMap = {};
      for (const exam of schedule.exams) examMap[exam.subject_id] = exam.exam_date;
      setExams(examMap);
      setTopics(schedule.topics);
      setDraft((current) => ({ ...current, subject_id: subjectRows[0]?.id || "" }));
    }
    load().catch((err) => setError(err.message));
  }, []);

  function updateSlot(key, field, value) {
    setSlots((current) => current.map((slot) => (slot.key === key ? { ...slot, [field]: value } : slot)));
  }

  async function saveSchedule(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const body = {
        slots: slots.map((slot) => ({
          weekday: Number(slot.weekday),
          start_minute: timeToMinutes(slot.start),
          end_minute: timeToMinutes(slot.end),
        })),
        exams: subjects
          .filter((subject) => exams[subject.id])
          .map((subject) => ({ subject_id: subject.id, exam_date: exams[subject.id] })),
      };
      const saved = await api("/schedule", { method: "PUT", body });
      setTopics(saved.topics);
      setNotice("Free time and exam dates saved. Today’s plan was rebuilt.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function addTopic(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    setNotice("");
    try {
      await api("/topics", {
        method: "POST",
        body: {
          subject_id: draft.subject_id,
          title: draft.title,
          estimated_minutes: Number(draft.estimated_minutes),
        },
      });
      const schedule = await api("/schedule");
      setTopics(schedule.topics);
      setDraft((current) => ({ ...current, title: "" }));
      setNotice("Topic added and the plan was updated.");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function removeTopic(id) {
    setBusy(true);
    setError("");
    try {
      await api(`/topics/${id}`, { method: "DELETE" });
      setTopics((current) => current.filter((topic) => topic.id !== id));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <h1>Schedule setup</h1>
      <p className="muted">Free time, exam dates, and topics. Subjects come from the server config.</p>
      {error ? <p className="error">{error}</p> : null}
      {notice ? <p className="notice">{notice}</p> : null}

      <form className="stack" onSubmit={saveSchedule}>
        <h2>Free time</h2>
        {slots.map((slot) => (
          <div className="card stack" key={slot.key}>
            <label>
              Day
              <select value={slot.weekday} onChange={(event) => updateSlot(slot.key, "weekday", event.target.value)}>
                {WEEKDAYS.map((name, index) => (
                  <option key={name} value={index}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
            <div className="split">
              <label>
                Start
                <input type="time" value={slot.start} onChange={(event) => updateSlot(slot.key, "start", event.target.value)} required />
              </label>
              <label>
                End
                <input type="time" value={slot.end} onChange={(event) => updateSlot(slot.key, "end", event.target.value)} required />
              </label>
            </div>
            <button
              className="ghost"
              type="button"
              onClick={() => setSlots((current) => current.filter((item) => item.key !== slot.key))}
            >
              Remove slot
            </button>
          </div>
        ))}
        <button className="ghost" type="button" onClick={() => setSlots((current) => [...current, blankSlot()])}>
          Add slot
        </button>

        <h2>Exam dates</h2>
        {subjects.map((subject) => (
          <label key={subject.id}>
            {subject.name}
            <input
              type="date"
              value={exams[subject.id] || ""}
              onChange={(event) => setExams((current) => ({ ...current, [subject.id]: event.target.value }))}
            />
          </label>
        ))}
        <button type="submit" disabled={busy || subjects.length === 0}>
          {busy ? "Saving…" : "Save free time and exams"}
        </button>
      </form>

      <form className="card stack" onSubmit={addTopic}>
        <h2>Topics</h2>
        <label>
          Subject
          <select value={draft.subject_id} onChange={(event) => setDraft((current) => ({ ...current, subject_id: event.target.value }))}>
            {subjects.map((subject) => (
              <option key={subject.id} value={subject.id}>
                {subject.name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Topic
          <input
            value={draft.title}
            onChange={(event) => setDraft((current) => ({ ...current, title: event.target.value }))}
            required
          />
        </label>
        <label>
          Estimated minutes
          <input
            type="number"
            min={10}
            max={600}
            value={draft.estimated_minutes}
            onChange={(event) => setDraft((current) => ({ ...current, estimated_minutes: event.target.value }))}
            required
          />
        </label>
        <button type="submit" disabled={busy}>
          Add topic
        </button>
      </form>

      {topics.map((topic) => (
        <article className="card row" key={topic.id}>
          <div>
            <strong>{topic.title}</strong>
            <div className="muted">
              {subjectName(subjects, topic.subject_id)} · {topic.estimated_minutes} min · {STATUS_LABELS[topic.status] || topic.status}
              {topic.difficult ? " · Difficult" : ""}
            </div>
          </div>
          <button className="ghost" type="button" onClick={() => removeTopic(topic.id)} disabled={busy}>
            Delete
          </button>
        </article>
      ))}
    </div>
  );
}
