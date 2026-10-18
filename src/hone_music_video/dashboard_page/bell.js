// The bell (0016, D-097): whenever a project starts waiting for the owner at a gate, the page rings for
// 15 seconds (chime.js) and shows "Waiting for you: <project> — <gate>" with Stop. It rings once per wait,
// not on every poll, and again at the next gate. A wait counts once two polls in a row see it, so the gates
// an unattended run passes on its own (0004) never ring. The waits already rung are kept in localStorage,
// so opening the page again does not ring for them. The header has the mute toggle and, while the browser
// keeps audio locked, "Enable sound".

import { api, GATE_NAMES, h, humanize } from "./core.js";
import { icon } from "./icons.js";
import { isLocked, isMuted, onSoundChange, rememberSound, ring, RING_MS, setMuted, stopRing, store, stored, unlock } from "./chime.js";

const POLL_MS = 4000;
const WAITING = ["awaiting_review", "waiting"];

// The projects waiting for the owner, each with its gate in words; `key` names this wait.
export function waitsOf(projects) {
  return projects.filter((p) => p.waiting || WAITING.includes(p.status)).map((p) => {
    const gate = p.waiting || "review";
    return { key: `${p.id}:${gate}`, id: p.id, name: p.name, gate: GATE_NAMES[gate] || humanize(gate) };
  });
}

// From this poll's waits, the keys the last poll saw and the keys already rung: the waits to ring now (seen
// twice in a row, never rung), and what to keep (a wait that ended is forgotten, so its gate rings again
// the next time it waits).
export function nextWaits(waits, seen, rung) {
  const now = new Set(waits.map((w) => w.key));
  const fresh = waits.filter((w) => seen.has(w.key) && !rung.has(w.key));
  const kept = [...rung, ...fresh.map((w) => w.key)].filter((key) => now.has(key));
  return { ring: fresh, seen: now, rung: new Set(kept) };
}

function readRung() {
  try { return new Set(JSON.parse(stored("bell.rung") || "[]")); } catch { return new Set(); } // not JSON
}

const saveRung = (rung) => store("bell.rung", JSON.stringify([...rung]));

let shown = []; // the waits in the banner: rung, still waiting, not stopped
let drawn = "";

function stop() {
  stopRing();
  shown = [];
  draw();
}

// "Enable sound": a click lets the page play sound (and rings the bell if a wait is in the banner).
function enableButton(extra = "") {
  return h("button", { type: "button", class: `button ${extra}`.trim(), onclick: () => unlock().then(() => ring(shown.length ? RING_MS : 0)) },
    icon("bell"), "Enable sound");
}

function banner() {
  const note = isMuted() ? h("p", { class: "xs" }, "The bell is muted (the bell button at the top of the sidebar).")
    : isLocked() ? h("p", { class: "xs row wrap" }, "Sound is locked: the browser plays none until you click on this page.", enableButton()) : null;
  return [h("span", { class: "gate-icon" }, icon("bell")),
    h("div", { class: "grow stack small-gap" }, shown.map((w) => h("p", {}, h("strong", {}, "Waiting for you: "),
      h("a", { href: `#/p/${w.id}`, dir: "auto" }, w.name), ` — ${w.gate}`)), note),
    h("button", { type: "button", class: "button", onclick: stop }, icon("x"), "Stop")];
}

// The banner, the mute toggle and "Enable sound", drawn again only when one of them changed.
function draw() {
  const state = JSON.stringify([shown.map((w) => w.key), isMuted(), isLocked()]);
  if (state === drawn) return;
  drawn = state;
  const node = document.getElementById("bell");
  node.hidden = !shown.length;
  node.replaceChildren(...(shown.length ? banner() : []));
  const muted = isMuted();
  const toggle = document.getElementById("sound");
  toggle.replaceChildren(icon(muted ? "bell-off" : "bell"));
  toggle.setAttribute("aria-pressed", String(muted));
  toggle.setAttribute("aria-label", muted ? "The approval bell is muted; unmute it" : "Mute the approval bell");
  toggle.title = toggle.getAttribute("aria-label");
  document.getElementById("enable-sound").replaceChildren(...(!muted && isLocked() ? [enableButton("small-button")] : []));
}

async function poll(state) {
  let projects;
  try { projects = await api("/projects"); } catch { return; }
  const next = nextWaits(waitsOf(projects), state.seen, readRung());
  state.seen = next.seen;
  saveRung(next.rung);
  shown = [...shown.filter((w) => next.seen.has(w.key)), ...next.ring];
  if (next.ring.length) ring();
  else if (!shown.length) stopRing();
  draw();
}

export function watchWaits() {
  document.getElementById("sound").addEventListener("click", () => {
    if (isMuted()) { setMuted(false); unlock(); } else setMuted(true);
  });
  rememberSound();
  onSoundChange(draw);
  const state = { seen: new Set() };
  draw();
  poll(state);
  setInterval(() => poll(state), POLL_MS);
}
