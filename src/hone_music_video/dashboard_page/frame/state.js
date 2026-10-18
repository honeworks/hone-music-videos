// What the Scenes view knows, and who wants to hear when it changes. The server's views are kept as they
// arrive; screens subscribe to topics and update their own nodes in place.
// Hone Frame: ported from dashboard_page/state.js. The project view's `id` is the video project's (the
// page's routes and API calls use it); the frame project's own id is kept as `frame_id`, which a run names.

import { api } from "./api.js";

export const state = {
  project: null, // the open ProjectView, its items in file order
  models: null, // [ModelView], loaded once and on the Models page
  notifications: [],
  connected: false,
};

const listeners = new Map();

export function on(topic, fn) {
  if (!listeners.has(topic)) listeners.set(topic, new Set());
  listeners.get(topic).add(fn);
  return () => listeners.get(topic).delete(fn);
}

export function emit(topic, data) {
  for (const fn of listeners.get(topic) || []) {
    try { fn(data); } catch (error) { console.error(`listener for ${topic}`, error); }
  }
}

export async function loadProject(id) {
  const view = await api.project(id);
  view.frame_id = view.id;
  view.id = id;
  view.run = stampRun(view.run);
  state.project = view;
  emit("project", view);
  return view;
}

export async function loadModels(force = false) {
  if (!state.models || force) state.models = await api.models();
  return state.models;
}

export function modelById(id) {
  return (state.models || []).find((m) => m.id === id) || null;
}

export function itemById(id) {
  return state.project ? state.project.items.find((it) => it.id === id) || null : null;
}

// When this page received the run, so the elapsed time can tick on without asking the server.
function stampRun(run) {
  if (run) run.received_at = performance.now();
  return run;
}

// An item of a project changed: an SSE `item` event, or an API answer, as {project, item: ItemView}.
export function applyItem({ project, item }) {
  emit("any-item", { project, item });
  if (!state.project || project !== state.project.id) return;
  const index = state.project.items.findIndex((it) => it.id === item.id);
  if (index < 0) return;
  state.project.items[index] = item;
  emit("item", item);
}

export function applyRun(run) {
  if (!run) return;
  stampRun(run);
  emit("any-run", run);
  if (state.project && run.project === state.project.frame_id) {
    state.project.run = run;
    emit("run", run);
  }
}

export function setConnected(connected) {
  if (state.connected === connected) return;
  state.connected = connected;
  emit("connection", connected);
}
