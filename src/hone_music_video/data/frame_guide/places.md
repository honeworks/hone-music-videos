### Places

A place is a location that recurs: a kitchen, a street corner, a park. Give it a hero (a wide view of
the whole place, **empty of people**), then the other views your scenes will need (the reverse angle,
each side, a high view) and its states (evening, rain, lights on). A place with a picture stays the same
room from scene to scene; a place given only as a word changes in every picture (the window moves, the
furniture changes: hone-music-video weak point 21).

#### What the prompt must say

1. **The view:** "a wide view of a small kitchen, seen from the doorway at eye level".
2. **The layout, with positions:** "a straight wooden counter along the back wall, a window above the
   sink on the left, a small round table with two chairs in the front right". These anchors are what
   later views and scenes must keep.
3. **Materials and colours:** "cream-painted cabinets, light oak worktop, white square wall tiles,
   terracotta floor tiles".
4. **The light, as daylight or a lamp:** "soft morning daylight from the window on the left". Neutral
   studio light suits characters and objects on a plain backdrop, not places (0007 made daylight the
   place default). Name the light source: a lamp, the moon, a neon sign through the blinds.
5. **That it is empty:** "the kitchen is empty and quiet". A place described with any hint of people
   fills with them (D-039).
6. **The style**, as for the characters, so they fit together later.

#### References

- The hero needs none.
- Every other view and state takes the hero as image 1 and says "the same place: the same layout,
  furniture, materials and colours" (never "the same face": a view of a place once came out as a man's
  portrait, D-040).
- In scenes, the place's best-matching view is one reference among the characters and objects.
- **The place picture fixes the camera.** A scene keeps the viewpoint of the place picture it is given:
  "a straight top-down view of the alley from image 1" came back as the alley at eye level with tiny
  figures, and "looking down into a puddle" kept the street view (stress tests 2026-10-14). Make every
  viewpoint a scene needs as a view of the place (`market.above`, `stairs.from-below`), or leave the
  place picture out and describe the place in words for that one shot.
- **States keep the layout:** a night view and a dawn view made from one place kept the same spring,
  stones, reeds and tree in every scene; make the times of day as states of one hero.

#### Common failures and what to do

- **People appear:** state that it is empty, and keep people out of the place's description.
- **The layout moves** between views: name each anchor with its position in every view prompt.
- **A reverse angle invents a new room:** it has never been seen. Describe what is behind the camera of
  the hero ("the doorway, a tall white fridge to its right") and expect to redo it once.
- **Neutral grey light** makes an outdoor place look like a studio: give the time of day.
- **Signs and labels** are unreliable, most of all in edits: quote short words and say where they are
  (a shop sign that reads "BAKERY"); the model's notes (`text`) say how well it renders them. Keep
  readable text short, or leave it out.
- **Wide places shrink detail:** small things on shelves blur. Make a closer view of the part a scene
  needs.
- **Mirrored text** (a door's lettering seen from inside, a sign reflected upside down in a puddle)
  came out as a blur or not at all. Text read the right way round, quoted, came out well on a model
  whose notes say so.

#### Examples

The examples use `qwen-image-2.1-turbo`, the default model of Hone Frame's examples, and show the form
only: how long a prompt may be, how many references a model takes, how to name them and whether its
pictures may be used commercially are in each model's notes below.

##### The place hero, from text

```toml
[places.kitchen.wide]
model = "qwen-image-2.1-turbo"
size = "1024x576"
hold = true
prompt = "Photorealistic interior photograph: a wide view of a small home kitchen seen from the doorway at eye level. A straight light-oak worktop runs along the back wall under cream-painted cabinets, with a white ceramic sink below a window on the left. A small round wooden table with two chairs stands in the front right. The walls have white square tiles above the worktop, the floor is terracotta tiles. A kettle and a wooden bread board stand on the worktop. Soft morning daylight comes through the window on the left. The kitchen is empty and quiet. Natural colours, sharp focus."
```

```toml
[places.park.wide]
model = "qwen-image-2.1-turbo"
size = "1024x576"
hold = true
prompt = "Illustrated storybook painting: a wide view of a small city park on a calm spring afternoon, seen from the gravel path at eye level. A curved path runs from the front left to a green wooden bench under a large old plane tree in the centre. Behind it, a low red-brick wall with a black iron gate on the right, and tall houses beyond the wall. Short green grass, a round flowerbed of yellow tulips on the left. Soft warm sunlight from the right with long gentle shadows. The park is empty and quiet. Soft watercolour textures, gentle colours."
```

##### Other views of the same place

```toml
[places.kitchen.reverse]
model = "qwen-image-2.1-turbo"
size = "1024x576"
refs = ["kitchen.wide"]
prompt = "The same kitchen from image 1 seen from the opposite side, looking back towards the doorway: the open white door in the centre, a tall white fridge to its right, the round wooden table and two chairs now in the front left. The same cream cabinets, light-oak worktop, white wall tiles, terracotta floor and soft morning daylight. The kitchen is empty."
```

```toml
[places.kitchen.high]
model = "qwen-image-2.1-turbo"
size = "1024x576"
refs = ["kitchen.wide"]
prompt = "The same kitchen from image 1 seen from high in the corner by the doorway, looking down: the same layout, furniture, materials, colours and morning light. The kitchen is empty."
```

##### A state: change only the light or the weather

```toml
[places.kitchen.evening]
model = "qwen-image-2.1-turbo"
size = "1024x576"
refs = ["kitchen.wide"]
prompt = "The same kitchen from image 1 in the evening: dark blue sky in the window, a warm yellow ceiling light on, soft warm shadows. Same place, same layout, furniture, materials and colours, same camera. The kitchen is empty."
```

##### A place made from pictures of its parts

```toml
[places.kitchen.corner]
model = "qwen-image-2.1-turbo"
size = "1024x576"
refs = ["kitchen.wide", "kettle.hero"]
prompt = "A closer view of the worktop corner of the kitchen from image 1, with the kettle from image 2 standing by the sink under the window. The same cream cabinets, light-oak worktop, white wall tiles and soft morning daylight from the left. The kitchen is empty. Photorealistic."
```

##### For commercial work

A model whose licence does not allow commercial use (part 3 warns of it) is for trying things out and
for work you will not sell. For commercial pictures, write the item for a model that allows it, in the
form its notes ask for:

```toml
[places.kitchen.wide]
model = "z-image-turbo"
size = "1024x576"
hold = true
prompt = "Photorealistic interior photograph. A wide view of a small home kitchen seen from the doorway at eye level. A straight light-oak worktop runs along the back wall under cream-painted cabinets, with a white ceramic sink below a window on the left. A small round wooden table with two chairs stands in the front right. The walls have white square tiles above the worktop, the floor is terracotta tiles. A kettle and a wooden bread board stand on the worktop. Soft morning daylight comes through the window on the left. The kitchen is empty and quiet. Natural colours, sharp focus."
```

```toml
[places.kitchen.reverse]
model = "qwen-image-edit-2511"
size = "1024x576"
refs = ["kitchen.wide"]
prompt = "Show the kitchen from image 1 from the opposite side, looking back towards the doorway: the open white door in the centre, a tall white fridge to its right, the round wooden table and two chairs now in the front left. Keep exactly the same place: cream cabinets, light-oak worktop, white wall tiles, terracotta floor and soft morning daylight. The kitchen is empty."
```

```toml
[places.kitchen.evening]
model = "flux.2-klein-4b"
size = "1024x576"
refs = ["kitchen.wide"]
prompt = "The kitchen from image 1 in the evening: dark blue sky in the window, a warm yellow ceiling light on, soft warm shadows. Same place, same layout, furniture, materials and colours, same camera. The kitchen is empty."
```
