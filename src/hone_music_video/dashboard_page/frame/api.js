// The frame workspace's API (0027 §6): Hone Frame's routes, mounted under /api/projects/<video>/frame.
// Every failure becomes an ApiError whose message says what happened and whose `items` name the items a 400
// answer refused. `p` is the music video project's id; the server finds its frame project.
// Hone Frame: ported from dashboard_page/api.js. A file is sent as JSON ({name, data_b64}) instead of
// multipart/form-data, and the workspace's routes (models, guide) are asked through the project; the
// project list, imports and exports are not here (the plan writes the project file).

import { readFile } from "../core.js";

export class ApiError extends Error {
  constructor(status, body) {
    super((body && body.error) || `The server answered ${status}.`);
    this.status = status;
    this.items = (body && Array.isArray(body.items)) ? body.items : [];
  }
}

async function request(method, path, body) {
  const init = { method, headers: { Accept: "application/json" } };
  if (body !== undefined) {
    init.headers["Content-Type"] = "application/json";
    init.body = JSON.stringify(body);
  }
  let response;
  try {
    response = await fetch(path, init);
  } catch {
    throw new ApiError(0, { error: "The dashboard server did not answer. Is `hone-music-video dashboard` still running?" });
  }
  const text = await response.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { data = { error: text.slice(0, 300) }; }
  if (!response.ok) throw new ApiError(response.status, data);
  return data;
}

const e = encodeURIComponent;
const P = (p) => `/api/projects/${e(p)}/frame`;
const I = (p, item) => `${P(p)}/items/${e(item)}`;
let video = null; // the open video project: the workspace's routes are asked through it

export const api = {
  open: (p) => { video = p; },
  project: (p) => request("GET", P(p)),
  file: (p) => request("GET", `${P(p)}/file`),
  putFile: (p, text) => request("PUT", `${P(p)}/file`, { text }),
  patchItem: (p, item, fields) => request("PATCH", I(p, item), fields),
  dependants: (p, item) => request("GET", `${I(p, item)}/dependants`),
  mark: (p, item, dependants) => request("POST", `${I(p, item)}/mark`, { dependants }),
  unmark: (p, item) => request("POST", `${I(p, item)}/unmark`, {}),
  runPrompt: (p, item, prompt) => request("POST", `${I(p, item)}/run-prompt`, { prompt }),
  accept: (p, item, version) => request("POST", `${I(p, item)}/accept`, version == null ? {} : { version }),
  useVersion: (p, item, version, dependants) => request("POST", `${I(p, item)}/use-version`, { version, dependants }),
  async replaceFile(p, item, file, dependants) {
    return request("POST", `${I(p, item)}/file`, { file: await readFile(file), dependants: dependants ? "true" : "false" });
  },
  runAction: (p, action) => request("POST", `${P(p)}/${action}`, {}),
  models: () => request("GET", `${P(video)}/models`),
  guide(models) {
    const query = new URLSearchParams();
    if (models && models.length) query.set("models", models.join(","));
    else query.set("project", "this"); // the server puts the frame project's id in its place
    return request("GET", `${P(video)}/guide?${query}`);
  },
  events: (p) => request("GET", `${P(p)}/events`), // the frame project's past events, oldest first
};
