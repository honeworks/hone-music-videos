// Video (design §13.2, §12): the assembled video with the song, the downloads (the video, every clip, the
// edit list, the edit for DaVinci Resolve and Premiere), what the video cost (design §13.5), the edit
// list itself (each shot's frames in the video, design §5.3) and "Assemble again" (D-036).

import { api, empty, formatMs, h, STAGE_NAMES } from "../core.js";
import { icon } from "../icons.js";
import { actionButton, stat } from "../parts.js";
import { stopAll } from "../player.js";

const name = (url) => decodeURIComponent(String(url).split("?")[0].split("/").pop());

function download(url, label, detail) {
  return h("a", { class: "download", href: url, download: "" }, icon("download"),
    h("span", { class: "grow" }, h("strong", {}, label), detail ? h("span", { class: "muted xs" }, detail) : null));
}

// The clip's frames from its first; a clip shorter than its shot holds its last frame (D-035).
function held(cut) {
  return cut.held_frames ? h("span", { class: "badge warn", title: "the clip was shorter than its shot: its last frame is held" }, icon("alert"), `${cut.held_frames} held`) : null;
}

function edlTable(assembly) {
  const fps = assembly.fps;
  return h("div", { class: "table-wrap" }, h("table", { class: "table" },
    h("thead", {}, h("tr", {}, ["Shot", "First frame", "Last frame", "Starts", "Length", "Clip"].map((t) => h("th", {}, t)))),
    h("tbody", {}, assembly.edl.map((cut) => h("tr", {},
      h("td", { class: "mono" }, cut.shot), h("td", { class: "mono" }, cut.first_frame), h("td", { class: "mono" }, cut.last_frame),
      h("td", { class: "mono" }, formatMs(Math.round((cut.first_frame * 1000) / fps))),
      h("td", { class: "mono" }, `${cut.last_frame - cut.first_frame + 1} frames `, held(cut)),
      h("td", { class: "mono faint clip-path", title: cut.clip }, cut.clip.split("/").slice(-3).join("/")))))));
}

// Assemble again: once every clip is finished and while the run is stopped; a fork of the run where only
// the assembly runs, so a video assembled by an older version is cut with this one (D-036).
function assembleAgain(ctx) {
  const finished = ctx.project.run.stages.find((s) => s.name === "finish")?.status === "done";
  const stopped = ctx.project.status !== "queued" && ctx.project.run.status !== "running";
  if (!finished || !stopped) return null;
  return actionButton(ctx, "Assemble again", "film", "assemble", {}, "Assembling the video again from the finished clips.", "ghost");
}

function player(ctx) {
  if (!ctx.records.video) {
    return h("section", { class: "panel" }, empty(icon("video"), "No video yet", "The last stage cuts every finished clip to its shot's frames and lays them under the song; the video appears here."), assembleAgain(ctx));
  }
  const video = h("video", { class: "main-video", src: ctx.records.video, controls: true, preload: "metadata", poster: Object.values(ctx.records.shot_files)[0]?.stills || null });
  video.addEventListener("play", stopAll); // one sound at a time
  return h("section", { class: "panel flush video-panel" }, video);
}

function downloads(ctx) {
  const clips = Object.entries(ctx.records.shot_files).filter(([, f]) => f.finish);
  return h("section", { class: "panel" }, h("div", { class: "panel-head" }, h("h2", {}, "Downloads")),
    h("div", { class: "downloads" },
      ctx.records.video ? download(ctx.records.video, "video.mp4", "the video with the song") : null,
      ctx.records.edl ? download(ctx.records.edl, "edl.json", "the edit list, every shot's frames") : null,
      ctx.records.edit_xml ? download(ctx.records.edit_xml, "edit.xml", "the edit for DaVinci Resolve and Premiere (FCP7 XML)") : null,
      ctx.records.edit_edl ? download(ctx.records.edit_edl, "edit.edl", "the same edit as a CMX3600 EDL") : null,
      clips.length ? h("details", { class: "clip-list" }, h("summary", {}, `${clips.length} finished clips`),
        clips.map(([id, f]) => download(f.finish, `${id} · ${name(f.finish)}`))) : null,
      !ctx.records.video && !ctx.records.edl && !clips.length ? h("p", { class: "muted small" }, "The files appear here as the run makes them.") : null));
}

// What the video cost so far (design §13.5, D-062): the hosted calls' recorded prices and each stage's
// time, read from the run's records when the panel is drawn; a call without a price is "unknown".
const hours = (ms) => (ms >= 360000 ? `${(ms / 3600000).toFixed(1)} h` : `${Math.round(ms / 60000)} min`);
const dollars = (usd) => `$${usd.toFixed(2)}`;

function costTable(costs) {
  const rows = costs.stages.filter((s) => s.first.time_ms + s.reruns.time_ms + s.redos.time_ms > 0);
  // a part's time, then its hosted calls' price ("+ ?" when a call has none recorded)
  const part = (p) => {
    if (!p.time_ms && !p.calls) return "–";
    const price = p.calls ? ` · ${dollars(p.cost_usd)}${p.unknown_calls ? " + ?" : ""}` : "";
    return `${hours(p.time_ms)}${price}`;
  };
  return h("div", { class: "table-wrap" }, h("table", { class: "table" },
    h("thead", {}, h("tr", {}, ["Stage", "Runs on", "First pass", "Reruns", "Redos"].map((t) => h("th", {}, t)))),
    h("tbody", {}, rows.map((s) => h("tr", {}, h("td", {}, STAGE_NAMES[s.stage] || s.stage), h("td", { class: "muted" }, s.where.toUpperCase()),
      ...[s.first, s.reruns, s.redos].map((p) => h("td", { class: "mono" }, part(p))))))));
}

function costPanel(ctx) {
  const panel = h("section", { class: "panel" }, h("div", { class: "panel-head" }, h("h2", {}, "What it cost")),
    h("p", { class: "muted small" }, "Adding up the run's records…"));
  api(`/projects/${ctx.id}/costs`).then((costs) => {
    const unknown = costs.unknown_calls ? ` (and ${costs.unknown_calls} calls without a recorded price)` : "";
    panel.replaceChildren(h("div", { class: "panel-head" }, h("h2", {}, "What it cost")),
      h("p", {}, `This video cost ${dollars(costs.hosted_usd)} of hosted calls${unknown} and ${hours(costs.gpu_ms)} of GPU.`),
      costs.store_found ? null : h("p", { class: "muted small" }, `No hone-models records found at ${costs.store}: the planners' calls are counted as unknown.`),
      h("div", { class: "stats" }, stat(dollars(costs.hosted_usd), "hosted calls"), stat(hours(costs.gpu_ms), "GPU"),
        stat(hours(costs.cpu_ms), "CPU"), stat(hours(costs.hosted_ms), "waiting for hosted models"),
        stat(`${dollars(costs.added_usd)} · ${hours(costs.added_ms)}`, "added by reruns and redos")),
      costTable(costs));
  }).catch((error) => panel.replaceChildren(h("p", { class: "muted small" }, `The cost could not be read: ${error.message}`)));
  return panel;
}

export function videoView(ctx) {
  const assembly = ctx.records.assembly;
  return h("div", { class: "stack" },
    h("div", { class: "split" }, player(ctx), downloads(ctx)),
    costPanel(ctx),
    assembly ? h("section", { class: "panel" }, h("div", { class: "panel-head" }, h("h2", {}, "Edit list"),
      h("span", { class: "muted small grow" }, `${assembly.edl.length} cuts at ${assembly.fps} fps`), assembleAgain(ctx)), edlTable(assembly)) : null);
}
