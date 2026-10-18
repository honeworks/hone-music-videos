# The cast, the character packs and the prop packs (stages 5 to 7)

> **Since [0027](../design/changes/0027-hone-frame-is-the-scene-pipeline.md)**:
> the cast, packs, start-frame check, polish, picture menu and their gates described here are gone. The
> plan is written as a Hone Frame project file and the scenes are made in the dashboard's **Scenes** view
> (or `hone-music-video frame ...`, [cli.md](cli.md)); the gates are `review_lyrics`, `review_plan` and
> `review_scenes`. [design/current.md](../design/current.md) §7, §9 to §11 and §13.2 describe it.


Characters stay the same across shots because every shot with a character gets that character's
reference pictures (design §7.2, §9).

**`plan_cast`** is one call to the cast planner with the timed lyrics, your story notes, the style and
every sheet you gave as an image. It writes a short summary of the story, lists the characters (people,
animals, creatures) and the props that must look the same every time, decides which of your sheets
covers whom (`source: "given:Darvin"`), and writes a turnaround-sheet prompt for every character still to
make, with the `noun` and `cue` the shot prompts name them by and each character's `traits` (the fixed
look in one phrase: age, build, hair, beard, an animal's colour and markings). It also writes the
`anchor`: one sentence naming the kind of film, the period and the place, from your story (for a story
in a legendary ancient kingdom, "A still from a historical epic film, real set, a legendary ancient
kingdom."; for one set today, "A still from a contemporary drama film, real locations, a rainy city at
night in the present day."), which begins every still prompt, and the story's `world`: the period and
place, what belongs in it (materials, clothing, light sources, technology) and what must not appear
(phones and cars belong to a modern story, never to an ancient one). The shot planner and the check of
the start frames read the world. The mood (`settings.mood`) colours how the story is pictured, never
the characters' looks. Each prop gets a `look`: the object alone in one phrase (shape, material,
colour, how many of each part, its size: "a gold armband a finger wide, set with one large blood-red
ruby"), apart from its `note` (who wears it, what happens to it). A plan
that breaks the rules goes back once. **The cast gate (`review_cast`):** approve it, or plan it again with a note.

**Pictures, not sheets** ([0020](../design/changes/0020-owner-sheets-and-frames.md), D-128 to D-138).
A new project (`packs: "views"`) makes each character's pack as separate pictures and each prop as one
picture, and you can change any single one. A project made before keeps the four-figure turnaround
sheets and the cutter described under `sheets` and `packs` below (`packs: "sheet"`). The cast planner
also writes, for each character, up to four **details**: what must stay the same and is too small for one
full-body picture (a ring, a snake's head), each a `{id, look}`.

- **`sheets`** draws one picture per character, its first view (front, full body, facing the camera; an
  animal's first picture is its side), from a single-figure prompt, on `models.sheets`, and one picture
  per prop (the whole object on a plain light-grey backdrop). The judge checks each and draws it again
  as for sheets (`sheet_retries`); its flags are shown, never blocking. **`pick_sheets`**: accept, redo or
  upload each picture.
- **`packs`** draws, from each accepted first picture, the character's side, back, portrait and each
  detail, each its own picture, on `models.views` (a model that takes reference pictures; Qwen-Image-Edit
  by default). Judged and drawn again like the first pictures. **`review_packs`** (a new gate): accept,
  redo or upload each picture. The pack is the accepted pictures, uncut, in `current/packs/<character>/`
  (`front.png`, `side.png`, `back.png`, `portrait.png`, one file per detail) and `current/props/<prop>/main.png`.
- **Redo** a picture with a note added to its prompt and a model from the menu, or **upload** your own
  picture; only that picture is drawn, and every other is found, not drawn again. Redo a front and its
  views are drawn again from the new one before `review_packs`. Every take is kept and any can be put
  back in use.
- **The menu** lists the local models and the hosted ones (an OpenAI-compatible gateway) that can draw the picture, each with
  an estimate ("about $0.035"; a local model is free, with its time). A hosted model spends money and the
  pictures you give it leave your machine. `hone-music-video image-models` prints the same menu;
  `hmv.image_models` returns it.
- **An upload** is checked by its bytes (PNG, JPEG or WebP, at most 25 MB, at least the picture's size on
  both sides), kept under its sha256 and cover-cropped to the picture's size, with the crop recorded.
  The judge never checks it and it is never drawn again.
- **Both gates always wait** in a new project, also when it runs without stopping for approval: the run
  stops (`auto_stopped`, and a notification) so you see the pictures before they are used. They pass on
  their own only when no character and no prop needs a picture (every one is a given sheet). A sheet you
  give is still cut into the views it holds, and any view can then be replaced at `review_packs`.
- A shot's `refs` may name a detail (`"morvane/ring"`); a scene's references are the named details first,
  then the characters' views, then the props' pictures, up to the model's limit (three on Qwen).

```text
hone-music-video redo-picture projects/my-song morvane front --model seedream-5-0-260128 --note "two snakes"
hone-music-video redo-picture projects/my-song morvane ring --upload ring.png
hone-music-video approve projects/my-song          # accepts what is shown; then resume
```

The rest of this page describes the four-figure sheets of `packs: "sheet"` projects.

**`sheets`** draws `sheet_takes` turnaround sheets per character to make (Z-Image Turbo, 2048x1024: the
same subject four times, front, three-quarter, side and back), each with a preview of how it would be
cut. The cut keeps in each figure only what is joined to its own head, so a neighbour's tail or rump
reaching into its box is left out. **The sheet gate (`pick_sheets`):** pick a take per character, or ask for new takes with a note
(new seeds, the note added to the prompts, the earlier takes still on offer). When every character has a
given sheet and no prop is drawn the gate passes on its own.

**The judge of the sheets** (0019). With `quality_check` on, the judge (`models.quality`) looks at every
new take in one call: it counts the figures, names each one's direction, checks each fixed trait of the
cast entry (two snakes from the shoulders, the crown, the beard, the costume) in every view, and that the
backdrop is plain; it scores each take and flags `figure-count`, `wrong-trait`, `inconsistent-views` or
`extra`. A take with a major flag is drawn again from the corrected prompt the judge writes, up to
`sheet_retries` rounds (default 2), and its best round is the one on offer. The Cast view shows each
take's score, flags and retries ("retry 1 of 2: 5 figures → redrawn"); the best take is chosen for you
and an unattended run goes on with it. A character's take the judge counted with other than four
figures cannot be picked: its cut would name the wrong views. A character the planner marks `unusual`
(a creature, snakes or wings growing from the body, extra limbs, a mask) gets at least four takes.

**Props** (0017). In the same stage each prop with a look gets `prop_sheet_takes` sheets (default 4):
the object twice on a plain grey backdrop, whole on the left and a close detail on the right, drawn from
its look in the story's world. You pick a prop's take at the same gate, by its id
(`--take ruby-token=2`), or a retake draws new ones for characters and props alike. To give a prop's
picture yourself, add it like a character's sheet (`--sheet armband=armband.png --note "the ruby
armband"`): the cast planner sees it and sets the prop's `source` to `given:armband`. A cast planned
before 0017 has no looks: its props get no sheet and are drawn from words as before.

```text
hone-music-video pick projects/my-song --take celina=3 --take darvin=1
hone-music-video retake projects/my-song --note "darker armour"
hone-music-video resume projects/my-song
```

**`packs`** cuts each picked or given sheet into its figures (`figure-N.png`, found in the top third of
the picture, where heads stand apart): the first is the front view, the next the side, the last the
back; for an animal the longest figure is the side view. A person gets a head-and-shoulders portrait
(Qwen-Image-Edit, then the Z-Image polish). A given sheet is never redrawn; a single portrait or figure
is used as the front view. The packs are in `current/packs/<character>/`. A prop's picked take (or its
given picture) is cut by its objects: the first is `main.png`, a second `detail.png`, in
`current/props/<prop>/`; every shot that shows the prop gets its pictures (see [render.md](render.md)).

Sheets and portraits run on local models through ComfyUI (see [render.md](render.md) for the setup).
