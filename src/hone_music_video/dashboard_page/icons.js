// Inline SVG icons (24 x 24, stroked), so the page needs no icon font and works offline.

import { s } from "./core.js";

const PATHS = {
  logo: ["M3 12h2", "M7 8v8", "M11 4v16", "M15 7v10", "M19 10v4"],
  plus: ["M12 5v14", "M5 12h14"],
  play: ["M7 4.5v15l12.5-7.5z"],
  pause: ["M7 5h3.5v14H7z", "M13.5 5H17v14h-3.5z"],
  check: ["M5 12.5l4.5 4.5L19 7.5"],
  x: ["M6 6l12 12", "M18 6L6 18"],
  hand: ["M8 13V5.5a1.5 1.5 0 0 1 3 0V12", "M11 11V4a1.5 1.5 0 0 1 3 0v7", "M14 11V5.5a1.5 1.5 0 0 1 3 0V14a6 6 0 0 1-6 6h-.5a6 6 0 0 1-4.6-2.2L3.6 15a1.5 1.5 0 0 1 2.3-1.9L8 15"],
  sun: ["M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8z", "M12 2v2", "M12 20v2", "M4.9 4.9l1.4 1.4", "M17.7 17.7l1.4 1.4", "M2 12h2", "M20 12h2", "M4.9 19.1l1.4-1.4", "M17.7 6.3l1.4-1.4"],
  moon: ["M20 14.5A8 8 0 1 1 9.5 4a6.5 6.5 0 0 0 10.5 10.5z"],
  overview: ["M3 13h4l3-8 4 14 3-6h4"],
  lyrics: ["M4 6h16", "M4 11h11", "M4 16h14", "M4 21h8"],
  cast: ["M9 11a4 4 0 1 0 0-8 4 4 0 0 0 0 8z", "M2 21v-1a6 6 0 0 1 6-6h2a6 6 0 0 1 6 6v1", "M16 3.5a4 4 0 0 1 0 7.5", "M22 21v-1a6 6 0 0 0-4-5.6"],
  shots: ["M3 5h18v14H3z", "M8 5v14", "M16 5v14", "M3 12h5", "M16 12h5"],
  plan: ["M3 5h18v14H3z", "M8 5v14", "M16 5v14", "M3 12h5", "M16 12h5"], // the Plan view (0027)
  storyboard: ["M3 3h8v8H3z", "M13 3h8v8h-8z", "M3 13h8v8H3z", "M13 13h8v8h-8z"],
  scenes: ["M3 3h8v8H3z", "M13 3h8v8h-8z", "M3 13h8v8H3z", "M13 13h8v8h-8z"], // the Scenes view (0027)
  video: ["M3 6h13v12H3z", "M16 10l5-3v10l-5-3"],
  clips: ["M3 3h18v18H3z", "M7 3v18", "M17 3v18", "M3 8h4", "M3 16h4", "M17 8h4", "M17 16h4"],
  preview: ["M2 12s3.5-7 10-7 10 7 10 7-3.5 7-10 7S2 12 2 12z", "M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"],
  download: ["M12 3v12", "M7 10l5 5 5-5", "M4 20h16"],
  clock: ["M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z", "M12 7v5l3 2"],
  music: ["M9 18V5l11-2v13", "M6 21a3 3 0 1 0 0-6 3 3 0 0 0 0 6z", "M17 19a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"],
  image: ["M3 4h18v16H3z", "M8.5 10a1.5 1.5 0 1 0 0-3 1.5 1.5 0 0 0 0 3z", "M21 15l-5-5L5 20"],
  film: ["M3 3h18v18H3z", "M7 3v18", "M17 3v18", "M3 8h4", "M3 16h4", "M17 8h4", "M17 16h4"],
  alert: ["M12 3l10 18H2z", "M12 10v4", "M12 17.5v.5"],
  info: ["M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z", "M12 11v5", "M12 7.5v.5"],
  upload: ["M12 15V3", "M7 8l5-5 5 5", "M4 20h16"],
  layers: ["M12 3l9 5-9 5-9-5z", "M3 13l9 5 9-5"],
  sparkle: ["M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8z", "M19 16l.7 2.3L22 19l-2.3.7L19 22l-.7-2.3L16 19l2.3-.7z"],
  camera: ["M4 7h3l2-3h6l2 3h3v13H4z", "M12 17a4 4 0 1 0 0-8 4 4 0 0 0 0 8z"],
  arrow: ["M5 12h14", "M13 6l6 6-6 6"],
  expand: ["M14 4h6v6", "M20 4l-7 7", "M10 20H4v-6", "M4 20l7-7"],
  left: ["M15 5l-7 7 7 7"],
  right: ["M9 5l7 7-7 7"],
  external: ["M14 4h6v6", "M20 4l-9 9", "M18 14v6H4V6h6"],
  bell: ["M6 16v-5a6 6 0 0 1 12 0v5l2 2H4z", "M10 21a2 2 0 0 0 4 0"],
  "bell-off": ["M6 16v-5a6 6 0 0 1 12 0v5l2 2H4z", "M10 21a2 2 0 0 0 4 0", "M3 3l18 18"],
  activity: ["M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18z", "M12 7v5h4"],
};

export function icon(name, extra = "") {
  return s("svg", { class: `svg ${extra}`.trim(), viewBox: "0 0 24 24", "aria-hidden": "true" },
    (PATHS[name] || PATHS.info).map((d) => s("path", { d })));
}
