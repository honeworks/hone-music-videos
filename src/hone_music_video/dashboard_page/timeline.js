// The song as a timeline: the waveform (drawn from the player's peaks) with the sections above it, the
// lines and the shots below it, a playhead and time marks. Positions are percentages of the song, so the
// lanes follow any width; only the waveform canvases are redrawn on a resize or a theme change.

import { empty, FRAMINGS, formatMs, h, humanize } from "./core.js";
import { icon } from "./icons.js";
import { playSlice, seek, toggle, watch } from "./player.js";

const pct = (ms, total) => `${(100 * ms) / total}%`;

function place(start, end, total) {
  return { left: pct(start, total), width: pct(Math.max(end - start, 0), total) };
}

function drawBars(canvas, peaks, colour) {
  const ratio = devicePixelRatio || 1;
  const { width, height } = canvas.getBoundingClientRect();
  if (!width) return;
  canvas.width = Math.round(width * ratio);
  canvas.height = Math.round(height * ratio);
  const paint = canvas.getContext("2d");
  paint.scale(ratio, ratio);
  paint.fillStyle = colour;
  const bars = Math.floor(width / 3);
  for (let n = 0; n < bars; n += 1) {
    const from = Math.floor((n * peaks.length) / bars);
    const to = Math.max(from + 1, Math.floor(((n + 1) * peaks.length) / bars));
    let peak = 0;
    for (let i = from; i < to; i += 1) peak = Math.max(peak, peaks[i]);
    const bar = Math.max(2, Math.pow(peak, 0.8) * (height - 6));
    paint.beginPath();
    paint.roundRect(n * 3, (height - bar) / 2, 2, bar, 1);
    paint.fill();
  }
}

function waveform(player, total) {
  const base = h("canvas", { class: "tl-canvas", "aria-hidden": "true" });
  const lit = h("canvas", { class: "tl-canvas", "aria-hidden": "true" });
  const played = h("div", { class: "tl-played" }, lit);
  const head = h("div", { class: "tl-playhead" });
  const hover = h("div", { class: "tl-hover", hidden: true });
  const wave = h("div", { class: "tl-wave skeleton" }, base, played, head, hover);
  let peaks = null;
  const draw = () => {
    if (!peaks) return;
    const colours = getComputedStyle(wave);
    lit.style.width = `${wave.clientWidth}px`;
    drawBars(base, peaks, colours.getPropertyValue("--wave").trim());
    drawBars(lit, peaks, colours.getPropertyValue("--wave-played").trim());
  };
  player.peaks.then((found) => {
    wave.classList.remove("skeleton");
    if (found) { peaks = found.peaks; draw(); } else wave.classList.add("flat");
  });
  new ResizeObserver(draw).observe(wave);
  const onTheme = () => (wave.isConnected ? requestAnimationFrame(draw) : removeEventListener("themechange", onTheme));
  addEventListener("themechange", onTheme);
  watch(player, wave, (ms) => {
    played.style.width = pct(Math.min(ms, total), total);
    head.style.left = pct(Math.min(ms, total), total);
  });
  const at = (event) => {
    const box = wave.getBoundingClientRect();
    return Math.round(Math.min(Math.max((event.clientX - box.left) / box.width, 0), 1) * total);
  };
  wave.addEventListener("pointermove", (event) => {
    hover.hidden = false;
    hover.style.left = pct(at(event), total);
    hover.dataset.time = formatMs(at(event));
  });
  wave.addEventListener("pointerleave", () => { hover.hidden = true; });
  wave.addEventListener("click", (event) => {
    seek(player, at(event));
    if (player.audio.paused) toggle(player);
  });
  return wave;
}

function sectionLane(sections, instrumental, total) {
  return h("div", { class: "tl-lane tl-sections" },
    instrumental.map((span) => h("div", { class: "tl-instrumental", style: place(span.start_ms, span.end_ms, total), title: `${span.kind} (instrumental) ${formatMs(span.start_ms)}–${formatMs(span.end_ms)}` })),
    sections.map((section, n) => h("div", { class: `tl-section tone-${n % 4}`, style: place(section.start_ms, section.end_ms, total), title: `${section.id} ${formatMs(section.start_ms)}–${formatMs(section.end_ms)}` }, h("span", {}, section.kind))));
}

function lineLane(lines, total, player) {
  return h("div", { class: "tl-lane tl-lines" }, lines.map((line) => h("button", {
    type: "button", class: "tl-line", style: place(line.start_ms, line.end_ms, total), title: `${line.id} ${formatMs(line.start_ms)} ${line.text}`,
    "aria-label": `Play line ${line.id}`, onclick: () => playSlice(player, line.start_ms, line.end_ms),
  })));
}

// The shot under a pointer (a touch keeps sending its events to where it began, so it is looked up).
const shotAt = (event) => document.elementFromPoint(event.clientX, event.clientY)?.closest(".tl-shot")?.dataset.shot;

// `selected` is one shot id or a Set of them; with `onRange(from, to)` a press and a drag over the
// shots picks a range (a click is a range of one, 0008) instead of `onShot`.
function shotLane(shots, total, { selected, onShot, onRange, made }) {
  const isSelected = (id) => (selected instanceof Set ? selected.has(id) : id === selected);
  const lane = h("div", { class: `tl-lane tl-shots${onRange ? " picking" : ""}` }, shots.map((shot) => h("button", {
    type: "button", class: `tl-shot f-${shot.framing}${isSelected(shot.id) ? " selected" : ""}${made && !made.has(shot.id) ? " waiting" : ""}`,
    style: place(shot.start_ms, shot.end_ms, total), title: `${shot.id} · ${shot.framing} · ${formatMs(shot.start_ms)}–${formatMs(shot.end_ms)}\n${shot.beat}`,
    "aria-label": `Shot ${shot.id}`, "aria-pressed": onRange ? String(isSelected(shot.id)) : null, dataset: { shot: shot.id },
    onclick: onRange ? null : () => onShot(shot),
    onkeydown: onRange ? (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onRange(shot.id, shot.id); } } : null,
  }, (shot.end_ms - shot.start_ms) / total >= 0.02 ? h("span", {}, shot.id.replace(/^S0*/, "")) : null, shot.faces ? h("i", { class: "face", title: "a face must be recognisable" }) : null)));
  if (onRange) {
    let from = null;
    lane.addEventListener("pointerdown", (event) => { from = shotAt(event) || null; if (from) event.preventDefault(); });
    lane.addEventListener("pointerup", (event) => { const to = shotAt(event); if (from && to) onRange(from, to); from = null; });
    lane.addEventListener("pointercancel", () => { from = null; });
  }
  return lane;
}

function axis(total) {
  const step = [5, 10, 15, 30, 60, 120].find((s) => total / (s * 1000) <= 11) || 300;
  const marks = [];
  for (let t = 0; t <= total; t += step * 1000) marks.push(t);
  return h("div", { class: "tl-axis", "aria-hidden": "true" },
    marks.map((t) => h("span", { style: { left: pct(t, total) } }, formatMs(t).slice(0, -4))));
}

// timeline(player, total, {sections, instrumental, lines, shots, selected, onShot, onRange})
export function timeline(player, total, plan = {}) {
  const onShot = plan.onShot || ((shot) => playSlice(player, shot.start_ms, shot.end_ms));
  const sections = plan.sections || [];
  return h("div", { class: "timeline" },
    sections.length || plan.instrumental?.length ? sectionLane(sections, plan.instrumental || [], total) : null,
    waveform(player, total),
    plan.lines?.length ? lineLane(plan.lines, total, player) : null,
    plan.shots?.length ? shotLane(plan.shots, total, { selected: plan.selected, onShot, onRange: plan.onRange, made: plan.made }) : null,
    axis(total));
}

// The play button and the time: 0:42.180 / 5:13.000.
export function transport(player, total) {
  const button = h("button", { type: "button", class: "round-button", "aria-label": "Play or pause the song", onclick: () => toggle(player) }, icon("play"));
  const now = h("span", { class: "now" }, formatMs(0));
  const node = h("div", { class: "transport" }, button,
    h("div", { class: "clock" }, now, h("span", { class: "faint" }, ` / ${formatMs(total)}`)));
  let shown = null;
  watch(player, node, (ms, playing) => {
    now.textContent = formatMs(Math.round(ms));
    if (shown !== playing) { button.replaceChildren(icon(playing ? "pause" : "play")); shown = playing; }
  });
  return node;
}

function legend(shots) {
  const used = new Set(shots.map((s) => s.framing));
  return h("div", { class: "legend" }, FRAMINGS.filter((f) => used.has(f)).map((f) =>
    h("span", {}, h("i", { class: `swatch f-${f}` }), humanize(f))));
}

// While the frames are being made, the shots still waiting for one are dimmed on the timeline.
function madeSoFar(ctx) {
  const made = Object.entries(ctx.records.shot_files).filter(([, f]) => f.stills).map(([id]) => id);
  return made.length ? new Set(made) : null;
}

export function songPanel(ctx, extra = {}) {
  const total = ctx.project.duration_ms || ctx.records.timeline?.duration_ms;
  if (!total) return h("section", { class: "panel" }, empty(icon("music"), "Measuring the song", "Its waveform, sections and shots appear here once the first stage has measured it."));
  const timed = ctx.records.timeline || {};
  const shots = ctx.records.shots?.shots || [];
  return h("section", { class: "panel hero" },
    h("div", { class: "hero-head" }, transport(ctx.player, total),
      h("div", { class: "grow" }, h("div", { class: "eyebrow" }, "The song"),
        h("div", { class: "hero-title" }, timed.lines ? `${timed.sections.length} sections · ${timed.lines.length} lines` : "Lyrics not timed yet",
          shots.length ? ` · ${shots.length} shots` : "")),
      shots.length ? legend(shots) : null),
    timeline(ctx.player, total, { sections: timed.sections, instrumental: timed.instrumental, shots, made: madeSoFar(ctx), ...extra }));
}
