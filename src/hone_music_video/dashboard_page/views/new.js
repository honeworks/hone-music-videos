// New video (design §13.2, 0027): drop the song; paste the lyrics; story notes; given sheets and pose
// pictures with names; the settings with their defaults (design §2.3): the pace, mood and style
// (options.js), the image models of the scenes (the first is the project's default, the planner may give a
// picture another), Start. The models that forbid commercial use are listed above Start; the form shows what
// it sends.

import { api, formatMs, h, parseMs, readFile, toast } from "../core.js";
import { icon } from "../icons.js";
import { lookFields, readLook } from "./options.js";

const ROLES = {
  speech: "Word times", lyrics: "Lyrics editor", planner: "Planner (story, shots, prompts)", clips: "Clips",
  finish: "Finish (upscale and 32 fps)",
};

function field(label, control, hint) {
  return h("div", { class: "field" }, h("label", { for: control.id }, label), control,
    hint ? h("span", { class: "hint" }, hint) : null);
}

function songDrop() {
  const input = h("input", { type: "file", id: "song", accept: "audio/*,.wav,.flac,.mp3,.m4a,.ogg", hidden: true });
  const label = h("span", {}, "Drop the song here, or choose a file");
  const zone = h("div", { class: "drop", tabindex: "0", role: "button" }, icon("music"), label,
    h("span", { class: "xs faint" }, "WAV, FLAC, MP3, M4A or OGG"));
  const pick = (file) => {
    if (!file) return;
    const list = new DataTransfer();
    list.items.add(file);
    input.files = list.files;
    label.textContent = file.name;
    zone.classList.add("has-file");
    input.dispatchEvent(new Event("picked")); // a dropped file fires no "change"
  };
  zone.addEventListener("click", () => input.click());
  zone.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") input.click(); });
  zone.addEventListener("dragover", (e) => e.preventDefault());
  zone.addEventListener("drop", (e) => { e.preventDefault(); pick(e.dataTransfer.files[0]); });
  input.addEventListener("change", () => pick(input.files[0]));
  return { input, node: h("div", { class: "field" }, h("label", {}, "Song"), zone, input) };
}

function choice(id, options, selected) {
  return h("select", { id }, Object.entries(options).map(([value, label]) => h("option", { value, selected: value === String(selected) }, label)));
}

// Given pictures with a name and a note each: the characters' sheets, or pose pictures (0027).
function pictureRows(title, hint, placeholder, more) {
  const list = h("div", {});
  const add = () => list.append(h("div", { class: "sheet-row" },
    h("input", { type: "file", accept: "image/*", "aria-label": `${title}: picture` }),
    h("input", { type: "text", placeholder, "aria-label": `${title}: name` }),
    h("input", { type: "text", placeholder: "Note (optional)", "aria-label": `${title}: note` }),
    h("button", { type: "button", class: "icon-button", "aria-label": "Remove", onclick: (e) => e.target.closest(".sheet-row").remove() }, icon("x"))));
  return { list, node: h("div", { class: "field" }, h("label", {}, title), h("span", { class: "hint" }, hint),
    list, h("button", { type: "button", class: "button", onclick: add }, icon("plus"), more)) };
}

// What Start sends as the settings (`#sent`), kept up to date as the form changes.
function watchSent(form) {
  const show = () => { form.querySelector("#sent").textContent = JSON.stringify(readSettings(form), null, 2); };
  form.addEventListener("input", show);
  form.addEventListener("change", show);
  show();
}

// The local image models the scenes may use (0027): the first checked is the project's default model.
function frameModels(selected, menu) {
  const lines = menu.some((m) => selected.includes(m.id)) ? menu : [...selected.map((id) => ({ id })), ...menu];
  return h("fieldset", { class: "field", id: "model-frame" }, h("legend", {}, "Image models of the scenes"),
    lines.map((m) => h("label", { class: "switch" }, h("input", { type: "checkbox", value: m.id, checked: selected.includes(m.id) }),
      h("span", {}, m.id, m.commercial_use === false ? " · research licence" : ""))),
    h("span", { class: "hint" }, "The first checked is the default of every picture; the planner may give a picture another checked model."));
}

function settingsPanel(defaults, ratios, paces, menu) {
  const input = (id, value, type = "text") => h("input", { type, id, value: String(value ?? "") });
  const ratio = h("select", { id: "aspect_ratio" }, ratios.map((r) => h("option", { value: r, selected: r === defaults.aspect_ratio }, r)));
  const models = [frameModels(defaults.models.frame, menu),
    ...Object.entries(ROLES).map(([role, label]) => field(label, input(`model-${role}`, defaults.models[role])))];
  return h("div", { class: "panel" }, h("div", { class: "panel-head" }, h("h2", {}, "Settings"), h("span", { class: "muted small" }, "defaults are fine")),
    lookFields(defaults, paces),
    h("div", { class: "grid-2" },
      field("Aspect ratio", ratio),
      field("Resolution", input("resolution", defaults.resolution, "number"), "Short side, pixels."),
      field("Shortest shot", input("min_shot", formatMs(defaults.min_shot_ms)), "m:ss.mmm"),
      field("Longest shot", input("max_shot", formatMs(defaults.max_shot_ms)), "m:ss.mmm"),
      field("Frame rate", input("fps", defaults.fps, "number"), "32 fps (Wan 16 fps doubled)."),
      field("Language", input("language", defaults.language || ""), "Optional, e.g. en.")),
    h("details", {}, h("summary", {}, "Models"), models),
    h("details", {}, h("summary", {}, "What will be sent"), h("pre", { id: "sent", class: "sent", dir: "auto" })));
}

export function readSettings(form) {
  const value = (id) => form.querySelector(`#${id}`).value.trim();
  const frame = [...form.querySelectorAll("#model-frame input:checked")].map((box) => box.value);
  const models = { ...Object.fromEntries(Object.keys(ROLES).map((role) => [role, value(`model-${role}`)])), frame };
  return {
    ...readLook(form), aspect_ratio: value("aspect_ratio"), resolution: Number(value("resolution")),
    fps: Number(value("fps")), min_shot_ms: parseMs(value("min_shot")), max_shot_ms: parseMs(value("max_shot")),
    language: value("language") || null, models,
  };
}

// The models that forbid commercial use (0021), listed above Start: a notice that asks nothing.
function watchLicences(form) {
  const licences = form.querySelector("#licences");
  const refresh = async () => {
    try {
      const found = await api("/estimate", { method: "POST", body: { settings: readSettings(form) } });
      licences.textContent = (found.not_commercial || []).join("\n");
    } catch (error) {
      licences.textContent = error.problems?.length ? error.problems.join("; ") : error.message;
    }
    licences.hidden = !licences.textContent;
  };
  form.querySelector("#model-frame").addEventListener("change", refresh);
  refresh();
}

async function readSheets(list) {
  const sheets = [];
  for (const row of list.querySelectorAll(".sheet-row")) {
    const [file, name, note] = row.querySelectorAll("input");
    if (!file.files[0]) continue;
    sheets.push({ name: name.value.trim(), note: note.value.trim(), file: await readFile(file.files[0]) });
  }
  return sheets;
}

// "Don't wait for my approval, just do it" (0004): each gate passes on its own unless its check finds errors.
function autoChoice() {
  return h("label", { class: "panel switch-row" }, h("input", { type: "checkbox", id: "auto-approve" }),
    h("span", { class: "grow" }, h("strong", {}, "Run without stopping for my approval"),
      h("span", { class: "hint" }, "Each review is approved as soon as it is reached. If a check finds errors, the run still stops and waits for you. You can switch this on the project page.")));
}

// "Prepare only" (0028 §6): every hosted call now (lyrics, plan), the pictures and clips later, offline.
function prepareChoice() {
  return h("label", { class: "panel switch-row" }, h("input", { type: "checkbox", id: "prepare" }),
    h("span", { class: "grow" }, h("strong", {}, "Prepare only (to run offline later)"),
      h("span", { class: "hint" }, "Makes the lyrics and the plan (the steps that need the internet), then waits. When several videos are prepared, \u201cRun all prepared\u201d on the Videos page makes them one after another, without stopping.")));
}

export async function newVideoView(main) {
  const { defaults, aspect_ratios: ratios, paces, image_models: menu } = await api("/settings");
  const song = songDrop();
  const sheets = pictureRows("Characters you already have", "A reference sheet or portrait each, with the name the story uses.", "Name (e.g. Darvin)", "Add a sheet");
  const poses = pictureRows("Pose pictures", "A body pose for the scenes, with the name the story's poses use (on a model that takes poses).", "Name (e.g. kneeling)", "Add a pose");
  const problems = h("div", { class: "problems", hidden: true });
  const start = h("button", { type: "submit", class: "button primary large block" }, icon("play"), "Start the video");
  const form = h("form", { class: "form" },
    h("div", { class: "panel" }, problems,
      field("Name", h("input", { type: "text", id: "name", required: true, placeholder: "The video's name" })),
      song.node,
      field("Lyrics", h("textarea", { id: "lyrics", rows: 8, dir: "auto" }), "Optional. One sung line per line, a blank line between sections."),
      field("Story notes", h("textarea", { id: "story", rows: 5, dir: "auto" }), "Optional. What happens: setting, era, the characters' names and relationships."),
      field("Feeling", h("textarea", { id: "feeling", rows: 3, dir: "auto" }), "Optional. What the viewer should feel, and how it changes through the song (\u201cwarm nostalgia that turns to dread; cold resolve at the end\u201d)."),
      sheets.node, poses.node),
    h("div", { class: "stack" }, settingsPanel(defaults, ratios, paces, menu), autoChoice(), prepareChoice(),
      h("pre", { class: "panel warnings licences", id: "licences", hidden: true }), start));
  watchLicences(form);
  watchSent(form);
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    problems.hidden = true;
    if (!song.input.files[0]) { toast("Add the song first."); return; }
    start.disabled = true;
    try {
      const made = await api("/projects", { method: "POST", body: {
        name: form.querySelector("#name").value, lyrics: form.querySelector("#lyrics").value,
        story: form.querySelector("#story").value, feeling: form.querySelector("#feeling").value,
        settings: readSettings(form), prepare: form.querySelector("#prepare").checked,
        song: await readFile(song.input.files[0]), sheets: await readSheets(sheets.list), poses: await readSheets(poses.list),
        approve: form.querySelector("#auto-approve").checked ? "auto" : "ask",
      } });
      location.hash = `#/p/${made.id}`;
    } catch (error) {
      problems.replaceChildren(h("strong", {}, "Not started. "), error.problems.length ? h("ul", {}, error.problems.map((p) => h("li", {}, p))) : error.message);
      problems.hidden = false;
      start.disabled = false;
    }
  });
  main.append(h("div", { class: "page" }, h("div", { class: "page-head" }, h("div", {}, h("h1", {}, "New video"),
    h("p", { class: "lede" }, "The song and what you know about it; everything else has a default."))), form));
}
