// Lyrics (design §13.2, D-003): the sections, lines and words with their times (m:ss.mmm), the
// instrumental spans and the checks, each finding under the line it is about. Click a line to play exactly
// that slice of the song. At the gate: fix a line's start and end (timing.js, 0018), then approve, or
// reject with a note to run the lyrics editor again (D-015).

import { empty, formatMs, h, humanize, spoken } from "../core.js";
import { icon } from "../icons.js";
import { blocked, checks, findingsOf, gateBar, notesList, stat } from "../parts.js";
import { playSlice, watch } from "../player.js";
import { songPanel } from "../timeline.js";
import { lyricsCalls } from "./calls.js";
import { approveLyrics, draftOf, isOpen, measuredOf, timesOf, timingBar, timingEditor, timingToggle } from "./timing.js";

// The checks' findings under a line (about the line, or one of its words).
function lineNotes(ctx, line) {
  return notesList(findingsOf(ctx.records.lyrics_check, line.id), "line-notes");
}

const range = (span) => `${formatMs(span.start_ms)} – ${formatMs(span.end_ms)}`;

// A line with its start and end (the draft's while the owner changes them), marked when the owner timed it.
function lineRow(ctx, line, shown) {
  const draft = draftOf(ctx.id);
  const times = timesOf(line, draft, measuredOf(ctx));
  const mark = line.id in draft ? "changed" : ctx.records.timeline.owner_timed?.includes(line.id) ? "your timing" : null;
  const words = line.words.map((w) => h("span", { class: "word", title: `${w.text} ${range(w)}` }, w.text, " "));
  const row = h("button", { type: "button", class: "lyric-line", onclick: () => playSlice(ctx.player, times.start_ms, times.end_ms) },
    h("span", { class: "lyric-time mono" }, icon("play"), h("span", {}, formatMs(times.start_ms), h("br"), h("span", { class: "faint" }, formatMs(times.end_ms)))),
    h("span", { class: "lyric-text", dir: "auto" }, words.length ? words : line.text, mark ? h("span", { class: "chip timing-mark" }, mark) : null),
    h("span", { class: "lyric-end mono faint" }, spoken(times.end_ms - times.start_ms)));
  shown.push({ line, row, words });
  return [h("div", { class: "lyric-line-wrap" }, row, timingToggle(ctx, line)),
    isOpen(ctx, line) ? timingEditor(ctx, line, times) : null, lineNotes(ctx, line)];
}

function sectionBlock(ctx, section, lines, shown, tone) {
  return h("section", { class: `lyric-section tone-${tone}` },
    h("header", {}, h("span", { class: "section-kind" }, humanize(section.kind)), h("span", { class: "faint small" }, section.id),
      h("span", { class: "grow" }), h("span", { class: "mono small muted" }, range(section))),
    lines.map((line) => lineRow(ctx, line, shown)));
}

function instrumentalBlock(span) {
  return h("div", { class: "instrumental-row" }, icon("music"), h("span", {}, `Instrumental · ${humanize(span.kind)}`),
    h("span", { class: "grow" }), h("span", { class: "mono small" }, range(span)));
}

// Light the line and the word being sung while the song plays.
function follow(ctx, list, shown) {
  let current = null;
  watch(ctx.player, list, (ms) => {
    const found = shown.find((s) => s.line.start_ms <= ms && ms < s.line.end_ms) || null;
    if (current && current !== found) { current.row.classList.remove("playing"); current.words.forEach((w) => w.classList.remove("on")); }
    current = found;
    if (!found) return;
    found.row.classList.add("playing");
    found.line.words.forEach((w, n) => found.words[n].classList.toggle("on", w.start_ms <= ms && ms < w.end_ms));
  });
}

function sheet(ctx, timed) {
  const shown = [];
  const parts = [
    ...timed.sections.map((section, n) => ({ at: section.start_ms, node: () => sectionBlock(ctx, section, timed.lines.filter((l) => l.section === section.id), shown, n % 4) })),
    ...timed.instrumental.map((span) => ({ at: span.start_ms, node: () => instrumentalBlock(span) })),
  ].sort((a, b) => a.at - b.at);
  const list = h("div", { class: "lyric-sheet" }, parts.map((p) => p.node()));
  follow(ctx, list, shown);
  return list;
}

function side(ctx, timed) {
  const words = timed.lines.reduce((sum, line) => sum + line.words.length, 0);
  return h("aside", { class: "stack sticky" },
    h("section", { class: "panel" }, h("div", { class: "panel-head" }, h("h2", {}, "Checks")), checks(ctx.records.lyrics_check, "timed lyrics")),
    h("section", { class: "panel" }, h("div", { class: "stats two" }, stat(timed.lines.length, "lines"), stat(timed.sections.length, "sections"),
      stat(words, "words"), stat(timed.language || "–", "language"))),
    lyricsCalls(ctx),
    h("p", { class: "muted small hint-text" }, icon("info"), "Times come from the heard words. While the lyrics wait for you, open a line's timing (the clock beside it) to set its start or end; the words move with it. To change the words, lines or sections, reject with a note."));
}

// The gate bar: Approve (not while the checks found errors), or reject with a note to run the lyrics
// editor again (D-015); the times are fixed in the lines below (0018).
function lyricsGate(ctx) {
  const errors = ctx.records.lyrics_check?.errors.length || 0;
  const text = errors
    ? `The checks found ${errors} ${errors === 1 ? "error" : "errors"}, so the lyrics cannot be approved: fix the times below and save them, or reject with a note.`
    : "Play the lines you are unsure of; fix a line's times below, or reject with a note to run the lyrics editor again; approve to plan the scenes.";
  return gateBar(ctx, "review_lyrics", text, { approvable: !blocked(ctx, "review_lyrics"), approve: approveLyrics(ctx.id) });
}

export function lyricsView(ctx) {
  const timed = ctx.records.timeline;
  if (!timed) return empty(icon("lyrics"), "No timed lyrics yet", "Stage 3 hears the words and times every line to the millisecond; they appear here, ready to play line by line.");
  const draft = draftOf(ctx.id);
  return h("div", { class: "stack" },
    lyricsGate(ctx),
    timingBar(ctx),
    songPanel(ctx, { lines: timed.lines.map((line) => ({ ...line, ...timesOf(line, draft, measuredOf(ctx)) })) }),
    h("div", { class: "split" }, sheet(ctx, timed), side(ctx, timed)));
}
