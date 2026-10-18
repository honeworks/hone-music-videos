// The bell's sound (D-097): a two-note chime made with the Web Audio API (no audio file), repeated for
// 15 seconds. Browsers keep audio locked until the owner interacts with the page, so the sound is
// "enabled" by a click (remembered in localStorage) and unlocked again by the first click or key of each
// visit; muting is remembered too.

export const RING_MS = 15000;
const NOTES = [880, 698.46]; // A5 then F5: a door-chime "ding-dong"
const PARTIALS = [[1, 1], [2, 0.42], [3, 0.2], [4.2, 0.08]]; // frequency ratio, loudness: bell-like
const EVERY_S = 2.5;

let context = null;
let ringing = null; // the master gain of the ring playing now
let onChange = () => {}; // the bell's redraw

export function stored(key) {
  try { return localStorage.getItem(key); } catch { return null; } // a private window, blocked storage
}

export function store(key, value) {
  try {
    if (value === null) localStorage.removeItem(key); else localStorage.setItem(key, value);
  } catch { /* the choice then lasts for this visit only */ }
}

const changed = () => onChange();

export function onSoundChange(listener) {
  onChange = listener;
}

export const isMuted = () => stored("bell.muted") === "1";
// Locked: the browser has not let this page play sound yet (no click on it since it opened).
export const isLocked = () => !context || context.state !== "running";

// The AudioContext, created and resumed from a click or key press (the browser allows it then).
// Resolves once the browser has said yes or no.
export function unlock() {
  const Context = window.AudioContext || window.webkitAudioContext;
  if (!Context) return Promise.resolve();
  if (!context) {
    context = new Context();
    context.addEventListener("statechange", changed);
  }
  store("bell.enabled", "1");
  return context.resume().then(changed, changed);
}

export function setMuted(muted) {
  store("bell.muted", muted ? "1" : null);
  if (muted) stopRing();
  changed();
}

// One struck note: a few sine partials that fade out together.
function strike(at, frequency, out) {
  for (const [ratio, loudness] of PARTIALS) {
    const oscillator = context.createOscillator();
    const gain = context.createGain();
    oscillator.frequency.value = frequency * ratio;
    gain.gain.setValueAtTime(0.0001, at);
    gain.gain.exponentialRampToValueAtTime(loudness, at + 0.01);
    gain.gain.exponentialRampToValueAtTime(0.0001, at + 1.8 / ratio ** 0.3);
    oscillator.connect(gain).connect(out);
    oscillator.start(at);
    oscillator.stop(at + 2);
  }
}

// The chime, repeated for `ms` and a little more (15 s for a wait; 0 is one chime, to confirm the sound is
// on); nothing when muted or locked.
export function ring(ms = RING_MS) {
  stopRing();
  if (isMuted() || isLocked()) return;
  const out = context.createGain();
  out.gain.value = 0.18;
  out.connect(context.destination);
  const start = context.currentTime + 0.05;
  for (let t = 0; t * 1000 <= ms; t += EVERY_S) NOTES.forEach((note, n) => strike(start + t + n * 0.45, note, out));
  ringing = out;
}

export function stopRing() {
  if (!ringing) return;
  ringing.gain.cancelScheduledValues(0);
  ringing.disconnect();
  ringing = null;
}

// A visit after sound was enabled: a click or key press anywhere unlocks it again (tried on each one until
// the browser lets it: a touch or Escape may not count).
export function rememberSound() {
  if (stored("bell.enabled") !== "1") return;
  const kinds = ["pointerdown", "click", "keydown"];
  const again = () => unlock().then(() => {
    if (!isLocked()) kinds.forEach((kind) => removeEventListener(kind, again, true));
  });
  kinds.forEach((kind) => addEventListener(kind, again, true));
}
