// The items list: every item in file order (the demo first, D-077), a heading where the group or subject changes, each row with its
// thumbnail, status, mark and place in the run, version count and flags. Rows are patched in place.
// Hone Frame: ported from dashboard_page/screens/items.js.

import { h, itemHref, ITEM_STATUS, pill, setImage } from "../ui.js";

const GROUPS = { demo: "Demo", characters: "Characters", objects: "Objects", places: "Places", scenes: "Scenes", sheets: "Sheets" };
const FILTERS = [["all", "All"], ["marked", "Marked"], ["waiting", "Waiting"], ["failed", "Failed"], ["flagged", "Flagged"]];

function flags(item) {
  const out = [];
  if (item.changed_since_made) out.push(h("span", { class: "flag", title: "Its fields differ from what made the current version" }, "Changed since made"));
  for (const ref of item.older_refs) out.push(h("span", { class: "flag", title: `Made from an older version of ${ref}` }, `Older ${ref}`));
  if (item.license_warning) out.push(h("span", { class: "flag warn", title: item.license_warning }, "Research licence"));
  return out;
}

// Where the item stands in the run: being made, next, or its place among the marked items.
function runBadge(item, order, current) {
  if (item.id === current) return h("span", { class: "badge running" }, "Making now");
  const at = order.indexOf(item.id);
  if (at === 0) return h("span", { class: "badge next" }, "Next");
  if (at > 0) return h("span", { class: "badge marked", title: `Marked to run: number ${at + 1} in line` }, `Marked · ${at + 1}`);
  if (item.marked) return h("span", { class: "badge marked" }, "Marked");
  return null;
}

function matches(item, filter, text) {
  if (text && !`${item.id} ${item.prompt || ""} ${(item.prompts || []).join(" ")}`.toLowerCase().includes(text)) return false;
  if (filter === "marked") return item.marked;
  if (filter === "waiting") return item.status === "waiting";
  if (filter === "failed") return item.status === "failed";
  if (filter === "flagged") return item.changed_since_made || item.older_refs.length > 0 || Boolean(item.license_warning);
  return true;
}

export function createItemList(projectId) {
  const list = h("ul", { class: "item-list", role: "list" });
  const search = h("input", { type: "search", placeholder: "Filter by id or prompt", "aria-label": "Filter items" });
  const filterBar = h("div", { class: "segmented", role: "group", "aria-label": "Show" });
  const summary = h("p", { class: "caption list-summary", "aria-live": "polite" });
  const el = h("aside", { class: "pane items-pane", "aria-label": "Items" },
    h("div", { class: "pane-head" }, h("h2", {}, "Items"), summary), search, filterBar, list);
  const rows = new Map();
  let items = [];
  let order = [];
  let current = null;
  let filter = "all";
  let shape = "";

  function drawFilters() {
    filterBar.replaceChildren(...FILTERS.map(([key, label]) => h("button", {
      type: "button", class: "seg", "aria-pressed": String(filter === key),
      onclick: () => { filter = key; drawFilters(); applyFilter(); },
    }, label)));
  }

  function fillRow(row, item) {
    setImage(row.thumb, item.thumb, "");
    row.status.replaceChildren(pill("item", item.status, ITEM_STATUS));
    const versions = item.versions.length;
    const shown = item.current ? `v${item.current} of ${versions}` : versions ? `${versions} versions, none current` : "no versions";
    row.meta.textContent = [item.kind === "sheet" ? "sheet" : null, shown, item.effective.per_run > 1 ? `${item.effective.per_run} at once` : null, item.effective.hold ? "hold" : null].filter(Boolean).join(" · ");
    row.badges.replaceChildren(...[runBadge(item, order, current), ...flags(item)].filter(Boolean));
    row.li.dataset.status = item.status;
    row.link.setAttribute("aria-label", `${item.id}: ${ITEM_STATUS[item.status] || item.status}${item.marked ? ", marked to run" : ""}`);
  }

  function makeRow(item) {
    const thumb = h("span", { class: "thumb-holder" });
    const status = h("span", { class: "row-status" });
    const meta = h("span", { class: "row-meta" });
    const badges = h("span", { class: "row-badges" });
    const label = item.name && item.name !== item.subject ? item.name : item.id;
    const link = h("a", { class: "item-row", href: itemHref(projectId, item.id), "data-id": item.id },
      thumb, h("span", { class: "row-text" }, h("span", { class: "row-name" }, label), meta, badges), status);
    const li = h("li", { class: "row" }, link);
    return { li, link, thumb, status, meta, badges };
  }

  function build() {
    rows.clear();
    const nodes = [];
    let group = null;
    let subject = null;
    for (const item of items) {
      if (item.group !== group) {
        group = item.group;
        subject = null;
        nodes.push(h("li", { class: "group-head", dataset: { group } }, GROUPS[group] || group));
      }
      if (item.subject && item.subject !== subject && item.name && item.name !== item.subject) {
        subject = item.subject;
        nodes.push(h("li", { class: "subject-head", dataset: { group } }, item.subject));
      }
      const row = makeRow(item);
      rows.set(item.id, row);
      fillRow(row, item);
      nodes.push(row.li);
    }
    list.replaceChildren(...nodes);
  }

  function applyFilter() {
    const text = search.value.trim().toLowerCase();
    let shown = 0;
    for (const item of items) {
      const visible = matches(item, filter, text);
      rows.get(item.id).li.hidden = !visible;
      if (visible) shown += 1;
    }
    for (const head of list.querySelectorAll(".group-head, .subject-head")) {
      let next = head.nextElementSibling;
      let any = false;
      while (next && !next.classList.contains("group-head") && !(head.classList.contains("subject-head") && next.classList.contains("subject-head"))) {
        if (next.classList.contains("row") && !next.hidden) { any = true; break; }
        next = next.nextElementSibling;
      }
      head.hidden = !any;
    }
    const marked = items.filter((it) => it.marked).length;
    const waiting = items.filter((it) => it.status === "waiting").length;
    summary.textContent = `${items.length} items · ${marked} marked${waiting ? ` · ${waiting} waiting for you` : ""}${shown < items.length ? ` · ${shown} shown` : ""}`;
  }

  function takeRun(run) {
    current = run.current ? run.current.item : null;
    order = run.remaining; // the marked items in run order, without the current one
  }

  list.addEventListener("keydown", (event) => {
    if (!["ArrowDown", "ArrowUp"].includes(event.key)) return;
    const links = [...list.querySelectorAll("li.row:not([hidden]) .item-row")];
    const at = links.indexOf(document.activeElement);
    const next = links[at + (event.key === "ArrowDown" ? 1 : -1)];
    if (next) { event.preventDefault(); next.focus(); next.click(); }
  });
  search.addEventListener("input", applyFilter);
  drawFilters();

  return {
    el,
    setItems(next, run) {
      items = next;
      takeRun(run);
      const nextShape = items.map((it) => `${it.group}/${it.id}`).join("|");
      if (nextShape !== shape) { shape = nextShape; build(); } else items.forEach((it) => fillRow(rows.get(it.id), it));
      applyFilter();
    },
    updateItem(item, run) {
      const index = items.findIndex((it) => it.id === item.id);
      if (index < 0) return;
      items[index] = item;
      takeRun(run);
      items.forEach((it) => fillRow(rows.get(it.id), it)); // the marks move everyone's place in line
      applyFilter();
    },
    setRun(run) {
      takeRun(run);
      items.forEach((it) => fillRow(rows.get(it.id), it));
    },
    select(id) {
      for (const [key, row] of rows) {
        if (key === id) row.link.setAttribute("aria-current", "true"); else row.link.removeAttribute("aria-current");
      }
      const row = rows.get(id);
      if (row) row.li.scrollIntoView({ block: "nearest" });
    },
  };
}
