// Shared helpers: the JSON API, element building, times as m:ss.mmm (D-007), names, the theme, a toast.

export async function api(path, { method = "GET", body } = {}) {
  const response = await fetch(`/api${path}`, {
    method,
    headers: body === undefined ? {} : { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.error || response.statusText);
    error.problems = data.problems || [];
    throw error;
  }
  return data;
}

function build(node, attrs, children) {
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value === undefined || value === null || value === false) continue;
    if (key.startsWith("on")) node.addEventListener(key.slice(2), value);
    else if (key === "dataset") Object.assign(node.dataset, value);
    else if (key === "style" && typeof value === "object") Object.assign(node.style, value);
    else node.setAttribute(key, value === true ? "" : value);
  }
  for (const child of children.flat(Infinity)) {
    if (child === undefined || child === null || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

// h("div", {class: "x", onclick: fn, style: {width: "3px"}}, child, "text", [more children])
export function h(tag, attrs = {}, ...children) {
  return build(document.createElement(tag), attrs, children);
}

export function s(tag, attrs = {}, ...children) {
  return build(document.createElementNS("http://www.w3.org/2000/svg", tag), attrs, children);
}

// Integer milliseconds as m:ss.mmm (3:32.050); records keep milliseconds, only the page formats them.
export function formatMs(ms) {
  if (ms === null || ms === undefined) return "";
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  const millis = Math.round(ms % 1000);
  return `${minutes}:${String(seconds).padStart(2, "0")}.${String(millis).padStart(3, "0")}`;
}

// m:ss.mmm (or plain seconds) back to integer milliseconds; NaN when it does not read as a time.
export function parseMs(text) {
  const match = /^\s*(?:(\d+):)?(\d{1,2})(?:\.(\d{1,3}))?\s*$/.exec(text);
  if (!match) return NaN;
  const [, minutes = "0", seconds, millis = "0"] = match;
  return Number(minutes) * 60000 + Number(seconds) * 1000 + Number(millis.padEnd(3, "0"));
}

// A length in words, for durations: "2.4 s", "1 min 12 s".
export function spoken(ms) {
  if (ms === null || ms === undefined) return "";
  if (ms < 1000) return `${ms} ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)} s`;
  return `${Math.floor(ms / 60000)} min ${Math.round((ms % 60000) / 1000)} s`;
}

// A duration as m:ss, or h:mm:ss from an hour (progress, 0003).
export function duration(ms) {
  if (ms === null || ms === undefined) return "";
  const total = Math.max(0, Math.round(ms / 1000));
  const [hours, minutes, seconds] = [Math.floor(total / 3600), Math.floor((total % 3600) / 60), total % 60];
  const ss = String(seconds).padStart(2, "0");
  return hours ? `${hours}:${String(minutes).padStart(2, "0")}:${ss}` : `${minutes}:${ss}`;
}

// A moment (epoch ms) as a clock time, with the day when it is not today.
export function clockAt(ms) {
  const at = new Date(ms);
  const time = at.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  return at.toDateString() === new Date().toDateString() ? time : `${at.toLocaleDateString([], { weekday: "short" })} ${time}`;
}

export const LABELS = {
  not_started: "not started", pending: "waiting", running: "running", done: "done", failed: "failed",
  blocked: "blocked", interrupted: "interrupted", paused: "paused", awaiting_review: "needs you", completed: "finished",
  skipped: "skipped", queued: "queued", unreadable: "cannot be read",
};

export const STAGE_NAMES = {
  measure: "Measure the song", transcribe: "Hear the words", lyrics: "Time the lyrics",
  check_lyrics: "Check the lyrics", plan: "Plan the scenes", check_plan: "Check the shot list",
  scenes: "Make the scenes", clips: "Clips", finish: "Finish", assemble: "Assemble",
};

export const GATE_NAMES = {
  review_lyrics: "Review the timed lyrics", review_plan: "Review the plan", review_scenes: "Review the scenes",
};

// When a running stage started: its record, else the run's step_started event (the record has no start
// time until the step ends).
export function startedAt(ctx, stage) {
  const event = [...ctx.events].reverse().find((e) => e.event === "step_started" && e.step === stage.name);
  return stage.started_at || event?.at || new Date().toISOString();
}

// Where a project's run stands, in words (the sidebar and the Projects view).
export function runWhere(project) {
  if (project.problem) return project.problem; // a project this version cannot read
  if (project.waiting) return `Needs you: ${GATE_NAMES[project.waiting] || humanize(project.waiting)}`;
  if (project.status === "completed") return "Finished";
  if (project.status === "queued") return "Queued";
  if (project.status === "not_started") return "Not started"; // made by `new`, waiting for Start
  return project.stage ? STAGE_NAMES[project.stage] || humanize(project.stage) : "Starting";
}

export const FRAMINGS = ["extreme-wide", "wide", "medium", "close-up", "extreme-close-up", "insert"];

export const humanize = (text) => String(text || "").replaceAll("_", " ").replaceAll("-", " ");

export function pill(status) {
  return h("span", { class: `pill ${status}` }, LABELS[status] || humanize(status));
}

export function toast(text) {
  const node = document.getElementById("toast");
  node.textContent = text;
  node.hidden = false;
  clearTimeout(toast.timer);
  toast.timer = setTimeout(() => { node.hidden = true; }, 3500);
}

export function empty(icon, title, text) {
  return h("div", { class: "empty" }, icon, h("strong", {}, title), text ? h("p", {}, text) : null);
}

export function isDark() {
  const theme = document.documentElement.dataset.theme;
  return theme ? theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
}

export function setTheme(theme) {
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem("theme", theme); } catch { /* a private window */ }
  dispatchEvent(new Event("themechange"));
}

export function savedTheme() {
  const fromUrl = new URLSearchParams(location.search).get("theme"); // ?theme=dark, for screenshots
  if (fromUrl) return fromUrl;
  try { return localStorage.getItem("theme"); } catch { return null; }
}

// A picked file as the API takes it: {name, data_b64}.
export function readFile(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve({ name: file.name, data_b64: String(reader.result).split(",", 2)[1] });
    reader.onerror = () => reject(reader.error);
    reader.readAsDataURL(file);
  });
}
