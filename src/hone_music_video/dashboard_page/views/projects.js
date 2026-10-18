// Projects (design §13.2): every video with its thumbnail, where its run stands and its length; New video.

import { api, empty, formatMs, h, pill, runWhere, toast } from "../core.js";
import { icon } from "../icons.js";
import { cardBar } from "../progress.js";

function where(project) {
  if (project.prepared) return h("span", {}, icon("check"), "Prepared: ready to run offline");
  const glyph = project.waiting ? "hand" : project.status === "completed" ? "check" : "activity";
  return h("span", { class: project.waiting ? "wait" : "" }, icon(glyph), runWhere(project));
}

function card(project) {
  return h("a", { class: "card", href: `#/p/${project.id}` },
    h("div", { class: "thumb" }, project.thumbnail ? h("img", { src: project.thumbnail, alt: "" }) : h("div", { class: "thumb-empty" }, icon("film"), "frames appear as they are made"),
      project.duration_ms ? h("span", { class: "thumb-time mono" }, formatMs(project.duration_ms)) : null),
    h("div", { class: "card-body" },
      h("div", { class: "row between" }, h("span", { class: "card-title" }, project.name), pill(project.status)),
      h("div", { class: "card-where small muted" }, where(project)), cardBar(project)));
}

// "Run all prepared" (0028 §6): every prepared video, oldest first, one after another, without stopping.
export function runPreparedButton(projects, done = () => {}) {
  const ready = projects.filter((p) => p.prepared).length;
  if (!ready) return null;
  const button = h("button", { type: "button", class: "button large",
    title: "Makes the scenes, clips and video of every prepared video, one after another, without stopping for approval. No internet needed." },
  icon("play"), `Run all prepared (${ready})`);
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      const { queued } = await api("/run-prepared", { method: "POST", body: {} });
      toast(queued.length ? `Queued ${queued.length}: they run one after another.` : "Nothing to run.");
      done();
    } catch (error) {
      toast(error.message);
      button.disabled = false;
    }
  });
  return button;
}

export async function projectsView(main) {
  const projects = await api("/projects");
  main.append(h("div", { class: "page" },
    h("div", { class: "page-head" },
      h("div", {}, h("h1", {}, "Videos"), h("p", { class: "lede" }, "Every music video on this machine, newest first.")),
      h("div", { class: "row" }, runPreparedButton(projects, () => { location.reload(); }),
        h("a", { class: "button primary large", href: "#/new" }, icon("plus"), "New video"))),
    projects.length
      ? h("div", { class: "cards" }, projects.map(card),
        h("a", { class: "card new-card", href: "#/new" }, icon("plus"), h("strong", {}, "New video"), h("span", { class: "muted small" }, "Drop a song, add its lyrics and story")))
      : empty(icon("music"), "No videos yet", "Start with a song: its lyrics and story notes help, and characters' sheets you already have are reused.")));
}
