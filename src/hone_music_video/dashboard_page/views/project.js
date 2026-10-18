// A project (design §13.2): its header, the views as tabs, the records they read, live updates.
// Every view is a function of `ctx` (the project, its records, the song player, the activity so far);
// a server-sent event refreshes the records and redraws the view when something changed. The Scenes view is
// Hone Frame's workspace (0027): it stays mounted across redraws and follows the stream's `frame` events.

import { api, duration, empty, formatMs, h, pill, spoken, toast } from "../core.js";
import { icon } from "../icons.js";
import { songPlayer, stopAll } from "../player.js";
import { refreshSidebar } from "../sidebar.js";
import { overviewView } from "./overview.js";
import { lyricsView } from "./lyrics.js";
import { planView } from "./plan.js";
import { closeScenes, routeScenes, scenesView } from "./scenes.js";
import { clipsView } from "./clips.js";
import { previewView } from "./preview.js";
import { closeScene, refreshScene } from "./scene.js";
import { videoView } from "./video.js";

const VIEWS = {
  overview: ["Overview", overviewView],
  lyrics: ["Lyrics", lyricsView],
  plan: ["Plan", planView], // 0027
  scenes: ["Scenes", scenesView], // Hone Frame's workspace (0027)
  clips: ["Clips", clipsView], // 0024
  preview: ["Preview", previewView], // 0024
  video: ["Video", videoView],
};

function counts(records) {
  const files = Object.values(records.shot_files);
  return {
    lyrics: records.timeline?.lines.length,
    plan: records.shots?.shots.length,
    scenes: records.plan?.items,
    clips: files.filter((f) => f.finish).length || null,
  };
}

function tabs(ctx) {
  const count = counts(ctx.records);
  return h("nav", { class: "tabs", "aria-label": "Project views" }, Object.entries(VIEWS).map(([key, [label]]) =>
    h("a", { href: `#/p/${ctx.id}${key === "overview" ? "" : `/${key}`}`, "aria-current": key === ctx.view ? "page" : null },
      icon(key), label, count[key] ? h("span", { class: "count" }, count[key]) : null)));
}

function header(ctx) {
  const { project, records } = ctx;
  const length = project.duration_ms ? formatMs(project.duration_ms) : "measuring…";
  const shots = records.shots?.shots.length;
  return h("header", { class: "project-head" },
    h("div", { class: "grow" },
      h("div", { class: "crumbs" }, h("a", { href: "#/" }, "Videos"), icon("arrow"), h("span", {}, project.name)),
      h("h1", {}, project.name),
      h("div", { class: "meta" },
        h("span", {}, icon("music"), length),
        shots ? h("span", {}, icon("shots"), `${shots} shots`) : null,
        h("span", {}, icon("clock"), `made ${new Date(project.created).toLocaleString([], { dateStyle: "medium", timeStyle: "short" })}`),
        pill(project.status), project.approve === "auto" ? h("span", { class: "pill auto", title: "Runs without stopping for your approval" }, "auto") : null,
        h("span", { class: `live${ctx.live ? " on" : ""}`, id: "live" }, h("span", { class: "dot" }), ctx.live ? "Live" : "Offline"))),
    autoToggle(ctx), prepareToggle(ctx),
    ["failed", "interrupted", "paused"].includes(project.status) ? h("button", { type: "button", class: "button", onclick: async () => {
      await api(`/projects/${ctx.id}/resume`, { method: "POST" });
      ctx.refresh();
    } }, "Resume the run") : null);
}

// Switch the project to unattended runs and back (0004); a gate waiting then passes unless it has errors.
function autoToggle(ctx) {
  const box = h("input", { type: "checkbox", checked: ctx.project.approve === "auto" });
  box.addEventListener("change", async () => {
    box.disabled = true;
    try {
      await api(`/projects/${ctx.id}/approve-mode`, { method: "POST", body: { approve: box.checked ? "auto" : "ask" } });
      toast(box.checked ? "The run continues without stopping for your approval, unless a check finds errors." : "The run stops at each review for you again.");
    } catch (error) { toast(error.message); }
    ctx.refresh();
  });
  return h("label", { class: "switch", title: "Each review is approved as soon as it is reached, unless a check finds errors" }, box, h("span", {}, "Run without stopping for my approval"));
}

// "Prepare only" (0028 §6): the run stops before the scenes, every step that needs the internet done.
function prepareToggle(ctx) {
  const { project } = ctx;
  if (project.status === "completed" || project.prepared || project.run.stages.some((s) => s.name === "scenes" && s.status !== "not_started" && s.status !== "pending")) return null;
  const box = h("input", { type: "checkbox", checked: !!project.prepare });
  box.addEventListener("change", async () => {
    box.disabled = true;
    try {
      await api(`/projects/${ctx.id}/prepare`, { method: "POST", body: { prepare: box.checked } });
      toast(box.checked ? "The run stops before the scenes, once the lyrics and the plan are made." : "The run goes on through the scenes.");
    } catch (error) { toast(error.message); }
    ctx.refresh();
  });
  return h("label", { class: "switch", title: "Stop when every step that needs the internet is done; run the rest later, offline" }, box, h("span", {}, "Prepare only"));
}

// Once a second: how long a stage has run, and the time left counting down between updates (0003).
function tickClocks() {
  for (const node of document.querySelectorAll("[data-since]")) {
    node.textContent = spoken(Math.max(0, Date.now() - Date.parse(node.dataset.since)));
  }
  for (const node of document.querySelectorAll("[data-elapsed]")) node.textContent = duration(Date.now() - Number(node.dataset.elapsed));
  for (const node of document.querySelectorAll("[data-until]")) node.textContent = duration(Number(node.dataset.until) - Date.now());
}

function listen(ctx) {
  const source = new EventSource(`/api/projects/${ctx.id}/events`);
  let timer = null;
  const live = (on) => {
    ctx.live = on;
    const node = document.getElementById("live");
    if (node) { node.classList.toggle("on", on); node.lastChild.textContent = on ? "Live" : "Offline"; }
  };
  source.onopen = () => live(true);
  source.onerror = () => live(false);
  source.onmessage = (message) => {
    const event = JSON.parse(message.data);
    ctx.events.push(event);
    if (event.event === "frame") ctx.scenes?.frameEvent(event);
    if (ctx.events.length > 400) ctx.events.splice(0, ctx.events.length - 400);
    clearTimeout(timer);
    timer = setTimeout(() => { ctx.refresh(); refreshSidebar(); }, 200);
  };
  return () => { source.close(); clearTimeout(timer); };
}

export async function projectView(main, id, view, rest = []) {
  const ctx = { id, view: VIEWS[view] ? view : "overview", rest, events: [], live: false, selected: null, scenes: null };
  const page = h("div", { class: "page" });
  let shown = "";
  ctx.render = () => {
    ctx.gallery = []; // the pictures and clips the view shows, in order, for the viewer (0003)
    page.replaceChildren(header(ctx), tabs(ctx), h("div", { class: "view" }, VIEWS[ctx.view][1](ctx)));
    tickClocks();
  };
  ctx.refresh = async () => {
    const [project, records] = await Promise.all([api(`/projects/${id}`), api(`/projects/${id}/records`)]);
    Object.assign(ctx, { project, records, player: songPlayer(id, records.song) });
    const seen = JSON.stringify([project, records, ctx.view === "overview" ? ctx.events.length : 0]);
    if (seen !== shown) { shown = seen; ctx.render(); }
    refreshScene(ctx); // an open scene viewer follows the run (0024)
  };
  try {
    await ctx.refresh();
  } catch (error) {
    main.append(h("div", { class: "page" }, empty(icon("alert"), "This video cannot be shown", error.message)));
    return null;
  }
  main.append(page);
  const stop = listen(ctx);
  const clock = setInterval(tickClocks, 1000);
  const leave = () => { stop(); clearInterval(clock); stopAll(); closeScene(); closeScenes(ctx); };
  // Another view of this project (or another item of the Scenes view): drawn without leaving the project.
  leave.update = (next, more = []) => {
    const was = ctx.view;
    ctx.view = VIEWS[next] ? next : "overview";
    ctx.rest = more;
    if (ctx.view !== "scenes") closeScenes(ctx);
    if (was !== ctx.view || ctx.view !== "scenes" || !ctx.scenes) ctx.render(); else routeScenes(ctx);
  };
  return leave;
}
