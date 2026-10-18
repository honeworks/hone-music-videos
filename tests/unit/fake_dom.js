// A stand-in for the few DOM calls the gate controls make (0018), for the page logic tests: elements with
// children, attributes, listeners and a value; `fetch` records what is posted and answers {}.
class Node {
  constructor(tag) { Object.assign(this, { tag, children: [], attrs: {}, dataset: {}, style: {}, on: {}, value: "", disabled: false, paused: true, currentTime: 0 }); }
  append(...nodes) { this.children.push(...nodes); }
  setAttribute(key, value) { this.attrs[key] = value; }
  addEventListener(type, fn) { (this.on[type] ||= []).push(fn); }
  async fire(type) { for (const fn of this.on[type] || []) await fn({ preventDefault() {} }); }
  get text() { return this.children.map((c) => c.text ?? "").join(""); }
  all(tag) { return [this, ...this.children.flatMap((c) => c.all ? c.all(tag) : [])].filter((n) => n.tag === tag); }
  focus() { document.activeElement = this; }
  setSelectionRange(start, end) { Object.assign(this, { selectionStart: start, selectionEnd: end }); }
  // what the Storyboard, Clips and Preview views use too (0024)
  getAttribute(key) { return this.attrs[key] ?? null; }
  removeAttribute(key) { delete this.attrs[key]; }
  get src() { return this.attrs.src ?? ""; }
  set src(value) { this.attrs.src = value; }
  replaceChildren(...nodes) { this.children = nodes; }
  get textContent() { return this.text; }
  set textContent(text) { this.children = [new Text(text)]; }
  get classList() { const names = () => new Set(String(this.attrs.class || "").split(" ").filter(Boolean));
    return { add: (n) => { this.attrs.class = [...names().add(n)].join(" "); }, remove: (n) => { const s = names(); s.delete(n); this.attrs.class = [...s].join(" "); }, contains: (n) => names().has(n) }; }
  play() { this.paused = false; return Promise.resolve(); }
  pause() { this.paused = true; }
}
class Text extends Node { constructor(text) { super("#text"); this.content = text; } get text() { return this.content; } }
globalThis.Node = Node;
globalThis.document = { activeElement: null, createElement: (t) => new Node(t), createElementNS: (_, t) => new Node(t),
  createTextNode: (t) => new Text(t), getElementById: () => new Node("div") };
globalThis.requestAnimationFrame = (fn) => fn();
const posted = [];
globalThis.fetch = async (url, { method, body }) => { posted.push([url, JSON.parse(body)]); return { ok: true, json: async () => ({}) }; };
const ctx = { id: "song", refreshed: 0, refresh() { this.refreshed += 1; } };
const button = (node, label) => node.all("button").find((b) => b.text.includes(label));
