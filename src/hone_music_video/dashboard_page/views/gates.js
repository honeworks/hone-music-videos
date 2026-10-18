// The Overview's main card: the gate waiting for the owner with a preview of what it approves and the
// same controls as the gate's own page (decide.js, 0018), or else what the run is doing (a stage with its
// real progress, a failure, the finished video).

import { formatMs, FRAMINGS, GATE_NAMES, h, humanize, spoken, STAGE_NAMES, startedAt } from "../core.js";
import { icon } from "../icons.js";
import { gateControls } from "../decide.js";
import { approveLyrics } from "./timing.js";
import { actionButton, blocked, shotsBar, stat, zoomPicture } from "../parts.js";
import { stageDetail } from "../progress.js";

const problems = (report) => report ? `${report.errors.length} errors · ${report.warnings.length} warnings` : "not checked yet";

function lyricsPreview(ctx) {
  const timed = ctx.records.timeline;
  const words = timed.lines.reduce((sum, line) => sum + line.words.length, 0);
  return [h("div", { class: "stats" }, stat(timed.lines.length, "lines"), stat(timed.sections.length, "sections"),
    stat(timed.instrumental.length, "instrumental spans"), stat(words, "words")),
  h("ol", { class: "mini-lines" }, timed.lines.slice(0, 4).map((line) => h("li", {},
    h("span", { class: "mono faint" }, formatMs(line.start_ms)), h("span", { dir: "auto" }, line.text)))),
  h("p", { class: "muted small" }, `Checks: ${problems(ctx.records.lyrics_check)}.`)];
}

function planPreview(ctx) {
  const shots = ctx.records.shots.shots;
  const lengths = shots.map((s) => s.end_ms - s.start_ms);
  const mix = Object.fromEntries(FRAMINGS.map((f) => [f, shots.filter((s) => s.framing === f)]).filter(([, l]) => l.length));
  return [h("div", { class: "stats" }, stat(shots.length, "shots"), stat(spoken(Math.round(lengths.reduce((a, b) => a + b, 0) / shots.length)), "average"),
    stat(spoken(Math.min(...lengths)), "shortest"), stat(spoken(Math.max(...lengths)), "longest")),
  h("div", { class: "mix" }, Object.entries(mix).map(([framing, list]) => h("span", { class: `f-${framing}`, style: { flex: list.length }, title: `${humanize(framing)}: ${list.length}` }))),
  h("p", { class: "muted small" }, `Checks: ${problems(ctx.records.plan_check)}. ${ctx.records.plan ? `${ctx.records.plan.items} items to draw.` : ""} After this the scenes are drawn on the local models.`)];
}

// review_scenes (0027): every scene's start frame (its picture in use), or what still has none.
function scenesPreview(ctx) {
  const missing = ctx.records.scenes_missing || [];
  const shots = ctx.records.shots?.shots || [];
  if (missing.length) return [h("p", { class: "muted" }, `${missing.length} ${missing.length === 1 ? "scene has" : "scenes have"} no picture in use yet (${missing.slice(0, 6).join(", ")}${missing.length > 6 ? "…" : ""}). Open the Scenes to accept, pick or run them.`)];
  return [h("div", { class: "mini-takes" }, h("div", { class: "take-row" }, shots.map((shot) => {
    const src = ctx.records.shot_files[shot.id]?.stills;
    return src ? zoomPicture(ctx, src, `${shot.id} · start frame`) : null;
  }))),
  h("p", { class: "muted small" }, "Approve makes the clips from these pictures; a scene changed later remakes only its clip.")];
}

const GATES = {
  review_lyrics: ["lyrics", "Read the lines and their times; play any line against the song.", lyricsPreview],
  review_plan: ["plan", "Every shot on the song's timeline with its framing and cast; the project file the scenes are drawn from.", planPreview],
  review_scenes: ["scenes", "Every scene's picture, before their clips are made.", scenesPreview],
};

// The events that decide a gate: after one, an earlier unattended stop there no longer stands (D-076).
const DECIDED = ["gate_approved", "gate_auto_approved", "gate_rejected", "gate_edited"];

function stoppedHere(ctx, gate) {
  for (const event of [...ctx.events].reverse()) {
    if (event.gate === gate && DECIDED.includes(event.event)) return false;
    if (event.event === "auto_stopped") return event.gate === gate;
  }
  return false;
}

// An unattended project at a gate: stopped for the owner (its check found errors), or about to pass it.
function autoNotice(ctx, gate) {
  if (blocked(ctx, gate) || stoppedHere(ctx, gate)) {
    return h("p", { class: "auto-stopped small" }, h("strong", {}, "Stopped: needs you. "), "This project runs without stopping for approval, but the checks found errors here; only you can accept or fix them.");
  }
  return h("p", { class: "muted small" }, "Continuing on its own…");
}

function waitingCard(ctx, gate) {
  const [view, text, preview] = GATES[gate];
  return h("section", { class: "panel gate-card" },
    h("div", { class: "gate-head" }, h("span", { class: "gate-icon" }, icon("hand")),
      h("div", { class: "grow" }, h("div", { class: "eyebrow wait" }, "Your turn"), h("h2", {}, GATE_NAMES[gate]), h("p", { class: "muted small" }, text))),
    ctx.project.approve === "auto" ? autoNotice(ctx, gate) : null,
    h("div", { class: "gate-body" }, preview(ctx)),
    gateControls(ctx, gate, { approvable: !blocked(ctx, gate) && !(gate === "review_scenes" && ctx.records.scenes_missing?.length), approve: gate === "review_lyrics" ? approveLyrics(ctx.id) : undefined, extra: h("a", { class: "button ghost", href: `#/p/${ctx.id}/${view}` }, `Open ${view}`, icon("arrow")) }));
}

// Pause and Stop now while the run is busy (0022); shown only by a server that reports `pausing`.
function pauseControls(ctx) {
  const { run, status } = ctx.project;
  if (status !== "running" || !("pausing" in run)) return null;
  if (run.pausing) return h("span", { class: "pill" }, run.pausing === "stop" ? "Stopping…" : "Pausing after the file being made…");
  const ask = (now) => actionButton(ctx, now ? "Stop now" : "Pause", now ? "x" : "pause", "pause", { now },
    now ? "Stopping: the picture or clip being made is drawn again on Resume." : "Pausing once the file being made is done.", "ghost");
  const pause = ask(false), stop = ask(true);
  pause.title = "Finishes the picture or clip being made, then stops. Resume goes on.";
  stop.title = "Stops the picture, clip or planner call being made; it is made again on Resume.";
  return h("div", { class: "row wrap" }, pause, stop);
}

function runningCard(ctx) {
  const stage = ctx.project.run.stages.find((s) => s.status === "running");
  const detail = stage ? stageDetail(ctx, stage, "large") : null;
  return h("section", { class: "panel now-card" }, h("div", { class: "row" }, h("span", { class: "spinner large" }),
    h("div", { class: "grow" }, h("div", { class: "eyebrow" }, "Working on"), h("h2", {}, stage ? STAGE_NAMES[stage.name] : "Starting"),
      stage ? h("p", { class: "muted small" }, "for ", h("span", { dataset: { since: startedAt(ctx, stage) } }),
        !detail && stage.shots_total ? ` · ${stage.shots_done} of ${stage.shots_total} shots made` : "") : null),
    pauseControls(ctx)),
  detail || shotsBar(stage, "large"));
}

// A paused run (0022): what is made is kept; a scene redone now is made at once and the run stays paused.
function pausedCard(ctx) {
  if (ctx.project.prepared) {  // 0028 §6
    return h("section", { class: "panel now-card done" }, h("div", { class: "row" }, h("span", { class: "gate-icon good" }, icon("check")),
      h("div", { class: "grow" }, h("div", { class: "eyebrow" }, "Prepared"), h("h2", {}, "Ready to run offline"),
        h("p", { class: "muted small" }, "The lyrics and the plan are made: nothing left needs the internet. Resume makes the scenes, clips and video, or use \u201cRun all prepared\u201d on the Videos page.")),
      actionButton(ctx, "Resume", "play", "resume", {}, "Resuming the run.", "primary")));
  }
  const stage = ctx.project.run.stages.find((s) => s.status === "paused");
  return h("section", { class: "panel now-card" }, h("div", { class: "row" }, h("span", { class: "gate-icon" }, icon("pause")),
    h("div", { class: "grow" }, h("div", { class: "eyebrow" }, "Paused"), h("h2", {}, stage ? STAGE_NAMES[stage.name] : "The run is paused"),
      h("p", { class: "muted small" }, "Everything finished is kept. Resume goes on from here.")),
    actionButton(ctx, "Resume", "play", "resume", {}, "Resuming the run.", "primary")));
}

// A project made without starting it (`new` on the command line): nothing runs until Start.
function notStartedCard(ctx) {
  return h("section", { class: "panel now-card" }, h("div", { class: "row" }, h("span", { class: "gate-icon" }, icon("play")),
    h("div", { class: "grow" }, h("div", { class: "eyebrow" }, "Not started"), h("h2", {}, "Ready to start"),
      h("p", { class: "muted small" }, "Nothing has run yet and no model has been called. Start runs it, or queues it behind the video running.")),
    actionButton(ctx, "Start", "play", "resume", {}, "Starting the run.", "primary")));
}

function endCard(ctx) {
  const { status, run } = ctx.project;
  if (status === "completed") {
    return h("section", { class: "panel now-card done" }, h("div", { class: "row" }, h("span", { class: "gate-icon good" }, icon("check")),
      h("div", { class: "grow" }, h("div", { class: "eyebrow" }, "Finished"), h("h2", {}, ctx.records.video ? "The video is ready" : "Every stage is done")),
      h("a", { class: "button primary", href: `#/p/${ctx.id}/video` }, icon("video"), "Watch")));
  }
  if (status === "paused") return pausedCard(ctx);
  if (status === "queued") return h("section", { class: "panel now-card" }, h("h2", {}, "Waiting its turn"), h("p", { class: "muted small" }, "Another video is running; one runs at a time on this machine."));
  const failed = run.stages.find((s) => s.status === "failed");
  return h("section", { class: "panel now-card bad" }, h("div", { class: "eyebrow" }, humanize(status)),
    h("h2", {}, failed ? `${STAGE_NAMES[failed.name]} failed` : "The run stopped"), h("p", { class: "small" }, failed?.error || "Resume the run to continue where it stopped."));
}

export function gateCard(ctx) {
  const { status, run } = ctx.project;
  if (run.waiting && GATES[run.waiting]) return waitingCard(ctx, run.waiting);
  if (status === "not_started") return notStartedCard(ctx);
  if (status === "running") return runningCard(ctx);
  return endCard(ctx);
}
