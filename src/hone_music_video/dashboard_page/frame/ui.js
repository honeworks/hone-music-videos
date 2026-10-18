// Small DOM and wording helpers of the Scenes view. Text always goes in as text nodes: nothing from the
// server is parsed as HTML.
// Hone Frame: ported from dashboard_page/ui.js. The links lead to the video project's Scenes view
// (#/p/<video>/scenes/i/<item>); toasts go to the page's #frame-toasts region.

const PROPS = new Set(["value", "checked", "selected", "disabled", "indeterminate"]);

export function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [key, value] of Object.entries(attrs || {})) {
    if (value == null || value === false) continue;
    if (key.startsWith("on") && typeof value === "function") el.addEventListener(key.slice(2), value);
    else if (key === "class") el.className = value;
    else if (key === "dataset") Object.assign(el.dataset, value);
    else if (PROPS.has(key)) el[key] = value;
    else el.setAttribute(key, value === true ? "" : String(value));
  }
  append(el, children);
  return el;
}

export function append(el, children) {
  for (const child of [children].flat(Infinity)) {
    if (child == null || child === false) continue;
    el.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return el;
}

const PATHS = {
  play: "M7 5v14l11-7z",
  pause: "M8 5v14M16 5v14",
  stop: "M6 6h12v12H6z",
  bell: "M6 16V11a6 6 0 0 1 12 0v5l2 2H4zM10 20a2 2 0 0 0 4 0",
  check: "M5 12l5 5L20 7",
  x: "M6 6l12 12M18 6L6 18",
  mark: "M4 12a8 8 0 1 0 2.3-5.7M4 4v5h5",
  upload: "M12 16V4M7 9l5-5 5 5M5 20h14",
  open: "M14 4h6v6M20 4l-9 9M18 14v6H4V6h6",
  up: "M6 15l6-6 6 6",
  down: "M6 9l6 6 6-6",
  flag: "M5 21V4h11l-2 4 2 4H5",
  sound: "M5 9v6h4l5 4V5L9 9zM17 9a4 4 0 0 1 0 6",
  download: "M12 4v12M7 11l5 5 5-5M5 20h14",
};

export function icon(name) {
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", "0 0 24 24");
  svg.setAttribute("class", "icon");
  svg.setAttribute("aria-hidden", "true");
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", PATHS[name] || "");
  svg.append(path);
  return svg;
}

export const ITEM_STATUS = {
  todo: "Not made yet",
  running: "Making now",
  waiting: "Waiting for you",
  done: "Done",
  failed: "Failed",
  provided: "Provided file",
};

export const RUN_STATUS = {
  idle: "Not running",
  queued: "Queued",
  running: "Running",
  pausing: "Pausing…",
  paused: "Paused",
  waiting: "Waiting for you",
  stopped: "Stopped",
  failed: "Failed",
  done: "Finished",
};

export function pill(kind, status, labels) {
  const text = labels[status] || status || "unknown";
  return h("span", { class: `pill pill-${status}`, dataset: { kind } }, h("span", { class: "pill-dot", "aria-hidden": "true" }), text);
}

export function duration(seconds) {
  if (seconds == null || !Number.isFinite(seconds)) return "—";
  const s = Math.max(0, Math.round(seconds));
  if (s < 60) return `${s} s`;
  const m = Math.floor(s / 60);
  if (m < 60) return s % 60 && m < 10 ? `${m} min ${s % 60} s` : `${m} min`;
  return `${Math.floor(m / 60)} h ${m % 60} min`;
}

export function clockTime(seconds) {
  const s = Math.max(0, Math.floor(seconds || 0));
  const mm = String(Math.floor(s / 60) % 60).padStart(2, "0");
  const ss = String(s % 60).padStart(2, "0");
  return s >= 3600 ? `${Math.floor(s / 3600)}:${mm}:${ss}` : `${Math.floor(s / 60)}:${ss}`;
}

export function range(low, high) {
  if (low == null) return "—";
  if ((high ?? low) < 5) return "a few seconds";
  if (high == null || Math.round(low) === Math.round(high)) return `about ${duration(low)}`;
  if (low >= 60 && high >= 60) return `${Math.round(low / 60)}–${Math.round(high / 60)} min`;
  return `${duration(low)} – ${duration(high)}`;
}

// "14:32" for an ISO time or an "HH:MM" string; a date is added when it is not today.
export function at(value) {
  if (!value) return "";
  if (/^\d{1,2}:\d{2}$/.test(value)) return value;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value);
  const time = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", hourCycle: "h23" });
  return date.toDateString() === new Date().toDateString() ? time : `${date.toLocaleDateString()} ${time}`;
}

export function plural(n, one, many = `${one}s`) {
  return `${n} ${n === 1 ? one : many}`;
}

let toastSeq = 0;
// A short message; `actions` are [label, fn] buttons; `sticky` keeps it until dismissed.
export function toast(message, { kind = "info", actions = [], sticky = false, onDismiss } = {}) {
  const region = document.getElementById("frame-toasts");
  const id = `toast-${++toastSeq}`;
  const close = () => { node.remove(); if (onDismiss) onDismiss(); };
  const node = h("div", { class: `toast toast-${kind}`, id, role: kind === "error" ? "alert" : "status" },
    h("div", { class: "toast-text" }, message),
    h("div", { class: "toast-actions" },
      actions.map(([label, fn]) => h("button", { type: "button", class: "button small", onclick: () => { node.remove(); fn(); } }, label)),
      h("button", { type: "button", class: "iconbutton small", "aria-label": "Dismiss", onclick: close }, icon("x"))));
  region.append(node);
  if (!sticky) setTimeout(() => node.isConnected && node.remove(), kind === "error" ? 8000 : 4000);
  return node;
}

// The refusal of a 400 answer: the message and each item it names.
export function errorBox(error) {
  if (!error) return null;
  return h("div", { class: "errorbox", role: "alert" },
    h("strong", {}, error.message || String(error)),
    error.items && error.items.length
      ? h("ul", {}, error.items.map((it) => h("li", {}, it.item ? h("code", {}, it.item) : null, it.item ? ": " : "", it.message)))
      : null);
}

export function emptyState(title, text) {
  return h("div", { class: "empty" }, h("strong", {}, title), text ? h("p", {}, text) : null);
}

export function imageOrPlaceholder(src, alt, cls = "thumb") {
  if (!src) return h("span", { class: `${cls} placeholder`, role: "img", "aria-label": alt ? `${alt}: no image yet` : "no image yet" });
  return h("img", { class: cls, src, alt: alt || "", loading: "lazy", decoding: "async" });
}

// Swap an <img> or its placeholder only when the picture changed, so the browser keeps what it shows.
export function setImage(holder, src, alt, cls = "thumb") {
  const current = holder.firstElementChild;
  if (current && current.tagName === "IMG" && current.getAttribute("src") === src) return;
  if (current && !src && current.classList.contains("placeholder")) return;
  holder.replaceChildren(imageOrPlaceholder(src, alt, cls));
}

// Replace a container's children, keeping focus on the element with the same data-key (a live update must
// not throw the owner's keyboard focus away).
export function refill(container, ...children) {
  const active = document.activeElement;
  const key = active && container.contains(active) ? active.dataset.key : null;
  container.replaceChildren();
  append(container, children);
  if (key) {
    const again = container.querySelector(`[data-key="${CSS.escape(key)}"]`);
    if (again) again.focus();
  }
}

// Draw a section again only when what it shows changed.
export function redrawIf(container, signature, draw) {
  if (container.dataset.sig === signature) return;
  container.dataset.sig = signature;
  refill(container, draw());
}

export const projectHref = (project) => `#/p/${encodeURIComponent(project)}/scenes`;
export const itemHref = (project, item) => `${projectHref(project)}/i/${encodeURIComponent(item)}`;

// This browser's own settings (theme, sound). Storage may be blocked: the choice then lasts for this visit.
export function stored(key) {
  try { return localStorage.getItem(key); } catch { return null; }
}

export function store(key, value) {
  try {
    if (value == null) localStorage.removeItem(key); else localStorage.setItem(key, value);
  } catch { /* the choice lasts for this visit only */ }
}
