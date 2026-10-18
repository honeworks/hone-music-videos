// The refs editor: the references in the order they are sent ("image 1, image 2..."), each with its
// thumbnail and state; reorder, remove, add one written above this item. Refs point upward
// (§1), so the suggestions are the items above; the server still checks.
// Hone Frame: ported from dashboard_page/screens/refs.js.

import { itemById, state } from "../state.js";
import { h, icon, ITEM_STATUS, setImage } from "../ui.js";

let editors = 0;

export function createRefsEditor(itemId, onChange) {
  const listId = `refs-options-${++editors}`;
  const list = h("ol", { class: "refs" });
  const input = h("input", { type: "text", list: listId, placeholder: "woman.hero", "aria-label": "Reference to add" });
  const options = h("datalist", { id: listId });
  const limit = h("p", { class: "caption refs-limit", "aria-live": "polite" });
  const el = h("div", { class: "refs-editor" }, list,
    h("div", { class: "refs-add" }, input, options, h("button", { type: "button", class: "button small", onclick: add }, "Add reference")), limit);
  let refs = [];
  let max = null;

  function add() {
    const value = input.value.trim();
    if (!value) return;
    refs = [...refs, value];
    input.value = "";
    draw();
    onChange();
  }
  input.addEventListener("keydown", (event) => { if (event.key === "Enter") { event.preventDefault(); add(); } });

  function move(index, by) {
    const next = refs.slice();
    const [ref] = next.splice(index, 1);
    next.splice(index + by, 0, ref);
    refs = next;
    draw();
    onChange();
    const button = list.querySelectorAll("li")[index + by]?.querySelector(by < 0 ? "[data-up]" : "[data-down]");
    if (button && !button.disabled) button.focus();
  }

  function row(ref, index) {
    const item = itemById(ref);
    const thumb = h("span", { class: "thumb-holder small" });
    setImage(thumb, item ? item.thumb : null, "");
    return h("li", {},
      h("span", { class: "ref-order" }, `Image ${index + 1}`), thumb,
      h("span", { class: "ref-text" }, h("code", {}, ref),
        h("span", { class: `caption ${item ? "" : "danger"}` }, item ? ITEM_STATUS[item.status] || item.status : "not in this project")),
      h("span", { class: "ref-buttons" },
        h("button", { type: "button", class: "iconbutton small", "data-up": "", disabled: index === 0, "aria-label": `Move ${ref} up`, onclick: () => move(index, -1) }, icon("up")),
        h("button", { type: "button", class: "iconbutton small", "data-down": "", disabled: index === refs.length - 1, "aria-label": `Move ${ref} down`, onclick: () => move(index, 1) }, icon("down")),
        h("button", { type: "button", class: "iconbutton small", "aria-label": `Remove ${ref}`, onclick: () => { refs = refs.filter((_, i) => i !== index); draw(); onChange(); } }, icon("x"))));
  }

  function suggestions() {
    const items = state.project ? state.project.items : [];
    const at = items.findIndex((it) => it.id === itemId);
    return items.slice(0, at < 0 ? items.length : at).map((it) => it.id).filter((id) => !refs.includes(id));
  }

  function draw() {
    list.replaceChildren(...refs.map(row));
    if (!refs.length) list.append(h("li", { class: "muted none" }, "No references: the model gets the prompt only."));
    options.replaceChildren(...suggestions().map((id) => h("option", { value: id })));
    limit.className = `caption refs-limit ${max != null && refs.length > max ? "danger" : ""}`;
    limit.textContent = max == null ? "" : max === 0 ? `This model takes no references${refs.length ? ": remove them." : "."}`
      : `This model takes up to ${max} ${max === 1 ? "reference" : "references"}${refs.length > max ? `: remove ${refs.length - max}.` : "."}`;
  }

  return {
    el,
    get: () => refs.slice(),
    set(next) { refs = (next || []).slice(); draw(); },
    setMax(next) { max = next; draw(); },
    refresh: draw,
  };
}
