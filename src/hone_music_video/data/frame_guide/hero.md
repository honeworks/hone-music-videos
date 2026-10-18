### Hero

A character's hero is the identity picture every other picture of it is made from: the whole figure,
from the front, standing still, alone, on a plain mid-grey background, in one soft white key light from
one side. Make it first, set `hold = true`, and only go on when you would be happy to see this exact person, face and clothes in
every later picture. A hero that is not quite right gets worse in every edit made from it.

#### What the prompt must say

Write plain sentences, not a list of tags, in this order:

1. **The shot:** "A full-length studio photograph of one woman standing facing the camera, the whole
   figure from head to feet." For a drawn style, name the medium here ("A clean 2D animation character
   design of one woman ..."). Name the kind of picture once, as the film or book it belongs to ("A
   costume test photograph from a 1920s period film", "A character page from a gouache picture book"):
   the scenes then name the same kind ("A still from a 1920s period drama"). Avoid words for a physical
   thing that can be drawn: "Prop presentation frame" drew a wooden picture frame round a mace, and "A
   photograph from a 1920s film" gave a dog a black photo-print border (stress tests 2026-10-14).
2. **The pose:** "a neutral standing pose, the weight on both feet, the arms relaxed at her sides, her
   hands empty." A neutral pose is what an edit model can turn and re-pose later.
3. **Who it is, by what can be seen:** age, build and height, face shape, skin, eyes, eyebrows, hair
   (length, colour, parting), facial hair. Describe what is visible; a label barely helps ("a 1970s
   look" changes little; "a brown corduroy jacket with wide lapels" changes a lot). Models fall back to
   their defaults unless the visible details are spelled out (research: plain sentences, not labels).
   **Age drifts toward the style's default:** a "seven-year-old" in a picture-book style came out three
   or four, a man of "about sixty" over seventy. Add what the age looks like ("tall for her age, a gap
   where a front tooth is missing", "a few grey hairs at the temples, no deep wrinkles") and check it.
4. **Every garment**, one after another, with its material, colour and fit, and on which side anything
   one-sided sits ("a silver watch on her left wrist"). Footwear too: it shows in every full figure.
   A rich costume with one or two props of its own (a helmet, a leopard-skin vest, an orange jacket with
   a bandage across the nose) is what keeps a character recognisable in a wide shot where the face is a
   few pixels; a plain outfit leaves only the face to carry it.
5. **The background and light:** "on a plain seamless mid-grey background, lit by one soft key light
   from the upper left." White light keeps the hero usable in any later scene (D-021); a coloured or
   dramatic light gets copied into every edit. One soft key light from a side shows the shape of the
   face and the texture of the clothes, and scenes made from it keep that modelled look; flat, even
   light on white was copied into scenes as a flat, lit-from-nowhere look (D-078). A scene that has no
   place picture can pick up the plain backdrop (see Scenes).
6. **The style**, in a few concrete words, at the start (the model's notes say if it also helps at the
   end).

Say everything as something that **is** there: "no hat" in a prompt tends to draw a hat (D-034); write
"her head is bare, her hair loose". Whether the model takes a `negative` at all is in its notes below.

#### References

Usually none: the hero is drawn from words. Two exceptions:

- A garment, a piece of jewellery or a tool that must look exactly the same everywhere: make it first as
  an object (see Objects) and give it as image 1 to a model that takes references ("the woman wears the
  jacket from image 1").
- A picture you made elsewhere: use `file = "assets/anna.png"` instead of a prompt.

#### Common failures and what to do

- **Near-identical images from different seeds.** With some models a new seed of the same prompt gives
  almost the same picture, so `count = 3` gives near-copies (the model's notes below say so). To choose
  between readings, write two or three hero items whose prompts differ in what your description leaves
  open (face shape, build, how a garment is worn), hold them all, and point the views at the one you
  keep (D-037).
- **Small details of the face move later** (a mole, a small scar): they move between pictures even when
  stated. Keep them large and few, or accept that they drift.
- **The face is small in a full figure** (about a tenth of the height): make the face close-ups from
  the hero in the Faces stage, not from text.
- **Someone else appears**, or a second figure: say "one woman, alone".
- **Left and right swap** in later edits: state the side here, and again in every edit that shows it.
  The hero itself can come out mirrored: "an eyepatch over his LEFT eye", in capitals, was drawn over his
  right eye, and every scene made from that hero copied the wrong side. Check one-sided details on the
  hero before you accept it (his left is on the right of the picture when he faces you), and redo it
  until the side is right: a scene copies the hero, not the words.
- **A change of costume does not come from words alone.** Given a hero in a beekeeper's hat, a scene
  "now in striped pyjamas" kept the hat in bed. Make each costume the story needs as an item of its own
  (`pip.pyjamas`, made from the hero) and give that one to the scenes; a close-up that is about the
  change ("his helmet off, his hair rumpled") can work from words.
- **Two characters drawn from similar words get the same face.** Give characters who meet faces that
  differ in the face itself (face shape, nose, brows, age gap), not only in hair and clothes.

#### Examples

The examples use `qwen-image-2.1-turbo`, the default model of Hone Frame's examples, and show the form
only: how long a prompt may be, how many references a model takes, how to name them and whether its
pictures may be used commercially are in each model's notes below.

##### From text alone

The shot and the style first, then the pose, the person, every garment, the background and light.

```toml
[characters.woman.hero]
model = "qwen-image-2.1-turbo"
size = "832x1248"
seed = 11
hold = true
prompt = "Photorealistic character reference: one full-length studio photograph of one woman, full body head to toe, standing facing the camera in a neutral pose, the weight on both feet, her arms relaxed at her sides, her hands empty. She is about thirty, of average height and slim build, with an oval face, warm light-brown skin, dark brown eyes, straight dark eyebrows and shoulder-length dark brown hair with a side parting on the left. She wears a loose oatmeal-coloured knitted jumper with the sleeves pushed to the elbows, straight dark-blue jeans and plain white canvas trainers, and a thin silver watch on her left wrist. She is alone on a plain seamless mid-grey background lit by one soft key light from the upper left, with a faint shadow at her feet; no props, no text. Natural colours, sharp focus, photorealistic."
```

```toml
[characters.grandfather.hero]
model = "qwen-image-2.1-turbo"
size = "832x1248"
hold = true
prompt = "Clean 2D animation character design: one elderly man, full body head to toe, standing facing the viewer in a neutral pose, his arms relaxed at his sides, his hands empty. He is about seventy-five, tall and thin with a slight stoop, a long narrow face, pale skin with deep laugh lines, light blue eyes, thick white eyebrows, short white hair combed back and a neat short white beard. He wears a moss-green wool cardigan buttoned over a white collared shirt, brown corduroy trousers and polished brown lace-up shoes, and round tortoiseshell glasses. He stands alone on a plain flat mid-grey background in one soft key light from the upper left; no props, no text. Bold clean outlines, flat colour fills, simple soft shading, clean 2D animation style."
```

```toml
[characters.courier.hero]
model = "qwen-image-2.1-turbo"
size = "832x1248"
hold = true
prompt = "Stylised 3D animation character reference: one young bicycle courier, full body head to toe, standing facing the viewer in a neutral pose, arms relaxed, hands empty. A man of about twenty with a round face, dark skin, short black curly hair and a thin moustache. He wears a bright yellow waterproof jacket, black cycling shorts over grey leggings, black trainers and a red cap worn backwards. Alone on a plain mid-grey background, one soft key light from the upper left, no props, no text. Soft rounded shapes, smooth surfaces, stylised 3D animated film look."
```

##### Wearing something made first

When a garment or an object must be exactly the one you made, give its picture as image 1 and say what
the person wears from it.

```toml
[characters.woman.hero]
model = "qwen-image-2.1-turbo"
size = "832x1248"
refs = ["jacket.hero"]                      # image 1: a garment made first as an object
hold = true
prompt = "Photorealistic character reference: one full-length studio photograph of one woman of about thirty, full body head to toe, standing facing the camera in a neutral pose, arms relaxed, hands empty. She has an oval face, warm light-brown skin, dark brown eyes and shoulder-length dark brown hair parted on the left. She wears exactly the green rain jacket from image 1, zipped up, over dark-blue jeans and white trainers. Alone on a plain seamless mid-grey background, one soft key light from the upper left, no text."
```

##### Several things worn

Each picture is named by its number.

```toml
[characters.baker.hero]
model = "qwen-image-2.1-turbo"
size = "832x1248"
refs = ["apron.hero", "cap.hero"]          # image 1, image 2
hold = true
prompt = "Photographic character reference: one studio photograph of one man, full body head to toe, facing the camera, neutral standing pose, arms relaxed at the sides, hands empty, plain seamless light-grey studio backdrop, even soft studio lighting. He is about forty, broad and stocky, with a square face, ruddy skin, brown eyes and a short brown beard. He wears the flour-dusted blue apron from image 1 over a white T-shirt, grey work trousers and black clogs, and the white baker's cap from image 2."
```

##### For commercial work

A model whose licence does not allow commercial use (part 3 warns of it) is for trying things out and
for work you will not sell. For commercial pictures, write the item for a model that allows it, in the
form its notes ask for:

```toml
[characters.woman.hero]
model = "z-image-turbo"
size = "832x1248"
seed = 11
hold = true
prompt = "Photorealistic character reference. A full-length studio photograph of one woman standing facing the camera, the whole figure from head to feet visible. She stands in a neutral pose, the weight on both feet, her arms relaxed at her sides, her hands empty. She is about thirty, of average height and slim build, with an oval face, warm light-brown skin, dark brown eyes, straight dark eyebrows and shoulder-length dark brown hair with a side parting on the left. She wears a loose oatmeal-coloured knitted jumper with the sleeves pushed to the elbows, straight dark-blue jeans and plain white canvas trainers. A thin silver watch sits on her left wrist. She is alone on a plain seamless mid-grey background, lit by one soft key light from the upper left with a faint shadow at her feet. Natural colours, sharp focus, photorealistic."
```

The same hero written short, subject first, one idea per sentence, for a model whose notes ask for a
short prompt:

```toml
[characters.woman.hero]
model = "flux.2-klein-4b-text"
size = "832x1248"
hold = true
prompt = "One woman of about thirty standing facing the camera, full length from head to feet, neutral pose, arms at her sides, hands empty. Oval face, warm light-brown skin, dark brown eyes, shoulder-length dark brown hair parted on the left. Loose oatmeal knitted jumper with pushed-up sleeves, dark-blue straight jeans, white canvas trainers, thin silver watch on her left wrist. Plain mid-grey studio background, one soft key light from the upper left. Photorealistic, natural colours."
```

An edit model, told what to keep from the garment it is shown:

```toml
[characters.woman.hero]
model = "qwen-image-edit-2511"
size = "832x1248"
refs = ["jacket.hero"]                      # image 1: a garment made first as an object
hold = true
prompt = "A full-length studio photograph of one woman of about thirty standing facing the camera, neutral pose, arms relaxed, hands empty. She has an oval face, warm light-brown skin, dark brown eyes and shoulder-length dark brown hair parted on the left. She wears exactly the green rain jacket from image 1, zipped up, over dark-blue jeans and white trainers. Plain mid-grey background, one soft key light from the upper left. Photorealistic."
```
