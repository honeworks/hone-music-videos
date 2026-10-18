// The dependants question (§3): before a mark, a replace or "use this version", the server lists the items
// made from this one; the owner chooses to mark them to run again too, keep them (they are then flagged
// "made from an older" this item), or cancel. Resolves true, false, or null for cancel.
// Hone Frame: ported from dashboard_page/screens/dependants.js.

import { api } from "../api.js";
import { itemById } from "../state.js";
import { h, ITEM_STATUS, toast } from "../ui.js";

export async function askDependants(projectId, itemId, what) {
  let ids;
  try {
    ids = await api.dependants(projectId, itemId);
  } catch (error) {
    toast(`Could not list the items made from ${itemId}: ${error.message}`, { kind: "error" });
    return null;
  }
  if (!ids || !ids.length) return false;
  const dialog = document.getElementById("frame-dialog");
  return new Promise((resolve) => {
    let answer = null;
    const choose = (value) => { answer = value; dialog.close(); };
    dialog.replaceChildren(
      h("h2", { id: "dialog-title" }, `${ids.length} ${ids.length === 1 ? "item was" : "items were"} made from ${itemId}`),
      h("p", {}, `${what}. Mark ${ids.length === 1 ? "it" : "them"} to run again too?`),
      h("ul", { class: "dependants" }, ids.map((id) => {
        const it = itemById(id);
        return h("li", {}, h("code", {}, id), it ? h("span", { class: "muted" }, ` · ${ITEM_STATUS[it.status] || it.status}${it.marked ? ", already marked" : ""}`) : null);
      })),
      h("p", { class: "caption" }, `Items you keep stay as they are and are flagged "made from an older ${itemId}".`),
      h("div", { class: "dialog-actions" },
        h("button", { type: "button", class: "button ghost", onclick: () => choose(null) }, "Cancel"),
        h("button", { type: "button", class: "button", onclick: () => choose(false) }, "Keep them"),
        h("button", { type: "button", class: "button primary", autofocus: true, onclick: () => choose(true) }, "Mark them to run too")));
    dialog.addEventListener("close", () => resolve(answer), { once: true });
    dialog.showModal();
  });
}
