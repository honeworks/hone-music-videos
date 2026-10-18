// Clips (0024, 0027 §7): every shot's clip as it arrives, raw while it is finished, hover to play; a shot
// without one shows its start frame dimmed. A click opens the scene viewer (scene.js): the raw clip against
// the finished one with the song, every version and Redo. Redo makes only that shot's clip again with a new
// seed or an edited motion prompt from the same start frame; a start frame is its scene's picture, changed
// in the Scenes view.

import { empty, h } from "../core.js";
import { icon } from "../icons.js";
import { WORKING } from "../progress.js";
import { boardTop, cardClasses, cardHead, sceneMedia } from "./board.js";
import { canRemake, clipOf, clipState, redoPanel } from "./scene-parts.js";

function card(ctx, shot, redoable) {
  const files = ctx.records.shot_files[shot.id] || {};
  const state = clipState(ctx.project, shot.id, files);
  const clip = clipOf(files);
  const tag = clip.tag || (clip.poster ? "no clip yet" : null);
  return h("article", { class: cardClasses(ctx, shot, state, [!clip.src && "no-clip"]), dataset: { state, shot: shot.id } },
    sceneMedia(ctx, shot, "clip", { picture: clip.poster, tag, clip: clip.src, working: Boolean(WORKING[state]) }),
    h("div", { class: "board-body" }, cardHead(ctx, shot, files, state),
      h("p", { class: "xs faint motion-line" }, shot.motion_prompt),
      redoable && files.stills ? redoPanel(ctx, shot) : null));
}

export function clipsView(ctx) {
  const shots = ctx.records.shots?.shots;
  if (!shots) return empty(icon("film"), "No clips yet", "Once the scenes are approved, every shot's clip appears here as it is made: raw first, then finished.");
  const files = (s) => ctx.records.shot_files[s.id] || {};
  const finished = shots.filter((s) => files(s).finish).length;
  const raw = shots.filter((s) => files(s).clips && !files(s).finish).length;
  const redoable = canRemake(ctx);
  const top = boardTop(ctx, ["clips", "finish"], redoable);
  return h("div", { class: "stack" }, ...top.nodes,
    h("div", { class: "row between wrap" }, h("p", { class: "muted" }, `${finished} of ${shots.length} clips finished`, raw ? ` · ${raw} raw` : "", top.counted),
      h("p", { class: "muted small" }, "Hover to play a clip; click it for the raw against the finished clip with the song, its versions and Redo.")),
    h("div", { class: "board" }, shots.map((shot) => card(ctx, shot, redoable))));
}
