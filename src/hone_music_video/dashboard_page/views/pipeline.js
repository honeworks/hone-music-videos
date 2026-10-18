// The 10 stages (0027) as a pipeline: done, running (with its progress: units done, the unit being made,
// the time left, 0003), waiting at a gate, pending or failed, with the durations the run recorded, the
// owner's three gates between, and the overall estimate on top.

import { GATE_NAMES, h, LABELS, spoken, STAGE_NAMES, startedAt } from "../core.js";
import { icon } from "../icons.js";
import { shotsBar } from "../parts.js";
import { overallDetail, stageDetail } from "../progress.js";

const GROUPS = [
  ["Timed lyrics", ["measure", "transcribe", "lyrics", "check_lyrics"]],
  ["The plan", ["plan", "check_plan"]],
  ["The scenes", ["scenes"]],
  ["Clips", ["clips", "finish"]],
  ["The video", ["assemble"]],
];
const STARTED = new Set(["running", "done", "failed", "paused", "awaiting_review", "interrupted", "blocked"]);

function marker(stage) {
  const glyph = { done: "check", failed: "x", awaiting_review: "pause", paused: "pause", interrupted: "alert", blocked: "x" }[stage.status];
  if (stage.status === "running") return h("span", { class: "marker running" }, h("span", { class: "spinner" }));
  return h("span", { class: `marker ${stage.status}` }, glyph ? icon(glyph) : stage.number);
}

function meta(stage, ctx) {
  if (stage.status === "running") {
    const since = startedAt(ctx, stage);
    return [h("span", {}, "running for ", h("span", { dataset: { since } }, "")),
      stage.shots_total && !ctx.project.progress?.stages?.[stage.name] ? h("span", {}, ` · ${stage.shots_done} of ${stage.shots_total} shots`) : null];
  }
  if (stage.status === "failed") return h("span", { class: "bad" }, stage.error || "failed");
  const took = stage.status === "done" || stage.status === "awaiting_review";
  return [took && stage.duration_ms !== null ? `took ${spoken(stage.duration_ms)}` : LABELS[stage.status] || stage.status,
    stage.shots_total && stage.status !== "done" ? ` · ${stage.shots_done} of ${stage.shots_total} shots` : ""];
}



function gateRow(stage, stages, waiting) {
  const after = stages[stage.number]; // the stage after the gate (numbers start at 1)
  const state = waiting === stage.gate ? "waiting" : after && STARTED.has(after.status) ? "passed" : "ahead";
  const text = { waiting: "waiting for you", passed: stage.gate_auto ? "auto-approved" : "approved", ahead: "you, later" }[state];
  return h("li", { class: `gate-step ${state}` }, h("span", { class: "marker gate" }, icon("hand")),
    h("span", { class: "grow" }, GATE_NAMES[stage.gate]), h("span", { class: "xs" }, text));
}

export function pipeline(ctx) {
  const stages = ctx.project.run.stages;
  const done = stages.filter((s) => s.status === "done").length;
  return h("section", { class: "panel" },
    h("div", { class: "panel-head" }, h("h2", {}, "Pipeline"), h("span", { class: "muted small" }, `${done} of ${stages.length} stages done`)),
    overallDetail(ctx.project),
    GROUPS.map(([title, names]) => h("div", { class: "stage-group" }, h("div", { class: "eyebrow" }, title),
      h("ol", { class: "stages" }, names.map((name) => {
        const stage = stages.find((s) => s.name === name);
        const detail = stageDetail(ctx, stage);
        return [h("li", { class: `stage ${stage.status}` }, marker(stage),
          h("div", { class: "grow" }, h("div", { class: "stage-name" }, STAGE_NAMES[name]),
            h("div", { class: "stage-meta" }, meta(stage, ctx)), detail || (stage.status === "done" ? null : shotsBar(stage)))),
        stage.gate ? gateRow(stage, stages, ctx.project.run.waiting) : null];
      })))));
}
