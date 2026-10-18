// The scene viewer of the Scenes view (0030 §1): one item of the frame project over the page, opened from
// the board. Hone Frame's item panel (the picture large, what made it, every version with "use this
// version", pick among takes, accept, mark to run, replace with a file, and its fields: the prompts, the
// references, the seed, the model) beside what the shot is (its time, beat, feel and evidence, the lines
// sung over it, framing and camera, the motion prompt). It follows the run while open. Keys: ←/→ the item
// before and after on its board, Esc closes; "Open in the workspace" goes to the item in Hone Frame's
// screens.

import { formatMs, h, spoken } from "../core.js";
import { icon } from "../icons.js";
import { itemById, on, state } from "../frame/state.js";
import { createItemPanel } from "../frame/screens/item.js";

let open = null; // { ctx, id, list, root, panel, aside, offs, opener }

function field(label, value) {
  return value ? h("div", { class: "field-view" }, h("div", { class: "eyebrow" }, label), h("div", {}, value)) : null;
}

// What the shot is: the frame plan's shot and its feeling, the lines sung over it.
function shotSide(ctx, id) {
  const shot = (ctx.records.shots?.shots || []).find((s) => s.id === id);
  if (!shot) return [h("p", { class: "muted small" }, "A picture the scenes are made from.")];
  const feeling = (ctx.records.feelings || {})[id] || {};
  const lines = (ctx.records.timeline?.lines || []).filter((l) => shot.lines.includes(l.id));
  return [
    h("p", { class: "mono small muted" }, `${formatMs(shot.start_ms)} – ${formatMs(shot.end_ms)} · ${spoken(shot.end_ms - shot.start_ms)} · ${shot.framing}${shot.faces ? " · faces" : ""}`),
    h("p", { class: "beat" }, shot.beat),
    field("Feel", feeling.feel), field("What shows it", feeling.evidence),
    lines.length ? field("Sung over it", h("ul", { class: "shot-lines" }, lines.map((l) => h("li", { dir: "auto" }, l.text)))) : null,
    field("Camera", shot.camera),
    field("Motion prompt", h("p", { class: "prompt-text" }, shot.motion_prompt)),
  ];
}

function draw() {
  const item = itemById(open.id);
  if (!item) { closeFrameScene(); return; }
  open.label.replaceChildren(h("strong", { class: "mono" }, item.id), h("span", { class: "faint xs" }, ` · ${item.group}`));
  open.workspace.setAttribute("href", `#/p/${encodeURIComponent(open.ctx.id)}/scenes/i/${encodeURIComponent(item.id)}`);
  open.aside.replaceChildren(...shotSide(open.ctx, item.id));
  open.panel.show(item);
}

function step(by) {
  const at = open.list.indexOf(open.id);
  const next = open.list[(at + by + open.list.length) % open.list.length];
  if (next) { open.id = next; draw(); }
}

const typing = (target) => target instanceof HTMLInputElement || target instanceof HTMLTextAreaElement || target instanceof HTMLSelectElement || target?.isContentEditable;

function keys(event) {
  if (!open || document.querySelector("#frame-dialog[open]")) return;
  if (event.key === "Escape") { event.preventDefault(); closeFrameScene(); return; }
  if (typing(event.target)) return;
  if (event.key === "ArrowLeft" || event.key === "ArrowRight") { event.preventDefault(); step(event.key === "ArrowLeft" ? -1 : 1); }
}

export function closeFrameScene() {
  if (!open) return;
  const { root, panel, offs, opener } = open;
  open = null;
  offs.forEach((off) => off());
  panel.destroy();
  root.remove();
  document.removeEventListener("keydown", keys);
  document.body.classList.remove("lb-open");
  opener?.focus?.({ preventScroll: true });
}

// Open item `id` of the open frame project; `list` is the board's order for ←/→.
export function openFrameScene(ctx, id, list = [id]) {
  closeFrameScene();
  const panel = createItemPanel(ctx.id);
  const label = h("div", { class: "grow lb-label" });
  const workspace = h("a", { class: "button ghost", href: "#" }, "Open in the workspace", icon("arrow"));
  const aside = h("aside", { class: "scene-side stack" });
  const root = h("div", { class: "lightbox scene hf", role: "dialog", "aria-modal": "true", "aria-label": `${id}: its versions and actions` },
    h("div", { class: "lb-frame scene-frame" },
      h("div", { class: "lb-bar" },
        h("button", { type: "button", class: "icon-button", "aria-label": "Previous", onclick: () => step(-1) }, icon("left")),
        label, workspace,
        h("button", { type: "button", class: "icon-button", "aria-label": "Next", onclick: () => step(1) }, icon("right")),
        h("button", { type: "button", class: "icon-button", "aria-label": "Close", onclick: closeFrameScene }, icon("x"))),
      h("div", { class: "scene-body frame-scene-body" }, h("div", { class: "scene-main" }, panel.el), aside)));
  root.addEventListener("click", (event) => { if (event.target === root) closeFrameScene(); });
  workspace.addEventListener("click", () => closeFrameScene());
  const offs = [
    on("item", (item) => { if (open && item.id === open.id) open.panel.update(item); }),
    on("run", () => open?.panel.setRun()),
    on("project", () => { if (open) { const item = itemById(open.id); if (item) open.panel.update(item); } }),
  ];
  open = { ctx, id, list, root, panel, aside, label, workspace, offs, opener: document.activeElement };
  document.body.append(root);
  document.body.classList.add("lb-open");
  document.addEventListener("keydown", keys);
  draw();
  root.querySelector(".lb-bar [aria-label='Close']")?.focus();
  return state.project;
}
