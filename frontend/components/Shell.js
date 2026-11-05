"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { createContext, useContext, useEffect, useState } from "react";
import { api, clearSession, token } from "../lib/api";

const UserContext = createContext(null);

export function useUser() {
  return useContext(UserContext);
}

const LINKS = [
  ["/", "Today"],
  ["/timer", "Timer"],
  ["/tutor", "Tutor"],
  ["/quiz", "Quiz"],
  ["/syllabus", "Syllabus"],
  ["/mistakes", "Mistakes"],
  ["/progress", "Progress"],
  ["/critiques", "Critiques"],
  ["/schedule", "Setup"],
];

export default function Shell({ children }) {
  const path = usePathname();
  const router = useRouter();
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(false);
  const [tick, setTick] = useState(0);
  const publicPage = path === "/login" || path === "/signup";

  useEffect(() => {
    const bump = () => setTick((value) => value + 1);
    window.addEventListener("auth-changed", bump);
    return () => window.removeEventListener("auth-changed", bump);
  }, []);

  useEffect(() => {
    if (process.env.NODE_ENV !== "production" || !("serviceWorker" in navigator)) return;
    navigator.serviceWorker.register("/sw.js").catch(() => {});
  }, []);

  useEffect(() => {
    let cancel = false;
    setReady(false);
    async function load() {
      if (!token()) {
        if (!cancel) {
          setUser(null);
          setReady(true);
        }
        return;
      }
      try {
        const me = await api("/auth/me");
        if (!cancel) setUser(me);
      } catch {
        if (!cancel) setUser(null);
      } finally {
        if (!cancel) setReady(true);
      }
    }
    load();
    return () => {
      cancel = true;
    };
  }, [path, tick]);

  useEffect(() => {
    if (!ready) return;
    if (!user && !publicPage) router.replace("/login");
    if (user && publicPage) router.replace("/");
  }, [ready, user, publicPage, router]);

  function logout() {
    clearSession();
    router.replace("/login");
  }

  if (!ready || (!user && !publicPage)) {
    return (
      <main>
        <p className="muted">Loading…</p>
      </main>
    );
  }

  const links = user?.role === "teacher" ? [...LINKS, ["/review", "Review"]] : LINKS;

  return (
    <UserContext.Provider value={user}>
      {user ? (
        <header className="top">
          <div>
            <strong>{user.name}</strong>
            <div className="muted">
              {user.course}
              {user.role === "teacher" ? " · Teacher" : ""}
            </div>
          </div>
          <button className="ghost" type="button" onClick={logout}>
            Log out
          </button>
        </header>
      ) : null}
      <main>{children}</main>
      {user ? (
        <nav className="nav" aria-label="Sections">
          {links.map(([href, label]) => (
            <Link key={href} href={href} className={path === href ? "active" : ""}>
              {label}
            </Link>
          ))}
        </nav>
      ) : null}
    </UserContext.Provider>
  );
}
