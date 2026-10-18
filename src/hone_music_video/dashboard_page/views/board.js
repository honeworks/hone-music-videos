// What the Clips view's cards show (0024): a card's picture or clip that opens the scene viewer, a card's
// head (id, state, beat, time, cast, framing), and above the cards the song's timeline, "Remake changed
// clips" and the progress of the view's running stage.

import { formatMs, h, spoken, STAGE_NAMES } from "../core.js";
import { icon } from "../icons.js";
import { avatar, framingChip } from "../parts.js";
import { overallDetail, stageDetail, WORKING } from "../progress.js";
import { songPanel } from "../timeline.js";
import { openScene } from "./scene.js";
import { remakeButton, stateBadge, versionsChip } from "./scene-parts.js";

// The card's picture (or a clip that plays on hover), tagged with what it is; a click opens the viewer.
export function sceneMedia(ctx, shot, mode, { picture, tag, clip = null, working = false }) {
  const box = h("button", { type: "button", class: `board-media${working ? " working" : ""}${clip ? " has-clip" : ""}`, "aria-label": `Open ${shot.id}: its versions and redo`, onclick: () => openScene(ctx, shot.id, mode) },
    picture ? h("img", { src: picture, alt: `${tag || "picture"} of ${shot.id}`, loading: "lazy" }) : h("div", { class: "no-picture" }),
    tag ? h("span", { class: `media-tag tag-${tag.replaceAll(" ", "-")}` }, tag) : null);
  if (!clip) return box;
  const video = h("video", { src: clip, muted: true, loop: true, playsinline: true, preload: "none", poster: picture || null });
  video.muted = true; // the attribute alone does not mute in every browser, and autoplay needs a muted video
  box.append(video, h("span", { class: "play-hint" }, icon("play")));
  box.addEventListener("pointerenter", () => { box.classList.add("playing"); video.play().catch(() => {}); });
  box.addEventListener("pointerleave", () => { box.classList.remove("playing"); video.pause(); });
  return box;
}

export function cardHead(ctx, shot, files, state) {
  return [
    h("div", { class: "row between" }, h("strong", { class: "mono" }, shot.id), stateBadge(state)),
    h("p", { class: "board-beat" }, shot.beat),
    h("div", { class: "row between" }, h("span", { class: "mono xs faint" }, `${formatMs(shot.start_ms)} · ${spoken(shot.end_ms - shot.start_ms)}`),
      h("span", { class: "avatars" }, shot.cast.map((id) => avatar(ctx, id, "small")))),
    h("div", { class: "row wrap" }, framingChip(shot.framing), shot.faces ? h("span", { class: "chip" }, "faces") : null, versionsChip(files)),
  ];
}

export function cardClasses(ctx, shot, state, extra = []) {
  return ["board-card", WORKING[state] && "working", state === "failed" && "failed", ctx.selected === shot.id && "picked", ...extra].filter(Boolean).join(" ");
}

// The panels above the cards; `run` is the view's stage running (or stopped) among `stages`.
export function boardTop(ctx, stages, redoable) {
  const run = ctx.project.run.stages.find((s) => stages.includes(s.name) && ["running", "failed", "interrupted"].includes(s.status));
  const detail = run ? stageDetail(ctx, run) : null;
  const nodes = [
    songPanel(ctx, { selected: ctx.selected, onShot: (shot) => openScene(ctx, shot.id, "clip") }),
    redoable ? h("div", { class: "row wrap" }, remakeButton(ctx, "primary"), h("span", { class: "muted small" }, "After you change scenes in the Scenes view, or motion prompts here.")) : null,
    detail ? h("section", { class: "panel progress-panel" }, h("div", { class: "eyebrow" }, STAGE_NAMES[run.name]), detail, overallDetail(ctx.project)) : null,
  ];
  const counted = run && !detail && run.shots_total ? ` · ${STAGE_NAMES[run.name]}: ${run.shots_done} of ${run.shots_total}` : "";
  return { nodes, counted };
}
