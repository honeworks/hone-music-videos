// The run's progress as the server computed it (0003, D-054): each stage's bar (done of total, the unit
// being made, elapsed, time left), the overall estimate with its end clock time, and what state each
// shot or character is in. Nothing here guesses: every number comes from `project.progress`.

import { clockAt, duration, h, STAGE_NAMES } from "./core.js";

// What each unit is, and what making one is called while it is made (D-054).
export const KIND_NAMES = {
  draft: "draft", still: "still", raw_clip: "raw clip, 16 fps", clip: "finished clip",
  sheet_take: "sheet take", view: "view", portrait_draft: "portrait draft", portrait: "portrait",
};
const MAKING = {
  draft: "drafting", still: "polishing", raw_clip: "animating", clip: "finishing",
  sheet_take: "drawing a sheet take", view: "drawing a view", portrait_draft: "drawing the portrait", portrait: "polishing the portrait",
};
// What a card says while its shot is in that state (the motion is in live.css, only on these).
export const WORKING = { drafting: "drafting…", polishing: "polishing…", animating: "animating…", finishing: "upscaling + smoothing…" };
const PER_SHOT = ["stills", "clips", "finish"];

export function stageProgress(project, name) {
  return project.progress?.stages?.[name] || null;
}

// The bar of a stage (done of total) or of the whole (a fraction); `working` adds the light motion.
export function bar(fraction, { size = "", working = false } = {}) {
  const width = `${Math.max(0, Math.min(1, fraction)) * 100}%`;
  return h("div", { class: `bar ${size} ${working ? "working" : ""}`.trim(), role: "progressbar",
    "aria-valuemin": 0, "aria-valuemax": 100, "aria-valuenow": Math.round(Math.max(0, Math.min(1, fraction)) * 100) },
  h("span", { style: { width } }));
}

// "about 1:23:45 left" that counts down between updates (`data-until`, ticked by the project view).
export function timeLeft(project, leftMs) {
  const until = project.progress.now_ms + leftMs;
  return h("span", { dataset: { until } }, duration(leftMs));
}

// What making the current unit is called; a still of a shot without a cast is drawn from text at once.
function making(ctx, c) {
  const shot = ctx.records.shots?.shots.find((s) => s.id === c.subject);
  return c.kind === "still" && shot && !shot.cast.length ? "drawing" : MAKING[c.kind];
}

function unitText(ctx, p, running) {
  const c = p.current;
  if (!c) return `${p.done} of ${p.total}`;
  const doing = running ? making(ctx, c) : `stopped while ${making(ctx, c)}`;
  return `${doing} ${c.subject} · ${c.n} of ${p.total}`;
}

// A stage's numbers in words, with its bar: the unit being made, elapsed, the time left and the load.
export function stageDetail(ctx, stage, size = "") {
  const { project } = ctx;
  const p = stageProgress(project, stage.name);
  if (!p) return null;
  const running = stage.status === "running";
  const left = !running ? null : p.left_ms === null ? h("span", {}, "estimating…")
    : h("span", {}, "about ", timeLeft(project, p.left_ms), " left", p.estimate ? " (estimate)" : "");
  const each = Object.entries(p.per_unit_ms).map(([kind, ms]) => `${duration(ms)} per ${KIND_NAMES[kind]}`).join(" · ");
  return h("div", { class: "progress-detail" },
    h("div", { class: "progress-line" }, h("strong", {}, unitText(ctx, p, running)), left),
    bar(p.total ? p.done / p.total : 0, { size, working: running }),
    h("div", { class: "progress-meta" },
      p.elapsed_ms !== null && running ? h("span", {}, h("span", { dataset: { elapsed: project.progress.now_ms - p.elapsed_ms } }, duration(p.elapsed_ms)), " elapsed") : null,
      each ? h("span", {}, each) : null,
      p.load_ms >= 1000 ? h("span", {}, `model load ${duration(p.load_ms)}`) : null,
      p.source === "files" ? h("span", {}, "counted from the files (a run from before live progress)") : null));
}

// The overall estimate of the long local part: its bar, the time left and when it should end.
export function overallDetail(project, size = "") {
  const o = project.progress?.overall;
  if (!o) return null;
  const running = project.status === "running";
  const stages = o.stages.map((s) => STAGE_NAMES[s]).join(", ");
  return h("div", { class: "progress-detail overall" },
    h("div", { class: "progress-line" }, h("strong", {}, "Overall"),
      h("span", {}, "about ", running ? timeLeft(project, o.left_ms) : duration(o.left_ms), running ? ` left · done around ${clockAt(o.ends_ms)}` : " once it runs", o.estimate ? " (estimate)" : "")),
    bar(o.fraction, { size }),
    h("div", { class: "progress-meta" }, h("span", {}, stages),
      o.estimate ? h("span", {}, "measured times of this run where known, else the reference machine's") : null));
}

// The state of one shot (D-054): what is being made for it now in one of `stages`, else its furthest file.
export function shotState(project, id, files, stages = PER_SHOT) {
  for (const name of stages) {
    const p = stageProgress(project, name);
    if (p?.current?.subject !== id) continue;
    const status = project.run.stages.find((s) => s.name === name)?.status;
    if (status === "failed") return "failed";
    if (status !== "running") break;
    return { draft: "drafting", raw_clip: "animating", clip: "finishing" }[p.current.kind];
  }
  if (files.finish) return "finished";
  if (files.clips) return "clip ready";
  if (files.stills) return "still ready";
  return "waiting";
}

// The small bar of a project's card (the sidebar, the Projects view): its running stage, else nothing.
export function cardBar(project) {
  const stages = project.progress?.stages || {};
  const [name, p] = Object.entries(stages)[0] || [];
  if (!p || project.status !== "running") return null;
  const o = project.progress.overall;
  const text = `${STAGE_NAMES[name]} ${p.done}/${p.total}${o ? ` · ${o.estimate ? "~" : ""}${duration(o.left_ms)} left` : ""}`;
  return h("span", { class: "card-progress" }, bar(p.total ? p.done / p.total : 0, { size: "thin" }), h("span", { class: "xs muted" }, text));
}
