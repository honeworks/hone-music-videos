"""The dashboard page's own logic (0016), run in Node with no browser: when the bell rings for a wait, the
mood words, the pace choices from a stubbed settings reply, the settings the New video form sends (0027:
the scenes' image models), and the gates' controls. The page's modules touch the DOM only when called, so
these functions import as they are."""

import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

import hone_music_video as hmv
from hone_music_video.settings import parse_settings

PAGE = Path(hmv.__file__).parent / "dashboard_page"
NODE = shutil.which("node")
pytestmark = pytest.mark.skipif(NODE is None, reason="needs Node.js to run the page's modules")


def run_js(module: str, body: str) -> Any:
    """Import `module` (a path under dashboard_page) as `m`, run `body`, and return what it prints as JSON."""
    script = f"import * as m from {json.dumps((PAGE / module).as_uri())};\n{body}"
    found = subprocess.run(
        [str(NODE), "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert found.returncode == 0, found.stderr
    return json.loads(found.stdout)


def test_a_wait_rings_once_after_two_polls_and_again_at_the_next_gate() -> None:
    polls = run_js(
        "bell.js",
        """
        const project = (id, waiting, status = waiting ? "awaiting_review" : "running") =>
          ({ id, name: id.toUpperCase(), waiting, status });
        const polls = [
          [project("a", null)],
          [project("a", "review_lyrics"), project("b", null, "awaiting_review")],
          [project("a", "review_lyrics"), project("b", null, "awaiting_review")],
          [project("a", "review_lyrics"), project("b", null, "awaiting_review")],
          [project("a", null), project("b", null, "completed")],
          [project("a", "review_plan")],
          [project("a", "review_plan")],
          [project("a", "review_lyrics")],
          [project("a", "review_lyrics")],
        ];
        let seen = new Set(), rung = new Set();
        const out = [];
        for (const projects of polls) {
          const waits = m.waitsOf(projects);
          const next = m.nextWaits(waits, seen, rung);
          ({ seen, rung } = next);
          out.push({ ring: next.ring.map((w) => `${w.name}: ${w.gate}`), rung: [...rung] });
        }
        console.log(JSON.stringify(out));
        """,
    )
    assert [p["ring"] for p in polls] == [
        [],
        [],  # seen once: an unattended run may pass it on its own
        ["A: Review the timed lyrics", "B: review"],
        [],  # not again on every poll
        [],
        [],
        ["A: Review the plan"],  # the next gate
        [],
        ["A: Review the timed lyrics"],  # the same gate waiting again after it ended
    ]
    assert polls[3]["rung"] == ["a:review_lyrics", "b:review"]
    assert polls[4]["rung"] == []  # waits that ended are forgotten


def test_a_wait_rung_before_the_page_was_opened_again_does_not_ring() -> None:
    found = run_js(
        "bell.js",
        """
        const projects = [{ id: "a", name: "A", waiting: "review_lyrics", status: "awaiting_review" },
          { id: "b", name: "B", waiting: null, status: "waiting" },
          { id: "c", name: "C", waiting: "review_new_thing", status: "awaiting_review" }];
        let seen = new Set(), rung = new Set(["a:review_lyrics"]); // as kept in localStorage
        const rings = [];
        for (let poll = 0; poll < 3; poll++) {
          const next = m.nextWaits(m.waitsOf(projects), seen, rung);
          ({ seen, rung } = next);
          rings.push(next.ring.map((w) => `${w.key}: ${w.gate}`));
        }
        console.log(JSON.stringify([rings, [...rung]]));
        """,
    )
    assert found == [
        [[], ["b:review: review", "c:review_new_thing: review new thing"], []],
        ["a:review_lyrics", "b:review", "c:review_new_thing"],
    ]


def test_mood_words_are_added_and_taken_out() -> None:
    found = run_js(
        "views/options.js",
        """
        console.log(JSON.stringify([
          m.toggleWord("", "tragic"),
          m.toggleWord("tragic", "tender"),
          m.toggleWord("tragic, Tender ,  hopeful", "tender"),
          m.toggleWord("غمگین، دلهره‌آور", "dark"),
          m.toggleWord("غمگین، دلهره‌آور", "دلهره‌آور"),
          m.hasWord("tragic, tenderness", "tender"),
          m.MOODS,
        ]));
        """,
    )
    assert found[:6] == [
        "tragic",
        "tragic, tender",
        "tragic, hopeful",
        "غمگین, دلهره‌آور, dark",
        "غمگین",
        False,
    ]
    assert found[6][6:8] == ["dark", "dreadful"] and len(found[6]) == 10


def test_the_pace_choices_come_from_the_settings_reply() -> None:
    found = run_js(
        "views/options.js",
        """
        console.log(JSON.stringify([
          m.paceChoices(undefined).map(([pace]) => pace),
          m.paceChoices(["calm", "balanced", "energetic"]).map(([pace, text]) => [pace, text.length > 0]),
          m.paceChoices(["calm", "brisk"]),
        ]));
        """,
    )
    assert found[0] == ["calm", "balanced", "energetic"]  # a server from before 0016 sends no paces
    assert found[1] == [["calm", True], ["balanced", True], ["energetic", True]]
    assert found[2][1] == ["brisk", ""]  # a pace the page does not know is offered without a line


def test_the_style_presets_name_no_era() -> None:
    styles = run_js("views/options.js", "console.log(JSON.stringify(m.STYLES));")
    assert list(styles) == [
        "Historical epic film", "Dark & moody cinema", "Natural documentary realism", "Modern cinematic"
    ]  # fmt: skip
    eras = (
        r"\b(century|medieval|ancient|victorian|\d{3,4}s?|\d+(st|nd|rd|th)|modern-day|contemporary|bc|ad)\b"
    )
    for name, look in styles.items():
        assert len(look) > 120, name
        assert not re.search(eras, look, re.IGNORECASE), name


def read_form(fields: dict[str, Any], pace: str | None, frame: list[str]) -> Any:
    """What the New video form sends from these field values (by id; `pace` is the checked radio, or none;
    `frame` the checked image models), read through a stand-in for the form."""
    body = f"""
        const fields = {json.dumps(fields)}, pace = {json.dumps(pace)}, frame = {json.dumps(frame)};
        const form = {{
          querySelector: (selector) => selector === "input[name=pace]:checked"
            ? (pace === null ? null : {{ value: pace }})
            : {{ value: String(fields[selector.slice(1)] ?? "") }},
          querySelectorAll: (selector) =>
            selector === "#model-frame input:checked" ? frame.map((value) => ({{ value }})) : [],
        }};
        console.log(JSON.stringify(m.readSettings(form)));
        """
    return run_js("views/new.js", body)


def default_fields() -> dict[str, Any]:
    """The form's fields as it fills them from the server's defaults."""
    defaults = hmv.Settings().model_dump(mode="json")
    fields = {k: v for k, v in defaults.items() if k != "models"} | {
        f"model-{role}": name for role, name in defaults["models"].items() if role != "frame"
    }
    return fields | {"min_shot": "0:02.000", "max_shot": "0:08.000", "language": ""}


def test_the_form_sends_pace_mood_style_and_the_image_models_the_server_accepts() -> None:
    fields = default_fields() | {"mood": " غمگین، tragic ", "style": "Dark, moody cinema"}
    frame = ["qwen-image-2.1-turbo", "flux2-klein-9b"]
    sent = read_form(fields, "calm", frame)
    assert {k: sent[k] for k in ("pace", "mood", "style")} == {
        "pace": "calm",
        "mood": "غمگین، tragic",
        "style": "Dark, moody cinema",
    }
    assert sent["models"]["frame"] == frame  # the first is the project's default model
    settings = parse_settings(sent)  # what POST /api/projects does with it
    expected = hmv.Settings().model_dump(mode="json")
    expected |= {k: sent[k] for k in ("pace", "mood", "style")}
    expected["models"]["frame"] = frame
    assert settings.model_dump(mode="json") == expected
    defaults = hmv.Settings().model_dump(mode="json")["models"]["frame"]
    assert read_form(default_fields(), None, defaults)["pace"] == "balanced"  # no choice checked


def test_the_page_has_the_bell_and_its_controls() -> None:
    page = (PAGE / "index.html").read_text()
    assert 'id="bell" class="bell-banner" role="alert" hidden' in page
    assert 'id="sound"' in page and 'id="enable-sound"' in page
    assert 'href="/bell.css"' in page and 'href="/options.css"' in page


# A stand-in for the few DOM calls the gate controls make (0018); `posted` holds what they send.
FAKE_DOM = (Path(__file__).parent / "fake_dom.js").read_text()


def test_a_typed_note_survives_a_redraw_with_its_caret() -> None:
    found = run_js(
        "decide.js",
        FAKE_DOM
        + """
        const first = m.gateControls(ctx, "review_lyrics");
        const box = first.all("textarea")[0];
        box.value = "timing is not accurate";
        await box.fire("input");
        box.focus(); box.setSelectionRange(6, 9);
        const again = m.gateControls(ctx, "review_lyrics");  // a server-sent event redrew the view
        const other = m.gateControls(ctx, "review_plan");    // each gate keeps its own note
        const kept = again.all("textarea")[0];
        console.log(JSON.stringify([kept.value, document.activeElement === kept, kept.selectionStart,
          kept.selectionEnd, other.all("textarea")[0].value, m.noteFor("song", "review_lyrics")]));
        """,
    )
    assert found == ["timing is not accurate", True, 6, 9, "", "timing is not accurate"]


def test_approve_with_a_typed_note_asks_first_and_each_answer_does_what_it_says() -> None:
    found = run_js(
        "decide.js",
        FAKE_DOM
        + """
        const out = [];
        for (const answer of ["cancel", "reject", "approve"]) {
          posted.length = 0;
          const asked = [];
          m.keepNote("song", "review_lyrics", "timing is not accurate");
          const ask = async (reject) => { asked.push(reject.label); return answer; };
          const controls = m.gateControls(ctx, "review_lyrics", { ask });
          await button(controls, "Approve").fire("click");
          const sent = posted.map(([url, body]) => [url.split("/").pop(), body]);
          out.push([answer, asked, sent, m.noteFor("song", "review_lyrics")]);
        }
        m.keepNote("song", "review_lyrics", "");
        let asked = 0;
        const ask = async () => { asked += 1; return "cancel"; };
        const quiet = m.gateControls(ctx, "review_lyrics", { ask });
        posted.length = 0;
        await button(quiet, "Approve").fire("click");  // no note: approved without a question
        out.push([asked, posted.map(([url, body]) => [url.split("/").pop(), body])]);
        console.log(JSON.stringify(out));
        """,
    )
    assert found == [
        ["cancel", ["Reject with note"], [], "timing is not accurate"],
        [
            "reject",
            ["Reject with note"],
            [["reject", {"gate": "review_lyrics", "note": "timing is not accurate"}]],
            "",
        ],
        ["approve", ["Reject with note"], [["approve", {"gate": "review_lyrics"}]], ""],
        [0, [["approve", {"gate": "review_lyrics"}]]],
    ]


def test_reject_with_note_waits_for_a_note_and_says_what_it_does_at_each_gate() -> None:
    found = run_js(
        "decide.js",
        FAKE_DOM
        + """
        const out = {};
        for (const gate of ["review_lyrics", "review_plan", "review_scenes"]) {
          const controls = m.gateControls(ctx, gate);
          const box = controls.all("textarea")[0];
          const reject = controls.all("button").find((b) => !b.text.includes("Approve"));
          const empty = reject ? reject.disabled : null;
          if (box) { box.value = "more close-ups"; await box.fire("input"); m.keepNote("song", gate, ""); }
          const help = controls.all("p")[0].text;
          out[gate] = [reject?.text ?? null, empty, reject ? reject.disabled : null, help];
        }
        posted.length = 0;
        const card = m.gateControls(ctx, "review_plan", { approvable: false });  // the Overview card
        const box = card.all("textarea")[0];
        box.value = "Darvin rides a black horse"; await box.fire("input");
        await button(card, "Reject with note").fire("click");
        out.posted = posted.map(([url, body]) => [url, body]);
        out.approve = button(card, "Approve") ?? null;
        console.log(JSON.stringify(out));
        """,
    )
    assert found["review_lyrics"][:3] == ["Reject with note", True, False]
    assert "runs the lyrics editor again" in found["review_lyrics"][3]
    assert "to fix timing, edit the lines' times" in found["review_lyrics"][3]
    assert found["review_plan"][:3] == ["Reject with note", True, False]
    assert "plans again with your note" in found["review_plan"][3]
    assert found["review_scenes"][:3] == [None, None, None]
    assert "takes no note" in found["review_scenes"][3] and "Scenes view" in found["review_scenes"][3]
    assert found["posted"] == [
        ["/api/projects/song/reject", {"gate": "review_plan", "note": "Darvin rides a black horse"}]
    ]
    assert found["approve"] is None


def test_the_timing_draft_nudges_and_sets_an_edge_inside_the_song() -> None:
    found = run_js(
        "views/timing.js",
        """
        const t = { start_ms: 8000, end_ms: 13750 };
        console.log(JSON.stringify([
          m.nudged(t, "start", -500, 20000),
          m.nudged(t, "end", 100, 20000),
          m.nudged(t, "start", 6000, 20000),
          m.moved(t, "end", 20500.4, 20000),
          m.moved(t, "start", -30, 20000),
          m.moved(t, "start", 9123.6, 20000),
          m.timesOf({ id: "L002", ...t }, { L002: { start_ms: 1, end_ms: 2 } }),
          m.timesOf({ id: "L003", ...t }, {}),
          m.NUDGES,
        ]));
        """,
    )
    assert found == [
        {"start_ms": 7500, "end_ms": 13750},
        {"start_ms": 8000, "end_ms": 13850},
        None,  # a start after the end: refused
        {"start_ms": 8000, "end_ms": 20000},  # kept inside the song, whole milliseconds
        {"start_ms": 0, "end_ms": 13750},
        {"start_ms": 9124, "end_ms": 13750},
        {"start_ms": 1, "end_ms": 2},
        {"start_ms": 8000, "end_ms": 13750},
        [-500, -100, 100, 500],
    ]


def test_the_note_is_kept_in_local_storage_until_a_decision_is_sent() -> None:
    fresh = json.dumps((PAGE / "decide.js").as_uri() + "?reopened")  # the page opened again: no memory
    found = run_js(
        "decide.js",
        FAKE_DOM
        + """
        const stored = new Map();
        globalThis.localStorage = { getItem: (k) => stored.get(k) ?? null,
          setItem: (k, v) => stored.set(k, v), removeItem: (k) => stored.delete(k) };
        const box = m.gateControls(ctx, "review_plan").all("textarea")[0];
        box.value = "more close-ups"; await box.fire("input");
        const saved = stored.get("note:song:review_plan");
        const reopened = await import(FRESH);
        const back = reopened.noteFor("song", "review_plan");
        await button(reopened.gateControls(ctx, "review_plan"), "Reject with note").fire("click");
        console.log(JSON.stringify([saved, back, stored.has("note:song:review_plan"), posted.length]));
        """.replace("FRESH", fresh),
    )
    assert found == ["more close-ups", "more close-ups", False, 1]  # removed once the decision is sent


def test_a_gates_own_approve_asks_first_too_and_can_be_cancelled() -> None:
    """A gate's own Approve (the lyrics' "Approve" with unsaved times, D-119) replaces the plain one."""
    found = run_js(
        "decide.js",
        FAKE_DOM
        + """
        const out = [];
        const picks = () => ({ gate: "review_plan", plan: 1 });
        const use = { label: "Use this plan", path: "approve", body: picks, done: "approved" };
        m.keepNote("song", "review_plan", "more close-ups");
        let card = m.gateControls(ctx, "review_plan", { approve: use, ask: async () => "reject" });
        await button(card, "Use this plan").fire("click");
        m.keepNote("song", "review_plan", "more close-ups");
        card = m.gateControls(ctx, "review_plan", { approve: use, ask: async () => "approve" });
        await button(card, "Use this plan").fire("click");
        m.keepNote("song", "review_plan", "");
        const refused = { label: "Approve with 2 errors", path: "approve", body: () => null, done: "" };
        const shots = m.gateControls(ctx, "review_plan", { approve: refused });
        await button(shots, "Approve with 2 errors").fire("click");
        console.log(JSON.stringify(posted.map(([url, body]) => [url.split("/").pop(), body])));
        """,
    )
    assert found == [
        ["reject", {"gate": "review_plan", "note": "more close-ups"}],
        ["approve", {"gate": "review_plan", "plan": 1}],
    ]  # the cancelled confirmation posts nothing


def test_approving_the_lyrics_with_unsaved_times_asks_first() -> None:
    found = run_js(
        "views/timing.js",
        """
        const asked = [];
        const ask = (text) => { asked.push(text); return false; };
        const before = m.approveLyrics("song", ask).body();
        m.draftOf("song").L002 = { start_ms: 8100, end_ms: 13700 };
        const refused = m.approveLyrics("song", ask).body();
        const anyway = m.approveLyrics("song", () => true).body();
        const line = { id: "L002", start_ms: 8200, end_ms: 13600 };
        const back = m.timesOf(line, { L002: null }, { L002: [8000, 13750] });  // a saved edit taken back
        console.log(JSON.stringify([before, refused, anyway, asked, back]));
        """,
    )
    assert found[:3] == [{"gate": "review_lyrics"}, None, {"gate": "review_lyrics"}]
    assert found[3] == [
        "L002: new times not saved. Approve without them? (Cancel, then Save timing, to use them.)"
    ]
    assert found[4] == {"start_ms": 8000, "end_ms": 13750}
