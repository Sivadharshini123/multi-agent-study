"use client";

import { useEffect, useState } from "react";
import { useUser } from "../../components/Shell";
import { api } from "../../lib/api";
import { cite, subjectName } from "../../lib/time";

const FILTERS = ["pending", "flagged", "approved", "rejected"];

export default function ReviewPage() {
  const user = useUser();
  const [subjects, setSubjects] = useState([]);
  const [status, setStatus] = useState("pending");
  const [rows, setRows] = useState([]);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  async function load(nextStatus = status) {
    const [subjectRows, queue] = await Promise.all([api("/subjects"), api(`/review?status=${nextStatus}`)]);
    setSubjects(subjectRows);
    setRows(queue);
  }

  useEffect(() => {
    if (user?.role !== "teacher") return;
    load().catch((err) => setError(err.message));
  }, [user, status]);

  async function decide(id, action) {
    setBusy(true);
    setError("");
    try {
      await api(`/review/${id}`, { method: "POST", body: { action } });
      await load();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function ingest() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const report = await api("/materials/ingest", { method: "POST" });
      const count = report.subjects?.length || 0;
      setNotice(`Ingested material for ${count} subjects.`);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  if (user?.role !== "teacher") {
    return (
      <div className="stack">
        <h1>Review</h1>
        <p>This queue is for teacher accounts. Students see a question only after it is approved.</p>
      </div>
    );
  }

  return (
    <div className="stack">
      <h1>Question review</h1>
      <p className="muted">Approve questions before students can take them. Flagged items were questioned by the critic.</p>
      <div className="row">
        {FILTERS.map((item) => (
          <button key={item} className={item === status ? "" : "ghost"} type="button" onClick={() => setStatus(item)}>
            {item}
          </button>
        ))}
        <button className="ghost" type="button" onClick={ingest} disabled={busy}>
          Re-ingest materials
        </button>
      </div>
      {error ? <p className="error">{error}</p> : null}
      {notice ? <p className="notice">{notice}</p> : null}
      {rows.length === 0 ? <p className="muted">Nothing in {status}.</p> : null}
      {rows.map((item) => (
        <article className="card stack" key={item.id}>
          <div className="row">
            <span className="tag">{subjectName(subjects, item.subject_id)}</span>
            <span className="tag">{item.topic_title}</span>
            <span className="tag">{item.qtype}</span>
          </div>
          <h2>{item.prompt}</h2>
          {Array.isArray(item.choices) ? <p>Choices: {item.choices.join(" · ")}</p> : null}
          <p>Answer: {item.answer}</p>
          {item.reasoning ? <p className="muted">{item.reasoning}</p> : null}
          {item.flag_reason ? <p className="error">{item.flag_reason}</p> : null}
          {Array.isArray(item.citations) && item.citations.length ? (
            <p className="muted">{item.citations.map(cite).join(" · ")}</p>
          ) : null}
          {status !== "approved" && status !== "rejected" ? (
            <div className="row">
              <button type="button" disabled={busy} onClick={() => decide(item.id, "approve")}>
                Approve
              </button>
              <button className="ghost" type="button" disabled={busy} onClick={() => decide(item.id, "reject")}>
                Reject
              </button>
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}
