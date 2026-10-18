// Plan (0027): the planned shot list as blocks on the song's timeline (coloured by framing, faces marked),
// a list and the chosen shot in detail: times, lines, beat, framing, cast, camera, its scene's prompt and
// the motion prompt, and the checks' findings under the shot they are about; what the planner's repairs
// left. Approve (not while the checks found errors), or plan again with a note. The scenes themselves are
// edited in the Scenes view (Hone Frame's workspace). Under the checks, the planner's calls (calls.js, 0030 §2).

import { empty, formatMs, h, spoken } from "../core.js";
import { icon } from "../icons.js";
import { avatar, characterName, checks, findingsOf, framingChip, gateBar, notesList, picture, zoomPicture } from "../parts.js";
import { playSlice } from "../player.js";
import { songPanel } from "../timeline.js";
import { planCalls } from "./calls.js";

function select(ctx, shot) {
  const list = document.querySelector(".shot-list");
  const [top, page] = [list?.scrollTop || 0, scrollY];
  ctx.selected = shot.id;
  ctx.render();
  document.querySelector(".shot-list")?.scrollTo(0, top);
  scrollTo(0, page);
}

// An error or a warning about the shot, as a mark beside its id.
function flag(ctx, shot) {
  const found = findingsOf(ctx.records.plan_check, shot.id);
  if (!found.length) return null;
  const kind = found.some(([k]) => k === "errors") ? "errors" : "warnings";
  return h("span", { class: `shot-flag ${kind}`, title: `${found.length} ${found.length === 1 ? "finding" : "findings"}` }, icon(kind === "errors" ? "x" : "alert"));
}

function listRow(ctx, shot, selected) {
  return h("button", { type: "button", class: `shot-row${shot.id === selected ? " selected" : ""}`, onclick: () => select(ctx, shot) },
    h("span", { class: `shot-swatch f-${shot.framing}` }),
    h("span", { class: "shot-id mono" }, shot.id, flag(ctx, shot)),
    h("span", { class: "grow shot-beat" }, shot.beat),
    h("span", { class: "avatars" }, shot.cast.map((id) => avatar(ctx, id, "small"))),
    h("span", { class: "mono faint xs" }, formatMs(shot.start_ms)));
}

function field(label, value) {
  return h("div", { class: "field-view" }, h("div", { class: "eyebrow" }, label), h("div", {}, value));
}

function lineTexts(ctx, shot) {
  const lines = (ctx.records.timeline?.lines || []).filter((l) => shot.lines.includes(l.id));
  if (!lines.length) return h("span", { class: "muted" }, "no sung line (instrumental)");
  return h("ul", { class: "shot-lines" }, lines.map((l) => h("li", { dir: "auto" }, h("span", { class: "mono faint xs" }, `${l.id} `), l.text)));
}

// What the viewer should feel at this shot and what shows it (0028).
function feeling(ctx, shot) {
  const found = (ctx.records.feelings || {})[shot.id];
  if (!found) return null;
  return h("div", { class: "two-col" }, field("Feel", found.feel), field("What shows it", found.evidence));
}

function detail(ctx, shot) {
  const files = ctx.records.shot_files[shot.id] || {};
  return h("aside", { class: "panel shot-detail sticky" },
    h("div", { class: "shot-still" }, files.stills || files.draft
      ? zoomPicture(ctx, files.stills || files.draft, `${shot.id} · ${files.stills ? "start frame" : "draft"} · ${formatMs(shot.start_ms)}–${formatMs(shot.end_ms)}`)
      : picture(null),
      h("button", { type: "button", class: "round-button over", "aria-label": `Play ${shot.id} with the song`, onclick: () => playSlice(ctx.player, shot.start_ms, shot.end_ms) }, icon("play"))),
    h("div", { class: "row between" }, h("h2", {}, shot.id), framingChip(shot.framing)),
    h("p", { class: "mono small muted" }, `${formatMs(shot.start_ms)} – ${formatMs(shot.end_ms)} · ${spoken(shot.end_ms - shot.start_ms)}`),
    h("p", { class: "beat" }, shot.beat),
    feeling(ctx, shot),
    notesList(findingsOf(ctx.records.plan_check, shot.id)),
    field("Lines", lineTexts(ctx, shot)),
    field("Cast", shot.cast.length ? h("div", { class: "row wrap" }, shot.cast.map((id) => h("span", { class: "row cast-name" }, avatar(ctx, id, "small"), characterName(ctx, id)))) : h("span", { class: "muted" }, "nobody (drawn from text)")),
    h("div", { class: "two-col" }, field("Camera", shot.camera), field("Faces", shot.faces ? "recognisable (larger clip)" : "not needed")),
    field("Location", shot.location),
    field("Scene prompt", shot.still_prompt ? h("p", { class: "prompt-text" }, shot.still_prompt) : h("span", { class: "muted" }, "in the Scenes view")),
    h("a", { class: "button ghost", href: `#/p/${ctx.id}/scenes/i/${encodeURIComponent(shot.id)}` }, "Open its scene", icon("arrow")),
    field("Motion prompt", h("p", { class: "prompt-text" }, shot.motion_prompt)));
}

// The gate bar: Approve (not while the checks found errors), or plan again with a note.
function planGate(ctx) {
  const errors = ctx.records.plan_check?.errors.length || 0;
  const plural = `${errors} ${errors === 1 ? "error" : "errors"}`;
  const text = errors
    ? `The checks still found ${plural} after the planner's repairs, so the plan cannot be approved: plan again with a note.`
    : "Approve the plan to make the scenes (the demo pictures first, then the characters, objects, places and every scene), or plan again with a note.";
  return gateBar(ctx, "review_plan", text, { approvable: !errors });
}

// What the planner's repairs could not fix in the prompts (the code's check, never a picture judge).
function leftOver(ctx) {
  const problems = ctx.records.plan?.problems || [];
  if (!problems.length) return null;
  return h("section", { class: "panel" }, h("div", { class: "panel-head" }, h("h2", {}, "Left after the repairs")),
    h("ul", { class: "problems-list warnings" }, problems.map((p) => h("li", {}, icon("alert"), h("div", {}, p)))));
}

export function planView(ctx) {
  const shots = ctx.records.shots?.shots;
  if (!shots) {  // the calls show as they come back, before the plan is whole
    return h("div", { class: "stack" },
      empty(icon("plan"), "No plan yet", "Once the lyrics are approved, the planner writes the story, the shot list and every prompt in several calls; the shots appear here on the timeline."),
      planCalls(ctx));
  }
  const chosen = shots.find((s) => s.id === ctx.selected) || shots[0];
  return h("div", { class: "stack" },
    planGate(ctx),
    leftOver(ctx),
    songPanel(ctx, { selected: chosen.id, onShot: (shot) => select(ctx, shot) }),
    h("div", { class: "split wide-side" },
      h("div", { class: "stack" },
        h("section", { class: "panel flush" }, h("div", { class: "list-head" }, h("h2", {}, `${shots.length} shots`), h("span", { class: "muted small" }, "click a shot or a block on the timeline")),
          h("div", { class: "shot-list" }, shots.map((shot) => listRow(ctx, shot, chosen.id)))),
        h("section", { class: "panel" }, h("div", { class: "panel-head" }, h("h2", {}, "Checks")), checks(ctx.records.plan_check, "shots"),
          ctx.records.plan ? h("p", { class: "muted small" }, `${ctx.records.plan.shots} shots and ${ctx.records.plan.items} items in the project file.`) : null),
        planCalls(ctx)),
      detail(ctx, chosen)));
}
