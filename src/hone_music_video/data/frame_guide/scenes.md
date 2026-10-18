### Scenes

A scene puts accepted pictures together into one new picture: a character in a place with an object,
doing one thing. Its references are exactly the pictures you choose, in the order you write them, and
its prompt must say which picture is which. Use `count = 3` (or more) for a scene: people who make
films this way keep about one take in three, and you pick. For a hard scene, write two or three
different shots of the moment in `prompts` instead: in the stress tests (2026-10-14) a hard moment that
failed as one shot usually came out in another (the same fight as a close shot of the hands, a rescue
seen from the shore instead of from the water).

#### What the prompt must say

Start with **the kind of picture**, in the same words in every scene of the project: "A frame from a
feature-length stylised 3D animated film.", "A still from a 1920s period drama shot on 35mm film." With
that first sentence, and the shot, the lens and the light named in every prompt, five projects in five
styles kept their look from the first scene to the last (stress tests 2026-10-14). Leave out words of
computer graphics and advertising ("photorealistic", "razor-sharp", "8k", "glowing eyes"): they pull a
film still toward a render.

1. **The roles of the pictures, first and always:** "The woman from image 1 sits at the round table in
   the kitchen from image 2, holding the teal mug from image 3." When this sentence was left out of
   scenes, the model no longer knew who or what it was drawing: a sword appeared that nobody asked for,
   and a woman became "he" (root cause C).
2. **One clear action**, as what can be seen: "she holds the mug in both hands below her chin and looks
   out of the window". Describe the frame, not the story behind it.
3. **The framing and the lens:** "a medium shot from the waist up, the camera at eye level by the
   doorway, 50mm lens", "wide low-angle shot, 24mm lens". One shot per prompt. A face
   that must be recognised needs a medium shot or closer; in a wide shot faces are a few pixels and come
   out messy: show people small, from behind or turned away there.
4. **What changes from the references:** clothes, hair, a stain, the time of day. What is not said, the
   reference wins.
5. **Light and style:** where each light comes from and its colour ("orange campfire glow from below
   on his face, cold moonlight from behind"), and the same style words as the characters. The light is
   most of the mood; a fire or a lamp as "the only light" came out as asked.
6. **How many there are:** "one horse", "the girl, alone at the counter". A scene with several
   characters can draw one of them twice (see below); saying the number helps.
7. **Where it is, fully, when the place has no picture:** "in a poppy meadow" in one clause is not
   enough when the characters' pictures are on a plain backdrop: the backdrop shows through and the
   scene comes out on grey or cream paper. Describe the ground, the background and the light, or give
   the place a picture.
8. **What is seen, never a comparison:** the model draws the words. "A cloud of bees" drew a white
   cloud with bees on it, and "holds his paw over her head like an umbrella" drew an umbrella. Write
   "hundreds of small bees in a loose swarm around his head", "holds one paw above her head to keep the
   rain off". Words for a thing ("frame", "photograph", "poster") can be drawn as that thing too.

Name each object by a short name and its image ("the teal mug from image 3"), not its whole
description in the middle of a sentence (hone-music-video weak point 23).

#### References, in order

1. the characters (one picture each: the view facing the way the shot sees them; a close-up for a face
   shot);
2. the place (the view matching the camera);
3. the objects.

Stay within the number of references the model takes (part 3), and give no more than the shot shows:
a character far in the background can be words ("a small girl in white on his back"). **A changed
costume needs its own picture:** a scene keeps what the reference wears, so a hero in a beekeeper's hat
was drawn in bed in the hat; give the scene the costume item (`pip.pyjamas`, `darvin.sleeping`). **The
place picture fixes the camera:** a top-down or a straight-up shot needs a view of the place from there,
or no place picture (see Places). One full-body picture per person: a
front and a side of one person, or a portrait beside the full figure, can become two people (the
model's notes say where this was seen). **The angle of a reference is copied:** a front picture for a shot from behind
gives a person who faces the wrong way, or a laptop typed on from its back; give the back view for a
shot from behind.

#### Common failures and what to do

- **Who is who is lost:** the roles sentence is missing or vague. Name every picture by number.
- **Two characters become twins:** their heroes already share a face. Fix the heroes, not the scene.
- **One character is drawn twice** (two horses, two bears, two girls at one counter, a dragon with a
  head at each end), most often with three to five references and several characters in one picture:
  say the number ("one horse", "only one girl"), give fewer references, and keep the take where it
  did not happen. A pick among two or three takes usually has one without it.
- **Identical twins on purpose** (one actor, two characters): make the second from the first's hero
  ("the identical twin brother of the man in image 1 … he adds a pencil moustache and an eyepatch"), and
  tell them apart by large things (white dinner jacket against dark pinstripe, a moustache, an
  eyepatch), never by the face. That held in every scene; a small detail did not always (an eyepatch
  became dark glasses in one take).
- **More than two named people:** three or four characters with their own pictures can work (three
  people and a dog in a kitchen came out in one of two takes), but each one more raises the chance of
  someone drawn twice or missing. Keep the people who matter to the shot; others are unnamed extras
  described in words.
- **Bodies in contact.** What came out: gentle contact in a medium or close shot (a hug, a forehead
  to a horse's forehead, a child asleep against a bear, a hand on a forehead, a child riding an
  animal), and every close shot of hands (two hands on one revolver, a gloved hand on a wrist). What did
  not: force between two bodies in a wide shot (a horse biting a dragon's neck in none of three takes,
  a man hanging from a ledge by one wrist, a grapple, a body rolling under fire), which merged, swapped
  roles or grew parts. Show the moment as hands in close-up, as the moment just before or after, or
  with one body clearly in front of the other.
- **Hands holding small things** break: prefer the object resting on the table, or held in both hands.
- **Readable text:** quote it and say where it is ("a paper note taped to the door reads 'DELIVERY -
  RING TWICE' in black marker"); how well a model renders it is in its notes (`text`). Text that must
  read **mirrored or upside down** (door lettering from inside, a sign in a puddle) came out as a blur
  or not at all: keep it out of the point of the picture.
- **Mirrors:** a person in profile with her reflection facing us came out, with a one-sided mark on the
  matching side; say plainly what is seen in the glass and what outside it.
- **Left and right** come from the reference, not the words: check a one-sided detail on the hero (see
  Hero) and say the side again in the scene.
- **An extreme camera angle against the action** ("looking straight up the stairwell, her face looking
  down at the camera") came out at eye level: give the angle a place view of its own, or choose an angle
  closer to the place picture.
- **Small faces in wide shots** are fine when nobody has to be recognised (three figures in a ship's
  rigging, a man and a horse beside a fallen dragon); make the face shots separately.
- **A picture outweighs the words:** a pendant close-up given for a back view was painted on her back,
  even after redos that said otherwise (hone-music-video D-146). Give a picture only the references of
  what it shows.
- **References cost time:** each picture makes the image slower (the measured time is in part 3). Give
  what the picture needs, not more.
- **Too many words with many pictures** overloads the model: keep a many-picture prompt short and
  concrete; the model's notes may give a length.

#### A scene made from another scene

A scene's picked image can be the only reference of the next one: "The same picture as image 1, the same
girl, pose, lens, walkway and framing. Change only the light: the great lamp is now lit …" kept
everything and changed the light (stress tests 2026-10-14). The new scene waits for the pick of the one
it is made from, while the run makes the rest.

#### Examples

The examples use `qwen-image-2.1-turbo`, the default model of Hone Frame's examples, and show the form
only: how long a prompt may be, how many references a model takes, how to name them and whether its
pictures may be used commercially are in each model's notes below.

##### Characters, place and object, each by number

One picture of each person, then the place, then the objects.

```toml
[scenes.coffee]
model = "qwen-image-2.1-turbo"
size = "1024x576"
count = 3
refs = ["woman.three-quarter", "kitchen.wide", "mug.hero"]
prompt = "Photorealistic film still. The woman from image 1 sits at the round wooden table in the kitchen from image 2, holding the teal mug from image 3 in both hands below her chin and looking out of the window. A medium shot from the waist up, at eye level, from the doorway. She is one woman, alone in the kitchen, with the same face, shoulder-length dark brown hair and oatmeal knitted jumper as in image 1. The kitchen keeps its light-oak worktop, cream cabinets and the window on the left; the mug keeps its shape, teal glaze and cream rim. Soft morning daylight from the window on the left. Natural colours."
```

```toml
[scenes.park-bench]
model = "qwen-image-2.1-turbo"
size = "1024x576"
count = 3
refs = ["grandfather.three-quarter", "courier.side", "park.wide"]
prompt = "In the park from image 3, the elderly man from image 1 sits on the green bench on the left and the young courier from image 2 stands beside it on the right, holding his bicycle by the handlebars, the two of them talking. Medium wide shot at eye level, both faces visible. Warm afternoon sunlight from the right. Illustrated storybook style, soft watercolour textures."
```

##### Without references: scenes without your characters

An establishing picture with nobody recognisable, a crowd, a view from far away, or a test of a
composition before you write it with references:

```toml
[scenes.street-morning]
model = "qwen-image-2.1-turbo"
size = "1024x576"
count = 2
prompt = "Photorealistic wide street photograph on a quiet early morning. A narrow residential street of three-storey brick houses with white window frames, seen from the middle of the pavement at eye level. Far down the street a small figure walks a dog away from the camera, its back turned. Parked bicycles lean against black railings on the left. Low golden sunlight from the end of the street, long soft shadows, a light haze. Natural colours."
```

##### For commercial work

A model whose licence does not allow commercial use (part 3 warns of it) is for trying things out and
for work you will not sell. For commercial pictures, write the item for a model that allows it, in the
form its notes ask for:

```toml
[scenes.coffee]
model = "qwen-image-edit-2511"
size = "1024x576"
count = 3
refs = ["woman.three-quarter", "kitchen.wide", "mug.hero"]
prompt = "Place the woman from image 1 in the kitchen from image 2: she sits at the round wooden table holding the teal mug from image 3 in both hands below her chin, looking out of the window. Keep her face, hair and oatmeal jumper, the kitchen's layout and colours, and the mug's shape and colour. Soft morning daylight from the left. Photorealistic."
```

When the model takes fewer references than the scene has things, give the person and the place, and
describe a simple object in words:

```toml
[scenes.window]
model = "flux.2-klein-4b"
size = "1024x576"
count = 3
refs = ["woman.three-quarter", "kitchen.wide"]
prompt = "The woman from image 1 stands at the window of the kitchen from image 2, holding a teal mug, looking out. Medium shot from the waist up, eye level. Same face, hair and oatmeal jumper; same kitchen layout and colours. Soft morning daylight. Photorealistic."
```
