"use client";

import { useSearchParams } from "next/navigation";
import { Suspense, useEffect, useRef, useState } from "react";
import { api } from "../../lib/api";
import { formatClock, subjectName } from "../../lib/time";

const STUDY = 25 * 60;
const SHORT = 5 * 60;
const LONG = 15 * 60;
const KEY = "study-timer";

const PHASES = {
  study: { label: "Study", seconds: STUDY },
  short: { label: "Break", seconds: SHORT },
  long: { label: "Long break", seconds: LONG },
};

function freshState() {
  return {
    phase: "study",
    remaining: STUDY,
    running: false,
    endsAt: null,
    cycles: 0,
    subjectId: "",
    topicId: "",
  };
}

function readState() {
  const raw = sessionStorage.getItem(KEY);
  if (!raw) return freshState();
  try {
    const saved = { ...freshState(), ...JSON.parse(raw) };
    if (saved.running && saved.endsAt) {
      saved.remaining = Math.max(0, Math.ceil((saved.endsAt - Date.now()) / 1000));
    }
    return saved;
  } catch {
    return freshState();
  }
}

function nextPhase(prev, completed) {
  let cycles = prev.cycles;
  let phase = "study";
  if (prev.phase === "study") {
    if (completed) cycles += 1;
    phase = completed && cycles % 4 === 0 ? "long" : "short";
  }
  const remaining = PHASES[phase].seconds;
  return {
    ...prev,
    phase,
    cycles,
    remaining,
    running: true,
    endsAt: Date.now() + remaining * 1000,
  };
}

function Timer() {
  const params = useSearchParams();
  const [subjects, setSubjects] = useState([]);
  const [topics, setTopics] = useState([]);
  const [state, setState] = useState(freshState);
  const [ready, setReady] = useState(false);
  const [error, setError] = useState("");
  const stateRef = useRef(state);
  const finishing = useRef(false);
  const audioRef = useRef(null);
  stateRef.current = state;

  useEffect(() => {
    const saved = readState();
    const subject = params.get("subject");
    const topic = params.get("topic");
    if (!saved.running) {
      if (subject) saved.subjectId = subject;
      if (topic) saved.topicId = topic;
    }
    setState(saved);
    setReady(true);
    api("/subjects")
      .then(setSubjects)
      .catch((err) => setError(err.message));
    api("/schedule")
      .then((schedule) => setTopics(schedule.topics))
      .catch((err) => setError(err.message));
  }, [params]);

  useEffect(() => {
    if (ready) sessionStorage.setItem(KEY, JSON.stringify(state));
  }, [state, ready]);

  const completeRef = useRef(null);

  useEffect(() => {
    const id = setInterval(() => {
      const current = stateRef.current;
      if (!current.running || !current.endsAt || finishing.current) return;
      const remaining = Math.max(0, Math.ceil((current.endsAt - Date.now()) / 1000));
      if (remaining > 0) {
        if (remaining !== current.remaining) {
          const next = { ...current, remaining };
          stateRef.current = next;
          setState(next);
        }
        return;
      }
      completeRef.current?.(current, true);
    }, 250);
    return () => clearInterval(id);
  }, []);

  function ensureAudio() {
    if (!audioRef.current) audioRef.current = new AudioContext();
    audioRef.current.resume();
  }

  function chime() {
    const ctx = audioRef.current;
    if (!ctx) return;
    const oscillator = ctx.createOscillator();
    const gain = ctx.createGain();
    oscillator.frequency.value = 784;
    oscillator.connect(gain);
    gain.connect(ctx.destination);
    gain.gain.setValueAtTime(0.06, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 0.6);
    oscillator.start();
    oscillator.stop(ctx.currentTime + 0.6);
  }

  function notify(phase) {
    chime();
    if (typeof Notification !== "undefined" && Notification.permission === "granted") {
      const title = phase === "study" ? "Study block finished" : "Break finished";
      new Notification(title, { body: phase === "study" ? "Take a break." : "Start the next study block." });
    }
  }

  function complete(current, finishedStudy) {
    if (finishing.current) return;
    finishing.current = true;
    const upcoming = nextPhase(current, finishedStudy && current.phase === "study");
    stateRef.current = upcoming;
    setState(upcoming);
    notify(current.phase);
    const shouldLog = finishedStudy && current.phase === "study" && current.subjectId;
    if (!shouldLog) {
      finishing.current = false;
      return;
    }
    api("/pomodoro", {
      method: "POST",
      body: {
        subject_id: current.subjectId,
        topic_id: current.topicId ? Number(current.topicId) : null,
        minutes: 25,
      },
    })
      .catch((err) => setError(err.message))
      .finally(() => {
        finishing.current = false;
      });
  }

  completeRef.current = complete;

  function start() {
    if (state.phase === "study" && !state.subjectId) {
      setError("Choose a subject before the study block.");
      return;
    }
    setError("");
    ensureAudio();
    if (typeof Notification !== "undefined" && Notification.permission === "default") {
      Notification.requestPermission().catch(() => {});
    }
    setState({ ...state, running: true, endsAt: Date.now() + state.remaining * 1000 });
  }

  function pause() {
    setState({ ...state, running: false, endsAt: null });
  }

  function restart() {
    const remaining = PHASES[state.phase].seconds;
    setState({
      ...state,
      remaining,
      endsAt: state.running ? Date.now() + remaining * 1000 : null,
    });
  }

  const subjectTopics = topics.filter((topic) => topic.subject_id === state.subjectId);
  const topic = topics.find((item) => String(item.id) === String(state.topicId));
  const locked = state.running && state.phase === "study";

  return (
    <div className="stack">
      <h1>{PHASES[state.phase].label}</h1>
      <p className="timer" aria-live="polite">
        {formatClock(state.remaining)}
      </p>
      <p className="muted">
        {state.phase === "study"
          ? `${subjectName(subjects, state.subjectId) || "Choose a subject"}${topic ? ` · ${topic.title}` : ""}`
          : `Completed study cycles: ${state.cycles}. A 15 minute break follows every fourth cycle.`}
      </p>
      {error ? <p className="error">{error}</p> : null}
      <div className="row">
        {state.running ? (
          <button type="button" onClick={pause}>
            Pause
          </button>
        ) : (
          <button type="button" onClick={start}>
            Start
          </button>
        )}
        <button className="ghost" type="button" onClick={() => complete(state, false)}>
          Skip
        </button>
        <button className="ghost" type="button" onClick={restart}>
          Restart
        </button>
      </div>
      <label>
        Subject
        <select
          value={state.subjectId}
          disabled={locked}
          onChange={(event) => setState({ ...state, subjectId: event.target.value, topicId: "" })}
        >
          <option value="">Select</option>
          {subjects.map((subject) => (
            <option key={subject.id} value={subject.id}>
              {subject.name}
            </option>
          ))}
        </select>
      </label>
      <label>
        Topic
        <select
          value={state.topicId}
          disabled={locked || !state.subjectId}
          onChange={(event) => setState({ ...state, topicId: event.target.value })}
        >
          <option value="">No specific topic</option>
          {subjectTopics.map((item) => (
            <option key={item.id} value={item.id}>
              {item.title}
            </option>
          ))}
        </select>
      </label>
      <p className="muted">The clock stays in this browser session. A finished 25 minute study block is saved to your log.</p>
    </div>
  );
}

export default function TimerPage() {
  return (
    <Suspense fallback={<p className="muted">Loading timer…</p>}>
      <Timer />
    </Suspense>
  );
}
