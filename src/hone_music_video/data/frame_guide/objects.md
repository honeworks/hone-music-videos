### Objects

An object is anything that must look the same every time it appears: a mug, a bicycle, a lamp, a bag,
a garment to be worn. Give it a hero of its own (alone, whole, on a plain background), and views when
its sides differ. Make objects **before** the poses and scenes that use them: an object that has a
picture is drawn as itself; one that has only words is drawn as the nearest common object.

#### What the prompt must say

1. **The object alone and whole:** "one ceramic mug, alone, the whole mug in the frame, on a plain white
   background". Say there are no hands and no people by stating what is there ("standing alone on a
   white surface").
2. **Its shape**, then **size**, **materials**, **colours** and **distinctive details**, in that order
   of importance: "a tall straight-sided mug about 10 cm high, glazed stoneware, deep teal with a thin
   cream rim, a round handle on its right side, three small white dots near the base". An object's own
   details are what was missing when an ox-head mace came out as an axe (root cause B).
3. **Which side faces the camera:** the side shown is the side every later picture copies (a laptop's
   lid, a sign's printed face).
4. **Light:** one soft key light from the upper left, so later scenes can relight it.

#### References

- The hero needs none (from words), unless the object is made from a picture you have: `file = ...`.
- Views take the hero as image 1, and say the object's shape: "the same object, the same shape,
  materials and colours" (never the person's "same face and hair": that once drew a man's portrait in
  front of a building, D-040).
- A worn or held object is given to the character's pictures as a reference (see Hero, Poses, Scenes).

#### Common failures and what to do

- **Flat or round objects look the same from every side:** a plate, a book, a coiled rope. Ask only for
  views that really differ: front, edge-on, from above.
- **Near-copies instead of a turn:** some models return the object barely turned (0007); the models'
  notes below say which turn objects for real.
- **A top view from a side-on hero** is hard for most models: try one item first.
- **Text and logos:** quote the words and say where they are (a label that reads "FLOUR" across the
  front); how well a model renders text is in its notes (`text`). Keep words short, or add them later.
- **Tiny parts** (a clasp, a small charm) move or vanish: make a close-up item of the detail and give it
  as a reference where it matters.
- **Hands appear** holding the object: "standing alone on a mid-grey surface".
- **The words of the presentation get drawn:** "Prop presentation frame" put a wooden picture frame
  round a mace (stress tests 2026-10-14). Say what the picture is ("A prop photograph from a 3D animated
  film: one bronze mace lying on a mid-grey surface") and avoid "frame", "display", "print" or "poster"
  unless you want that thing in the picture.
- **Engraved or printed words on the object** (a monogram "J.A." on a lighter) came out and stayed the
  same in scenes when they were quoted in the hero and the object was the reference.

#### Examples

The examples use `qwen-image-2.1-turbo`, the default model of Hone Frame's examples, and show the form
only: how long a prompt may be, how many references a model takes, how to name them and whether its
pictures may be used commercially are in each model's notes below.

##### The object hero, from text

```toml
[objects.mug.hero]
model = "qwen-image-2.1-turbo"
size = "1024x1024"
hold = true
prompt = "Product reference photograph: one tall straight-sided ceramic mug about ten centimetres high stands alone on a plain mid-grey surface, seen from the front at a slight angle from above, the whole mug in the frame. It is glazed stoneware in a deep teal colour with a thin cream rim, a round handle on its right side and three small white dots in a row near the base. The surface and the background are plain seamless white, lit by one soft key light from the upper left with a soft shadow under the mug; nothing else is in the picture. Natural colours, sharp focus, photorealistic."
```

```toml
[objects.bicycle.hero]
model = "qwen-image-2.1-turbo"
size = "1024x576"
hold = true
prompt = "Clean 2D animation prop design: one old city bicycle stands alone in exact side view, facing right, the whole bicycle in the frame from the front tyre to the rear tyre. It has a step-through frame painted pale mint green, a brown leather saddle, curved swept-back handlebars with a small silver bell, a black wicker basket in front of the handlebars, black mudguards and a chrome chain guard. It stands on a plain flat mid-grey background in one soft key light from the upper left. Bold clean outlines, flat colour fills, simple soft shading."
```

##### Other sides of the object

```toml
[objects.mug.top]
model = "qwen-image-2.1-turbo"
size = "1024x1024"
refs = ["mug.hero"]
prompt = "The same mug from image 1 seen from high above, looking down into it: the round cream rim, the teal inside and the handle on the right. The same object, the same shape, materials and colours. It stands alone on a plain mid-grey surface, one soft key light from the upper left."
```

```toml
[objects.bicycle.front]
model = "qwen-image-2.1-turbo"
size = "832x1248"
refs = ["bicycle.hero"]
prompt = "The same bicycle from image 1 facing the camera head-on: the front tyre, the black wicker basket and the curved handlebars with the silver bell in front. The same mint-green frame, brown saddle, black mudguards and colours. Alone on a plain mid-grey background, one soft key light from the upper left. Bold clean outlines, flat colour fills."
```

##### A small change of the object: colour, state, detail

```toml
[objects.mug.empty-and-stained]
model = "qwen-image-2.1-turbo"
size = "1024x1024"
refs = ["mug.hero"]
prompt = "The same mug from image 1 after use: a faint brown coffee ring inside the cream rim and one dry drip down the outside below the handle. Same shape, teal glaze, cream rim, white dots and angle. Alone on a plain mid-grey surface, one soft key light from the upper left."
```

##### An object made from several pictures

```toml
[objects.breakfast-tray.hero]
model = "qwen-image-2.1-turbo"
size = "1024x576"
refs = ["mug.hero", "plate.hero"]
prompt = "A plain light-wood breakfast tray seen from a slight angle above, alone on a plain mid-grey surface, with the teal mug from image 1 on its left and the white plate from image 2 on its right, both exactly as in their pictures. Nothing else is on the tray or the surface. Even soft studio light, photorealistic."
```

##### For commercial work

A model whose licence does not allow commercial use (part 3 warns of it) is for trying things out and
for work you will not sell. For commercial pictures, write the item for a model that allows it, in the
form its notes ask for:

```toml
[objects.mug.hero]
model = "z-image-turbo"
size = "1024x1024"
hold = true
prompt = "Product reference photograph. One tall straight-sided ceramic mug about ten centimetres high stands alone on a plain mid-grey surface, seen from the front at a slight angle from above, the whole mug in the frame. It is glazed stoneware in a deep teal colour with a thin cream rim, a round handle on its right side and three small white dots in a row near the base. The surface and the background are plain seamless white, lit by one soft key light from the upper left with a soft shadow under the mug. Natural colours, sharp focus, photorealistic."
```

```toml
[objects.mug.top]
model = "qwen-image-edit-2511"
size = "1024x1024"
refs = ["mug.hero"]
prompt = "Show the mug from image 1 from high above, looking down into it: the round cream rim, the teal inside and the handle on the right. Keep exactly the same object, shape, materials and colours. It stands alone on a plain mid-grey surface, one soft key light from the upper left."
```
