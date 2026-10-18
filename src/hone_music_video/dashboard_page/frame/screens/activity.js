// Activity: the frame project's events, newest first: the past ones from GET .../frame/events, then each
// as it happens (the page's event stream sends them as `frame` events). The bell of the page rings for the
// video's gates; the frame run's notifications are in the run bar ("Waiting for you").
// Hone Frame: ported from dashboard_page/screens/activity.js.

import { api } from "../api.js";
import { on } from "../state.js";
import { at, duration, h, itemHref } from "../ui.js";

const KINDS = { // the kinds of events.jsonl (design §8.6), and the server's note that a view could not be made
  imported: "Imported", edited: "Edited", run_started: "Run started", run_resumed: "Resumed",
  item_started: "Started", item_made: "Made", item_failed: "Failed", run_waiting: "Waiting for you",
  accepted: "Accepted", picked: "Picked", marked: "Marked to run", unmarked: "Unmarked",
  version_used: "Version used", file_replaced: "Replaced with a file", run_paused: "Paused",
  run_stopped: "Stopped", run_done: "Run finished", view_unavailable: "Not shown",
};
const MAX = 200;

function tone(kind) {
  if (/fail|error/.test(kind)) return "danger";
  if (/wait/.test(kind)) return "waiting";
  if (/made|done|accept|pick/.test(kind)) return "done";
  return "";
}

export function createActivity(projectId) {
  const feed = h("ol", { class: "feed" });
  const feedNote = h("p", { class: "caption" });
  const el = h("aside", { class: "pane activity-pane", "aria-label": "Activity" },
    h("div", { class: "pane-head" }, h("h2", {}, "Activity")), feedNote, feed);
  let count = 0;

  function entry(ev) {
    const kind = ev.kind;
    const item = ev.item || null;
    const details = [ev.message, ev.error, ev.elapsed_s != null ? `in ${duration(ev.elapsed_s)}` : null, ev.version != null ? `v${ev.version}` : null].filter(Boolean).join(" · ");
    return h("li", { class: `feed-entry ${tone(kind)}` },
      h("time", { datetime: ev.at || null }, at(ev.at)),
      h("span", { class: "feed-kind" }, KINDS[kind] || kind),
      item ? h("a", { href: itemHref(projectId, item) }, item) : null,
      details ? h("span", { class: "feed-details" }, details) : null);
  }

  function add(ev, atTop = true) {
    const node = entry(ev);
    if (atTop) feed.prepend(node); else feed.append(node);
    count += 1;
    if (count > MAX) { feed.lastElementChild.remove(); count -= 1; }
    feedNote.textContent = "";
  }

  async function loadPast() {
    feedNote.textContent = "Loading…";
    try {
      const list = await api.events(projectId);
      feed.replaceChildren();
      count = 0;
      list.slice(-MAX).reverse().forEach((ev) => add(ev, false));
      feedNote.textContent = list.length ? "" : "Nothing has happened yet.";
    } catch (error) {
      feedNote.textContent = `The past events could not be loaded: ${error.message}`;
    }
  }

  const offs = [on("event", (ev) => add(ev)), on("resync", loadPast)];
  loadPast();
  return { el, destroy: () => offs.forEach((off) => off()) };
}
