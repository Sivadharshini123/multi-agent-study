"use client";

import { useEffect, useState } from "react";
import { api } from "../../lib/api";
import { subjectName } from "../../lib/time";

export default function QuizPage() {
  const [subjects, setSubjects] = useState([]);
  const [topics, setTopics] = useState([]);
  const [topicId, setTopicId] = useState("");
  const [questions, setQuestions] = useState([]);
  const [answers, setAnswers] = useState({});
  const [confidence, setConfidence] = useState("");
  const [result, setResult] = useState(null);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    Promise.all([api("/subjects"), api("/schedule")])
      .then(([subjectRows, schedule]) => {
        setSubjects(subjectRows);
        setTopics(schedule.topics);
        setTopicId(schedule.topics[0] ? String(schedule.topics[0].id) : "");
      })
      .catch((err) => setError(err.message));
  }, []);

  useEffect(() => {
    if (!topicId) {
      setQuestions([]);
      return;
    }
    api(`/quiz?topic_id=${topicId}`)
      .then((rows) => {
        setQuestions(rows);
        setAnswers({});
        setResult(null);
      })
      .catch((err) => setError(err.message));
  }, [topicId]);

  const topic = topics.find((item) => String(item.id) === String(topicId));

  async function generate() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      const body = await api("/quiz/generate", { method: "POST", body: { topic_id: Number(topicId) } });
      setNotice(body.message || "Questions are waiting for a teacher to approve them.");
      setQuestions(await api(`/quiz?topic_id=${topicId}`));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const body = {
        topic_id: Number(topicId),
        answers: questions.map((question) => ({
          question_id: question.id,
          answer: answers[question.id] || "",
        })),
      };
      if (confidence) body.confidence = Number(confidence);
      setResult(await api("/quiz/submit", { method: "POST", body }));
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="stack">
      <h1>Quiz</h1>
      <p className="muted">Questions are written from your material and stay hidden until a teacher approves them.</p>
      {error ? <p className="error">{error}</p> : null}
      {notice ? <p className="notice">{notice}</p> : null}
      {topics.length === 0 ? <p className="muted">Add a topic in Setup before generating a quiz.</p> : null}
      <label>
        Topic
        <select value={topicId} onChange={(event) => setTopicId(event.target.value)}>
          {topics.map((item) => (
            <option key={item.id} value={item.id}>
              {subjectName(subjects, item.subject_id)} · {item.title}
            </option>
          ))}
        </select>
      </label>
      <button type="button" onClick={generate} disabled={busy || !topicId}>
        {busy ? "Working…" : "Generate questions"}
      </button>
      {topic && questions.length === 0 ? (
        <p className="muted">No approved questions for {topic.title} yet.</p>
      ) : null}
      {questions.length > 0 ? (
        <form className="stack" onSubmit={submit}>
          {questions.map((question, index) => (
            <fieldset className="card stack" key={question.id}>
              <legend>
                {index + 1}. {question.qtype === "mcq" ? "Multiple choice" : "Short answer"}
                {question.language ? ` · ${question.language}` : ""}
              </legend>
              <p>{question.prompt}</p>
              {Array.isArray(question.choices) ? (
                question.choices.map((choice) => (
                  <label className="check" key={choice}>
                    <input
                      type="radio"
                      name={`q-${question.id}`}
                      value={choice}
                      checked={answers[question.id] === choice}
                      onChange={() => setAnswers((current) => ({ ...current, [question.id]: choice }))}
                      required
                    />
                    {choice}
                  </label>
                ))
              ) : (
                <textarea
                  value={answers[question.id] || ""}
                  onChange={(event) => setAnswers((current) => ({ ...current, [question.id]: event.target.value }))}
                  placeholder="Your answer"
                  required
                />
              )}
            </fieldset>
          ))}
          <label>
            How sure are you about this topic?
            <select value={confidence} onChange={(event) => setConfidence(event.target.value)}>
              <option value="">Skip</option>
              <option value="1">1 — unsure</option>
              <option value="2">2</option>
              <option value="3">3</option>
              <option value="4">4</option>
              <option value="5">5 — sure</option>
            </select>
          </label>
          <button type="submit" disabled={busy}>
            Submit answers
          </button>
        </form>
      ) : null}
      {result ? (
        <section className="stack">
          <h2>Results</h2>
          {result.results?.map((item) => (
            <article className="card" key={item.question_id}>
              <p>{item.correct ? "Correct" : "Needs review"}</p>
              {item.correct_answer ? <p>Answer: {item.correct_answer}</p> : null}
              {item.reasoning ? <p className="muted">{item.reasoning}</p> : null}
              {item.error ? <p className="error">{item.error}</p> : null}
            </article>
          ))}
          {result.critique?.body ? (
            <article className="card">
              <h2>Critique</h2>
              <p className="answer">{result.critique.body}</p>
            </article>
          ) : null}
        </section>
      ) : null}
    </div>
  );
}
