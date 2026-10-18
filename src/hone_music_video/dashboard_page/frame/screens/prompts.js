// The prompts editor of an item with `prompts` (D-076): one textarea per prompt ("Prompt 1, Prompt 2..."),
// image k is made with prompt k; add one, remove one. Each prompt is sent exactly as written.
// Hone Frame: ported from dashboard_page/screens/prompts.js.

import { h, icon } from "../ui.js";

export function createPromptsEditor(itemId, onChange) {
  const list = h("ol", { class: "prompts" });
  const addButton = h("button", { type: "button", class: "button small", onclick: add }, "Add a prompt");
  const el = h("div", { class: "prompts-editor" }, list, addButton);
  let areas = [];

  function add() {
    draw([...values(), ""]);
    areas[areas.length - 1].focus();
    onChange();
  }

  function remove(index) {
    draw(values().filter((_, i) => i !== index));
    onChange();
  }

  const values = () => areas.map((area) => area.value);

  function draw(prompts) {
    areas = prompts.map((text, index) => {
      const area = h("textarea", { rows: "5", spellcheck: "true", "aria-label": `Prompt ${index + 1} of ${itemId}` });
      area.value = text;
      return area;
    });
    list.replaceChildren(...areas.map((area, index) => h("li", {},
      h("div", { class: "prompt-head" },
        h("span", { class: "field-label" }, `Prompt ${index + 1}`),
        h("span", { class: "caption" }, `image ${index + 1}`),
        h("button", { type: "button", class: "iconbutton small", disabled: areas.length === 1, "aria-label": `Remove prompt ${index + 1}`, onclick: () => remove(index) }, icon("x"))),
      area)));
  }

  return {
    el,
    // The value the fields compare and save: the prompts as JSON, or "" for an item without `prompts`.
    get value() { return areas.length ? JSON.stringify(values()) : ""; },
    set value(text) { draw(text ? JSON.parse(text) : []); },
  };
}
