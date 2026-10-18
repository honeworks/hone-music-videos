// The viewer over the page (0003): a picture or clip at full size with its label, previous and next
// through the same list (arrow keys), Esc or a click outside to close, a link to the file itself. It is a
// modal dialog: focus stays inside it and goes back to what opened it.

import { h } from "./core.js";
import { icon } from "./icons.js";

let current = null; // { root, items, index, opener }

function focusables(root) {
  return [...root.querySelectorAll("button, a[href], video[controls]")];
}

function stay(event, root) {
  const nodes = focusables(root);
  if (!nodes.length) return;
  const [first, last] = [nodes[0], nodes[nodes.length - 1]];
  if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
  else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
}

function media(item) {
  if (!item.video) return h("img", { class: "lb-media", src: item.src, alt: item.label });
  const video = h("video", { class: "lb-media", src: item.src, controls: true, autoplay: true, playsinline: true, loop: true });
  video.muted = !item.onplay; // a clip with its song slice plays the song, not its own (silent) track
  if (item.onplay) {
    video.addEventListener("play", () => item.onplay(video));
    video.addEventListener("pause", () => item.onpause?.());
  }
  return video;
}

function draw(focus = "Close") {
  const { root, items, index } = current;
  const item = items[index];
  const step = (by) => () => { current.index = (index + by + items.length) % items.length; draw(by < 0 ? "Previous" : "Next"); };
  const many = items.length > 1;
  root.setAttribute("aria-label", item.label);
  root.replaceChildren(h("div", { class: "lb-frame" },
    h("div", { class: "lb-stage" }, media(item)),
    h("div", { class: "lb-bar" },
      many ? h("button", { type: "button", class: "icon-button", "aria-label": "Previous", onclick: step(-1) }, icon("left")) : null,
      h("div", { class: "grow lb-label" }, h("strong", {}, item.label), many ? h("span", { class: "faint xs" }, ` · ${index + 1} of ${items.length}`) : null),
      h("a", { class: "button ghost", href: item.src, target: "_blank", rel: "noopener" }, icon("external"), "Open the file"),
      many ? h("button", { type: "button", class: "icon-button", "aria-label": "Next", onclick: step(1) }, icon("right")) : null,
      h("button", { type: "button", class: "icon-button", "aria-label": "Close", onclick: closeLightbox }, icon("x")))));
  root.querySelector(`.lb-bar [aria-label="${focus}"]`)?.focus();
}

function keys(event) {
  if (!current) return;
  if (event.key === "Escape") { event.preventDefault(); closeLightbox(); }
  else if (event.key === "ArrowLeft" || event.key === "ArrowRight") {
    if (current.items.length < 2 || event.target instanceof HTMLVideoElement) return; // the video seeks
    event.preventDefault();
    current.index = (current.index + (event.key === "ArrowLeft" ? -1 : 1) + current.items.length) % current.items.length;
    draw(document.activeElement?.getAttribute("aria-label") || "Close"); // the focus stays where it was
  } else if (event.key === "Tab") stay(event, current.root);
}

export function closeLightbox() {
  if (!current) return;
  const { root, opener, items, index } = current;
  items[index]?.onpause?.();
  current = null;
  root.remove();
  document.removeEventListener("keydown", keys);
  document.body.classList.remove("lb-open");
  opener?.focus?.({ preventScroll: true });
}

// Open `items` ({src, label, video?, onplay?, onpause?}) at `index`; `opener` gets the focus back.
export function openLightbox(items, index, opener = document.activeElement) {
  closeLightbox();
  const root = h("div", { class: "lightbox", role: "dialog", "aria-modal": "true" });
  root.addEventListener("click", (event) => { if (event.target === root || event.target.classList.contains("lb-stage")) closeLightbox(); });
  current = { root, items: [...items], index, opener };
  document.body.append(root);
  document.body.classList.add("lb-open");
  document.addEventListener("keydown", keys);
  draw();
}
