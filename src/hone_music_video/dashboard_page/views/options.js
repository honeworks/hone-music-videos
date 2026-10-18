// The New video form's look of the video (0016, D-096): the pace (three choices), the mood (free text in
// any language, with words to add by a click) and the style (free text, or a preset to start from).

import { h } from "../core.js";

// What each pace means, for the owner (the server's `paces` list, when it sends one, gives the choices).
const PACE_TEXT = {
  calm: "Longer shots and slow camera moves; the picture lingers.",
  balanced: "Held shots and quicker cuts as the song's sections ask for them.",
  energetic: "Shorter shots, more cuts and livelier motion.",
};

export const MOODS = ["tragic", "sad", "tender", "hopeful", "triumphant", "tense", "dark", "dreadful", "mysterious", "epic"];
const MOOD_LABELS = { dreadful: "dreadful (دلهره‌آور)" };

// Each fills the style with a concrete look that names no era: the era comes from the story.
export const STYLES = {
  "Historical epic film": "Epic historical drama: sweeping wide landscapes and close, weathered faces; natural daylight, firelight and torchlight; an earthy palette of ochre, deep red, bronze and dusty gold; hand-made costumes of leather, metal and wool with real wear; atmospheric haze and dust; anamorphic widescreen composition, soft film grain.",
  "Dark & moody cinema": "Dark, moody cinema: low-key lighting with deep, rich shadows and one motivated light source; a desaturated cool palette with warm highlights on faces; haze and smoke in the air; shallow depth of field; quiet, still compositions; fine film grain.",
  "Natural documentary realism": "Natural documentary realism: available light only; true-to-life colour without a stylised grade; real textures and unretouched skin; eye-level framing with a 35 mm lens look; natural depth of field; nothing looks staged.",
  "Modern cinematic": "Modern cinematic look: a clean, high-dynamic-range image with soft contrast; precise motivated lighting with a gentle rim light; a restrained teal and amber grade; shallow depth of field with smooth bokeh; crisp detail and carefully balanced compositions.",
};

// The pace choices, each with what it means: the server's `paces` (a list of names), else these three.
export function paceChoices(paces) {
  return (paces || Object.keys(PACE_TEXT)).map((p) => [p, PACE_TEXT[p] || ""]);
}

const wordsOf = (text) => text.split(/[,،]/).map((w) => w.trim()).filter(Boolean);
export const hasWord = (text, word) => wordsOf(text).some((w) => w.toLowerCase() === word.toLowerCase());

// The mood with `word` added at the end, or taken out when it is there (commas, Arabic-script ones too, part words).
export function toggleWord(text, word) {
  const words = wordsOf(text);
  const kept = words.filter((w) => w.toLowerCase() !== word.toLowerCase());
  return (kept.length === words.length ? [...words, word] : kept).join(", ");
}

function paceField(paces, selected) {
  return h("fieldset", { class: "field choice-cards" }, h("legend", {}, "Pace"),
    paceChoices(paces).map(([pace, text]) => h("label", { class: "choice-card" },
      h("input", { type: "radio", name: "pace", value: pace, checked: pace === selected }),
      h("span", {}, h("strong", {}, pace[0].toUpperCase() + pace.slice(1)), h("span", { class: "hint" }, text)))));
}

// A field's value set by a click, told to the form like typing (the chips' marks and the preview follow).
function fill(field, value) {
  field.value = value;
  field.dispatchEvent(new Event("input", { bubbles: true }));
}

function moodField(mood) {
  const input = h("input", { type: "text", id: "mood", dir: "auto", value: mood, placeholder: "e.g. tragic, tender — any language" });
  const chips = MOODS.map((word) => h("button", { type: "button", class: "chip-button", dir: "auto", dataset: { word },
    onclick: () => fill(input, toggleWord(input.value, word)) }, MOOD_LABELS[word] || word));
  const mark = () => chips.forEach((chip) => chip.setAttribute("aria-pressed", String(hasWord(input.value, chip.dataset.word))));
  input.addEventListener("input", mark);
  mark();
  return h("div", { class: "field" }, h("label", { for: "mood" }, "Mood"), input, h("div", { class: "chip-row" }, chips),
    h("span", { class: "hint" }, "How the video should feel, in your words; click a word to add it or take it out."));
}

function styleField(style) {
  const text = h("textarea", { id: "style", rows: 4, dir: "auto" }, style);
  const presets = Object.entries(STYLES).map(([name, look]) => h("button", { type: "button", class: "chip-button", dataset: { look }, onclick: () => fill(text, look) }, name));
  const mark = () => presets.forEach((button) => button.setAttribute("aria-pressed", String(text.value.trim() === button.dataset.look)));
  text.addEventListener("input", mark);
  mark();
  return h("div", { class: "field" }, h("label", { for: "style" }, "Style"),
    h("div", { class: "chip-row" }, h("span", { class: "xs faint" }, "Start from:"), presets), text,
    h("span", { class: "hint" }, "The look, woven into every prompt. A preset fills it in; edit it as you like. The era comes from the story."));
}

export function lookFields(defaults, paces) {
  return [paceField(paces, defaults.pace ?? "balanced"), moodField(defaults.mood ?? ""), styleField(defaults.style)];
}

export function readLook(form) {
  return { pace: form.querySelector("input[name=pace]:checked")?.value ?? "balanced",
    mood: form.querySelector("#mood").value.trim(), style: form.querySelector("#style").value.trim() };
}
