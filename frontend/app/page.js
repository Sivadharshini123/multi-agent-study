"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { api } from "../lib/api";
import { subjectName } from "../lib/time";

export default function TodayPage() {
  const [subjects, setSubjects] = useState([]);
  const [plan, setPlan] = useState(null);
  const [due, setDue] = useState([]);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function load() {
    const [subjectRows, planBody, reviewBody] = await Promise.all([
      api("/subjects"),
      api("/plan"),
      api("/reviews/due"),
    ]);
    setSubjects(subjectRows);
    setPlan(planBody);
    setDue(reviewBody.topic_ids || []);
  }

  useEffect(() => {
    load().catch((err) => setError(err.message));
  }, []);

  async function act(blockId, action) {
    setBusy(true);
    setError("");
    try {
      const next = await api(`/plan/blocks/${blockId}`, { method: "POST", body: { action } });
      setPlan(next);
      const reviewBody = await api("/reviews/due");
      setDue(reviewBody.topic_ids || []);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function rebuild() {
    setBusy(true);
    setError("");
    try {
      setPlan(await api("/plan/rebuild", { method: "POST" }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  const blocks = plan?.blocks || [];

  return (
    <div className="stack">
      <div className="row">
        <h1>Today</h1>
        <button className="ghost" type="button" onClick={rebuild} disabled={busy}>
          Rebuild plan
        </button>
      </div>
      <p className="muted">
        {plan?.date || "Loading the day…"} The planner rebuilds this list when you finish or skip a topic.
      </p>
      {error ? <p className="error">{error}</p> : null}
      {!plan ? <p className="muted">Loading…</p> : null}
      {plan && blocks.length === 0 ? (
        <div className="card stack">
          <p>No blocks yet. Add free time and topics, then rebuild.</p>
          <Link className="button" href="/schedule">
            Set up schedule
          </Link>
        </div>
      ) : null}
      {blocks.map((block) => (
        <article className="card stack" key={block.id}>
          <div className="row">
            <span className="tag">{subjectName(subjects, block.subject_id)}</span>
            <span className={`tag status-${block.status}`}>{block.status}</span>
            {due.includes(block.topic_id) ? <span className="tag">Review due</span> : null}
          </div>
          <h2>{block.title}</h2>
          <p className="muted">
            {block.minutes} min · {block.reason}
          </p>
          {block.status === "planned" ? (
            <div className="row">
              <Link className="button" href={`/timer?subject=${block.subject_id}&topic=${block.topic_id}`}>
                Start timer
              </Link>
              <button type="button" onClick={() => act(block.id, "done")} disabled={busy}>
                Done
              </button>
              <button className="ghost" type="button" onClick={() => act(block.id, "skipped")} disabled={busy}>
                Skip
              </button>
              <button className="ghost" type="button" onClick={() => act(block.id, "difficult")} disabled={busy}>
                Difficult
              </button>
            </div>
          ) : null}
        </article>
      ))}
    </div>
  );
}
