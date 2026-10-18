// The Scenes view's board (0030 §1): one card per shot in time order, as on the Clips view (the scene's
// picture in use, its state, the beat, time and length, the cast, the framing, its takes), the song's
// timeline above, and the characters', objects' and places' pictures in a second board by subject. A card
// opens the scene viewer (scene-frame.js): the picture large with every version, what made it, the shot,
// and the item's actions. The cards follow the frame project live; a card is redrawn only when it changed.

import { formatMs, h, spoken } from "../core.js";
import { avatar, framingChip } from "../parts.js";
import { on, state } from "../frame/state.js";
import { ITEM_STATUS, pill } from "../frame/ui.js";
import { songPanel } from "../timeline.js";
import { openFrameScene } from "./scene-frame.js";

const GROUPS = [["characters", "Characters"], ["objects", "Objects"], ["places", "Places"]];

const pictureOf = (item) => item.versions.find((v) => v.n === item.current) || null;
const shotsOf = (ctx) => ctx.records.shots?.shots || [];

function media(ctx, item, list, label) {
  const shown = pictureOf(item);
  const tag = item.status === "done" ? null : ITEM_STATUS[item.status] || item.status;
  return h("button", { type: "button", class: `board-media${item.status === "running" ? " working" : ""}`, "aria-label": `Open ${label}: its versions, what made it and its actions`, onclick: () => openFrameScene(ctx, item.id, list) },
    shown ? h("img", { src: shown.thumb || shown.url, alt: `the picture of ${label}`, loading: "lazy" }) : h("div", { class: "no-picture" }),
    tag ? h("span", { class: `media-tag tag-${item.status}` }, tag) : null);
}

function takes(item) {
  const n = item.versions.length;
  return n > 1 ? h("span", { class: "chip" }, `${n} versions`) : null;
}

function sceneCard(ctx, item, shot, list) {
  return h("article", { class: `board-card${item.status === "running" ? " working" : ""}${item.status === "failed" ? " failed" : ""}`, dataset: { shot: item.id } },
    media(ctx, item, list, item.id),
    h("div", { class: "board-body" },
      h("div", { class: "row between" }, h("strong", { class: "mono" }, item.id), pill("item", item.status, ITEM_STATUS)),
      shot ? h("p", { class: "board-beat" }, shot.beat) : null,
      shot ? h("div", { class: "row between" }, h("span", { class: "mono xs faint" }, `${formatMs(shot.start_ms)} · ${spoken(shot.end_ms - shot.start_ms)}`),
        h("span", { class: "avatars" }, shot.cast.map((id) => avatar(ctx, id, "small")))) : null,
      h("div", { class: "row wrap" }, shot ? framingChip(shot.framing) : null, item.marked ? h("span", { class: "chip" }, "marked to run") : null, takes(item))));
}

function subjectCard(ctx, item, list) {
  return h("article", { class: "board-card subject-card", dataset: { item: item.id } },
    media(ctx, item, list, item.id),
    h("div", { class: "board-body" },
      h("div", { class: "row between" }, h("span", { class: "mono small" }, item.id), pill("item", item.status, ITEM_STATUS)),
      h("div", { class: "row wrap" }, item.marked ? h("span", { class: "chip" }, "marked to run") : null, takes(item))));
}

// Rebuild a card only when what it shows changed (the board follows every item event).
function keep(cards, key, signature, build) {
  const found = cards.get(key);
  if (found && found.signature === signature) return found.node;
  const node = build();
  cards.set(key, { signature, node });
  return node;
}

export async function mount(body, route, getCtx) {
  const cards = new Map();
  const songSlot = h("div");
  const scenes = h("div", { class: "board" });
  const subjects = h("div", { class: "stack" });
  const counted = h("p", { class: "muted" });
  body.replaceChildren(h("div", { class: "stack scene-board" }, songSlot,
    h("div", { class: "row between wrap" }, counted, h("p", { class: "muted small" }, "Click a picture for its versions, what made it and its actions.")),
    scenes, h("h2", {}, "Characters, objects and places"), subjects));

  function draw() {
    const ctx = getCtx();
    const view = state.project;
    if (!view) return;
    const byShot = new Map(shotsOf(ctx).map((s) => [s.id, s]));
    const sceneItems = view.items.filter((it) => it.group === "scenes");
    const list = sceneItems.map((it) => it.id);
    const sig = (item, more = "") => JSON.stringify([item.status, item.current, item.marked, item.versions.length, pictureOf(item)?.thumb, more]);
    scenes.replaceChildren(...sceneItems.map((item) => {
      const shot = byShot.get(item.id);
      return keep(cards, item.id, sig(item, shot && [shot.beat, shot.start_ms, shot.end_ms, shot.cast, shot.framing]), () => sceneCard(ctx, item, shot, list));
    }));
    const made = sceneItems.filter((it) => it.current != null).length;
    counted.textContent = `${made} of ${sceneItems.length} scenes have a picture`;
    subjects.replaceChildren(...GROUPS.map(([group, title]) => {
      const items = view.items.filter((it) => it.group === group);
      if (!items.length) return null;
      const ids = items.map((it) => it.id);
      return h("section", { class: "stack small-gap" }, h("div", { class: "eyebrow" }, title),
        h("div", { class: "board subjects" }, items.map((item) => keep(cards, item.id, sig(item), () => subjectCard(ctx, item, ids)))));
    }).filter(Boolean));
  }

  songSlot.replaceChildren(songPanel(getCtx(), { onShot: (shot) => openFrameScene(getCtx(), shot.id, shotsOf(getCtx()).map((s) => s.id)) }));
  draw();
  const offs = [on("item", draw), on("project", draw)];
  return { update: draw, unmount: () => offs.forEach((off) => off()) };
}
