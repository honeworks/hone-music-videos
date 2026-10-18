// The sidebar: every project with a small thumbnail, a status dot, where its run stands and, while it
// runs, its stage's bar and the time left (0003).

import { api, h, runWhere } from "./core.js";
import { icon } from "./icons.js";
import { cardBar } from "./progress.js";

export async function refreshSidebar() {
  const list = document.getElementById("project-list");
  let projects = [];
  try { projects = await api("/projects"); } catch { return; }
  const current = location.hash.split("/")[2];
  list.replaceChildren(...projects.map((p) => h("li", {},
    h("a", { class: "project-link", href: `#/p/${p.id}`, "aria-current": p.id === current ? "page" : null },
      h("span", { class: "mini-thumb" }, p.thumbnail ? h("img", { src: p.thumbnail, alt: "", loading: "lazy" }) : icon("music")),
      h("span", { class: "grow" }, h("span", { class: "name", title: p.name }, p.name),
        h("span", { class: "where" }, h("span", { class: `dot ${p.status}` }), runWhere(p)), cardBar(p))))));
  if (!projects.length) list.append(h("li", { class: "sidebar-foot" }, "No videos yet."));
}
