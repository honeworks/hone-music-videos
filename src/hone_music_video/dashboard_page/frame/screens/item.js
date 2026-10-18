// The open item: what it is and where it stands, what it waits for, its actions, the image large with what
// made it, every version (never deleted) with "use this version", and its fields (fields.js).
// Hone Frame: ported from dashboard_page/screens/item.js.

import { api } from "../api.js";
import { applyItem, applyRun, loadProject, state } from "../state.js";
import { at, clockTime, duration, h, icon, itemHref, ITEM_STATUS, pill, range, redrawIf, setImage, toast } from "../ui.js";
import { askDependants } from "./dependants.js";
import { createFields } from "./fields.js";
import { elapsedOf } from "./runbar.js";

const versionOf = (item, n) => item.versions.find((v) => v.n === n) || null;
// The images a pick chooses from (a waiting item with count > 1).
const candidatesOf = (item) => item.candidates.map((n) => versionOf(item, n)).filter(Boolean);
// "Prompt 2" for a version made with the item's second prompt (an item with `prompts`, D-076), else null.
function promptLabel(item, v) {
  const index = item.prompts ? item.prompts.indexOf(v.prompt) : -1;
  return index >= 0 ? `Prompt ${index + 1}` : null;
}

export function createItemPanel(projectId) {
  const head = h("div", { class: "item-head" });
  const banner = h("div", { class: "item-banner" });
  const actions = h("div", { class: "item-actions", role: "group", "aria-label": "Item actions" });
  const stage = h("div", { class: "stage" });
  const strip = h("div", { class: "versions" });
  const formSlot = h("div", { class: "fields-slot" });
  const el = h("section", { class: "pane item-pane", "aria-label": "Item" }, head, banner, actions, stage, strip, formSlot);
  const fileInput = h("input", { type: "file", accept: "image/png,image/jpeg,image/webp", hidden: true });
  el.append(fileInput);
  let item = null;
  let viewing = null; // the version number shown large
  let fields = null;
  let liveNode = null;

  async function act(label, fn) {
    try {
      const result = await fn();
      if (result && result.id) applyItem({ project: projectId, item: result });
      return result;
    } catch (error) {
      toast(`${label}: ${error.message}`, { kind: "error" });
      return null;
    }
  }

  async function mark() {
    const dependants = await askDependants(projectId, item.id, `Marking ${item.id} to run makes it again`);
    if (dependants === null) return;
    const result = await act("Mark to run", () => api.mark(projectId, item.id, dependants));
    if (!result) return;
    toast(`Marked to run: ${result.marked.join(", ")}`);
    loadProject(projectId).catch(() => {}); // the marks of several items moved
  }

  // Run this prompt (hone-music-video 0033): its picture is made beside the one in use, nothing made from
  // the item is marked; the run starts when it is not going already.
  async function runPrompt(k) {
    if (!(await act(`Run prompt ${k + 1}`, () => api.runPrompt(projectId, item.id, k)))) return;
    const status = state.project.run?.status;
    if (!["queued", "running", "pausing", "paused", "waiting"].includes(status)) {
      await act("Run", async () => applyRun(await api.runAction(projectId, "run")));
    }
    toast(`Prompt ${k + 1} of ${item.id} is marked to run. Its picture is kept beside the one in use.`);
  }

  async function useVersion(n) {
    const dependants = await askDependants(projectId, item.id, `Version ${n} becomes the current image of ${item.id}`);
    if (dependants === null) return;
    if (await act("Use this version", () => api.useVersion(projectId, item.id, n, dependants))) {
      viewing = null;
      toast(`Version ${n} is now the current image of ${item.id}.`);
      if (dependants) loadProject(projectId).catch(() => {});
    }
  }

  fileInput.addEventListener("change", async () => {
    const file = fileInput.files[0];
    fileInput.value = "";
    if (!file) return;
    const dependants = await askDependants(projectId, item.id, `${file.name} becomes a new version of ${item.id}`);
    if (dependants === null) return;
    if (await act("Replace with a file", () => api.replaceFile(projectId, item.id, file, dependants))) {
      viewing = null;
      toast(`${file.name} is now the current image of ${item.id}.`);
      if (dependants) loadProject(projectId).catch(() => {});
    }
  });

  function drawHead() {
    const { model, count, hold } = item.effective;
    redrawIf(head, JSON.stringify([item.id, item.status, item.marked, item.changed_since_made, item.older_refs, item.license_warning, item.effective, item.estimate]), () => [
      h("div", { class: "item-title" },
        h("h2", {}, item.id),
        pill("item", item.status, ITEM_STATUS),
        item.marked ? h("span", { class: "badge marked" }, "Marked to run") : null),
      h("p", { class: "caption" }, [item.group, item.kind === "sheet" ? "sheet (composed, no model)" : model,
        count > 1 ? (item.prompts ? `${count} prompts, one made at a time` : `${count} images, you pick one`) : null, hold ? "waits for your acceptance" : null,
        item.estimate ? `usually ${range(item.estimate.low_s, item.estimate.high_s)}` : null].filter(Boolean).join(" · ")),
      item.changed_since_made ? h("p", { class: "flag-line" }, icon("flag"), "Changed since made: its fields differ from what made the current image. Mark it to run to make it again.") : null,
      ...item.older_refs.map((ref) => h("p", { class: "flag-line" }, icon("flag"), "Made from an older ", h("a", { href: itemHref(projectId, ref) }, ref), ". Mark it to run to make it from the current one.")),
      item.license_warning ? h("p", { class: "flag-line warn" }, icon("flag"), item.license_warning) : null,
    ]);
  }

  function drawBanner() {
    const candidates = candidatesOf(item);
    redrawIf(banner, JSON.stringify([item.status, item.error, candidates.map((v) => v.n), item.prompts]), () => {
      if (item.status === "failed") return h("div", { class: "callout danger", role: "alert" }, h("strong", {}, "It failed. "), item.error || "No error was given.", " Fix the fields if needed, then Mark to run.");
      if (item.status === "waiting" && candidates.length) {
        return h("div", { class: "callout waiting" }, h("strong", {}, `Pick one of ${candidates.length}.`), " The run continues by itself once you pick.",
          h("div", { class: "pick-grid" }, candidates.map((v) => h("figure", {},
            promptLabel(item, v) ? h("span", { class: "pick-label", title: v.prompt || "" }, promptLabel(item, v)) : null,
            h("button", { type: "button", class: "pick-thumb", "aria-label": `Show version ${v.n} large`, onclick: () => { viewing = v.n; drawStage(); drawStrip(); } },
              h("img", { src: v.thumb, alt: `Version ${v.n}` })),
            h("figcaption", {}, h("button", { type: "button", class: "button small primary", "data-key": `pick-${v.n}`,
              onclick: () => act("Pick", () => api.accept(projectId, item.id, v.n)) }, icon("check"), `Pick v${v.n}`))))));
      }
      if (item.status === "waiting") return h("div", { class: "callout waiting" }, h("strong", {}, "The run waits for you. "), "Accept this image to continue, or edit and Mark to run to make it again.");
      return null;
    });
  }

  function drawActions() {
    const waitingOne = item.status === "waiting" && !item.candidates.length;
    const busy = item.status === "running";
    const prompts = item.prompts && item.prompts.length > 1 ? item.prompts : [];
    redrawIf(actions, JSON.stringify([item.id, item.status, item.marked, item.candidates, item.kind, prompts, item.run_prompt]), () => [
      waitingOne ? h("button", { type: "button", class: "button primary", "data-key": "accept", onclick: () => act("Accept", () => api.accept(projectId, item.id)) }, icon("check"), "Accept") : null,
      item.marked
        ? h("button", { type: "button", class: "button", "data-key": "unmark", disabled: busy, onclick: () => act("Unmark", () => api.unmark(projectId, item.id)) }, icon("x"), "Unmark")
        : h("button", { type: "button", class: "button", "data-key": "mark", disabled: busy, title: "The run makes it again when it reaches it", onclick: mark }, icon("mark"), "Mark to run"),
      item.kind === "sheet" ? null : h("button", { type: "button", class: "button", "data-key": "file", disabled: busy, onclick: () => fileInput.click() }, icon("upload"), "Replace with a file"),
      ...prompts.map((p, k) => h("button", { type: "button", class: "button", "data-key": `run-prompt-${k + 1}`, disabled: busy || item.run_prompt === k, title: p,
        onclick: () => runPrompt(k) }, icon("mark"), item.run_prompt === k ? `Prompt ${k + 1} marked` : `Run prompt ${k + 1}`)),
    ]);
  }

  function metaOf(v) {
    const from = Object.entries(v.made_from); // [[ref, version]]
    return h("dl", { class: "meta" },
      h("dt", {}, "Version"), h("dd", {}, `v${v.n}${v.n === item.current ? " (current)" : ""}`),
      v.source === "provided" ? [h("dt", {}, "Source"), h("dd", {}, "a provided file")] : [h("dt", {}, "Model"), h("dd", {}, v.model || "—"), h("dt", {}, "Seed"), h("dd", { class: "mono" }, v.seed ?? "—")],
      promptLabel(item, v) ? [h("dt", {}, "Prompt"), h("dd", { title: v.prompt }, promptLabel(item, v))] : null,
      v.elapsed_s != null ? [h("dt", {}, "Took"), h("dd", {}, duration(v.elapsed_s))] : null,
      v.at ? [h("dt", {}, "Made"), h("dd", {}, at(v.at))] : null,
      h("dt", {}, "Made from"), h("dd", {}, from.length ? from.map(([ref, n], i) => [i ? ", " : "", ref ? h("a", { href: itemHref(projectId, ref) }, ref) : ref, n != null ? ` v${n}` : ""]) : "no references"));
  }

  function drawStage() {
    const v = versionOf(item, viewing ?? item.current);
    const run = state.project.run;
    const making = run && run.current && run.current.item === item.id;
    redrawIf(stage, JSON.stringify([item.id, v && v.n, v && v.url, item.current, making, item.status, item.marked, item.prompts]), () => {
      liveNode = null;
      if (!v) {
        if (making) {
          liveNode = h("span", { class: "mono" }, clockTime(elapsedOf(run)));
          return h("div", { class: "stage-empty making" }, h("strong", {}, "Making it now… "), liveNode);
        }
        const place = run.remaining.indexOf(item.id);
        return h("div", { class: "stage-empty" }, item.marked ? `Marked to run${place >= 0 ? `: number ${place + 1} in line` : ""}. It is made when the run reaches it.` : "No image yet. Mark it to run to make it.");
      }
      const frame = h("a", { class: "stage-image", href: v.url, target: "_blank", rel: "noopener", title: "Open full size" });
      setImage(frame, v.url, `${item.id}, version ${v.n}`, "large");
      return [
        frame,
        h("div", { class: "stage-side" },
          making ? h("p", { class: "callout running" }, "Making a new version now. This one stays until it is done.") : null,
          metaOf(v),
          v.n !== item.current ? h("button", { type: "button", class: "button primary", "data-key": `use-${v.n}`, disabled: making, onclick: () => useVersion(v.n) }, "Use this version") : h("p", { class: "caption" }, "This is the current version."),
          h("a", { class: "button small ghost", href: v.url, target: "_blank", rel: "noopener" }, icon("open"), "Full size")),
      ];
    });
  }

  function drawStrip() {
    const versions = item.versions;
    redrawIf(strip, JSON.stringify([item.id, versions.map((v) => [v.n, v.thumb]), item.current, viewing]), () => versions.length ? [
      h("h3", { class: "overline" }, `Versions (${versions.length}) · never deleted`),
      h("ol", { class: "strip" }, versions.slice().reverse().map((v) => h("li", {},
        h("button", { type: "button", class: "strip-thumb", "data-key": `v-${v.n}`, "aria-pressed": String(v.n === (viewing ?? item.current)),
          "aria-label": `Version ${v.n}${v.n === item.current ? ", current" : ""}`, onclick: () => { viewing = v.n; drawStage(); drawStrip(); } },
          h("img", { src: v.thumb, alt: "", loading: "lazy" }),
          h("span", { class: "strip-label" }, `v${v.n}`, v.n === item.current ? h("span", { class: "current-tag" }, "current") : null, v.source === "provided" ? " · file" : null))))),
    ] : null);
  }

  function draw() {
    drawHead();
    drawBanner();
    drawActions();
    drawStage();
    drawStrip();
  }

  const timer = setInterval(() => {
    if (liveNode && state.project.run) liveNode.textContent = clockTime(elapsedOf(state.project.run));
  }, 1000);

  return {
    el,
    show(next) {
      if (item && next.id === item.id) return this.update(next);
      item = next;
      viewing = null;
      for (const node of [head, banner, actions, stage, strip]) delete node.dataset.sig;
      draw();
      fields = createFields(projectId, item);
      formSlot.replaceChildren(fields.el);
      el.scrollTop = 0;
    },
    update(next) {
      if (next.versions.length > item.versions.length) viewing = null; // a new version: show it
      item = next;
      draw();
      if (fields) fields.sync(item);
    },
    setRun() { if (item) { drawStage(); } },
    refsChanged(changed) {
      if (fields && item && item.refs.includes(changed.id)) fields.refreshRefs();
    },
    empty(node) {
      item = null;
      for (const n of [head, banner, actions, stage, strip]) { n.replaceChildren(); delete n.dataset.sig; }
      formSlot.replaceChildren(node);
    },
    destroy: () => clearInterval(timer),
  };
}
