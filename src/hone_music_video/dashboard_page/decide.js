// The controls of a gate the owner decides (0018, D-111, D-112), the same on the gate's own page and on
// the Overview: a note box always shown, then Approve and "Reject with note" side by side, with what
// rejecting does at this gate. "Reject with note" waits for a note; Approve with a note written asks
// first. The note is kept per project and gate (in memory, and in localStorage when it can be used) until
// the decision is sent, so a redraw of the view (every server-sent event) keeps it, and its focus.

import { api, GATE_NAMES, h, humanize, toast } from "./core.js";
import { icon } from "./icons.js";

// What rejecting does at each gate: the action it posts, its button and what it does, in words. A gate
// missing here takes no note (`review_scenes`: each scene is changed in the Scenes view).
export const REJECTS = {
  review_lyrics: {
    action: "reject", label: "Reject with note", iconName: "lyrics",
    help: "Reject runs the lyrics editor again with your note: words, lines and sections. It never moves a time; to fix timing, edit the lines' times in the Lyrics view and save them.",
    placeholder: "What should change? For example: L004 belongs to the chorus; split L007 after the third word.",
    done: "The lyrics stage runs again with your note.",
  },
  review_plan: {
    action: "reject", label: "Reject with note", iconName: "plan",
    help: "Reject plans again with your note: the story, the shot list and every prompt, in several calls. The project file is written again; nothing has been drawn yet.",
    placeholder: "What should change? For example: more close-ups of Celina in the chorus; S007 happens at night.",
    done: "The plan is made again with your note.",
  },
};
const NO_NOTE = {
  review_scenes: "This gate takes no note: change a scene in the Scenes view (edit it, mark it to run, pick or use another version); approve takes every scene as it is.",
};

// ---------------------------------------------------------------------------- the note, kept per gate

const notes = new Map();
const noteKey = (id, gate) => `note:${id}:${gate}`;

export function noteFor(id, gate) {
  const key = noteKey(id, gate);
  if (notes.has(key)) return notes.get(key);
  try { return localStorage.getItem(key) || ""; } catch { return ""; } // a private window, or no browser
}

export function keepNote(id, gate, text) {
  const key = noteKey(id, gate);
  notes.set(key, text);
  try {
    if (text) localStorage.setItem(key, text); else localStorage.removeItem(key);
  } catch { /* kept in memory only */ }
}

// ---------------------------------------------------------------------------- asking before Approve

// "You wrote a note. Reject with it instead?": resolves to "reject", "approve" or "cancel".
export function askNote(reject) {
  return new Promise((resolve) => {
    const dialog = h("dialog", { class: "note-dialog", "aria-labelledby": "note-dialog-title" });
    const answer = (choice) => () => { dialog.close(); dialog.remove(); resolve(choice); };
    dialog.addEventListener("cancel", (event) => { event.preventDefault(); answer("cancel")(); });
    dialog.append(h("h3", { id: "note-dialog-title" }, "You wrote a note. Reject with it instead?"),
      h("p", { class: "muted small" }, reject.help),
      h("div", { class: "row wrap" },
        h("button", { type: "button", class: "button primary", onclick: answer("reject") }, icon(reject.iconName), reject.label),
        h("button", { type: "button", class: "button", onclick: answer("approve") }, icon("check"), "Approve anyway"),
        h("button", { type: "button", class: "button ghost", onclick: answer("cancel") }, "Cancel")));
    document.body.append(dialog);
    dialog.showModal();
  });
}

// ---------------------------------------------------------------------------- the controls

// The default Approve: the gate as it is.
const approveGate = (gate) => ({
  label: "Approve", path: "approve", body: () => ({ gate }),
  done: `${GATE_NAMES[gate] || humanize(gate)}: approved. The run continues.`,
});

// POST one action to the project with its button disabled meanwhile; says it is done, or why not.
export async function send(ctx, button, path, body, done) {
  button.disabled = true;
  try {
    await api(`/projects/${ctx.id}/${path}`, { method: "POST", body });
    toast(typeof done === "function" ? done(body) : done);
    return true;
  } catch (error) {
    toast(error.message);
    button.disabled = false;
    return false;
  }
}

function noteBox(ctx, gate, reject) {
  const key = noteKey(ctx.id, gate);
  const box = h("textarea", { rows: 2, class: "gate-note", placeholder: reject.placeholder, "aria-label": `Your note: ${reject.label}`, dir: "auto", dataset: { note: key } });
  box.value = noteFor(ctx.id, gate);
  const was = document.activeElement;
  if (was?.dataset?.note === key) { // the view was redrawn while the owner typed: keep the caret there
    const [start, end] = [was.selectionStart, was.selectionEnd];
    requestAnimationFrame(() => { box.focus(); box.setSelectionRange(start, end); });
  }
  return box;
}

// gateControls(ctx, gate, {approvable, approve: {label, path, body() -> object | null, done(body) | text},
// extra, ask})
export function gateControls(ctx, gate, { approvable = true, approve = approveGate(gate), extra = null, ask = askNote } = {}) {
  const reject = REJECTS[gate];
  const box = reject ? noteBox(ctx, gate, reject) : null;
  const note = () => box?.value.trim() || "";
  const rejectButton = reject ? h("button", { type: "button", class: "button" }, icon(reject.iconName), reject.label) : null;
  const approveButton = approvable ? h("button", { type: "button", class: "button primary large" }, icon("check"), approve.label) : null;
  const fits = () => { if (rejectButton) rejectButton.disabled = !reject.optional && !note(); };
  const decided = (sent) => { if (sent) { keepNote(ctx.id, gate, ""); ctx.refresh(); } };
  const sendReject = async () => decided(await send(ctx, rejectButton, reject.action, { gate, note: note() }, reject.done));
  box?.addEventListener("input", () => { keepNote(ctx.id, gate, box.value); fits(); });
  rejectButton?.addEventListener("click", sendReject);
  approveButton?.addEventListener("click", async () => {
    const choice = note() ? await ask(reject) : "approve";
    if (choice === "reject") return sendReject();
    if (choice !== "approve") return;
    const body = approve.body();
    if (body !== null) decided(await send(ctx, approveButton, approve.path, body, approve.done));
  });
  fits();
  return h("div", { class: "gate-controls" }, box,
    h("div", { class: "gate-buttons" }, approveButton, rejectButton, extra),
    h("p", { class: "muted small" }, reject ? reject.help : NO_NOTE[gate] || null));
}
