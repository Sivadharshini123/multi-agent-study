export const WEEKDAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"];

export const STATUS_LABELS = {
  not_started: "Not started",
  learning: "Learning",
  revised: "Revised",
  mastered: "Mastered",
};

export function todayWeekday() {
  return (new Date().getDay() + 6) % 7;
}

export function minutesToTime(minutes) {
  const hours = Math.floor(minutes / 60);
  const mins = minutes % 60;
  return `${String(hours).padStart(2, "0")}:${String(mins).padStart(2, "0")}`;
}

export function timeToMinutes(value) {
  const [hours, mins] = value.split(":").map(Number);
  if (Number.isNaN(hours) || Number.isNaN(mins)) return 0;
  return hours * 60 + mins;
}

export function formatClock(totalSeconds) {
  const seconds = Math.max(0, totalSeconds);
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${String(minutes).padStart(2, "0")}:${String(rest).padStart(2, "0")}`;
}

export function percent(value) {
  if (value == null || Number.isNaN(value)) return "—";
  return `${Math.round(value * 100)}%`;
}

export function subjectName(subjects, id) {
  return subjects.find((item) => item.id === id)?.name || id;
}

export function cite(item) {
  if (!item) return "";
  const chapter = item.chapter || "Notes";
  const page = item.page == null ? "?" : item.page;
  return `${chapter}, p. ${page}`;
}
