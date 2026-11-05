"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { cite } from "../../lib/time";

export default function TutorPage() {
  const [subjects, setSubjects] = useState([]);
  const [subjectId, setSubjectId] = useState("");
  const [history, setHistory] = useState([]);
  const [question, setQuestion] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api("/subjects")
      .then((rows) => {
        setSubjects(rows);
        setSubjectId(rows[0]?.id || "");
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!subjectId) return;
    api(`/tutor/${subjectId}/history`)
      .then((rows) => setHistory(rows.slice().reverse()))
      .catch((err) => setError(err.message));
  }, [subjectId]);

  async function ask(event, simple = false, text = question) {
    event?.preventDefault();
    const trimmed = text.trim();
    if (!trimmed || !subjectId) return;
    setBusy(true);
    setError("");
    try {
      await api(`/tutor/${subjectId}`, { method: "POST", body: { question: trimmed, simple } });
      const rows = await api(`/tutor/${subjectId}/history`);
      setHistory(rows.slice().reverse());
      if (!simple) setQuestion("");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <h1>Study chat</h1>
      <p className="muted">
        Answers come only from that subject’s material, with chapter and page. A Tamil question gets a Tamil explanation, with English technical terms in brackets.
      </p>
      <label>
        Subject
        <select value={subjectId} onChange={(event) => setSubjectId(event.target.value)}>
          {subjects.map((subject) => (
            <option key={subject.id} value={subject.id}>
              {subject.name}
            </option>
          ))}
        </select>
      </label>
      {error ? <p className="error">{error}</p> : null}
      <div className="stack">
        {history.length === 0 ? <p className="muted">No doubts saved for this subject yet.</p> : null}
        {history.map((item) => (
          <article className="stack" key={item.id}>
            <div className="bubble me">{item.question}</div>
            <div className="bubble tutor">
              <p className="answer">{item.answer}</p>
              {Array.isArray(item.citations) && item.citations.length ? (
                <p className="muted">{item.citations.map(cite).join(" · ")}</p>
              ) : null}
              <button className="ghost" type="button" disabled={busy} onClick={() => ask(null, true, item.question)}>
                Explain simply
              </button>
            </div>
          </article>
        ))}
      </div>
      <form className="stack" onSubmit={(event) => ask(event, false)}>
        <label>
          Doubt
          <textarea
            value={question}
            onChange={(event) => setQuestion(event.target.value)}
            placeholder="Ask from your notes, in English or Tamil"
            required
          />
        </label>
        <button type="submit" disabled={busy || !subjectId}>
          {busy ? "Looking in the material…" : "Ask"}
        </button>
      </form>
    </div>
  );
}
