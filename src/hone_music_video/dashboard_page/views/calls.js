// The calls to hosted models (0030 §2): on the Plan view every kept planner call in the order made (the
// story, the shot list, the review, each subject, each scene batch, and the repairs), with its model, time
// and the problems the code found in its reply; a row opens what was sent (the data, the system prompt one
// click away) and what came back. On the Lyrics view the transcriptions, with their price. Read from
// GET …/calls (the list) and …/calls/<name> (one call), once per open project.

import { api, h, spoken } from "../core.js";
import { icon } from "../icons.js";

const cache = new Map(); // project id -> {list, at, one: Map(name -> call or promise)}
const FRESH_MS = 15000;

function load(ctx) {
  const found = cache.get(ctx.id);
  if (found && Date.now() - found.at < FRESH_MS) return found;
  const entry = { list: found?.list || null, at: Date.now(), one: found?.one || new Map() };
  cache.set(ctx.id, entry);
  api(`/projects/${ctx.id}/calls`).then((list) => {
    const changed = JSON.stringify(list) !== JSON.stringify(entry.list);
    entry.list = list;
    if (changed) ctx.render();
  }).catch(() => {});
  return entry;
}

const json = (value) => h("pre", { class: "call-json" }, JSON.stringify(value, null, 2));

function body(ctx, row, slot) {
  const entry = load(ctx);
  slot.replaceChildren(h("p", { class: "muted small" }, "Loading…"));
  const kept = entry.one.get(row.name) || api(`/projects/${ctx.id}/calls/${encodeURIComponent(row.name)}`);
  entry.one.set(row.name, kept);
  Promise.resolve(kept).then((call) => {
    entry.one.set(row.name, call);
    const found = call.found.length
      ? h("ul", { class: "problems-list warnings" }, call.found.map((p) => h("li", {}, icon("alert"), h("div", {}, `${p.where}: ${p.message}`))))
      : h("p", { class: "muted small" }, "The code found nothing wrong in the reply.");
    const parts = call.request
      ? [h("div", { class: "eyebrow" }, "Problems found in the reply"), found,
        h("details", { class: "call-part" }, h("summary", {}, `Sent: the data (${call.request.schema}${call.request.images.length ? `, ${call.request.images.length} pictures` : ""})`), json(call.request.data)),
        call.system_text ? h("details", { class: "call-part" }, h("summary", {}, "Sent: the system prompt"), h("pre", { class: "call-json" }, call.system_text)) : null]
      : [h("p", { class: "muted small" }, "Made before 0030: what was sent and the problems found in it were not kept.")];
    slot.replaceChildren(...parts.filter(Boolean), h("details", { class: "call-part", open: true }, h("summary", {}, "The reply"), json(call.reply)));
  }).catch((error) => slot.replaceChildren(h("p", { class: "muted small" }, error.message)));
}

function planRow(ctx, row) {
  const slot = h("div", { class: "call-body" });
  const flags = [
    row.sent_back ? h("span", { class: "chip" }, `repairs ${row.sent_back}`) : null,
    row.problems ? h("span", { class: "chip warn" }, `${row.problems} found`) : null,
  ];
  return h("details", { class: "call-row", ontoggle: (event) => { if (event.target.open) body(ctx, row, slot); } },
    h("summary", {}, h("span", { class: "mono grow" }, row.label), flags, h("span", { class: "faint xs" }, row.model),
      h("span", { class: "mono xs" }, spoken(row.took_ms))),
    slot);
}

export function planCalls(ctx) {
  const { list } = load(ctx);
  if (!list || !list.plan.length) return null;
  return h("section", { class: "panel" },
    h("div", { class: "panel-head" }, h("h2", {}, "Calls"), h("span", { class: "muted small" }, `${list.total.calls} calls · ${spoken(list.total.took_ms)} in all`)),
    h("div", { class: "call-list" }, list.plan.map((row) => planRow(ctx, row))));
}

export function lyricsCalls(ctx) {
  const { list } = load(ctx);
  if (!list || !list.lyrics.length) return null;
  const cost = (c) => (c.cost_usd === null || c.cost_usd === undefined ? "price unknown" : `$${c.cost_usd.toFixed(4)}`);
  return h("section", { class: "panel" }, h("div", { class: "panel-head" }, h("h2", {}, "Calls")),
    h("div", { class: "call-list" }, list.lyrics.map((c) => h("details", { class: "call-row" },
      h("summary", {}, h("span", { class: "grow" }, c.label), h("span", { class: "faint xs" }, c.model), h("span", { class: "mono xs" }, `${spoken(c.took_ms)} · ${cost(c)}`)),
      h("p", { class: "call-heard", dir: "auto" }, c.text || "(nothing heard)")))));
}
