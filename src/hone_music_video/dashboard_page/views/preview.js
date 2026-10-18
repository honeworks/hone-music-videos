// Preview (0024 §3): the song with, at each moment, the shot that covers it, from the best file its take in
// use has so far: the finished clip, the raw clip, the start frame, else a dark card. A clip
// plays from its start at the shot's start, muted, and holds its last frame when shorter (as the assembly
// cuts it, §12). The screen is kept while the page is open, so records arriving during playback change a
// shot's file at its next turn without stopping the song. Under it the shots coloured by what each has; a
// click seeks. Keys: space plays, ←/→ the previous and next shot. A click on the picture opens the scene.

import { empty, formatMs, h } from "../core.js";
import { icon } from "../icons.js";
import { seek, toggle, watch } from "../player.js";
import { transport } from "../timeline.js";
import { openScene } from "./scene.js";

export const KINDS = [["finished", "finished clip"], ["raw", "raw clip"], ["frame", "start frame"], ["none", "nothing yet"]];

// The best file a shot's take in use has (its chosen files, and its newest draft).
export function bestFile(files) {
  if (files?.finish) return { kind: "finished", src: files.finish, video: true };
  if (files?.clips) return { kind: "raw", src: files.clips, video: true };
  if (files?.stills) return { kind: "frame", src: files.stills, video: false };
  return { kind: "none", src: null, video: false };
}

export function shotAt(shots, ms) {
  return shots.findIndex((s) => ms >= s.start_ms && ms < s.end_ms);
}

// Where a clip should be at song time `ms`, in seconds, and whether it holds its last frame.
export function clipTime(shot, ms, clipSeconds) {
  const at = Math.max(0, (ms - shot.start_ms) / 1000);
  return clipSeconds && at >= clipSeconds ? { at: Math.max(0, clipSeconds - 0.04), hold: true } : { at, hold: false };
}

const previews = new Map(); // per project: its screen, kept while the page is open

function syncVideo(video, time, playing) {
  if (time.hold || !playing) {
    if (!video.paused) video.pause();
    if (Math.abs(video.currentTime - time.at) > 0.05) video.currentTime = time.at;
  } else if (video.paused) {
    video.currentTime = time.at;
    video.play().catch(() => {});
  } else if (Math.abs(video.currentTime - time.at) > 0.3) video.currentTime = time.at;
}

function lineAt(ctx, ms) {
  return (ctx.records.timeline?.lines || []).find((l) => ms >= l.start_ms && ms < l.end_ms)?.text || "";
}

// The screen and its `frame(ms, playing)`, which the song's player calls on every frame and seek.
export function screenOf(ctx) {
  const picture = h("img", { class: "pv-picture", alt: "" });
  const video = h("video", { class: "pv-video", playsinline: true, preload: "auto" });
  video.muted = true; // the song plays
  const preload = h("video", { preload: "auto", hidden: true });
  preload.muted = true;
  const blank = h("div", { class: "pv-blank" });
  const tag = h("span", { class: "media-tag" });
  const lyric = h("div", { class: "pv-lyric", dir: "auto" });
  const node = h("button", { type: "button", class: "pv-screen", "aria-label": "Open this shot" }, picture, video, blank, tag, lyric, preload);
  const c = { ctx, node, shot: null, key: "" };
  node.addEventListener("click", () => {
    if (!c.shot) return;
    c.ctx.player.audio.pause();
    openScene(c.ctx, c.shot.id, bestFile(c.ctx.records.shot_files[c.shot.id]).video ? "clip" : "frame");
  });
  c.frame = (ms, playing) => {
    const shots = c.ctx.records.shots?.shots || [];
    const n = shotAt(shots, ms);
    const shot = shots[n] || null;
    const file = shot ? bestFile(c.ctx.records.shot_files[shot.id]) : bestFile(null);
    const key = `${shot?.id}|${file.src}`;
    if (key !== c.key) {
      c.key = key;
      c.shot = shot;
      node.dataset.kind = file.kind;
      if (!file.video) video.removeAttribute("src");
      else if (video.getAttribute("src") !== file.src) video.src = file.src;
      if (file.src && !file.video && picture.getAttribute("src") !== file.src) picture.src = file.src;
      blank.replaceChildren(...(shot && !file.src ? [h("strong", { class: "mono" }, shot.id), h("span", {}, shot.beat)] : []));
      tag.textContent = shot ? `${shot.id} · ${KINDS.find(([k]) => k === file.kind)[1]}` : "";
      const next = shots[n + 1] && bestFile(c.ctx.records.shot_files[shots[n + 1].id]);
      if (next?.video && preload.getAttribute("src") !== next.src) preload.src = next.src;
    }
    if (file.video) syncVideo(video, clipTime(shot, ms, video.duration || 0), playing);
    lyric.textContent = lineAt(c.ctx, ms);
  };
  return c;
}

function lane(ctx, shots, total) {
  const pct = (ms) => `${(100 * ms) / total}%`;
  const head = h("div", { class: "tl-playhead" });
  const node = h("div", { class: "pv-lane" }, shots.map((shot) => {
    const kind = bestFile(ctx.records.shot_files[shot.id]).kind;
    return h("button", { type: "button", class: `pv-shot pv-${kind}`, style: { left: pct(shot.start_ms), width: pct(shot.end_ms - shot.start_ms) },
      title: `${shot.id} · ${formatMs(shot.start_ms)} · ${KINDS.find(([k]) => k === kind)[1]}\n${shot.beat}`, "aria-label": `Play from ${shot.id}`,
      onclick: () => { seek(ctx.player, shot.start_ms); if (ctx.player.audio.paused) toggle(ctx.player); } });
  }), head);
  watch(ctx.player, node, (ms) => { head.style.left = pct(Math.min(ms, total)); });
  return node;
}

function legend(ctx, shots) {
  const count = Object.fromEntries(KINDS.map(([k]) => [k, 0]));
  for (const shot of shots) count[bestFile(ctx.records.shot_files[shot.id]).kind] += 1;
  return h("div", { class: "legend" }, KINDS.filter(([k]) => count[k]).map(([k, label]) => h("span", {}, h("i", { class: `swatch pv-${k}` }), `${count[k]} ${label}`)));
}

function keys(c) {
  return (event) => {
    if (!c.node.isConnected || document.body.classList.contains("lb-open")) return;
    if (event.target.closest?.("input, textarea, select, [contenteditable]")) return;
    const shots = c.ctx.records.shots?.shots || [];
    const ms = c.ctx.player.audio.currentTime * 1000;
    if (event.key === " ") { event.preventDefault(); toggle(c.ctx.player); }
    else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
      event.preventDefault();
      const n = shotAt(shots, ms);
      const to = shots[Math.max(0, Math.min(shots.length - 1, (n < 0 ? 0 : n) + (event.key === "ArrowLeft" ? -1 : 1)))];
      if (to) seek(c.ctx.player, to.start_ms);
    }
  };
}

function screen(ctx) {
  let c = previews.get(ctx.id);
  if (!c || c.player !== ctx.player) {
    c = screenOf(ctx);
    c.player = ctx.player;
    previews.set(ctx.id, c);
    document.addEventListener("keydown", keys(c));
  }
  c.ctx = ctx;
  c.key = ""; // the records may have changed: choose every shot's file again
  if (![...ctx.player.watchers].some((w) => w.node === c.node)) watch(ctx.player, c.node, c.frame);
  else c.frame(ctx.player.audio.currentTime * 1000, !ctx.player.audio.paused);
  return c.node;
}

export function previewView(ctx) {
  const shots = ctx.records.shots?.shots;
  const total = ctx.project.duration_ms || ctx.records.timeline?.duration_ms;
  if (!shots?.length || !total) return empty(icon("preview"), "No preview yet", "Once the plan is approved, the preview plays the song with each shot's best picture or clip so far: its start frame (its scene's picture), then its raw and finished clip.");
  const ratio = (ctx.project.project.settings.aspect_ratio || "16:9").replace(":", " / ");
  const node = screen(ctx);
  node.style.aspectRatio = ratio;
  return h("div", { class: "stack" },
    h("p", { class: "muted small" }, "A preview from what is made so far. The Video view has the exact cut once the video is assembled."),
    h("section", { class: "panel preview" }, node,
      h("div", { class: "row between wrap" }, transport(ctx.player, total), legend(ctx, shots)),
      lane(ctx, shots, total)));
}
