// Sheets: the project's sheets (cast, turnarounds, place boards, storyboard), composed with Pillow when their
// images are done.
// Hone Frame: ported from dashboard_page/screens/sheets.js, without the exports (the video is the export).

import { on, state } from "../state.js";
import { h, itemHref, ITEM_STATUS, pill, setImage } from "../ui.js";

export async function mount(body, route) {
  const projectId = route.project;
  const sheetList = h("ul", { class: "sheet-list" });

  function drawSheets() {
    const sheets = state.project.items.filter((it) => it.kind === "sheet");
    sheetList.replaceChildren(...(sheets.length ? sheets.map((it) => {
      const thumb = h("a", { class: "thumb-holder big", href: itemHref(projectId, it.id) });
      setImage(thumb, it.thumb, it.id);
      const images = it.images;
      return h("li", { class: "sheet-card" }, thumb,
        h("div", {}, h("a", { href: itemHref(projectId, it.id) }, h("strong", {}, it.id)), " ", pill("item", it.status, ITEM_STATUS),
          h("p", { class: "caption" }, [it.layout, images.length ? `${images.length} images: ${images.join(", ")}` : null].filter(Boolean).join(" · ")),
          it.current ? h("a", { class: "button small ghost", href: it.versions.find((v) => v.n === it.current)?.url, target: "_blank", rel: "noopener" }, "Full size") : null));
    }) : [h("li", { class: "muted" }, "No sheets in this project. Add a [sheets.<name>] table to the project file.")]));
  }

  body.replaceChildren(h("div", { class: "page-body" }, h("section", { class: "panel" }, h("h2", {}, "Sheets"), sheetList)));
  drawSheets();
  const offs = [on("item", drawSheets), on("project", drawSheets)];
  return { unmount: () => offs.forEach((off) => off()) };
}
