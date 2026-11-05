"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { api, saveSession } from "../../lib/api";

export default function SignupPage() {
  const router = useRouter();
  const [form, setForm] = useState({
    username: "",
    password: "",
    name: "",
    course: "",
    teacher: false,
  });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function setField(key, value) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const data = await api("/auth/signup", {
        method: "POST",
        body: {
          username: form.username,
          password: form.password,
          name: form.name,
          course: form.course,
          role: form.teacher ? "teacher" : "student",
        },
      });
      saveSession(data.token);
      router.replace("/");
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="stack" onSubmit={submit}>
      <h1>Create an account</h1>
      <p className="muted">Only your name, class or course, and exam dates are stored with the account.</p>
      <label>
        Name
        <input value={form.name} onChange={(event) => setField("name", event.target.value)} required />
      </label>
      <label>
        Class or course
        <input
          value={form.course}
          onChange={(event) => setField("course", event.target.value)}
          placeholder="Class 12 or B.E. CSE"
          required
        />
      </label>
      <label>
        Username
        <input
          value={form.username}
          onChange={(event) => setField("username", event.target.value)}
          autoComplete="username"
          pattern="[A-Za-z0-9_]{3,32}"
          title="3–32 letters, numbers, or underscores"
          required
        />
      </label>
      <label>
        Password
        <input
          type="password"
          value={form.password}
          onChange={(event) => setField("password", event.target.value)}
          autoComplete="new-password"
          minLength={8}
          required
        />
      </label>
      <label className="check">
        <input
          type="checkbox"
          checked={form.teacher}
          onChange={(event) => setField("teacher", event.target.checked)}
        />
        I am a teacher and will approve quiz questions
      </label>
      {error ? <p className="error">{error}</p> : null}
      <button type="submit" disabled={busy}>
        {busy ? "Creating account…" : "Create account"}
      </button>
      <p>
        Already have an account? <Link href="/login">Sign in</Link>
      </p>
    </form>
  );
}
