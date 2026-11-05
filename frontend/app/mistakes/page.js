"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { subjectName } from "../../lib/time";

export default function MistakesPage() {
  const [subjects, setSubjects] = useState([]);
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    Promise.all([api("/subjects"), api("/mistakes")])
      .then(([subjectRows, items]) => {
        setSubjects(subjectRows);
        setRows(items);
      })
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="stack">
      <h1>Mistake notebook</h1>
      <p className="muted">Wrong answers stay here, with the reasoning from the material, and come back after 1, 3, and 7 days.</p>
      {error ? <p className="error">{error}</p> : null}
      {rows == null ? <p className="muted">Loading…</p> : null}
      {rows && rows.length === 0 ? <p className="muted">No mistakes yet.</p> : null}
      {rows?.map((item) => (
        <article className="card stack" key={item.id}>
          <div className="row">
            <span className="tag">{subjectName(subjects, item.subject_id)}</span>
            <span className="tag">{item.topic_title}</span>
          </div>
          <h2>{item.prompt}</h2>
          <p>Your answer: {item.student_answer}</p>
          <p>Correct answer: {item.correct_answer}</p>
          {item.reasoning ? <p className="muted">{item.reasoning}</p> : null}
          <p className="muted">Review on {item.due_on.join(", ")}</p>
        </article>
      ))}
    </div>
  );
}
