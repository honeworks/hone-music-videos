// The project's main screen: items (left, in file order), the open item (centre), activity (right).
// Live events update only the rows, the panel and the feed they concern.
// Hone Frame: ported from dashboard_page/screens/workspace.js.

import { on, state } from "../state.js";
import { emptyState, h } from "../ui.js";
import { createItemList } from "./items.js";
import { createItemPanel } from "./item.js";
import { createActivity } from "./activity.js";

// The item to open when the route names none: the one being made, else one waiting, else the first.
function defaultItem(view) {
  const run = view.run || {};
  if (run.current && run.current.item) return run.current.item;
  const waiting = view.items.find((it) => it.status === "waiting");
  return (waiting || view.items[0] || {}).id || null;
}

export async function mount(body, route) {
  const id = route.project;
  const list = createItemList(id);
  const panel = createItemPanel(id);
  const activity = createActivity(id);
  body.replaceChildren(h("div", { class: "workspace" }, list.el, panel.el, activity.el));

  let selected = null;
  function select(itemId) {
    const view = state.project;
    const wanted = itemId && view.items.some((it) => it.id === itemId) ? itemId : defaultItem(view);
    selected = wanted;
    list.select(wanted);
    const item = view.items.find((it) => it.id === wanted);
    if (item) panel.show(item);
    else panel.empty(itemId
      ? emptyState(`No item ${itemId} in this project`, "It may have been renamed in the project file.")
      : emptyState("This project has no items", "Add items to the project file."));
  }

  list.setItems(state.project.items, state.project.run);
  select(route.item);

  const offs = [
    on("item", (item) => {
      list.updateItem(item, state.project.run);
      if (item.id === selected) panel.update(item);
      panel.refsChanged(item);
    }),
    on("run", (run) => { list.setRun(run); panel.setRun(run); }),
    on("project", (view) => {
      list.setItems(view.items, view.run);
      const item = view.items.find((it) => it.id === selected);
      if (item) panel.update(item); else select(null);
    }),
  ];
  return {
    update: (next) => select(next.item),
    unmount() {
      offs.forEach((off) => off());
      panel.destroy();
      activity.destroy();
    },
  };
}
