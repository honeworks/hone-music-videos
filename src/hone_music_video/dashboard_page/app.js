// The page's routes: #/ (Projects), #/new (New video), #/p/<id>[/<view>] (a project and its views),
// the sidebar with every project, and the bell when a project waits for the owner (bell.js).

import { watchWaits } from "./bell.js";
import { isDark, savedTheme, setTheme } from "./core.js";
import { icon } from "./icons.js";
import { refreshSidebar } from "./sidebar.js";
import { projectsView } from "./views/projects.js";
import { newVideoView } from "./views/new.js";
import { projectView } from "./views/project.js";

let leave = () => {};
let open = null; // the project shown: another of its views is drawn without leaving it

function themeButton() {
  const button = document.getElementById("theme");
  const draw = () => button.replaceChildren(icon(isDark() ? "sun" : "moon"));
  button.addEventListener("click", () => { setTheme(isDark() ? "light" : "dark"); draw(); });
  const saved = savedTheme();
  if (saved) document.documentElement.dataset.theme = saved;
  draw();
}

async function show() {
  const main = document.getElementById("main");
  const [, first, id, view, ...rest] = location.hash.replace(/^#/, "").split("/").map((p) => {
    try { return decodeURIComponent(p); } catch { return p; }
  });
  if (first === "p" && id && id === open && leave.update) {
    leave.update(view || "overview", rest);
    return;
  }
  leave();
  leave = () => {};
  open = first === "p" ? id : null;
  for (const link of document.querySelectorAll("[data-nav]")) {
    const on = link.dataset.nav === (first === "new" ? "new" : first ? "" : "projects");
    if (on) link.setAttribute("aria-current", "page"); else link.removeAttribute("aria-current");
  }
  main.replaceChildren();
  refreshSidebar();
  if (first === "new") await newVideoView(main);
  else if (first === "p" && id) leave = (await projectView(main, id, view || "overview", rest)) || leave;
  else await projectsView(main);
  main.focus({ preventScroll: true });
}

document.getElementById("brand-logo").append(icon("logo"));
document.getElementById("new-video").append(icon("plus"), "New video");
themeButton();
watchWaits();
addEventListener("hashchange", show);
show();
