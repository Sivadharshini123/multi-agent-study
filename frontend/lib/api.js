export const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function token() {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

function errorMessage(data, fallback) {
  if (!data) return fallback;
  if (typeof data.detail === "string") return data.detail;
  if (Array.isArray(data.detail)) return data.detail.map((item) => item.msg || "Check the form").join(" ");
  return fallback;
}

export async function api(path, { method = "GET", body } = {}) {
  const headers = {};
  const auth = token();
  if (auth) headers.Authorization = `Bearer ${auth}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";
  const response = await fetch(`${API_URL}${path}`, {
    method,
    headers,
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  const text = await response.text();
  let data = null;
  if (text) {
    try {
      data = JSON.parse(text);
    } catch {
      data = null;
    }
  }
  if (response.status === 401 && typeof window !== "undefined" && !path.startsWith("/auth/")) {
    localStorage.removeItem("token");
    window.dispatchEvent(new Event("auth-changed"));
    if (!window.location.pathname.startsWith("/login")) window.location.href = "/login";
  }
  if (!response.ok) throw new Error(errorMessage(data, text || response.statusText));
  return data;
}

export async function apiBlob(path) {
  const headers = {};
  const auth = token();
  if (auth) headers.Authorization = `Bearer ${auth}`;
  const response = await fetch(`${API_URL}${path}`, { headers });
  if (!response.ok) {
    const text = await response.text();
    let data = null;
    try {
      data = text ? JSON.parse(text) : null;
    } catch {
      data = null;
    }
    throw new Error(errorMessage(data, text || response.statusText));
  }
  return response.blob();
}

export function saveSession(tokenValue) {
  localStorage.setItem("token", tokenValue);
  window.dispatchEvent(new Event("auth-changed"));
}

export function clearSession() {
  localStorage.removeItem("token");
  sessionStorage.removeItem("study-timer");
  window.dispatchEvent(new Event("auth-changed"));
}
