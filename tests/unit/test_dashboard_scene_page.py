"""The Clips view and the scene viewer (0024 §1, §2; 0027 §7) as page logic in Node with the fake DOM: the
files the viewer shows of each kind and what Compare puts side by side, the Clips view showing clips with
the redo of a clip, and a redo from the viewer sending the same requests as the card's: a new seed, or an
edited motion prompt saved and then remade (only that clip)."""

from __future__ import annotations

from typing import Any

from tests.unit.test_dashboard_page import FAKE_DOM, run_js

VERSIONS = """
const v = (kind, url, made_at, extra = {}) =>
  ({ kind, url, made_at, from: null, in_use: false, model: "m", seed: 1, prompt: "", scene_version: null,
     ...extra });
const versions = [  // newest first, as the server sends them
  v("clip", "f1", "05", { from: "r1" }), v("raw_clip", "r1", "04", { from: "s1" }),
  v("clip", "f0", "03", { from: "r0", in_use: true }),
  v("raw_clip", "r0", "02", { from: "s0", in_use: true }),
  v("still", "s1", "01b", { scene_version: 2 }), v("still", "s0", "01", { scene_version: 1, in_use: true }),
];
"""

VIEW = """
const shot = (id) => ({ id, start_ms: 0, end_ms: 3000, beat: "the hall", cast: [], framing: "wide",
  faces: false, still_prompt: "a hall at dawn", motion_prompt: "slow push in" });
const files = {
  S001: { stills: "s1", clips: "r1", finish: "f1", versions: {} },
  S002: { versions: {} },
};
const view = { id: "song", refresh() {}, render() {}, gallery: [], selected: null,
  records: { shots: { shots: [shot("S001"), shot("S002")] }, shot_files: files, characters: {} },
  project: { status: "completed", progress: null,
             run: { status: "completed", waiting: null, stages: [{ name: "clips", status: "done" }] } } };
const labels = (node) => node.all("button").map((b) => b.text.trim()).filter(Boolean);
const card = (node, id) => node.all("article").find((a) => a.dataset.shot === id);
const srcs = (node, tag) => node.all(tag).map((x) => x.getAttribute("src"));
const shown = (node) =>
  ({ img: srcs(node, "img"), video: srcs(node, "video"), buttons: labels(node), text: node.text });
"""


def test_the_files_in_use_what_compare_shows_and_the_labels() -> None:
    found = run_js(
        "views/scene.js",
        VERSIONS
        + """
        const urls = (chain) => Object.fromEntries(Object.entries(chain).map(([k, x]) => [k, x.url]));
        const fresh = versions.map((x) => ({ ...x, in_use: false }));  // nothing chosen yet: the newest
        const steps = (chain) => [m.firstStep(chain, "frame"), m.firstStep(chain, "clip")];
        console.log(JSON.stringify([
          urls(m.chainOf(versions)), urls(m.chainOf(fresh)), urls(m.chainOf(versions.slice(4))),
          m.pairFor(m.chainOf(versions)).map((x) => x.url), m.pairFor(m.chainOf(versions.slice(4))),
          [...steps(m.chainOf(versions)), m.firstStep({}, "clip")],
          [m.versionLabel(versions[5]), m.versionLabel(v("still", "t", "")), m.versionLabel(versions[1]),
           m.versionLabel(versions[0])],
        ]));
        """,
    )
    assert found[0] == {"still": "s0", "raw_clip": "r0", "clip": "f0"}  # the ones the video uses
    assert found[1] == {"still": "s1", "raw_clip": "r1", "clip": "f1"}
    assert found[2] == {"still": "s0"}
    assert found[3] == ["r0", "f0"] and found[4] is None
    assert found[5] == ["still", "clip", "clip"]
    assert found[6] == ["start frame (scene v1)", "start frame", "raw clip", "finished clip"]


def render(module: str, fn: str) -> Any:
    return run_js(
        f"views/{module}",
        FAKE_DOM
        + VIEW
        + f"""
        const node = m.{fn}(view);
        console.log(JSON.stringify({{ S001: shown(card(node, "S001")), S002: shown(card(node, "S002")) }}));
        """,
    )


def test_the_clips_view_shows_clips_and_the_redo_of_a_clip() -> None:
    clips = render("clips.js", "clipsView")
    assert clips["S001"]["video"] == ["f1"] and "finished" in clips["S001"]["text"]
    assert clips["S002"]["video"] == [] and "waiting" in clips["S002"]["text"]
    assert any("New clip (new seed)" in b for b in clips["S001"]["buttons"])
    assert any("Remake with the edited prompt" in b for b in clips["S001"]["buttons"])
    assert not any("New clip" in b for b in clips["S002"]["buttons"])  # no start frame to animate yet
    assert "slow push in" in clips["S001"]["text"]  # the motion prompt is on the clip's card


def test_a_redo_from_the_viewer_sends_what_the_card_sends() -> None:
    found = run_js(
        "views/scene-parts.js",
        FAKE_DOM
        + VIEW
        + """
        const out = {};
        for (const where of ["card", "viewer"]) {
          posted.length = 0;
          const panel = m.redoPanel(view, shot("S001"), { where, open: where === "viewer" });
          await panel.all("button").find((b) => /New clip/.test(b.text)).fire("click");
          const send = button(panel, "Remake with the edited prompt");
          const before = send.disabled;  // nothing edited: nothing to send
          const box = panel.all("textarea")[0];
          box.value = `${box.value}, rain`; await box.fire("input");
          await send.fire("click");
          await new Promise((done) => setTimeout(done, 10));
          const sent = posted.map(([url, body]) => [url.split("/").pop(), body]);
          out[where] = [sent, before, panel.attrs.open ?? null];
        }
        console.log(JSON.stringify(out));
        """,
    )
    assert found["card"][0] == [
        ["redo-clip", {"shots": ["S001"]}],
        ["motion", {"shot": "S001", "motion_prompt": "slow push in, rain"}],
        ["remake", {}],
    ]
    assert found["card"][1] is True
    assert found["viewer"][0] == found["card"][0]
    assert found["viewer"][2] == "" and found["card"][2] is None  # the viewer's opens at once
