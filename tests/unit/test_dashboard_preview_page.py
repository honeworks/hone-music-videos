"""The Preview (0024 §3, case 48) as page logic in Node with the fake DOM: each shot's best file of the take
(finished clip, raw clip, start frame, nothing; 0027), the shot at a moment of the song, where a
clip is and when it holds its last frame, and a file that arrives changing the shot's choice on the screen
while the song plays on."""

from __future__ import annotations

from tests.unit.test_dashboard_page import FAKE_DOM, run_js


def test_the_best_file_is_the_furthest_one_the_take_in_use_has() -> None:
    found = run_js(
        "views/preview.js",
        """
        const all = { stills: "s", clips: "r", finish: "f" };
        const without = (...keys) =>
          Object.fromEntries(Object.entries(all).filter(([k]) => !keys.includes(k)));
        console.log(JSON.stringify([
          m.bestFile(all), m.bestFile(without("finish")), m.bestFile(without("finish", "clips")),
          m.bestFile({}), m.bestFile(undefined),
        ]));
        """,
    )
    assert found == [
        {"kind": "finished", "src": "f", "video": True},
        {"kind": "raw", "src": "r", "video": True},
        {"kind": "frame", "src": "s", "video": False},
        {"kind": "none", "src": None, "video": False},
        {"kind": "none", "src": None, "video": False},
    ]


def test_the_shot_at_a_moment_and_where_its_clip_is() -> None:
    found = run_js(
        "views/preview.js",
        """
        const shots = [{ start_ms: 0, end_ms: 2000 }, { start_ms: 2000, end_ms: 5000 }];
        console.log(JSON.stringify([
          [0, 1999, 2000, 4999, 5000].map((ms) => m.shotAt(shots, ms)),
          m.clipTime(shots[1], 3000, 2.5), m.clipTime(shots[1], 4600, 2.5), m.clipTime(shots[1], 3000, 0),
        ]));
        """,
    )
    assert found[0] == [0, 0, 1, 1, -1]
    assert found[1] == {"at": 1, "hold": False}
    assert found[2] == {"at": 2.46, "hold": True}  # a clip shorter than its shot holds its last frame
    assert found[3] == {"at": 1, "hold": False}  # the clip's length is not known yet


def test_a_file_that_arrives_changes_the_shots_choice_on_the_screen() -> None:
    found = run_js(
        "views/preview.js",
        FAKE_DOM
        + """
        const files = { S001: {}, S002: {} };
        const view = { id: "song", player: { audio: { pause() {} } }, records: {
          shots: { shots: [{ id: "S001", start_ms: 0, end_ms: 2000, beat: "the gate" },
                           { id: "S002", start_ms: 2000, end_ms: 5000, beat: "the hall" }] },
          shot_files: files, timeline: { lines: [{ start_ms: 2100, end_ms: 4000, text: "a line" }] } } };
        const c = m.screenOf(view);
        const [picture, video] = [c.node.all("img")[0], c.node.all("video")[0]];
        const src = (node) => node.getAttribute("src");
        const seen = () => [c.node.dataset.kind, src(picture), src(video), c.node.text];
        const out = [];
        c.frame(500, true); out.push(seen());
        c.frame(2500, true); out.push(seen());
        files.S002 = { stills: "s2" }; c.frame(2600, true); out.push(seen());
        files.S002.clips = "r2"; c.frame(2700, true); out.push([...seen(), video.paused]);
        files.S002.finish = "f2"; c.frame(2800, false); out.push([...seen(), video.paused]);
        console.log(JSON.stringify(out));
        """,
    )
    assert found[0][0] == "none" and "S001" in found[0][3] and "the gate" in found[0][3]
    assert found[1][:3] == ["none", None, None] and "a line" in found[1][3]
    assert found[2][:2] == ["frame", "s2"]
    assert found[3][:3] == ["raw", "s2", "r2"] and found[3][4] is False  # plays with the song
    assert found[4][:3] == ["finished", "s2", "f2"] and found[4][4] is True  # the song paused: so is the clip
