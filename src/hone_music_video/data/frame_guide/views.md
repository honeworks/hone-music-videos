### Views and turnarounds

Views are the same character (or object) from other sides: three-quarter, side, back, and any other
angle you will need. Each is an edit of the accepted hero: `refs = ["woman.hero"]`, so the hero is
image 1. A sheet (`four-view-turnaround`) then puts them side by side.

#### What the prompt must say

1. **The new view first**, as a sentence: "Turn the woman from image 1 to an exact side profile facing
   left." If the model's notes describe a camera phrase or an input for angles, use it as they say.
2. **Who it is.** Never only "the same person as image 1": also "a woman of about thirty with
   shoulder-length dark brown hair". Edits that never said who the person was let beards change length
   and a woman in armour drift into a man (root cause D, 2026-10-03).
3. **What must not change, by name:** "the same face, the same hair length and parting, the same build,
   the same oatmeal jumper, dark-blue jeans and white trainers". Name each garment; "the same clothes" is
   too weak.
4. **What the hero does not show.** A back view is invented: say what is on the back ("her hair falls
   straight to her shoulders at the back; the jumper is plain at the back"). The hero never shows it.
5. **The body turns with the camera.** For side and three-quarter views write "her face, chest and both
   feet point the same way": feet turned backwards in a side view were seen and no local judge caught it
   (D-029).
6. **The same background and light as the hero:** "plain mid-grey background, one soft key light from the upper left".

#### References

- Image 1 is the hero, and usually the only reference. A second full-body picture of the same person
  (the front and the side together) can make two people appear (the model's notes say where): give one
  full body per person.
- For a back view give the hero only. A three-quarter view as well as the hero may help a side view on a
  model that takes more references; test it on one item first.
- An object's views: the object's hero as image 1, and the object's shape in words ("a flat round mug
  seen from directly above"). See Objects.

#### Common failures and what to do

- **Near-copies of the hero** instead of a turn: some models return the hero barely turned, most of all
  for objects (0007). The models' notes below say which turn for real.
- **Clothes differ from behind.** The back is invented; describe it, and make garments that must match
  exactly as objects first.
- **Left and right swap** when the figure turns (a watch moves to the other wrist): state the side in
  every view where it shows.
- **A top view from a side-on or three-quarter hero** is hard: few models manage it (0007); try one item
  first.
- **Flat objects** (a plate, a book) look the same from front, back and side: ask only for views that
  differ (front, edge-on, top).
- **The background changes** to a room: repeat the hero's background sentence.

#### Examples

The examples use `qwen-image-2.1-turbo`, the default model of Hone Frame's examples, and show the form
only: how long a prompt may be, how many references a model takes, how to name them and whether its
pictures may be used commercially are in each model's notes below.

##### "The same woman from image 1", then the view

The hero is image 1 and the only reference. Say the view first, then who she is and everything that
stays, by name.

```toml
[characters.woman.three-quarter]
model = "qwen-image-2.1-turbo"
size = "832x1248"
refs = ["woman.hero"]
prompt = "The same woman from image 1 in a three-quarter view: she stands turned halfway to her right, her body at a 45-degree angle to the camera, her left shoulder nearer the camera, her face, chest and both feet pointing towards the left edge of the picture, the far side of her face partly hidden. Full body head to toe, neutral standing pose, arms relaxed at her sides. She is a woman of about thirty with shoulder-length dark brown hair parted on the left. Same face, same hair, same build, same oatmeal knitted jumper, dark-blue jeans, white trainers and the silver watch on her left wrist, same colours. Alone on a plain seamless mid-grey background, one soft key light from the upper left, no props, no text."
```

```toml
[characters.woman.side]
model = "qwen-image-2.1-turbo"
size = "832x1248"
refs = ["woman.hero"]
prompt = "The same woman from image 1 in exact side profile facing left, her left side towards the camera: her face, chest and both feet pointing left, full body head to toe, neutral standing pose, the silver watch on her left wrist in view. Same oatmeal jumper, dark-blue jeans and white trainers, same shoulder-length dark brown hair. Alone on a plain seamless mid-grey background, one soft key light from the upper left, no props, no text."
```

```toml
[characters.woman.back]
model = "qwen-image-2.1-turbo"
size = "832x1248"
refs = ["woman.hero"]
prompt = "The same woman from image 1 seen from directly behind, full body head to toe: the back of her head and the back of her body, her face hidden. Her shoulder-length dark brown hair falls straight at the back; the oatmeal knitted jumper is plain at the back, with the same dark-blue jeans and white trainers. Same build and proportions. Alone on a plain seamless mid-grey background, one soft key light from the upper left, no props, no text."
```

##### Without references: a quick look only

An item without references cannot see the hero, so a view from text alone is another drawing of a
similar person. Use it only for a quick look at an angle, writing the hero's whole description again:

```toml
[characters.woman.side-sketch]
model = "qwen-image-2.1-turbo"
size = "832x1248"
prompt = "Photorealistic character reference: one full-length studio photograph of one woman in exact side profile facing left, full body head to toe, her face, chest and both feet pointing left. She is about thirty, slim, with an oval face, warm light-brown skin and shoulder-length dark brown hair. She wears a loose oatmeal knitted jumper, dark-blue jeans and white canvas trainers. Alone on a plain seamless mid-grey background, one soft key light from the upper left, no props, no text."
```

##### For commercial work

A model whose licence does not allow commercial use (part 3 warns of it) is for trying things out and
for work you will not sell. For commercial pictures, write the item for a model that allows it, in the
form its notes ask for:

```toml
[characters.woman.three-quarter]
model = "qwen-image-edit-2511"
size = "832x1248"
refs = ["woman.hero"]
prompt = "Show the woman from image 1 in three-quarter view, seen from her front right, the whole figure from head to feet, her face, chest and both feet turned the same way. She is a woman of about thirty with shoulder-length dark brown hair parted on the left. Keep exactly the same face, hair, build, oatmeal knitted jumper, dark-blue jeans, white trainers and the silver watch on her left wrist. Plain mid-grey background, one soft key light from the upper left."
```

```toml
[characters.woman.side]
model = "flux.2-klein-4b"
size = "832x1248"
refs = ["woman.hero"]
prompt = "Exact side profile of the woman from image 1, facing left, whole figure from head to feet, her face, chest and both feet pointing left. A woman of about thirty, shoulder-length dark brown hair. Same face, hair, build, oatmeal jumper, dark-blue jeans, white trainers. Plain mid-grey background, one soft key light from the upper left."
```
