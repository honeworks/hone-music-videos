// The scene viewer (0024 §2, 0027 §7): one shot over the page, opened from the Clips view or the Preview.
// Its steps (start frame, raw clip, finished clip) as the video uses them; Compare puts the raw clip against
// the finished one, played together with the song; every kept version, newest first, from GET
// …/shots/<id>/versions; and the redo of its clip. Its start frame is its scene's picture in use, changed in
// the Scenes view. It follows the run while open: its versions are read again on the project's events.
// Keys: ←/→ the previous and next shot, C compare, Esc close; the focus stays inside and goes back to the
// opener.

import { api, formatMs, h } from "../core.js";
import { icon } from "../icons.js";
import { playSlice } from "../player.js";
import { canRemake, redoPanel } from "./scene-parts.js";

export const STEPS = [["still", "Start frame"], ["raw_clip", "Raw clip"], ["clip", "Finished clip"]];
const CLIPS = new Set(["raw_clip", "clip"]);

// The file of each kind the video uses, else the newest of that kind (the versions come newest first).
export function chainOf(versions) {
  const chain = {};
  for (const [kind] of STEPS) {
    const found = versions.find((v) => v.kind === kind && v.in_use) || versions.find((v) => v.kind === kind);
    if (found) chain[kind] = found;
  }
  return chain;
}

// The two files Compare shows: the raw and the finished clip.
export function pairFor(chain) {
  return chain.raw_clip && chain.clip ? [chain.raw_clip, chain.clip] : null;
}

// The step a view opens on: its own furthest file.
export function firstStep(chain, mode) {
  const order = mode === "clip" ? ["clip", "raw_clip", "still"] : ["still", "clip", "raw_clip"];
  return order.find((kind) => chain[kind]) || order[0];
}

export function versionLabel(v) {
  if (v.kind === "still") return v.scene_version ? `start frame (scene v${v.scene_version})` : "start frame";
  return { raw_clip: "raw clip", clip: "finished clip" }[v.kind];
}

let open = null; // { ctx, shot, mode, step, pick, compare, data, root, opener, shown }

const shotsOf = (ctx) => ctx.records.shots?.shots || [];
const filesOf = (ctx, id) => ctx.records.shot_files[id] || {};

function media(item, { withSong = null, cls = "lb-media" } = {}) {
  if (!CLIPS.has(item.kind)) return h("img", { class: cls, src: item.url, alt: versionLabel(item) });
  const video = h("video", { class: cls, src: item.url, controls: true, playsinline: true, loop: !withSong });
  video.muted = true; // the song plays, not the clip's own track
  if (withSong) {
    video.addEventListener("play", () => playSlice(open.ctx.player, withSong.start_ms + Math.round(video.currentTime * 1000), withSong.end_ms));
    video.addEventListener("pause", () => open?.ctx.player.audio.pause());
  }
  return video;
}

function sideBySide(shot, pair) {
  const nodes = pair.map((v) => media(v, { cls: "side-media" }));
  const both = CLIPS.has(pair[0].kind) ? h("button", { type: "button", class: "button", onclick: () => {
    for (const video of nodes) { video.currentTime = 0; video.play().catch(() => {}); }
    playSlice(open.ctx.player, shot.start_ms, shot.end_ms);
  } }, icon("play"), "Play both with the song") : null;
  return h("div", { class: "stack small-gap" }, h("div", { class: "side-by-side" },
    pair.map((v, n) => h("figure", {}, nodes[n], h("figcaption", { class: "xs faint" }, versionLabel(v))))), both);
}

function stage(shot, chain) {
  const pair = open.compare && !open.pick ? pairFor(chain) : null;
  if (pair) return sideBySide(shot, pair);
  const item = open.pick || chain[open.step];
  if (!item) return h("div", { class: "scene-empty muted" }, "Not made yet.");
  return media(item, { withSong: shot });
}

function details(item) {
  if (!item) return null;
  const at = new Date(item.made_at).toLocaleString([], { dateStyle: "medium", timeStyle: "short" });
  return h("div", { class: "scene-details" },
    h("div", { class: "xs faint" }, `${versionLabel(item)} · ${item.model} · seed ${item.seed} · ${at}`),
    item.prompt ? h("details", {}, h("summary", { class: "xs" }, "Prompt"), h("p", { class: "xs" }, item.prompt)) : null);
}

function stepBar(chain) {
  const choose = (kind) => () => { open.step = kind; open.pick = null; draw(); };
  const pair = pairFor(chain);
  return h("div", { class: "row wrap scene-steps" },
    STEPS.map(([kind, label]) => h("button", { type: "button", class: "button ghost", disabled: !chain[kind], "aria-pressed": String(open.step === kind && !open.pick), onclick: choose(kind) }, label)),
    h("span", { class: "grow" }),
    h("button", { type: "button", class: "button ghost", disabled: !pair, "aria-pressed": String(Boolean(open.compare)),
      onclick: () => { open.compare = open.compare ? null : "side"; open.pick = null; draw(); } }, "Compare"));
}

function thumb(v, still) {
  const picture = CLIPS.has(v.kind) ? still : v.url;
  const pick = () => { open.pick = v; open.step = v.kind; draw(); };
  return h("button", { type: "button", class: `version${open.pick === v ? " picked" : ""}`, onclick: pick, title: v.prompt || "" },
    picture ? h("img", { src: picture, alt: "", loading: "lazy" }) : h("span", { class: "no-picture" }),
    CLIPS.has(v.kind) ? h("span", { class: "version-icon" }, icon("film")) : null,
    h("span", { class: "xs" }, versionLabel(v), v.in_use ? " · in the video" : ""), h("span", { class: "xs faint" }, new Date(v.made_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })));
}

function versionList(chain) {
  const versions = open.data.versions;
  const byUrl = new Map(versions.map((v) => [v.url, v]));
  const stillOf = (v) => { // a clip's start frame: through its raw clip for a finished one
    let w = v;
    for (let n = 0; n < 2 && w && w.kind !== "still"; n += 1) w = byUrl.get(w.from);
    return w?.kind === "still" ? w.url : chain.still?.url;
  };
  return h("div", { class: "stack small-gap" }, h("div", { class: "eyebrow" }, `Versions (${versions.length}) · never deleted`),
    h("div", { class: "versions" }, versions.map((v) => thumb(v, stillOf(v)))));
}

function step(by) {
  const shots = shotsOf(open.ctx);
  const at = shots.findIndex((s) => s.id === open.shot);
  const next = shots[(at + by + shots.length) % shots.length];
  if (next) show(open.ctx, next.id, open.mode);
}

function draw() {
  if (!open?.data) return;
  const { ctx } = open;
  const shot = shotsOf(ctx).find((s) => s.id === open.shot);
  if (!shot) { closeScene(); return; }
  const files = filesOf(ctx, shot.id);
  const chain = chainOf(open.data.versions);
  const shown = open.pick || chain[open.step];
  const redo = canRemake(ctx) && files.stills ? redoPanel(ctx, shot, { where: "viewer", open: true }) : null;
  open.root.setAttribute("aria-label", `${shot.id}, its versions and redo`);
  open.root.replaceChildren(h("div", { class: "lb-frame scene-frame" },
    h("div", { class: "lb-bar" },
      h("button", { type: "button", class: "icon-button", "aria-label": "Previous shot", onclick: () => step(-1) }, icon("left")),
      h("div", { class: "grow lb-label" }, h("strong", { class: "mono" }, shot.id), ` · ${formatMs(shot.start_ms)}–${formatMs(shot.end_ms)}`, h("span", { class: "faint xs" }, ` · ${shot.beat}`)),
      shown ? h("a", { class: "button ghost", href: shown.url, target: "_blank", rel: "noopener" }, icon("external"), "Open the file") : null,
      h("button", { type: "button", class: "icon-button", "aria-label": "Next shot", onclick: () => step(1) }, icon("right")),
      h("button", { type: "button", class: "icon-button", "aria-label": "Close", onclick: closeScene }, icon("x"))),
    h("div", { class: "scene-body" },
      h("div", { class: "scene-main stack small-gap" }, stepBar(chain), h("div", { class: "lb-stage scene-stage" }, stage(shot, chain)), details(open.compare ? null : shown)),
      h("aside", { class: "scene-side stack" }, h("p", { class: "xs faint" }, shot.motion_prompt), redo, versionList(chain)))));
}

async function load() {
  const { ctx, shot } = open;
  try {
    return await api(`/projects/${ctx.id}/shots/${shot}/versions`);
  } catch (error) {
    return { shot, versions: [], error: error.message };
  }
}

async function show(ctx, shotId, mode) {
  Object.assign(open, { ctx, shot: shotId, mode, pick: null, compare: null, data: null, shown: "" });
  const data = await load();
  if (!open || open.shot !== shotId) return;
  Object.assign(open, { data, step: firstStep(chainOf(data.versions), mode), shown: seenOf(open.ctx, data) });
  draw();
  open.root.querySelector(".lb-bar [aria-label='Close']")?.focus();
}

const typing = (target) => target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement;

function keys(event) {
  if (!open) return;
  if (event.key === "Escape") { event.preventDefault(); closeScene(); return; }
  if (typing(event.target) || event.target instanceof HTMLVideoElement) return;
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") { event.preventDefault(); step(event.key === "ArrowLeft" ? -1 : 1); }
  else if (event.key === "c" || event.key === "C") {
    if (pairFor(chainOf(open.data.versions))) { open.compare = open.compare ? null : "side"; open.pick = null; draw(); }
  } else if (event.key === "Tab") {
    const nodes = [...open.root.querySelectorAll("button:not([disabled]), a[href], input, textarea, select, video[controls]")];
    if (!nodes.length) return;
    const [first, last] = [nodes[0], nodes[nodes.length - 1]];
    if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
    else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
  }
}

export function closeScene() {
  if (!open) return;
  const { root, opener, ctx } = open;
  open = null;
  ctx.player?.audio.pause();
  root.remove();
  document.removeEventListener("keydown", keys);
  document.body.classList.remove("lb-open");
  opener?.focus?.({ preventScroll: true });
}

// Open shot `shotId` of the project; `mode` is the step it opens on ("frame" or "clip").
export function openScene(ctx, shotId, mode = "frame") {
  closeScene();
  const root = h("div", { class: "lightbox scene", role: "dialog", "aria-modal": "true" }, h("p", { class: "muted" }, "Loading…"));
  root.addEventListener("click", (event) => { if (event.target === root) closeScene(); });
  open = { ctx, root, opener: document.activeElement };
  document.body.append(root);
  document.body.classList.add("lb-open");
  document.addEventListener("keydown", keys);
  return show(ctx, shotId, mode);
}

// After the project's records are read again: the open viewer reads its versions again and redraws only
// when something it shows changed (a playing clip is not restarted for nothing).
const seenOf = (ctx, data) => JSON.stringify([data, filesOf(ctx, data.shot), ctx.project.status]);

export async function refreshScene(ctx) {
  if (!open?.data || open.ctx.id !== ctx.id) return;
  open.ctx = ctx;
  const data = await load();
  if (!open?.data || data.shot !== open.shot) return;
  const seen = seenOf(ctx, data);
  if (seen === open.shown) return;
  Object.assign(open, { data, shown: seen });
  draw();
}
