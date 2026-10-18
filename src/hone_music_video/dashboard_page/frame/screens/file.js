// The project file itself: read it, edit it, save it (checked like an import; a refusal names each item).
// Hone Frame: ported from dashboard_page/screens/file.js.

import { api } from "../api.js";
import { loadProject } from "../state.js";
import { at, errorBox, h, toast } from "../ui.js";

export async function mount(body, route) {
  const projectId = route.project;
  const text = h("textarea", { class: "mono file-text", rows: "30", spellcheck: "false", "aria-label": "Project file" });
  const status = h("span", { class: "save-state", role: "status" });
  const errors = h("div");
  const save = h("button", { type: "submit", class: "button primary", disabled: true }, "Save the file");
  const reload = h("button", { type: "button", class: "button ghost" }, "Reload from disk");
  const name = h("code", {});
  let loaded = "";

  async function load() {
    const file = await api.file(projectId);
    loaded = file.text;
    text.value = file.text;
    name.textContent = `project.${file.format || "toml"}`;
    save.disabled = true;
    status.className = "save-state";
    status.textContent = "";
    errors.replaceChildren();
  }

  const form = h("form", { class: "panel file-form" },
    h("p", {}, "This is ", name, " in the project folder, the source of truth. Saving checks it like an import; nothing is saved if an item is refused."),
    text, errors, h("div", { class: "form-actions" }, save, reload, status));
  text.addEventListener("input", () => {
    save.disabled = text.value === loaded;
    status.className = text.value === loaded ? "save-state" : "save-state unsaved";
    status.textContent = text.value === loaded ? "" : "Unsaved changes";
  });
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    save.disabled = true;
    errors.replaceChildren();
    try {
      await api.putFile(projectId, text.value);
      loaded = text.value;
      status.className = "save-state saved";
      status.textContent = `Saved at ${at(new Date().toISOString())}`;
      loadProject(projectId).catch(() => {});
    } catch (error) {
      status.className = "save-state error";
      status.textContent = "Not saved";
      errors.replaceChildren(errorBox(error));
      save.disabled = false;
    }
  });
  reload.addEventListener("click", () => {
    if (text.value !== loaded && !confirm("Drop your unsaved changes and reload the file?")) return;
    load().catch((error) => toast(error.message, { kind: "error" }));
  });
  text.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") { event.preventDefault(); form.requestSubmit(); }
  });

  body.replaceChildren(h("div", { class: "page-body" }, form));
  await load();
  return {};
}
