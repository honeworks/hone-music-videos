# 0035: Simple scenes that show the song's story and its feeling

## Status

`accepted (approved by the maintainer 2026-10-31: "make it a new design doc and start developing")`,
proposed the same day after 0034's measurement. Its smaller choices are D-184 onwards. It is built in three parts: the shot focuses
(§1 to §3), the instructions pruned (§4), and a measurement on real songs (Verification) before it is
made the default for new plans.

## Context

0029 and 0034 measured what the planner writes and which pictures the image model gets, on 100 hard
cases. Each idea moved the facts a picture keeps by two or three points; checks passed stayed between
75% and 78% under every idea, and the facts that fail under every idea are the same six (a body's own
side, a grip or a bite, more than three to count, a small mark on a face, eyes meeting, a movement
state). Both studies ended with the same sentence: **the ceiling is the shot, not the prompt.** The
pictures fail where the shot asks for something the models can't draw.

The plans of the 2026-10-19 batch show why: a shot list of 50 to 100 shots plans two people gripping,
creatures fighting, crowds, overhead views and faces in wide shots, because the story and the lyrics
suggest them. The instructions then try to rescue each shot with more rules: the planner's own prompts
are about 6,000 words across six files (`frame_bible`, `frame_shots`, `frame_review`, `frame_scenes`,
`frame_assets`, `limits`), many rules repeated in two or three of them, and the guide adds more. 0034
showed what that costs: the shot list's rule "a wide shot without faces gets no picture of its people"
and the review's rule "a figure needs a cast and a pose" pulled the same shots in opposite directions.

What the owner wants is not complicated: **simple scenes that show the story of the song and the
feeling, the feeling above all.** A viewer feels a music video through one person at a time: a face, a
body in a place, two people and the space between them, a place's light, one thing that matters. Those
are also the pictures the models draw well.

## Problem

1. The shot list may plan any picture, so many shots ask for what the models can't draw; rules then try
   to fix those shots one by one.
2. The feeling is planned (0028) but carried by staging the models can't hold (contact, crowds, small
   marks), so it is written but not drawn.
3. The instructions are long, repeated and sometimes contradictory; each new rule risks fighting an old
   one.

## Options

1. **More rules for hard moments.** Measured twice (0029, 0034): two to three points per idea.
   Rejected.
2. **A judge and retries per picture.** Ruled out by the owner in 0029; removed in 0027. Rejected.
3. **Plan only simple shots: a small closed set of shot focuses**, each one subject and one carrier of the
   feeling, with the references code gives it; the instructions shrink to what each call needs. Chosen.

## Decision

### 1. Every shot has one focus, of five

The shot list gives every shot a `focus` (not `kind`, which is the bible's kind of picture). A focus
says who is in the frame, how close, and what carries the feeling; code knows each focus's pictures and
checks it.

| Focus | In the frame | Framing | The feeling is carried by | References (0034's order) |
|---|---|---|---|---|
| `face` | one character's face and shoulders | close-up or medium close-up | the eyes, the brows, the mouth held, the jaw | the place, the character's close-up |
| `figure` | one character, the whole body or from the waist, in the place | medium to wide | the posture, where the body is in the frame, what it does with its hands, the light on it | the place, the character's view or pose |
| `pair` | two characters, apart or in gentle contact (a hand on a shoulder, side by side) | medium or wide, eye level | the distance between them, who looks at whom or away, who leans | the place, both characters |
| `place` | the place, no character (figures too small to matter are words) | wide or extreme-wide | the light, the weather, the emptiness, what moves | the place in its state |
| `detail` | one thing filling the frame: an object, a hand, a part of a character | insert or extreme close-up | the thing itself and what has happened to it | the object, or the character's detail |

- A shot that would need anything else (a fight with contact, a crowd that matters, three people,
  creatures against each other, a straight-down or worm's-eye view) is **planned as a focus instead**: the
  moment before or after, a `face` of the one who reacts, a `detail` of the hand or the mark it left, a
  `place` with the crowd small. The focuses are how the six limits are planned around, as plans, not
  rules (0029 §2 stays as the reason, in one place).
- **Code checks the focus** (a shot problem sent back): the number of characters in `cast` (`face` 1,
  `figure` 1, `pair` 2, `place` 0, `detail` 0 or 1), the framing the focus allows, no `faces` on a
  `place` or a `detail`, a `detail` with a character naming its `part`. The view follows
  the focus (`face` → `close`; `detail` → `detail`), so the shot list no longer chooses it for them.
- `place_in_words`, `takes: "prompts"`, three-person casts and the hard-moment list are retired: a focus
  never needs them. `takes: "count"` stays for a `face` (a recognisable face may need a second draw).

### 2. The story and the feeling, part by part

The bible's arc (0028) stays: per part of the song its feel, intensity, turn and visible evidence. The
shot list now plans each part as **a short sequence of focuses** that shows its story and builds its
feeling, and each shot's `feel` and `evidence` say how its focus carries it:

- **What is sung is shown, simply.** The story a line tells is shown by the focus that shows it best: an
  action by the one who does it (`figure`), a relationship by the two (`pair`), an inner state by the
  face (`face`), a symbol or a consequence by the thing (`detail`), a time or a world by the place
  (`place`). A metaphor becomes one picture, never a contradiction.
- **The feeling is in the person.** Prefer `face` and `figure`: a feeling reads on one person. The
  stronger the arc's intensity, the closer: quiet parts open on `place` and `figure`, the strongest
  parts hold on `face`. A hidden feeling still shows its surface and its leak (0028), on one face.
- **Few subjects, one at a time.** A part of the song follows one or two characters; the sequence cuts
  between focuses (a `figure`, then the `face`, then the `detail` it looks at) instead of putting
  everything in one frame.

### 3. The scene call writes a focus

The scene call gets the shot's focus and writes its prompt by the focus's short recipe: who and where (the
references in order, as 0034), the one carrier of the feeling made concrete (the face's parts, the
body's posture, the distance between two, the light), the framing and camera, the finish. Facts first
(0029 §1) stays, much shorter for a simple shot.

### 4. The instructions, pruned

Each rule is said once, in the call that acts on it:

- `limits.md` keeps what the models can and can't do, once; the shot list gets it, the scene call only
  its video part.
- `frame_shots.md` is rewritten around the focuses and the arc: timing, the focuses with their checks, the
  story and the feeling. The rules the focuses make unnecessary go (contact, crowds, hard moments,
  `place_in_words`, the six limits as rules).
- `frame_review.md` reads three things only: is the feeling visible in each shot's focus, is the song's
  story readable in order, does the intensity grow. What code checks, it does not.
- `frame_scenes.md` keeps the facts-first form and 0034's order and "say what changes", and adds the
  five recipes; rules about shots it never gets go.
- The guide's sections are sent only where a call needs them (Hone Frame's guide stays word for word,
  0026).

Target: the planner's own instructions at about half their length, with a test that the retired rules
are gone and every focus is named in the shot list's, the review's and the scene call's instructions.

### 5. What a shot looks like

```json
{"id": "S014", "start_ms": 61200, "end_ms": 66400, "lines": ["L011"],
 "focus": "face", "framing": "close-up", "faces": true,
 "cast": [{"character": "arnavaz"}], "place": {"place": "bedchamber", "view": "close"},
 "beat": "Arnavaz lies awake in the dark, her face turned toward the camera on the pillow.",
 "feel": "dread held still", "evidence": "her eyes wide and fixed past the camera, her lips pressed",
 "motion": "her eyes close slowly", "camera": "static camera", "light": "one lamp behind her"}
```

The shot list's other fields stay (`ends`, `setup`, `from_scene`, `objects`, `takes`); a `face` needs no
`view` (code gives it the close-up), a `detail` with a character names its `part`.

### 6. What is not changed

The bible call (cast, places, objects, arc), the subject pictures, 0034's reference order, the timing
rules and their checks, the clips and the assembly. A project planned before 0035 keeps its plan; its
shots read without `focus` (an older shot list reads as focuses by its framing and cast, D-184).

## Verification

**On real songs, not hard cases.** Four of the batch projects of 2026-10-19, chosen apart (*Dancing
with a Ghost*, playful and modern; *Zahaak*, myth and dread; *Quiet Morning Pages*, calm; *Stay on the
Gate*, action and humour): each shot list planned again with 0035 from its kept bible and timeline
(agents answering the calls, as for 0034), then twenty moments per song, evenly spaced in time, drawn:

- **A**: the old shot list's shot at that moment, drawn with today's code (0034's order);
- **B**: the 0035 shot list's shot at that moment.

Scored blind (Haiku, A and B shuffled), per picture: **clean** (no merged or extra limbs, no wrong count,
not pasted in), **story** (it shows what its line or beat is about) and **feeling** (a viewer would feel
the shot's `feel`), and per pair which picture better shows that moment of the song with its feeling.
0035 is made the default when B is at least A on clean and on story, and better on feeling and in the
pairwise choice. If it is not, the focuses stay an option and the reason is kept here.

### Tests

- `tests/unit/test_focus.py`: each focus's cast count, framings and faces sent back (80); the views a
  focus sets and the references in order (81); an older shot's focus worked out from its framing and
  cast (83).
- `tests/e2e/test_ac80_simple_scenes.py`: a plan through the fakes, every shot with a focus, the scene
  and review calls given it (80, 82).
- `tests/unit/test_still_guideline.py`: the retired rules absent and each focus named (84).
- The measurement's harness and results go to `design/research/simple-scenes-2026-11.md`.

### Guarantees (new acceptance cases, after 79 in `design/current.md` §14)

80. Every planned shot has one of the five focuses; a shot whose cast, framing or faces its focus does not
    allow is sent back.
81. A shot's references follow its focus: a `face` the place and the character's close-up, a `figure`
    the place and the view or pose, a `pair` the place and both, a `place` the place only, a `detail`
    the object or the character's detail.
82. The scene call gets the shot's focus and the focus's recipe; the review call gets the focuses.
83. A shot list kept before 0035 reads, each shot given the focus its framing and cast imply.
84. The retired rules are not in the instructions, and each focus is named in the shot list's, the
    review's and the scene call's.

## Consequences

- Plans are simpler: fewer people per frame, no fights with contact, no crowds that matter. A song whose
  story is a battle shows it through faces, figures, details and places; the owner asked for this.
- Fewer references per scene (at most three), so scenes draw faster.
- The planner's instructions are about half as long, so its calls cost less.
- A re-plan calls everything again; a project planned before keeps its plan until the owner re-plans.

## Migration and compatibility

- `FrameShot.focus` is new and optional in a stored reply: a reply kept before 0035 reads, its focus
  worked out from its framing and cast (D-184). `place_in_words` and `takes: "prompts"` still read in an
  old reply; a new plan never writes them.
- No dependency, extra or secret changes. Nothing new is written during a run, so a crash halfway and
  two processes behave as before (the planner writes its kept replies and the plan, 0027).
- **The smaller option:** only rewriting `frame_shots.md` around the focuses, without code checks. It
  would be one more rule a reply can ignore; the code checks are what make the plan simple, so they stay.
