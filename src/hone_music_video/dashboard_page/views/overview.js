// Overview: the song as a timeline, the current gate (or what the run is doing), the newest pictures,
// the 14 stages as a pipeline and the activity, all from the run's records (never invented progress).

import { duration, empty, GATE_NAMES, h, humanize, STAGE_NAMES } from "../core.js";
import { icon } from "../icons.js";
import { characterName, zoom } from "../parts.js";
import { KIND_NAMES } from "../progress.js";
import { songPanel } from "../timeline.js";
import { pipeline } from "./pipeline.js";
import { gateCard } from "./gates.js";

function version(url) {
  return Number(new URLSearchParams(String(url).split("?")[1] || "").get("v") || 0);
}

// The newest start frames and clips (the scenes' own pictures are in the Scenes view).
function newest(ctx) {
  const { records } = ctx;
  const found = [];
  for (const [id, files] of Object.entries(records.shot_files)) {
    const newest = files.newest; // a draft, a still, a raw clip or a finished clip (0003)
    if (!newest) continue;
    const picture = files.stills;
    const kind = { stills: "start frame", clips: KIND_NAMES.raw_clip, finish: "finished clip" }[newest.kind];
    found.push({ url: picture, open: newest.url, video: ["clips", "finish"].includes(newest.kind), label: `${id} · ${kind}`, at: version(newest.url) });
  }
  return found.map((f) => ({ ...f, at: f.at || version(f.url) })).sort((a, b) => b.at - a.at).slice(0, 12);
}

function filmstrip(ctx) {
  const items = newest(ctx);
  return h("section", { class: "panel" },
    h("div", { class: "panel-head" }, h("h2", {}, "Latest pictures"), h("span", { class: "muted small" }, items.length ? "newest first · click to open" : "")),
    items.length
      ? h("div", { class: "filmstrip" }, items.map((item) => zoom(ctx, h("div", { class: "frame" },
        h("img", { src: item.url, alt: "", loading: "lazy" }),
        item.video ? h("span", { class: "frame-badge" }, icon("film")) : null,
        h("span", { class: "frame-label" }, item.label)), { src: item.open || item.url, label: item.label, video: item.video })))
      : empty(icon("image"), "Nothing drawn yet", "Every start frame and clip appears here as it is made; the characters, places and scenes are drawn in the Scenes view."));
}

function describe(ctx, event) {
  const stage = STAGE_NAMES[event.step] || GATE_NAMES[event.step] || humanize(event.step);
  switch (event.event) {
    case "run_started": return ["sparkle", "The run started"];
    case "run_finished": return event.status === "awaiting_review" ? ["pause", "The run waits for you"]
      : ["check", `The run ${event.status === "completed" ? "finished" : `stopped (${humanize(event.status)})`}`];
    case "step_started": return ["activity", `${stage} started`];
    case "step_finished": return event.status === "awaiting_review" ? ["hand", `${stage}: waiting for you`]
      : [event.status === "failed" ? "x" : "check", `${stage}: ${humanize(event.status)}`];
    case "version_made": return ["image", `${STAGE_NAMES[event.stage]}: ${KIND_NAMES[event.kind]} for ${event.shot || characterName(ctx, event.character)} (${event.done} of ${event.total}, ${duration(event.took_ms)})`];
    case "shot_finished": return ["image", `${STAGE_NAMES[event.stage]}: shot ${event.shot} (${event.done} of ${event.total})`];
    case "frame": return ["image", `Scenes: ${humanize(event.kind)}${event.item ? ` ${event.item}` : ""}`];
    case "clip_seed": return ["sparkle", `New clip seeds: ${(event.shots || []).join(", ")}`];
    case "motion_edited": return ["clips", `${event.shot}: motion prompt edited`];
    case "gate_approved": return ["hand", `${GATE_NAMES[event.gate] || humanize(event.gate)}: approved`];
    case "gate_auto_approved": return ["check", `${GATE_NAMES[event.gate] || humanize(event.gate)}: approved automatically`];
    case "auto_stopped": return ["alert", `${GATE_NAMES[event.gate] || humanize(event.gate)}: stopped, needs you (${event.reason})`];
    case "run_error": return ["alert", event.message];
    default: return ["info", `${humanize(event.event)}${event.step ? `: ${stage}` : ""}`];
  }
}

const QUIET = new Set(["version_started", "units"]); // the progress shows these; the feed lists what was made

function activity(ctx) {
  const events = ctx.events.filter((e) => !QUIET.has(e.event)).slice(-40).reverse();
  return h("section", { class: "panel" }, h("div", { class: "panel-head" }, h("h2", {}, "Activity"), h("span", { class: "muted small" }, `${ctx.events.length} events`)),
    events.length ? h("ol", { class: "feed" }, events.map((event) => {
      const [glyph, text] = describe(ctx, event);
      return h("li", { class: event.event }, icon(glyph), h("span", { class: "grow" }, text),
        h("time", { class: "faint xs" }, new Date(event.at).toLocaleTimeString()));
    })) : h("p", { class: "muted small" }, "The run's events appear here as they happen."));
}

export function overviewView(ctx) {
  return h("div", { class: "stack" }, songPanel(ctx),
    h("div", { class: "overview-grid" },
      h("div", { class: "stack" }, gateCard(ctx), filmstrip(ctx), activity(ctx)),
      h("div", { class: "stack" }, pipeline(ctx))));
}

