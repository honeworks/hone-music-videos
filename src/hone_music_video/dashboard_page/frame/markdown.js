// A small, safe Markdown renderer for the guide: headings, paragraphs, lists, code, quotes, tables, rules,
// and inline code, bold, italic and links. It builds DOM nodes; text is never parsed as HTML, and a link is
// kept only when it is http(s), relative or an anchor.

import { h } from "./ui.js";

const SAFE_URL = /^(https?:\/\/|#|\/(?!\/)|\.{1,2}\/|[\w-]+(\.[\w-]+)*(#[\w-]*)?$)/i;
const INLINE = /(`+)([\s\S]*?)\1|\*\*([^*]+)\*\*|__([^_]+)__|\*([^*\s][^*]*)\*|_([^_\s][^_]*)_|\[([^\]]+)\]\(([^)\s]+)\)/g;

export function slug(text) {
  return text.toLowerCase().replace(/[^\w\s-]/g, "").trim().replace(/\s+/g, "-");
}

export function inline(text) {
  const out = [];
  let last = 0;
  for (const m of text.matchAll(INLINE)) {
    if (m.index > last) out.push(text.slice(last, m.index));
    if (m[1]) out.push(h("code", {}, m[2]));
    else if (m[3] || m[4]) out.push(h("strong", {}, inline(m[3] || m[4])));
    else if (m[5] || m[6]) out.push(h("em", {}, inline(m[5] || m[6])));
    else if (SAFE_URL.test(m[8])) {
      const external = /^https?:/i.test(m[8]);
      const anchor = m[8].startsWith("#") ? m[8].slice(1) : null; // the page's routes live in the hash
      out.push(h("a", {
        href: m[8], target: external ? "_blank" : null, rel: external ? "noopener noreferrer" : null,
        onclick: anchor ? (e) => { e.preventDefault(); document.getElementById(anchor)?.scrollIntoView(); } : null,
      }, inline(m[7])));
    } else out.push(m[7]);
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

const LIST = /^(\s*)([-*+]|\d+[.)])\s+(.*)$/;
const cells = (line) => line.trim().replace(/^\||\|$/g, "").split("|").map((c) => c.trim());

function list(lines, start) {
  const base = lines[start].match(LIST)[1].length;
  const ordered = /\d/.test(lines[start].match(LIST)[2]);
  const el = h(ordered ? "ol" : "ul");
  let i = start;
  while (i < lines.length) {
    const m = lines[i].match(LIST);
    if (!m || m[1].length < base || (m[1].length === base && /\d/.test(m[2]) !== ordered)) break;
    if (m[1].length > base) {
      const [nested, next] = list(lines, i);
      (el.lastElementChild || el.appendChild(h("li"))).append(nested);
      i = next;
      continue;
    }
    const li = h("li", {}, inline(m[3]));
    i += 1;
    while (i < lines.length && lines[i].trim() && !LIST.test(lines[i]) && /^\s{2,}/.test(lines[i])) {
      li.append(" ", ...inline(lines[i].trim()));
      i += 1;
    }
    el.append(li);
  }
  return [el, i];
}

function table(lines, start) {
  const head = cells(lines[start]);
  const rows = [];
  let i = start + 2;
  while (i < lines.length && lines[i].includes("|") && lines[i].trim()) rows.push(cells(lines[i++]));
  const el = h("div", { class: "table-wrap" }, h("table", {},
    h("thead", {}, h("tr", {}, head.map((c) => h("th", { scope: "col" }, inline(c))))),
    h("tbody", {}, rows.map((r) => h("tr", {}, r.map((c) => h("td", {}, inline(c))))))));
  return [el, i];
}

const STARTS_BLOCK = (line, next) => /^(#{1,6}\s|```|>|\s*([-*+]|\d+[.)])\s|(-{3,}|\*{3,})\s*$)/.test(line)
  || (line.includes("|") && next !== undefined && /^\s*\|?\s*:?-{3,}/.test(next));

export function render(markdown) {
  const lines = String(markdown || "").replace(/\r\n?/g, "\n").split("\n");
  const frag = document.createDocumentFragment();
  let i = 0;
  while (i < lines.length) {
    const line = lines[i];
    if (!line.trim()) { i += 1; continue; }
    const heading = line.match(/^(#{1,6})\s+(.*?)\s*#*$/);
    if (heading) {
      frag.append(h(`h${heading[1].length}`, { id: slug(heading[2]) }, inline(heading[2])));
      i += 1;
    } else if (line.startsWith("```")) {
      const lang = line.slice(3).trim();
      const body = [];
      i += 1;
      while (i < lines.length && !lines[i].startsWith("```")) body.push(lines[i++]);
      i += 1;
      frag.append(h("pre", {}, h("code", { "data-lang": lang || null }, body.join("\n"))));
    } else if (/^(-{3,}|\*{3,})\s*$/.test(line)) {
      frag.append(h("hr"));
      i += 1;
    } else if (line.startsWith(">")) {
      const body = [];
      while (i < lines.length && lines[i].startsWith(">")) body.push(lines[i++].replace(/^>\s?/, ""));
      frag.append(h("blockquote", {}, render(body.join("\n"))));
    } else if (LIST.test(line)) {
      const [el, next] = list(lines, i);
      frag.append(el);
      i = next;
    } else if (line.includes("|") && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1] || "")) {
      const [el, next] = table(lines, i);
      frag.append(el);
      i = next;
    } else {
      const body = [line.trim()];
      i += 1;
      while (i < lines.length && lines[i].trim() && !STARTS_BLOCK(lines[i], lines[i + 1])) body.push(lines[i++].trim());
      frag.append(h("p", {}, inline(body.join(" "))));
    }
  }
  return frag;
}
