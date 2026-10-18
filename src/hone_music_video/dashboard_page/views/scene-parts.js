// What the Clips view, the Preview and the scene viewer share (0024, 0027 §7): the file a shot shows (its
// start frame, its clip), its state badge, and the redo panel of a clip: a new seed, or an edited motion
// prompt, each remaking only that shot's clip (a fork from `clips`; the other clips are kept). A start
// frame is its scene's picture in use: it is changed in the Scenes view, then "Remake changed clips". An
// open redo panel keeps its edited prompt across the view's redraws (as the gates' notes, 0018).

import { api, h, toast } from "../core.js";
import { icon } from "../icons.js";
import { actionButton } from "../parts.js";
import { shotState, WORKING } from "../progress.js";

// The start frame of a shot: its scene's picture in use (0027).
export function frameOf(files) {
  return files?.stills ? { src: files.stills, tag: "start frame" } : { src: null, tag: null };
}

// The clip of a shot: finished, else raw while it is finished; its start frame as the poster.
export function clipOf(files) {
  const poster = frameOf(files).src;
  if (files?.finish) return { src: files.finish, tag: "finished", poster };
  if (files?.clips) return { src: files.clips, tag: "raw", poster };
  return { src: null, tag: null, poster };
}

// A shot's state in the Clips view (stages clips and finish).
export function clipState(project, id, files) {
  const state = shotState(project, id, files, ["clips", "finish"]);
  if (WORKING[state] || state === "failed") return state;
  return files.finish ? "finished" : files.clips ? "raw clip" : "waiting";
}

const STATE_STYLE = { finished: ["good", "check"], failed: ["bad", "x"], "raw clip": ["", "film"] };

export function stateBadge(state) {
  if (WORKING[state]) return h("span", { class: "badge working-label" }, h("span", { class: "working-dot" }), WORKING[state]);
  const [tone, glyph] = STATE_STYLE[state] || ["faint", null];
  return h("span", { class: `badge ${tone}`.trim() }, glyph ? icon(glyph) : null, state);
}

export function versionsChip(files) {
  const counts = files.versions || {};
  const total = (counts.stills || 0) + (counts.clips || 0) + (counts.finish || 0);
  return total ? h("span", { class: "chip", title: `${counts.stills} start frames, ${counts.clips} clips, ${counts.finish} finished clips kept` }, icon("layers"), `${total} ${total === 1 ? "version" : "versions"}`) : null;
}

// Clips can be remade once some exist and the run is not busy (the server refuses otherwise too).
export function canRemake(ctx) {
  const files = Object.values(ctx.records.shot_files);
  return !["running", "queued"].includes(ctx.project.status) && files.some((f) => f.clips);
}

// "Remake changed clips": the clips of the shots whose scene, motion prompt or seed changed, then the cut.
export function remakeButton(ctx, kind = "") {
  const button = actionButton(ctx, "Remake changed clips", "sparkle", "remake", {}, "Remaking the clips of the scenes that changed; the others are kept.", kind);
  button.title = "Makes again only the clips whose scene picture, motion prompt or seed changed, then cuts the video again";
  return button;
}

const drafts = new Map();

function kept(key, panel, box) {
  const draft = drafts.get(key);
  if (draft) {
    panel.open = draft.open;
    box.value = draft.text;
    if (draft.typing) requestAnimationFrame(() => { box.focus(); box.setSelectionRange(draft.caret, draft.caret); });
  }
  const save = (typing) => drafts.set(key, { open: panel.open, text: box.value, typing, caret: box.selectionStart });
  panel.addEventListener("toggle", () => save(drafts.get(key)?.typing));
  box.addEventListener("input", () => save(true));
}

// Save the edited motion prompt, then remake: only this shot's clip is made again.
async function sendMotion(ctx, button, shot, text, key) {
  button.disabled = true;
  try {
    const { warnings } = await api(`/projects/${ctx.id}/motion`, { method: "POST", body: { shot: shot.id, motion_prompt: text } });
    await api(`/projects/${ctx.id}/remake`, { method: "POST", body: {} });
    drafts.delete(key);
    toast(warnings?.length ? `${shot.id}: remaking its clip. The prompt names speech (${warnings.join(", ")}); the video model may move the mouth.` : `${shot.id}: remaking its clip with the edited motion prompt.`);
  } catch (error) {
    toast(error.message);
    button.disabled = false;
  }
  ctx.refresh();
}

// The redo panel of a shot's clip (0027 §7); `where` keeps the card's and the viewer's edits apart, `open`
// opens it at first.
export function redoPanel(ctx, shot, { where = "card", open = false } = {}) {
  const current = shot.motion_prompt || "";
  const key = `${ctx.id}/${shot.id}/${where}`;
  const box = h("textarea", { "aria-label": `Motion prompt of ${shot.id}`, rows: 3, dir: "auto" });
  box.value = current;
  const changed = () => box.value.trim() && box.value.trim() !== current.trim();
  const send = h("button", { type: "button", class: "button primary" }, icon("check"), "Remake with the edited prompt");
  send.addEventListener("click", () => sendMotion(ctx, send, shot, box.value, key));
  const update = () => { send.disabled = !changed(); };
  const seed = actionButton(ctx, "New clip (new seed)", "sparkle", "redo-clip", { shots: [shot.id] }, `${shot.id}: a new clip from the same start frame.`, "");
  const panel = h("details", { class: "redo", open }, h("summary", {}, "Redo this clip"),
    h("div", { class: "stack small-gap" },
      h("div", { class: "row wrap" }, seed,
        h("a", { class: "button ghost", href: `#/p/${ctx.id}/scenes/i/${encodeURIComponent(shot.id)}` }, icon("image"), "Change its scene")),
      h("label", { class: "xs faint" }, "Motion prompt (an edit makes a new clip from the same start frame)"), box,
      h("div", { class: "row wrap" }, send)));
  kept(key, panel, box);
  box.addEventListener("input", update);
  update();
  return panel;
}
