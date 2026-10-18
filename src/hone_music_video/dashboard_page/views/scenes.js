// Scenes (0027 §6, 0030 §1): the frame project the plan wrote. The run bar, then the board (one card per
// shot, as on Clips, and the subjects' pictures; a card opens the scene viewer with the item's actions),
// Hone Frame's workspace (the items in file order, the open item with its versions and fields, the
// activity), the sheets, the project file and the guide as tabs. Routes: #/p/<id>/scenes[/items |
// /i/<item> | /sheets | /file | /guide]. Above it, the gate bar while `review_scenes` waits: approving takes the scenes as they
// are, and the clips start.
//
// The workspace is mounted once per open project and kept across the project view's redraws (a redraw
// moves the same node back in), so an edit being typed survives the run's live updates. It reloads the
// frame project on each `frame` event of the page's event stream, and every few seconds while it runs.
// Hone Frame: the workspace is dashboard_page/screens/project.js's, ported in ../frame/.

import { empty, h } from "../core.js";
import { icon } from "../icons.js";
import { gateBar } from "../parts.js";
import { api } from "../frame/api.js";
import { emit, loadModels, loadProject, on, state } from "../frame/state.js";
import { createRunBar } from "../frame/screens/runbar.js";
import * as workspace from "../frame/screens/workspace.js";
import * as board from "./scene-board.js";
import { closeFrameScene } from "./scene-frame.js";
import * as sheets from "../frame/screens/sheets.js";
import * as file from "../frame/screens/file.js";
import * as guide from "../frame/screens/guide.js";

const TABS = { board: ["Board", board], items: ["Workspace", workspace], sheets: ["Sheets", sheets], file: ["Project file", file], guide: ["Guide", guide] };
const POLL_MS = 3000; // while the frame run is busy: its elapsed time and estimate stay fresh
const BUSY = ["queued", "running", "pausing"];

// "#/p/<id>/scenes" -> the board; "…/scenes/i/<item>" -> {tab: "items", item}; "…/scenes/items" -> the
// workspace; "…/scenes/sheets" and the other tabs by name (0030 §1).
export function sceneRoute(id, rest) {
  const [first, second] = rest;
  if (first === "i") return { project: id, tab: "items", item: second || null };
  return { project: id, tab: TABS[first] ? first : "board", item: null };
}

function mountWorkspace(id, route, getCtx) {
  const bar = createRunBar(id);
  const tabs = h("nav", { class: "tabs hf-tabs", "aria-label": "Scenes" });
  const body = h("div", { class: "project-body" });
  const el = h("div", { class: "hf project" }, bar.el, tabs, body);
  let tab = null, child = null, timer = null, closed = false;

  function drawTabs() {
    tabs.replaceChildren(...Object.entries(TABS).map(([key, [label]]) => h("a", {
      href: key === "board" ? `#/p/${encodeURIComponent(id)}/scenes` : `#/p/${encodeURIComponent(id)}/scenes/${key}`,
      "aria-current": key === tab ? "page" : null,
    }, label)));
  }

  async function show(next) {
    if (next.tab === tab && child && child.update) return child.update(next);
    if (child && child.unmount) child.unmount();
    tab = next.tab;
    drawTabs();
    body.replaceChildren();
    child = await TABS[tab][1].mount(body, next, getCtx);
  }

  function poll() {
    clearTimeout(timer);
    if (closed) return;
    timer = setTimeout(async () => {
      if (BUSY.includes(state.project?.run?.status)) await loadProject(id).catch(() => {});
      poll();
    }, POLL_MS);
  }

  const offs = [
    on("run", (run) => bar.update(run, state.project)),
    on("item", () => bar.update(state.project.run, state.project)),
    on("project", (view) => bar.update(view.run, view)),
    on("resync", () => loadProject(id).catch(() => {})),
  ];
  const ready = (async () => {
    api.open(id);
    const [view] = await Promise.all([loadProject(id), loadModels().catch(() => [])]);
    bar.update(view.run, view);
    await show(route);
    poll();
  })();
  return {
    el, ready, show,
    frameEvent(event) { emit("event", event); loadProject(id).catch(() => {}); },
    close() {
      closed = true;
      closeFrameScene();
      clearTimeout(timer);
      offs.forEach((off) => off());
      bar.destroy();
      if (child && child.unmount) child.unmount();
    },
  };
}

// The gate bar: Approve once every scene has a picture in use (read live, as the owner works below).
function scenesGate(ctx) {
  const missing = ctx.records.scenes_missing || [];
  const text = missing.length
    ? `${missing.length} ${missing.length === 1 ? "scene has" : "scenes have"} no picture in use yet (${missing.slice(0, 6).join(", ")}${missing.length > 6 ? "…" : ""}): accept, pick or run them below first.`
    : "Every scene has a picture in use. Approve to make the clips from them; a scene changed later remakes only its clip.";
  return gateBar(ctx, "review_scenes", text, { approvable: !missing.length });
}

// Mount the workspace, or show the route's tab and item in it.
export function routeScenes(ctx) {
  const route = sceneRoute(ctx.id, ctx.rest || []);
  if (!ctx.scenes) {
    ctx.scenes = mountWorkspace(ctx.id, route, () => ctx);
    ctx.scenes.ready.catch((error) => ctx.scenes?.el.replaceChildren(empty(icon("alert"), "The scenes cannot be shown", error.message)));
  } else if (ctx.scenes.route !== JSON.stringify(route)) {
    ctx.scenes.show(route);
  }
  ctx.scenes.route = JSON.stringify(route);
}

export function scenesView(ctx) {
  if (!ctx.records.frame) {
    return empty(icon("image"), "No scenes yet", "Once the lyrics are approved, the planner writes the project file: the characters, objects, places and every scene. They appear here, to be made, edited and picked.");
  }
  routeScenes(ctx);
  return h("div", { class: "stack" }, scenesGate(ctx), ctx.scenes.el);
}

// The project view closes the workspace when it is left (or the project changes).
export function closeScenes(ctx) {
  if (ctx.scenes) ctx.scenes.close();
  ctx.scenes = null;
}
