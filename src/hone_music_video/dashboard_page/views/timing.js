// The owner's timing in the Lyrics view (0018, D-119): while the lyrics gate waits, a line's start and
// end can be set to the play position or nudged by ±100 ms and ±500 ms. Changes are a draft, kept per
// project across redraws, until "Save timing" sends them (`POST lyrics-timing`); the server checks them,
// keeps the timeline as a version and runs the checks again. A null in the draft takes a saved edit back.

import { api, formatMs, h, toast } from "../core.js";
import { icon } from "../icons.js";
import { playSlice } from "../player.js";

const drafts = new Map(); // project id -> {line id: {start_ms, end_ms} | null}
const opened = new Map(); // project id -> the lines whose timing is open
const rippling = new Map(); // project id -> "Move the following lines too" is on
export const NUDGES = [-500, -100, 100, 500];

export function draftOf(id) {
  if (!drafts.has(id)) drafts.set(id, {});
  return drafts.get(id);
}

function openOf(id) {
  if (!opened.has(id)) opened.set(id, new Set());
  return opened.get(id);
}

// A line's times as shown: the draft's; a saved edit taken back (null), its measured times; else the line's.
export function timesOf(line, draft, measured = {}) {
  const back = draft[line.id] === null && measured[line.id];
  if (back) return { start_ms: back[0], end_ms: back[1] };
  return draft[line.id] || { start_ms: line.start_ms, end_ms: line.end_ms };
}

export const measuredOf = (ctx) => ctx.records.lyrics_timing?.measured || {};

// Approve at the lyrics gate asks first while the draft has unsaved times: they would not be used.
export function approveLyrics(id, ask = confirm) {
  return {
    label: "Approve", path: "approve", done: "Review the timed lyrics: approved. The run continues.",
    body: () => {
      const unsaved = Object.keys(draftOf(id));
      const sure = !unsaved.length || ask(`${unsaved.join(", ")}: new times not saved. Approve without them? (Cancel, then Save timing, to use them.)`);
      return sure ? { gate: "review_lyrics" } : null;
    },
  };
}

// One edge moved to `ms` (whole, inside the song); null when the line would have no length.
export function moved(times, edge, ms, duration) {
  const next = { ...times, [`${edge}_ms`]: Math.round(Math.min(Math.max(ms, 0), duration)) };
  return next.start_ms < next.end_ms ? next : null;
}

export const nudged = (times, edge, delta, duration) => moved(times, edge, times[`${edge}_ms`] + delta, duration);

export function editable(ctx) {
  return ctx.project.run.waiting === "review_lyrics";
}

// With "Move the following lines too" on, the lines after this one move by the same amount; moving the
// start then moves the whole line.
export function shifted(lines, line, before, times, edge, draft, measured, total) {
  const delta = times[`${edge}_ms`] - before[`${edge}_ms`];
  const changes = { [line.id]: edge === "start" ? { start_ms: times.start_ms, end_ms: Math.min(before.end_ms + delta, total) } : times };
  for (const next of lines.slice(lines.findIndex((l) => l.id === line.id) + 1)) {
    const now = timesOf(next, draft, measured);
    const start = now.start_ms + delta, end = Math.min(now.end_ms + delta, total);
    if (start >= 0 && start < end) changes[next.id] = { start_ms: start, end_ms: end };
  }
  return changes;
}

function change(ctx, line, times, before, edge) {
  if (!times) return toast("A line must end after it starts.");
  const draft = draftOf(ctx.id);
  if (!rippling.get(ctx.id)) draft[line.id] = times;
  else Object.assign(draft, shifted(ctx.records.timeline.lines, line, before, times, edge, draft, measuredOf(ctx), ctx.records.timeline.duration_ms));
  ctx.render();
}

function edgeRow(ctx, line, times, edge) {
  const total = ctx.records.timeline.duration_ms;
  const here = () => moved(times, edge, ctx.player.audio.currentTime * 1000, total);
  return h("div", { class: "timing-row" }, h("span", { class: "timing-label" }, edge === "start" ? "Start" : "End"),
    h("span", { class: "mono" }, formatMs(times[`${edge}_ms`])),
    NUDGES.map((delta) => h("button", { type: "button", class: "button small", "aria-label": `${edge} ${delta > 0 ? "+" : ""}${delta} ms`,
      onclick: () => change(ctx, line, nudged(times, edge, delta, total), times, edge) }, `${delta > 0 ? "+" : "−"}${Math.abs(delta)}`)),
    h("button", { type: "button", class: "button small", onclick: () => change(ctx, line, here(), times, edge) }, `Set ${edge} here`));
}

// The timing of one line, under it when opened.
export function timingEditor(ctx, line, times) {
  const draft = draftOf(ctx.id);
  const saved = ctx.records.timeline.owner_timed?.includes(line.id);
  // a saved edit is taken back on the server (null); a draft is only forgotten
  const backToMeasured = () => { if (saved) draft[line.id] = null; else delete draft[line.id]; ctx.render(); };
  return h("div", { class: "timing-editor" }, edgeRow(ctx, line, times, "start"), edgeRow(ctx, line, times, "end"),
    h("div", { class: "row wrap" },
      h("button", { type: "button", class: "button small", onclick: () => playSlice(ctx.player, times.start_ms, times.end_ms) }, icon("play"), "Play the line"),
      h("label", { class: "row small" }, h("input", { type: "checkbox", checked: Boolean(rippling.get(ctx.id)),
        onchange: (event) => { rippling.set(ctx.id, event.target.checked); } }), "Move the following lines too"),
      (saved && draft[line.id] !== null) || draft[line.id] ? h("button", { type: "button", class: "button small ghost", onclick: backToMeasured }, "Back to the measured times") : null));
}

// The toggle beside a line that opens its timing (only while the gate waits).
export function timingToggle(ctx, line) {
  if (!editable(ctx)) return null;
  const open = openOf(ctx.id);
  return h("button", { type: "button", class: `button small ghost timing-toggle${open.has(line.id) ? " on" : ""}`, "aria-expanded": String(open.has(line.id)),
    "aria-label": `Edit the timing of ${line.id}`, onclick: () => { if (open.has(line.id)) open.delete(line.id); else open.add(line.id); ctx.render(); } }, icon("clock"));
}

export const isOpen = (ctx, line) => editable(ctx) && openOf(ctx.id).has(line.id);

async function save(ctx, button) {
  button.disabled = true;
  try {
    const saved = await api(`/projects/${ctx.id}/lyrics-timing`, { method: "POST", body: draftOf(ctx.id) });
    drafts.set(ctx.id, {});
    const errors = saved.lyrics_timing.errors;
    toast(`Timing saved. The checks ran again: ${errors ? `${errors} ${errors === 1 ? "error" : "errors"}` : "no errors"}.`);
    ctx.refresh();
  } catch (error) {
    toast(error.problems?.length ? `Not saved: ${error.problems.join("; ")}` : error.message);
    button.disabled = false;
  }
}

// "Save timing" while the draft has changes; and what became of the saved edits after a rerun.
export function timingBar(ctx) {
  const changed = Object.keys(draftOf(ctx.id));
  const dropped = Object.entries(ctx.records.lyrics_timing?.dropped || {});
  const notice = dropped.length ? h("p", { class: "small auto-stopped" }, icon("alert"),
    `Your timing could not be kept for ${dropped.map(([id, why]) => `${id} (${why})`).join("; ")}.`) : null;
  if (!changed.length || !editable(ctx)) return notice;
  const button = h("button", { type: "button", class: "button primary" }, icon("check"), "Save timing");
  button.addEventListener("click", () => save(ctx, button));
  return h("div", { class: "timing-bar" }, notice,
    h("span", { class: "grow" }, `${changed.length} ${changed.length === 1 ? "line" : "lines"} with new times: ${changed.join(", ")}. Not saved yet.`),
    h("button", { type: "button", class: "button ghost", onclick: () => { drafts.set(ctx.id, {}); ctx.render(); } }, "Discard"), button);
}
