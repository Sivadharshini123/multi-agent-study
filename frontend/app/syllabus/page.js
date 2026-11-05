"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { STATUS_LABELS, subjectName } from "../../lib/time";

const COLUMNS = ["not_started", "learning", "revised", "mastered"];

export default function SyllabusPage() {
  const [subjects, setSubjects] = useState([]);
  const [topics, setTopics] = useState([]);
  const [error, setError] = useState("");
  const [busyId, setBusyId] = useState(null);

  useEffect(() => {
    Promise.all([api("/subjects"), api("/schedule")])
      .then(([subjectRows, schedule]) => {
        setSubjects(subjectRows);
        setTopics(schedule.topics);
      })
      .catch((err) => setError(err.message));
  }, []);

  async function patch(topic, body) {
    setBusyId(topic.id);
    setError("");
    try {
      await api(`/topics/${topic.id}`, { method: "PATCH", body });
      const schedule = await api("/schedule");
      setTopics(schedule.topics);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusyId(null);
    }
  }

  return (
    <div className="stack">
      <h1>Syllabus</h1>
      <p className="muted">Move a topic as you learn it. Marking it revised, mastered, or difficult rebuilds today’s plan.</p>
      {error ? <p className="error">{error}</p> : null}
      {topics.length === 0 ? <p className="muted">Add topics in Setup to fill the map.</p> : null}
      <div className="map">
        {COLUMNS.map((status) => (
          <section className="stack" key={status}>
            <h2>
              <span className={`tag status-${status}`}>{STATUS_LABELS[status]}</span>
            </h2>
            {topics
              .filter((topic) => topic.status === status)
              .map((topic) => (
                <article className="card stack" key={topic.id}>
                  <strong>{topic.title}</strong>
                  <p className="muted">
                    {subjectName(subjects, topic.subject_id)}
                    {topic.difficult ? " · Difficult" : ""}
                  </p>
                  <label>
                    Status
                    <select
                      value={topic.status}
                      disabled={busyId === topic.id}
                      onChange={(event) => patch(topic, { status: event.target.value })}
                    >
                      {COLUMNS.map((value) => (
                        <option key={value} value={value}>
                          {STATUS_LABELS[value]}
                        </option>
                      ))}
                    </select>
                  </label>
                  <label>
                    Confidence
                    <select
                      value={topic.confidence || ""}
                      disabled={busyId === topic.id}
                      onChange={(event) => patch(topic, { confidence: Number(event.target.value) })}
                    >
                      <option value="" disabled>
                        Not set
                      </option>
                      {[1, 2, 3, 4, 5].map((value) => (
                        <option key={value} value={value}>
                          {value}
                        </option>
                      ))}
                    </select>
                  </label>
                  <button
                    className="ghost"
                    type="button"
                    disabled={busyId === topic.id}
                    onClick={() => patch(topic, { difficult: !topic.difficult })}
                  >
                    {topic.difficult ? "Clear difficult" : "Mark difficult"}
                  </button>
                </article>
              ))}
          </section>
        ))}
      </div>
    </div>
  );
}
