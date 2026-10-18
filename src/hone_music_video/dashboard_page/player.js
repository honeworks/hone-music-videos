// The song of a project: one audio element, its waveform peaks (decoded in the browser with the Web Audio
// API, nothing on the server) and playing exactly a slice of it (a line, a shot).

const players = new Map();
const BUCKETS = 2000;

async function loadPeaks(url) {
  try {
    const data = await (await fetch(url)).arrayBuffer();
    const buffer = await new OfflineAudioContext(1, 1, 8000).decodeAudioData(data); // 8 kHz is plenty for peaks
    const channels = Array.from({ length: buffer.numberOfChannels }, (_, n) => buffer.getChannelData(n));
    const size = channels[0].length / BUCKETS;
    const peaks = new Float32Array(BUCKETS);
    let top = 0;
    for (let b = 0; b < BUCKETS; b += 1) {
      let peak = 0;
      for (let i = Math.floor(b * size); i < Math.floor((b + 1) * size); i += 1) {
        for (const channel of channels) peak = Math.max(peak, Math.abs(channel[i]));
      }
      peaks[b] = peak;
      top = Math.max(top, peak);
    }
    return { peaks: peaks.map((p) => p / (top || 1)), duration_ms: Math.round(buffer.duration * 1000) };
  } catch (error) {
    console.warn("the song's waveform could not be drawn:", error);
    return null; // the page still works without a waveform
  }
}

// Forget watchers whose part of the page was replaced (a node made a moment ago may not be attached yet).
function prune(player) {
  const now = performance.now();
  for (const watcher of [...player.watchers]) {
    if (!watcher.node.isConnected && now - watcher.born > 2000) player.watchers.delete(watcher);
  }
}

function makePlayer(url) {
  const audio = new Audio();
  audio.preload = "metadata";
  audio.src = url;
  const player = { url, audio, sliceEnd: null, watchers: new Set(), peaks: loadPeaks(url) };
  const update = () => {
    const ms = audio.currentTime * 1000;
    if (player.sliceEnd !== null && ms >= player.sliceEnd) { audio.pause(); player.sliceEnd = null; }
    prune(player);
    for (const watcher of player.watchers) if (watcher.node.isConnected) watcher.fn(ms, !audio.paused);
  };
  const loop = () => {
    update();
    if (audio.paused) player.looping = false; else requestAnimationFrame(loop);
  };
  const tick = () => {
    update();
    if (!audio.paused && !player.looping) { player.looping = true; requestAnimationFrame(loop); }
  };
  for (const name of ["play", "pause", "seeked", "loadedmetadata"]) audio.addEventListener(name, tick);
  player.tick = tick;
  return player;
}

// The project's player, made once and kept while the page is open (switching views keeps the song).
export function songPlayer(id, url) {
  const key = String(url || "").split("?")[0];
  let player = players.get(id);
  if (!player || player.url.split("?")[0] !== key) {
    player?.audio.pause();
    player = makePlayer(url);
    players.set(id, player);
  }
  return player;
}

export function stopAll() {
  for (const player of players.values()) player.audio.pause();
}

export function seek(player, ms) {
  player.audio.currentTime = ms / 1000;
  player.tick();
}

export function toggle(player) {
  player.sliceEnd = null;
  if (player.audio.paused) player.audio.play().catch(() => {});
  else player.audio.pause();
}

// Play [start_ms, end_ms) of the song and stop there.
export function playSlice(player, startMs, endMs) {
  player.audio.currentTime = startMs / 1000;
  player.sliceEnd = endMs;
  player.audio.play().catch(() => {});
}

// Call fn(ms, playing) on every frame while playing (and on seeks) for as long as node is on the page.
export function watch(player, node, fn) {
  prune(player);
  player.watchers.add({ node, fn, born: performance.now() });
  requestAnimationFrame(() => fn(player.audio.currentTime * 1000, !player.audio.paused));
}
