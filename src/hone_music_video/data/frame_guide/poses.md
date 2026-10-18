### Poses

A pose is the character's whole figure doing something with its body: walking, sitting, kneeling,
reaching, holding. It is made from the hero, and a model that is shown a standing hero tends to **keep
the pose of the picture it is shown**: asked in words alone, an edit model turned "running" into a hop,
"seated" into a crouch and "kneeling" into half-standing (research, 2026-10-03). There are two ways:

- **In words:** the hero as image 1 and the pose described plainly and completely. Simple poses
  (standing, sitting on a stool, walking) usually come out; check every one.
- **With a pose picture of your own:** a photograph, a drawing or a render of any figure in the pose,
  given as an item with `file = "assets/kneeling.png"` and referred to like any item. A second picture
  in the pose fixed kneeling, running, sitting and a fighting stance in a realistic and a 2D style
  (research, 2026-10-03). The pose item then has two references: the person, then the pose picture.

#### What the prompt must say

1. **The pose, plainly:** where the weight is, what each arm and leg does, which way the body faces
   ("sitting upright on a plain wooden stool, her thighs level, both feet flat on the floor, each hand
   resting on its knee"). With a pose picture, the roles of the pictures instead: "the woman from image 1
   in exactly the body pose of the figure in image 2", naming the parts that matter ("the same arm
   positions, the same body angle"), and do not describe a different pose in words: it fights the
   picture.
2. **Who it is**, and what must stay: face, hair length, build, every garment by name.
3. **With a pose picture, that only the person is drawn:** "only the woman is in the picture; the figure
   in image 2 is not drawn; do not copy its body, clothes or colour".
4. **Background and light** as the hero's: "plain mid-grey background, one soft key light from the upper left".

#### References, in this order

1. the character's hero (or a view facing the way the pose faces: a pose picture's angle is copied too);
2. an object the hands hold, made first as an object;
3. the pose picture, last, when you use one.

#### Common failures and what to do

- **The pose drifts back to standing:** describe it more completely, or give a pose picture and say
  which image it is.
- **The figure comes out slimmer or more 3D-looking**, mostly in 2D styles: say the build and the style
  in the prompt ("her slim build", "flat 2D colours and clean outlines").
- **The pose picture's body pulls the figure:** an adult in the picture can make a child look older.
  Choose a picture of a similar build.
- **Hands holding small objects** come out broken more often than empty hands: keep the object large
  and simple, or show it resting rather than gripped.
- **Two bodies in contact** (a hug, a dance hold, a fight): gentle contact in a medium or close shot
  can work, force between two bodies in a wide shot does not (see Scenes): show them side by side, one
  from behind, their hands in close-up, or the moment just before or after.
- **Left and right:** say which hand does what, as the character's own left and right.

#### Examples

The examples use `qwen-image-2.1-turbo`, the default model of Hone Frame's examples, and show the form
only: how long a prompt may be, how many references a model takes, how to name them and whether its
pictures may be used commercially are in each model's notes below.

##### In words, the hero as the only reference

```toml
[characters.woman.sitting]
model = "qwen-image-2.1-turbo"
size = "832x1248"
refs = ["woman.hero"]
prompt = "The same woman from image 1 sitting upright on a plain wooden stool of knee height, seen from the front, turned slightly to her left: her back straight, her thighs level, her knees bent at right angles, both feet flat on the floor, each hand resting palm down on its knee, full body head to toe. She is a woman of about thirty with shoulder-length dark brown hair; same face, hair, oatmeal jumper, dark-blue jeans and white trainers. Only the woman and the stool are in the picture. Plain mid-grey background, one soft key light from the upper left."
```

```toml
[characters.woman.holding-mug]
model = "qwen-image-2.1-turbo"
size = "832x1248"
refs = ["woman.hero", "mug.hero"]
prompt = "The same woman from image 1 standing, holding the mug from image 2 in both hands in front of her chest, her elbows bent and close to her body, her head bowed, looking down into the mug, full body head to toe. Same face, shoulder-length dark brown hair, oatmeal jumper, dark-blue jeans and white trainers, and exactly the same mug: its shape, colour and pattern. Only the woman and the mug are in the picture. Plain mid-grey background, one soft key light from the upper left."
```

##### With a pose picture of your own

On a model whose pose support is "as a reference picture" (part 3), the pose picture is an ordinary
picture, less exact than a control. Say plainly that it is only a guide for the pose.

```toml
[characters.grandfather.reaching-pose]
file = "assets/reaching-up.png"            # any figure in the pose: a photo, a drawing, a render

[characters.grandfather.reaching]
model = "qwen-image-2.1-turbo"
size = "832x1248"
refs = ["grandfather.hero", "grandfather.reaching-pose"]
prompt = "Image 2 is only a pose guide: draw the elderly man from image 1 in exactly the body pose and position of the figure in image 2, reaching up high with his right arm, on tiptoe; do not copy the figure's body, clothes or colour. Only the man is in the picture. Keep his face, short white beard, glasses, moss-green cardigan, white shirt, brown corduroy trousers and brown shoes. Plain mid-grey background, one soft key light from the upper left. Clean 2D animation style."
```

##### Without references: someone new

An item without references draws a pose described in words for a new figure, since no standing hero
pulls it back; but it cannot keep your character. Use one for a stranger or a crowd member:

```toml
[characters.runner.hero]
model = "qwen-image-2.1-turbo"
size = "832x1248"
prompt = "Photorealistic full-length photograph of one young woman running fast across a plain white studio, seen from the side: her left leg stretched forward, her right knee lifted behind her, her arms bent at the elbows and swinging, her body leaning forward. She wears a grey running vest, black shorts and white running shoes. Even soft studio light."
```

##### For commercial work

A model whose licence does not allow commercial use (part 3 warns of it) is for trying things out and
for work you will not sell. For commercial pictures, write the item for a model that allows it, in the
form its notes ask for:

```toml
[characters.woman.sitting]
model = "qwen-image-edit-2511"
size = "832x1248"
refs = ["woman.hero"]
prompt = "Make the woman from image 1 sit upright on a plain wooden stool, her thighs level, both feet flat on the floor, each hand resting on its knee. Only the woman and the stool are in the picture. She is a woman of about thirty with shoulder-length dark brown hair; keep exactly the same face, hair, oatmeal jumper, dark-blue jeans and white trainers. Plain mid-grey background, one soft key light from the upper left."
```

```toml
[characters.woman.kneeling]
model = "flux.2-klein-4b"
size = "832x1248"
refs = ["woman.hero", "woman.kneeling-pose"]
prompt = "The woman from image 1 kneeling on one knee, in exactly the body pose of the figure in image 2. A woman of about thirty, shoulder-length dark brown hair. Same face, hair, oatmeal jumper, dark-blue jeans and white trainers. Only the woman is shown. Plain mid-grey background, one soft key light from the upper left."
```
