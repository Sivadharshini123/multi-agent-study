"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";

export default function CritiquesPage() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api("/critiques")
      .then(setRows)
      .catch((err) => setError(err.message));
  }, []);

  return (
    <div className="stack">
      <h1>Critiques</h1>
      <p className="muted">The critic reads quiz results, mistakes, and Pomodoro logs. It does not change the plan.</p>
      {error ? <p className="error">{error}</p> : null}
      {rows == null ? <p className="muted">Loading…</p> : null}
      {rows && rows.length === 0 ? <p className="muted">No critiques yet. Finish a quiz to get the first one.</p> : null}
      {rows?.map((item) => (
        <article className="card stack" key={item.id}>
          <div className="row">
            <span className="tag">{item.kind}</span>
            <span className="muted">{new Date(item.created_at).toLocaleString()}</span>
          </div>
          <p className="answer">{item.body}</p>
          {Array.isArray(item.reasons) && item.reasons.length ? (
            <ul>
              {item.reasons.map((reason) => (
                <li key={reason}>{reason}</li>
              ))}
            </ul>
          ) : null}
        </article>
      ))}
    </div>
  );
}
