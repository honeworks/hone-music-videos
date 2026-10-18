// The guide (§6): how a project file works, per stage, for the models this project's file uses, or the
// models chosen. The Markdown is drawn by markdown.js, never as HTML.
// Hone Frame: ported from dashboard_page/screens/guide.js; the project is this video's frame project.

import { api } from "../api.js";
import { loadModels } from "../state.js";
import { errorBox, h, toast } from "../ui.js";
import { render } from "../markdown.js";

export async function mount(body) {
  const models = await loadModels().catch(() => []);
  const chosen = new Set(); // none: the models of this project's file
  const article = h("article", { class: "markdown" });
  let markdownText = "";
  const copyButton = h("button", { type: "button", class: "button primary", disabled: true, onclick: copy }, "Copy the whole guide");

  async function copy() {
    try {
      await navigator.clipboard.writeText(markdownText);
      toast(`Copied the guide (${markdownText.length.toLocaleString()} characters) as Markdown.`);
    } catch (error) {
      toast(`Copy: ${error.message}`, { kind: "error" });
    }
  }

  const toc = h("nav", { class: "toc", "aria-label": "Contents" });
  const boxes = h("fieldset", { class: "model-boxes" }, h("legend", { class: "field-label" }, "Models (none: this project's)"),
    ...models.map((m) => h("label", { class: "check" },
      h("input", { type: "checkbox", value: m.id, onchange: (e) => { if (e.target.checked) chosen.add(m.id); else chosen.delete(m.id); draw(); } }),
      ` ${m.id}`, m.commercial_use === false ? h("span", { class: "flag warn" }, "research") : null)));

  async function draw() {
    article.replaceChildren(h("p", { class: "muted" }, "Loading the guide…"));
    try {
      const { markdown } = await api.guide([...chosen]);
      markdownText = markdown;
      copyButton.disabled = !markdown;
      article.replaceChildren(render(markdown));
      toc.replaceChildren(h("strong", { class: "overline" }, "Contents"), h("ul", {},
        [...article.querySelectorAll("h1, h2")].map((node) => h("li", { class: node.tagName === "H1" ? "" : "sub" }, h("a", { href: `#${node.id}`, onclick: (e) => { e.preventDefault(); node.scrollIntoView(); } }, node.textContent)))));
    } catch (error) {
      markdownText = "";
      copyButton.disabled = true;
      article.replaceChildren(errorBox(error));
    }
  }

  body.replaceChildren(h("div", { class: "guide-grid" },
    h("aside", { class: "guide-side" }, h("div", { class: "copy-guide" }, copyButton), boxes, toc), article));
  await draw();
  return {};
}
