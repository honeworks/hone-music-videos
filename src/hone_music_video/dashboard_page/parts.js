// Small pieces several project views share: the gate bar, the checks, cast avatars, framing chips, media.

import { GATE_NAMES, h, humanize } from "./core.js";
import { gateControls, send } from "./decide.js";
import { icon } from "./icons.js";
import { openLightbox } from "./lightbox.js";

// A button that POSTs one action to the project (`body` and `done` may be functions, read on click; a
// `body` function that returns null cancels), says it is done, and refreshes the view; the run continues
// on the server and the page follows live.
export function actionButton(ctx, label, iconName, path, body, done, kind = "primary large") {
  const button = h("button", { type: "button", class: `button ${kind}` }, icon(iconName), label);
  button.addEventListener("click", async () => {
    const sent = typeof body === "function" ? await body() : body;
    if (sent !== null) await send(ctx, button, path, sent, done);
    ctx.refresh();
  });
  return button;
}

// The gate bar a view shows while its gate waits for the owner: what to look at, then the gate's
// controls (decide.js, 0018); `approve` replaces the plain Approve, `extra` adds controls.
export function gateBar(ctx, gate, text, { approvable = true, approve, extra = null } = {}) {
  if (ctx.project.run.waiting !== gate) return null;
  return h("div", { class: "gate-bar" }, h("span", { class: "gate-icon" }, icon("hand")),
    h("div", { class: "grow" }, h("h3", {}, GATE_NAMES[gate]), h("p", { class: "muted small" }, text)),
    gateControls(ctx, gate, { approvable, approve, extra }));
}

// The check each checked gate shows; while it reports errors the gate cannot be approved, and its stage is
// run again with a note instead (D-015), or at the lyrics gate the owner fixes the times (0018).
const CHECK_OF = { review_lyrics: "lyrics_check", review_plan: "plan_check" };

export function blocked(ctx, gate) {
  return (ctx.records[CHECK_OF[gate]]?.errors.length || 0) > 0;
}

// A check's findings about one thing: its id, or a part of it ("L004 word 2 (...)").
export function findingsOf(report, id) {
  const about = (p) => p.where === id || p.where.startsWith(`${id} `);
  return [...(report?.errors || []).filter(about).map((p) => ["errors", p]), ...(report?.warnings || []).filter(about).map((p) => ["warnings", p])];
}

export function notesList(found, extra = "") {
  if (!found.length) return null;
  return h("ul", { class: `problems-list ${extra}`.trim() }, found.map(([kind, p]) => h("li", { class: kind },
    icon(kind === "errors" ? "x" : "alert"), h("div", {}, p.message, h("span", { class: "faint xs" }, ` (${p.rule})`)))));
}

function problemList(kind, problems) {
  return h("ul", { class: `problems-list ${kind}` }, problems.map((p) => h("li", {},
    icon(kind === "errors" ? "x" : "alert"), h("div", {}, h("strong", {}, p.where), " ", p.message, h("span", { class: "faint xs" }, ` (${p.rule})`)))));
}

// A validator's report: errors and warnings, or that it found nothing.
export function checks(report, what) {
  if (!report) return h("p", { class: "muted small" }, `The checks run once the ${what} exist.`);
  const { errors = [], warnings = [] } = report;
  if (!errors.length && !warnings.length) {
    return h("div", { class: "all-clear" }, icon("check"), h("span", {}, "No errors, no warnings."));
  }
  return h("div", { class: "stack small-gap" }, errors.length ? problemList("errors", errors) : null,
    warnings.length ? problemList("warnings", warnings) : null);
}

export function stat(value, label) {
  return h("div", { class: "stat" }, h("span", { class: "stat-value" }, value), h("span", { class: "stat-label" }, label));
}

// A character's name: its id in words (the frame project names characters by id, 0027).
export function characterName(ctx, id) {
  return ctx.records.characters?.[id]?.name || humanize(id);
}

// The real count of shots a per-shot stage has made, as a bar (none for other stages).
export function shotsBar(stage, size = "") {
  if (!stage?.shots_total) return null;
  return h("div", { class: `bar ${size}`.trim() }, h("span", { style: { width: `${(100 * stage.shots_done) / stage.shots_total}%` } }));
}

// A character as a round picture: its close-up in use, else its hero picture, else the initial (0027).
export function avatar(ctx, id, size = "") {
  const picture = ctx.records.characters?.[id]?.picture;
  const name = characterName(ctx, id);
  return h("span", { class: `avatar ${size}`, title: name },
    picture ? h("img", { src: picture, alt: "" }) : name.slice(0, 1).toUpperCase());
}

export function framingChip(framing) {
  return h("span", { class: "chip" }, h("span", { class: `swatch f-${framing}` }), humanize(framing));
}

export function picture(src, alt = "", extra = "") {
  return src ? h("img", { src, alt, loading: "lazy", class: extra }) : h("div", { class: `no-picture ${extra}` }, icon("image"));
}

// Make a picture or clip open in the viewer (0003): `item` ({src, label, video?}) joins the view's list
// (`ctx.gallery`, in the order shown); a click on `node` or on its small "open" button opens it there.
export function zoom(ctx, node, item) {
  if (!item.src) return node;
  const index = ctx.gallery.push(item) - 1;
  const open = (event) => {
    event.preventDefault();
    event.stopPropagation();
    openLightbox(ctx.gallery, index, node.querySelector(".zoom-button"));
  };
  node.classList.add("zoomable");
  node.addEventListener("click", open);
  node.append(h("button", { type: "button", class: "zoom-button", "aria-label": `Open ${item.label}`, title: "Open", onclick: open }, icon("expand")));
  return node;
}

// A picture that opens in the viewer (a sheet take, a pack view, a given sheet).
export function zoomPicture(ctx, src, label, extra = "") {
  return zoom(ctx, h("span", { class: `zoom-box ${extra}`.trim() }, picture(src, label, extra)), { src, label });
}
