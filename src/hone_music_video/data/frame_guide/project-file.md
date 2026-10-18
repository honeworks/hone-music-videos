You write the whole project in one file, TOML or JSON. `hone-frame import FILE` (or **New project** in the
dashboard) copies it into the project folder as `project.toml` or `project.json`; from then on that copy
is the project, and every edit you make in the dashboard is written back into it (a TOML file keeps your
comments and your order).

**Every prompt is sent byte for byte.** Hone Frame adds nothing, removes nothing and rewrites nothing:
no style words, no "high quality", no reference roles. What a model gets is exactly an item's `prompt`
(or, image by image, its `prompts`), its `negative` for a model that takes one, its `refs` as pictures,
and its fields.

#### Where the look comes from

Hone Frame has no polish, upscale or retouching step after a picture is made: the look is what the
prompt and the references give. (A light img2img polish over each frame was tried in hone-music-video;
it changed faces and moved props, and was turned off.) Five test projects in five styles (stress tests
2026-10-14, `design/research/`) looked like films and books, not renders, when every prompt:

1. names the kind of picture first, the same words throughout the project ("A frame from a
   feature-length stylised 3D animated film.", "A still from a 1920s period drama shot on 35mm film.");
2. is one shot, with its framing and lens ("medium-wide side view, 35mm lens");
3. names the light and where it comes from ("cold moonlight from behind, an orange campfire glow from
   below");
4. names textures and materials (wool, wet cobbles, scales, brush strokes, film grain);
5. says everything as what is there, never "no …";
6. leaves out words of computer graphics and advertising ("photorealistic", "razor-sharp", "8k");
7. keeps continuity to short sentences ("Same face and leopard vest as image 1.");
8. describes what is seen, not a comparison ("a swarm of bees", not "a cloud of bees");

and when the characters wore rich costumes with props of their own, the references were on a plain
mid-grey backdrop with one soft key light from a side, and the size was near the model's trained size
(1664x928 rather than 1024x576 on Qwen). Each stage below adds what its pictures need.

#### Start with a demo (recommended)

A demo is a few plain prompts, with no references, written in the look of the whole project. They are
made **first**, before anything else, so within minutes you see the feel of the finished work: the
style, the light, the main character, the places. If you don't like it, stop the run and change the
words before hours go into heroes, views and scenes. A demo is optional, but recommended.

```toml
[demo]
prompts = [
  "A moonlit stone palace on a cliff above the sea, painterly, deep blue night, warm lamp light",
  "A young woman with a lantern in a dark stone corridor of the palace, painterly, deep blue night",
  "The young woman running across the palace roofs under the moon, painterly, deep blue night",
]
hold = true                              # the run stops after the demo until you accept it
```

- Write three to six prompts, each carrying the project's style words: the main character, a key
  place, a key moment, in the words the scenes will use. In a test project the demo showed the look in
  about two minutes, before any hero was made. Each prompt makes one picture, `demo.1`, `demo.2` and so on, sent byte for byte.
- `model`, `size`, `negative` and `inputs` come from `[defaults]` unless `[demo]` sets its own; `seed`
  gives `demo.1` that seed, `demo.2` the seed + 1, and so on.
- `hold = true` stops the run after the last demo picture until you **Accept** it: then you decide
  whether the rest is made. Recommended for long projects. Without it the run goes straight on, and you
  can still **Stop** it.
- A demo picture never waits for a pick, has no `refs` or `file`, and no item may refer to it: it is a
  preview, not a reference. It sits wherever you write `[demo]` in the file, but is always made first.

#### `[project]` and `[defaults]`

| Field | Meaning |
|---|---|
| `project.name` | the project's name |
| `project.style`, `project.notes` | **reference only: never sent to a model.** Keep your look and your notes here, and copy the words you want into each prompt yourself |
| `defaults.model`, `defaults.size`, `defaults.hold`, `defaults.negative`, `defaults.count`, `defaults.inputs` | used by every image item that does not set its own (an item's own value wins; `inputs` are merged) |

#### Groups and ids

| Group | Table | Item id (used in `refs` and `images`) |
|---|---|---|
| `characters` | `[characters.woman.hero]` | `woman.hero` |
| `objects` | `[objects.mug.hero]` | `mug.hero` |
| `places` | `[places.kitchen.wide]` | `kitchen.wide` |
| `scenes` | `[scenes.coffee]` (one image) or `[scenes.coffee.close]` | `coffee` or `coffee.close` |
| `sheets` | `[sheets.woman-turnaround]` | (a sheet is not a reference) |

Subject names (`woman`, `mug`, `kitchen`) are unique across characters, objects and places. A picture
you have (a pose, a garment, a place) is an item with `file`, referred to like any other.

#### The fields of an image item

| Field | Meaning |
|---|---|
| `prompt` | what the model is asked, exactly as written; required unless `prompts` or `file` is set |
| `prompts` | instead of `prompt`, for several shots of one item: a list, one image per prompt in order (image 1 is made with prompt 1 and `seed`, image 2 with prompt 2 and `seed + 1`, ...); leave `count` out (an item's own `count` must match; `defaults.count` is ignored); in hone-music-video a run makes one of them, the first (or the one in use), and **Run prompt N** makes another beside it, each image labelled with its prompt ("Prompt 2"); not allowed in `[defaults]` or together with `prompt` |
| `negative` | what the picture should not have; only for a model that takes a negative, and only where its guide says it works |
| `model` | a local model's id (part 3); else `defaults.model` |
| `size` | `"WxH"` from the model's sizes; never write the size or aspect into the prompt |
| `seed` | an integer; without one it is derived from the item's id, so a redo with an unchanged prompt is a true repeat |
| `count` | how many images (default 1); image 1 uses `seed`, image 2 `seed + 1`, and so on; with more than one the item waits for your pick, but the run goes on |
| `refs` | reference pictures, in order: the first is **image 1**, the second **image 2**, and so on; write the prompt with those numbers |
| `file` | a picture you made elsewhere (`"assets/mug.png"`): it is used as it is and never generated |
| `hold` | `true`: when it is made, the run waits until you accept it |
| `inputs` | the model's own inputs by their hone-models names (`steps`, ...): only those the model takes (part 3, and the Models page), or the file is refused |

A sheet item is composed by Pillow, with no model, once its images are done. Its fields:

| Field | Meaning (default) |
|---|---|
| `layout` | `four-view-turnaround`, `expression-grid`, `pose-grid`, `object-detail-board`, `environment-board`, `before-after`, `sequence-strip`, `contact-grid` (the default) or `character-model-sheet` |
| `images` | the item ids to show, in order (their current pictures) |
| `labels` | one label per image, or none |
| `columns` | the number of columns (the layout's own number) |
| `page` | `"auto"` (the default: from the images) or a `"WxH"` page size in pixels |
| `fit` | `"contain"` (the default: the whole picture, letterboxed) or `"cover"` (fill the cell, cropping the centre) |
| `background` | the page colour (`"#FFFFFF"`) |
| `spacing`, `margin` | pixels between cells (24) and around the page (48) |
| `heading` | the title printed at the top (the sheet's name) |
| `palette` | colours drawn as swatches with their hex codes (`["#C8B49A", "#2B3A55"]`) |
| `notes` | text printed under the pictures |
| `show_meta` | `true`: print each picture's item and size under its label |

#### References point upward

An item may refer only to items written **above** it in the file. Write the
file in the order things are made: heroes first, then the views made from them, then poses, objects and
places, then scenes that use them, then sheets. An item's dependants are simply the items below that
refer to it.

#### Marks, holds, counts and versions

- When a file is imported every item is `todo` and **marked to run**. **Run** makes the topmost marked
  item, then the next, until nothing is marked.
- An item with `hold = true` becomes `waiting` and **the run stops** until you **Accept** it; then it goes
  on by itself. Hold what everything below is made from, such as a hero, when you want to check it first.
- An item with `count > 1`, or with two or more `prompts`, also becomes `waiting`, for your **pick**,
  but **the run does not stop**: it goes on with every item that is not made from it. Items made from it
  wait until you pick, then the run makes them by itself. When nothing more can be made, the run ends `waiting` and tells you once.
- `count = 3` with one `prompt` is three takes of the same prompt (seeds `seed`, `seed + 1`,
  `seed + 2`); `prompts = ["...", "...", "..."]` is three different shots, one image each.
- **Redo** marks an item again. Before the run reaches it you can change anything: prompt or prompts, model,
  seed, size, refs, inputs, count, hold. Hone Frame asks whether to mark the items made from it too; the ones
  you keep are flagged "made from an older" version.
- **Replace with a file** and **use an older version** make that picture current; the same question
  about dependants follows. Versions are never deleted.
- An item whose fields differ from what made its current picture is flagged "changed since made"
  (with `prompts`, a change to any of its prompts); it is never marked by itself.
- **Pause** stops the current image at once and keeps it marked; **Resume** goes on from the topmost
  marked item. **Stop** ends the run.

#### What import refuses

Each message names the item and says what to do: an unknown group or field, a ref to an item below or
to nothing, an unknown model or one that is not local, refs to a model that takes none, more refs than
the model takes, a size the model does not list, a `negative` or an input the model does not take
(nothing is dropped on the way), an input that hone-models would write into the prompt (write those
words into the prompt yourself), a `file` that does not exist or is not a picture, `refs` or `file` in
`[demo]`, an empty demo prompt, and a ref to a demo picture. A model under a
research licence is allowed, with a warning.

#### A small file

```toml
[project]
name = "Morning at home"
style = "soft natural light, lived-in"   # reference only

[defaults]
model = "qwen-image-2.1-turbo"           # every item below uses it unless it sets its own `model`
size = "1024x1024"

[demo]                                   # made first: the feel of the whole project, no references
prompts = [
  "A woman in a small sunny kitchen in the morning, soft natural light, lived-in ...",
  "A small home kitchen in the morning, empty and quiet, soft natural light, lived-in ...",
  "A woman at a kitchen table holding a mug, morning light, soft natural light, lived-in ...",
]

[characters.woman.hero]
size = "832x1248"
hold = true
prompt = "Character reference: one full-length studio photograph of one woman, full body head to toe ... on a plain white background."

[characters.woman.side]
size = "832x1248"
refs = ["woman.hero"]                    # image 1
prompt = "The same woman from image 1 in exact side profile facing left ..."

[characters.woman.sitting]
size = "832x1248"
refs = ["woman.hero"]                    # image 1
prompt = "The same woman from image 1 sitting upright on a plain wooden stool ..."

[places.kitchen.wide]
model = "z-image-turbo"                  # this item only: another model, in its own form
size = "1024x576"
prompt = "Photorealistic interior photograph. A wide view of a small home kitchen ... The kitchen is empty and quiet."

# A scene and a sheet follow the items they use.
[scenes.coffee]
size = "1024x576"
count = 3                                # three images: you pick one
refs = ["woman.hero", "kitchen.wide"]    # image 1, image 2
prompt = "The woman from image 1 sits at the table in the kitchen from image 2, holding a mug ..."

[scenes.leaving]
size = "1024x576"
refs = ["woman.hero", "kitchen.wide"]    # image 1, image 2
prompts = [                              # three shots: one image each, you pick one
  "The woman from image 1 stands at the door of the kitchen from image 2, seen from across the room ...",
  "A close view of the face of the woman from image 1 as she looks back at the kitchen from image 2 ...",
  "The hand of the woman from image 1 on the door handle, the kitchen from image 2 behind her ...",
]

[sheets.woman-views]
layout = "before-after"
images = ["woman.hero", "woman.side"]
labels = ["Front", "Side"]
```

To make the whole project with another model, change `defaults.model`, and rewrite the prompts in that
model's form (part 3): a prompt written for one model is not always right for another.

The same file as JSON has the same tables as objects, in the same order:

```json
{
  "project": {"name": "Morning at home", "style": "soft natural light, lived-in"},
  "defaults": {"model": "qwen-image-2.1-turbo", "size": "1024x1024"},
  "characters": {
    "woman": {
      "hero": {"size": "832x1248", "hold": true, "prompt": "Character reference: one full-length ..."},
      "side": {"size": "832x1248", "refs": ["woman.hero"], "prompt": "The same woman from image 1 ..."}
    }
  }
}
```

Ten complete example projects, the same small world in ten styles with every prompt written out, are in
the repository's `examples/projects/` folder (`morning-cinematic-realism.toml` and the others).
