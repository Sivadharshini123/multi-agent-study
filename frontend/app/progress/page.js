"use client";

import { useEffect, useState } from "react";
import { api, apiBlob } from "../../lib/api";
import { percent, subjectName } from "../../lib/time";

export default function ProgressPage() {
  const [subjects, setSubjects] = useState([]);
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState("");

  useEffect(() => {
    Promise.all([api("/subjects"), api("/progress")])
      .then(([subjectRows, snapshot]) => {
        setSubjects(subjectRows);
        setProgress(snapshot);
      })
      .catch((err) => setError(err.message));
  }, []);

  async function openReport(path, filename) {
    setBusy(path);
    setError("");
    try {
      const blob = await apiBlob(path);
      const url = URL.createObjectURL(blob);
      if (filename) {
        const link = document.createElement("a");
        link.href = url;
        link.download = filename;
        link.click();
      } else {
        window.open(url, "_blank", "noopener");
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy("");
    }
  }

  return (
    <div className="stack">
      <h1>Progress</h1>
      {error ? <p className="error">{error}</p> : null}
      {!progress ? <p className="muted">Loading…</p> : null}
      {progress ? (
        <>
          <div className="stats">
            <div className="card">
              <p className="muted">Syllabus covered</p>
              <strong>{percent(progress.coverage)}</strong>
              <p className="muted">
                {progress.topics_done} of {progress.topics_total} topics revised or mastered
              </p>
            </div>
            <div className="card">
              <p className="muted">Quiz accuracy</p>
              <strong>{percent(progress.accuracy)}</strong>
            </div>
            <div className="card">
              <p className="muted">Accuracy on missed topics</p>
              <strong>{percent(progress.missed_topic_accuracy)}</strong>
            </div>
            <div className="card">
              <p className="muted">Pomodoros</p>
              <strong>{progress.pomodoro_count}</strong>
              <p className="muted">{progress.mistake_count} mistakes saved</p>
            </div>
          </div>
          <section className="stack">
            <h2>Time per topic</h2>
            {progress.time_by_topic.length === 0 ? <p className="muted">No topics yet.</p> : null}
            {progress.time_by_topic.map((item) => (
              <div className="card row" key={item.topic_id}>
                <div>
                  <strong>{item.title}</strong>
                  <div className="muted">{subjectName(subjects, item.subject_id)}</div>
                </div>
                <span>{item.minutes} min</span>
              </div>
            ))}
          </section>
          <section className="stack">
            <h2>Confidence compared with quizzes</h2>
            {progress.confidence_gaps.length === 0 ? (
              <p className="muted">No over- or underestimated topics yet. Rate confidence on a quiz or on the syllabus map.</p>
            ) : null}
            {progress.confidence_gaps.map((gap) => (
              <article className="card" key={gap.topic_id}>
                <strong>{gap.title}</strong>
                <p className="muted">
                  {gap.bias} · confidence {gap.confidence} · accuracy {percent(gap.accuracy)}
                </p>
              </article>
            ))}
          </section>
          <div className="row">
            <button type="button" disabled={busy !== ""} onClick={() => openReport("/reports/weekly.pdf", "weekly-report.pdf")}>
              {busy === "/reports/weekly.pdf" ? "Preparing PDF…" : "Download weekly PDF"}
            </button>
            <button className="ghost" type="button" disabled={busy !== ""} onClick={() => openReport("/reports/weekly.html")}>
              {busy === "/reports/weekly.html" ? "Opening…" : "Open weekly report"}
            </button>
          </div>
        </>
      ) : null}
    </div>
  );
}
