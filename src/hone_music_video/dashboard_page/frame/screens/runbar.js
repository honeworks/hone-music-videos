// The run bar (§10): the run's state and its controls, the item being made with its elapsed time, "n of m",
// what is next, the remaining estimate with "done at", what the estimate leaves out, and licence warnings.
// Elapsed time ticks locally from the last RunView, so the bar needs no polling.
// Hone Frame: ported from dashboard_page/screens/runbar.js.

import { api } from "../api.js";
import { applyRun, itemById } from "../state.js";
import { at, clockTime, duration, h, icon, itemHref, pill, plural, range, redrawIf, refill, RUN_STATUS, toast } from "../ui.js";

const CAN = {
  run: ["idle", "stopped", "done", "failed", "waiting"], // Run also goes on past an item left waiting
  pause: ["running"],
  resume: ["paused"],
  stop: ["queued", "running", "pausing", "paused", "waiting"],
};
const LABELS = { run: "Run", pause: "Pause", resume: "Resume", stop: "Stop" };
const ICONS = { run: "play", pause: "pause", resume: "play", stop: "stop" };
const HINTS = {
  run: "Make every item marked to run, top to bottom",
  pause: "Cancel the image being made now; it stays marked. Resume starts again from the topmost marked item",
  resume: "Continue from the topmost marked item",
  stop: "Cancel the image being made now and end the run",
};

export function elapsedOf(run) {
  if (!run || !run.current) return 0;
  const base = run.current.elapsed_s || 0;
  return base + (run.received_at != null ? (performance.now() - run.received_at) / 1000 : 0);
}

// "n of m": the items this run made, the one it is making, and the ones still marked (`remaining` does not
// hold the current one).
export function progressOf(run) {
  const current = run.current ? run.current.item : null;
  const total = run.made.length + run.remaining.length + (current ? 1 : 0);
  return { made: run.made.length, n: run.made.length + (current ? 1 : 0), total, current, remaining: run.remaining };
}

export function createRunBar(projectId) {
  const statusBox = h("div", { class: "runbar-status" });
  const controls = h("div", { class: "runbar-controls", role: "group", "aria-label": "Run controls" });
  const now = h("div", { class: "runbar-now", "aria-live": "polite" });
  const progress = h("div", { class: "runbar-progress" });
  const notes = h("div", { class: "runbar-notes" });
  const el = h("section", { class: "runbar", "aria-label": "Run" },
    h("div", { class: "runbar-main" }, statusBox, controls, now, progress), notes);
  const elapsedNode = h("span", { class: "mono elapsed" });
  let run = null;
  let view = null;
  let busy = null;

  async function act(action) {
    busy = action;
    draw();
    try {
      applyRun(await api.runAction(projectId, action));
    } catch (error) {
      toast(`${LABELS[action]}: ${error.message}`, { kind: "error" });
    } finally {
      busy = null;
      draw();
    }
  }

  function drawControls(status, marked) {
    redrawIf(controls, JSON.stringify([status, marked, busy]), () => Object.keys(CAN).map((action) => {
      if (action === "resume" && status !== "paused") return null;
      if (action === "run" && status === "paused") return null;
      const allowed = CAN[action].includes(status) && !busy && !(action === "run" && marked === 0);
      return h("button", {
        type: "button", class: `button ${action === "run" || action === "resume" ? "primary" : ""} ${action === "stop" ? "danger-ghost" : ""}`,
        disabled: !allowed, title: action === "run" && marked === 0 ? "Nothing is marked to run" : HINTS[action],
        "data-key": action, onclick: () => act(action),
      }, icon(ICONS[action]), busy === action ? `${LABELS[action]}…` : LABELS[action]);
    }));
  }

  function nowLine(status, p) {
    if (status === "waiting") {
      const id = run.item; // the item the run waits for (it may be a ref of the next item)
      const item = id ? itemById(id) : null;
      const ask = item && item.candidates.length ? `pick one of its ${item.candidates.length} images` : "accept it";
      return [h("strong", {}, "Waiting for you: "), id ? h("a", { href: itemHref(projectId, id) }, id) : "an item",
        ` — ${ask}, and the run continues by itself.`];
    }
    if (p.current) {
      const item = itemById(p.current);
      const estimate = item && item.estimate ? ` · usually ${range(item.estimate.low_s, item.estimate.high_s)}` : "";
      return [h("span", { class: "overline" }, status === "pausing" ? "Cancelling " : "Making "),
        h("a", { href: itemHref(projectId, p.current) }, p.current), " ", elapsedNode, h("span", { class: "muted" }, estimate)];
    }
    const next = p.remaining[0];
    if (next) return [h("span", { class: "overline" }, CAN.run.includes(status) ? "First to make " : "Next "), h("a", { href: itemHref(projectId, next) }, next)];
    return [h("span", { class: "muted" }, "Nothing is marked to run. Mark an item to make it (again).")];
  }

  function progressLine(p, marked) {
    const est = run.estimate;
    const parts = [];
    if (p.total) {
      parts.push(h("span", { class: "count" }, h("strong", {}, `${p.n} of ${p.total}`), p.current ? " being made" : " made"));
      parts.push(h("progress", { max: String(p.total), value: String(p.made), "aria-label": `${p.made} of ${p.total} made` }));
    } else if (marked) parts.push(h("span", { class: "count" }, plural(marked, "item"), " marked"));
    if (est && (est.high_s > 0 || !est.missing.length)) {
      parts.push(h("span", {}, h("strong", {}, range(est.low_s, est.high_s)), " left"));
      if (run.done_at) parts.push(h("span", {}, "done at about ", h("strong", {}, at(run.done_at))));
    } else if (p.remaining.length) parts.push(h("span", { class: "muted" }, "no estimate yet"));
    return parts;
  }

  // One line however many models lack a measurement; the list opens on demand.
  function missingLine(missing) {
    const items = missing.reduce((n, m) => n + m.items, 0);
    const each = missing.map((m) => h("li", {}, `${m.model} at ${m.size || "its default size"}: ${plural(m.items, "item")}`));
    return h("details", { class: "note-line muted missing" },
      h("summary", {}, `No measurement yet for ${plural(items, "item")}: left out of the estimate`),
      h("ul", {}, ...each));
  }

  function noteLines() {
    const lines = [];
    if (run.reason && ["failed", "stopped", "paused", "waiting", "queued"].includes(run.status)) {
      lines.push(h("p", { class: `note-line ${run.status === "failed" ? "danger" : ""}` }, run.reason));
    }
    const missing = run.estimate ? run.estimate.missing : [];
    if (missing.length) lines.push(missingLine(missing));
    for (const w of view.warnings) lines.push(h("p", { class: "note-line warn" }, icon("flag"), w)); // one per research-licence model of a marked item
    return lines;
  }

  function draw() {
    if (!run || !view) return;
    const status = run.status;
    const marked = view.items.filter((it) => it.marked).length;
    const p = progressOf(run);
    el.dataset.status = status;
    redrawIf(statusBox, status, () => pill("run", status, RUN_STATUS));
    drawControls(status, marked);
    refill(now, nowLine(status, p));
    refill(progress, progressLine(p, marked));
    refill(notes, noteLines());
    tick();
  }

  function tick() {
    elapsedNode.textContent = run && run.current ? clockTime(elapsedOf(run)) : "";
    elapsedNode.title = run && run.current ? `${duration(elapsedOf(run))} so far` : "";
  }
  const timer = setInterval(tick, 1000);

  return {
    el,
    update(nextRun, nextView) {
      run = nextRun;
      view = nextView;
      draw();
    },
    destroy: () => clearInterval(timer),
  };
}
