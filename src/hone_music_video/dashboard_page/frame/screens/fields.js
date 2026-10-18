// An item's fields, edited and saved to the project file (PATCH). The editor shows the item's own values
// (null in the ItemView when [defaults] or the derived seed applies, D-055) with what applies shown as the
// placeholder; only changed fields are sent, and an emptied field is sent as null (the default applies
// again). A live update replaces only the fields the owner is not editing. Ctrl+S (or Cmd+S) saves.
// Hone Frame: ported from dashboard_page/screens/fields.js.

import { api } from "../api.js";
import { applyItem, modelById, state } from "../state.js";
import { at, duration, errorBox, h } from "../ui.js";
import { createPromptsEditor } from "./prompts.js";
import { createRefsEditor } from "./refs.js";

const POSE = { none: "no pose support", reference: "poses from a reference picture", control: "poses as a control image" };

const lines = (v) => (Array.isArray(v) ? v.join("\n") : v || "");
const splitLines = (text) => text.split("\n").map((s) => s.trim()).filter(Boolean);
// What the controls show for an item: its own values, every one a string so changes compare simply.
function read(item) {
  if (item.kind === "sheet") return { layout: item.layout, images: lines(item.images), labels: lines(item.labels) };
  const own = (value) => (value == null ? "" : String(value));
  return {
    prompt: item.prompt, prompts: item.prompts ? JSON.stringify(item.prompts) : "", negative: own(item.negative), model: own(item.model), size: own(item.size),
    seed: own(item.seed), count: own(item.count), hold: own(item.hold), refs: JSON.stringify(item.refs),
    file: own(item.file), inputs: item.inputs ? JSON.stringify(item.inputs, null, 2) : "",
  };
}

// The value the server gets for a field.
function payload(key, value) {
  if (["negative", "model", "size", "file"].includes(key)) return value.trim() || null;
  if (key === "prompt") return value === "" ? null : value;
  if (key === "prompts") return value ? JSON.parse(value) : null;
  if (key === "seed" || key === "count") return value.trim() === "" ? null : Number(value);
  if (key === "hold") return value === "" ? null : value === "true";
  if (key === "refs") return JSON.parse(value);
  if (key === "images" || key === "labels") return splitLines(value);
  if (key === "inputs") {
    if (!value.trim()) return null;
    let parsed;
    try { parsed = JSON.parse(value); } catch { throw new Error("Inputs must be a JSON object, like {\"steps\": 8}."); }
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) throw new Error("Inputs must be a JSON object, like {\"steps\": 8}.");
    return parsed;
  }
  return value;
}

function modelLimits(modelId) {
  const m = modelById(modelId);
  if (!modelId) return h("p", { class: "caption" }, "No model set: the project has no default model.");
  if (!m) return h("p", { class: "caption danger" }, `${modelId} is not one of the local models.`);
  const sizes = (m.sizes || []).join(", ") || "any";
  return h("div", { class: "limits" },
    h("span", {}, h("strong", {}, m.max_references ?? 0), ` reference${m.max_references === 1 ? "" : "s"} at most`),
    h("span", {}, POSE[m.pose] || `poses: ${m.pose || "unknown"}`),
    h("span", {}, "sizes ", h("span", { class: "mono" }, sizes)),
    h("span", {}, "inputs ", h("span", { class: "mono" }, m.inputs ? m.inputs.join(", ") || "none" : "not known until installed")),
    h("span", {}, m.median_s != null ? `measured about ${duration(m.median_s)} per image` : "not measured on this machine yet"),
    m.installed === "yes" ? null : h("span", { class: "danger" }, m.installed === "no" ? "not installed" : "installed: unknown"),
    h("span", { class: m.commercial_use === false ? "warn" : "" }, `licence ${m.license || "unknown"}${m.commercial_use === false ? " · research only, not for commercial use" : ""}`));
}

function field(label, control, hint) {
  return h("div", { class: "field" }, h("label", {}, h("span", { class: "field-label" }, label), control), hint ? h("p", { class: "caption" }, hint) : null);
}

const INSTALLED = { yes: "", no: " · not installed", unknown: " · installed: unknown" };

export function createFields(projectId, item) {
  const defaults = state.project.defaults; // the [defaults] table as written
  const effective = item.effective; // what applies now, shown where the item leaves a field to the default
  const controls = {};
  const wraps = {};
  let base = read(item);
  const status = h("span", { class: "save-state", role: "status" });
  const errorSlot = h("div");
  const limits = h("div", { class: "limits-slot" });
  const save = h("button", { type: "submit", class: "button primary", disabled: true }, "Save to the file");
  const revert = h("button", { type: "button", class: "button ghost", disabled: true }, "Revert");
  const form = h("form", { class: "fields", "aria-label": `Fields of ${item.id}` });
  let refsEditor = null;

  const text = (key, rows) => (controls[key] = h("textarea", { rows: String(rows), spellcheck: key === "prompt" || key === "negative" ? "true" : "false", class: key === "inputs" || key === "images" || key === "labels" ? "mono" : "" }));
  const input = (key, attrs) => (controls[key] = h("input", attrs));

  function sizeOptions(modelId, value) {
    const m = modelById(modelId || defaults.model);
    const sizes = (m && m.sizes) || [];
    const opts = [h("option", { value: "" }, `Project default${defaults.size ? ` (${defaults.size})` : ""}`), ...sizes.map((s) => h("option", { value: s }, s))];
    if (value && !sizes.includes(value)) opts.push(h("option", { value }, `${value} (not listed for this model)`));
    controls.size.replaceChildren(...opts);
    controls.size.value = value;
  }

  function modelOptions(value) {
    const models = state.models || []; // local image models only
    const opts = [h("option", { value: "" }, `Project default${defaults.model ? ` (${defaults.model})` : ""}`),
      ...models.map((m) => h("option", { value: m.id }, `${m.id}${m.commercial_use === false ? " · research licence" : ""}${INSTALLED[m.installed]}`))];
    if (value && !models.some((m) => m.id === value)) opts.push(h("option", { value }, `${value} (not a local model)`));
    controls.model.replaceChildren(...opts);
    controls.model.value = value;
  }

  function showLimits() {
    const modelId = controls.model.value || defaults.model;
    limits.replaceChildren(modelLimits(modelId));
    const m = modelById(modelId);
    if (refsEditor) refsEditor.setMax(m ? m.max_references ?? 0 : null);
  }

  if (item.kind === "sheet") {
    wraps.layout = field("Layout", input("layout", { type: "text", class: "mono" }));
    wraps.images = field("Images (one item id per line)", text("images", 4));
    wraps.labels = field("Labels (one per line)", text("labels", 4));
    form.append(h("p", { class: "caption" }, "A sheet is composed with Pillow, no model, when its images are done."), wraps.layout, wraps.images, wraps.labels);
  } else {
    const several = h("button", { type: "button", class: "button small ghost", title: "One image per prompt: Prompt 1, Prompt 2...", onclick: usePrompts }, "Use several prompts");
    wraps.prompt = field("Prompt", text("prompt", 7), "Sent to the model exactly as written.");
    wraps.prompt.append(several);
    const prompts = createPromptsEditor(item.id, changed);
    controls.prompts = prompts;
    wraps.prompts = h("fieldset", { class: "field" }, h("legend", { class: "field-label" }, "Prompts, one image each"), prompts.el,
      h("p", { class: "caption" }, "Image 1 is made with Prompt 1 and the seed, image 2 with Prompt 2 and the seed + 1, and so on; each is sent exactly as written. You pick one."));
    wraps.negative = field("Negative prompt", text("negative", 2));
    if (defaults.negative) controls.negative.placeholder = `Project default: ${defaults.negative}`;
    controls.model = h("select", {});
    controls.size = h("select", {});
    wraps.model = field("Model", controls.model);
    wraps.size = field("Size", controls.size);
    wraps.seed = field("Seed", input("seed", { type: "number", step: "1", min: "0", placeholder: `${effective.seed} (from the item id)` }));
    wraps.count = field("Images", input("count", { type: "number", step: "1", min: "1", placeholder: `${effective.count}${defaults.count ? " (project default)" : ""}` }), "More than one: you pick one.");
    controls.hold = h("select", {},
      h("option", { value: "" }, `Project default (${defaults.hold ? "hold" : "don't hold"})`),
      h("option", { value: "true" }, "Hold: the run waits until I accept it"),
      h("option", { value: "false" }, "Don't hold"));
    wraps.hold = field("Hold", controls.hold);
    refsEditor = createRefsEditor(item.id, changed);
    controls.refs = { get value() { return JSON.stringify(refsEditor.get()); }, set value(v) { refsEditor.set(JSON.parse(v || "[]")); } };
    wraps.refs = h("fieldset", { class: "field" }, h("legend", { class: "field-label" }, "References, in the order they are sent"), refsEditor.el);
    wraps.inputs = field("Model inputs (JSON)", text("inputs", 3), "By their hone-models names, e.g. {\"steps\": 8}; the model's inputs are listed with its limits.");
    if (defaults.inputs) controls.inputs.placeholder = `Project default: ${JSON.stringify(defaults.inputs)}`;
    wraps.file = field("Provided file", input("file", { type: "text", class: "mono", placeholder: "assets/mug.png" }), "A provided file is never generated.");
    form.append(wraps.prompt, wraps.prompts, wraps.negative,
      h("div", { class: "field-row" }, wraps.model, wraps.size), limits,
      h("div", { class: "field-row three" }, wraps.seed, wraps.count, wraps.hold),
      wraps.refs, h("details", { class: "more", open: Boolean(base.inputs || base.file) }, h("summary", {}, "Inputs and provided file"), wraps.inputs, wraps.file));
    if (item.group === "demo") demoMode(several);
    modelOptions(base.model);
    sizeOptions(base.model, base.size);
    controls.model.addEventListener("change", () => { sizeOptions(controls.model.value, controls.size.value); showLimits(); });
  }
  form.append(errorSlot, h("div", { class: "form-actions" }, save, revert, status));

  // A demo item (D-077): its prompt is its entry of [demo] prompts; no references, no file, one image; its
  // model, size, seed, hold, negative and inputs are the [demo] table's, shared by every demo picture.
  function demoMode(several) {
    for (const key of ["prompts", "count", "refs", "file"]) wraps[key].hidden = true;
    several.hidden = true;
    form.prepend(h("p", { class: "caption" }, "A demo picture: no references, made before everything else. Its prompt is its line of [demo] prompts; the other fields belong to [demo] and change every demo picture."));
    wraps.seed.querySelector(".field-label").textContent = "Seed of the demo";
    controls.seed.title = "demo.1 uses this seed, demo.2 the seed + 1, and so on";
    controls.hold.options[1].textContent = "Hold: the run waits after the last demo picture";
  }

  const valueOf = (key) => controls[key].value;
  function setValue(key, value) {
    if (key === "model") { modelOptions(value); sizeOptions(value, controls.size.value); showLimits(); }
    else if (key === "size") sizeOptions(controls.model.value, value);
    else controls[key].value = value;
    if (key === "prompts") showPromptMode();
  }

  // An item with `prompts` shows one textarea per prompt and makes one image each: its count is theirs.
  function showPromptMode() {
    const many = valueOf("prompts") !== "";
    wraps.prompt.hidden = many;
    wraps.prompts.hidden = !many;
    controls.count.disabled = many;
    controls.count.title = many ? "One image per prompt" : "";
    controls.count.placeholder = many ? `${JSON.parse(valueOf("prompts")).length} (one per prompt)` : `${effective.count}${defaults.count ? " (project default)" : ""}`;
  }

  function usePrompts() {
    controls.prompts.value = JSON.stringify([valueOf("prompt")]);
    controls.prompt.value = "";
    controls.count.value = ""; // the count is the number of prompts now
    showPromptMode();
    changed();
  }
  const dirtyKeys = () => Object.keys(base).filter((key) => valueOf(key) !== base[key]);

  function changed() {
    const dirty = dirtyKeys();
    for (const key of Object.keys(base)) wraps[key].classList.toggle("dirty", dirty.includes(key));
    save.disabled = revert.disabled = !dirty.length;
    if (dirty.length) { status.className = "save-state unsaved"; status.textContent = `Unsaved: ${dirty.join(", ")}`; }
    else if (status.classList.contains("unsaved")) { status.className = "save-state"; status.textContent = ""; }
  }

  async function submit(event) {
    if (event) event.preventDefault();
    const dirty = dirtyKeys();
    if (!dirty.length) return;
    errorSlot.replaceChildren();
    let body;
    try {
      body = Object.fromEntries(dirty.map((key) => [key, payload(key, valueOf(key))]));
      if ("prompts" in body && base.count !== "") body.count = null; // one image per prompt: no count of its own
    } catch (error) {
      errorSlot.replaceChildren(errorBox(error));
      return;
    }
    save.disabled = true;
    status.className = "save-state"; status.textContent = "Saving…";
    try {
      const result = await api.patchItem(projectId, item.id, body);
      base = read(result);
      for (const key of Object.keys(base)) setValue(key, base[key]);
      status.className = "save-state saved";
      status.textContent = `Saved to the project file at ${at(new Date().toISOString())}`;
      changed();
      applyItem({ project: projectId, item: result });
    } catch (error) {
      status.className = "save-state error";
      status.textContent = "Not saved";
      errorSlot.replaceChildren(errorBox(error));
      changed();
    }
  }

  form.addEventListener("submit", submit);
  form.addEventListener("input", changed);
  form.addEventListener("change", changed);
  form.addEventListener("keydown", (event) => {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "s") { event.preventDefault(); submit(); }
  });
  revert.addEventListener("click", () => {
    for (const key of Object.keys(base)) setValue(key, base[key]);
    errorSlot.replaceChildren();
    changed();
  });

  for (const key of Object.keys(base)) if (key !== "model" && key !== "size") setValue(key, base[key]);
  if (item.kind !== "sheet") showLimits();

  return {
    el: form,
    sync(next) {
      const fresh = read(next);
      const dirty = dirtyKeys();
      for (const key of Object.keys(fresh)) if (!dirty.includes(key) && fresh[key] !== base[key]) setValue(key, fresh[key]);
      base = fresh;
      changed();
    },
    refreshRefs: () => refsEditor && refsEditor.refresh(),
  };
}
