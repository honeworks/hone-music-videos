### Faces and expressions

Close-ups of the face (head and shoulders) and its expressions, made from the hero: in a full figure
the face is too small to carry an identity, so every later close shot needs a picture where the face
fills the frame. Make a neutral close-up first, accept it, then the expressions.

#### What the prompt must say

1. **The framing:** "a close-up portrait: her face, head and shoulders fill the frame, seen from the
   front".
2. **Who it is**, again: age, face shape, skin, eyes, eyebrows, hair length and colour, facial hair and
   its length ("a short white beard reaching just below the chin"). Hair and beard length drift in edits
   unless named; the close crop also changes how long a beard looks.
3. **The expression as what the face does**, not a mood word alone: "a broad smile showing her upper
   teeth, her eyes narrowed and crinkled at the corners, her eyebrows raised". Sad: "the inner ends of
   her eyebrows raised, her eyes looking down, the corners of her mouth turned down, her lips closed".
4. **What stays:** "the same face, hair and parting, the same jumper neckline as image 1".
5. **Background and light:** plain and even, as the hero.

#### References

- Image 1 is the hero for the first, neutral close-up; after that, the neutral close-up. A close-up
  made from a full figure can come out younger and softer than the character; "keeps the face of image
  1: same age, same features" helps (the model's notes below say where this was seen). A model that
  takes more references may take the neutral close-up as image 1 and the hero as image 2 for the hair
  and clothes, but a portrait beside a full body of the same person can become two people: when the
  model's notes warn of it, give one of them.
- No pose picture: a face needs none.
- In scenes, a close shot takes the close-up as its reference, not the hero: in the stress tests
  (2026-10-14) every close shot made from a close-up kept the face, the scar and the moustache, and an
  expression made from the close-up (a shocked face with a drop of sweat) kept the character. Make the
  close-up of every character who will be seen close.

#### Common failures and what to do

- **Small marks move** (a mole, a small scar, a freckle pattern) from cheek to chin between
  expressions. State the exact place and size; it still may move. Prefer marks that are large.
- **Twins:** two characters described with similar words get the same default face. Make their faces
  differ in the face itself.
- **The face changes with a strong expression.** Make the expression from the neutral close-up, not from
  the full figure, and keep "the same face" in the prompt.
- **Hands near the face** (a hand on the cheek, fingers at the mouth) often come out broken: keep the
  hands out of a face close-up unless the gesture is the point, then check them.
- **Teeth and mouths** in wide-open expressions (shouting, laughing) are less reliable than a closed or
  slightly open mouth.
- **The clothes change** at the neckline: name the neckline ("the round neck of the oatmeal jumper").

#### Examples

The examples use `qwen-image-2.1-turbo`, the default model of Hone Frame's examples, and show the form
only: how long a prompt may be, how many references a model takes, how to name them and whether its
pictures may be used commercially are in each model's notes below.

##### The neutral close-up, then the expressions

The close-up keeps the face of the hero; each expression is made from the close-up and says what the
face does.

```toml
[characters.woman.close]
model = "qwen-image-2.1-turbo"
size = "1024x1024"
refs = ["woman.hero"]
hold = true
prompt = "Close-up head-and-shoulders portrait of the woman from image 1: exactly the same face, skin, eyes, eyebrows and hair, and the same oatmeal knitted jumper at the shoulders. Her face, head and shoulders fill the frame, facing the camera, a calm neutral expression, lips closed. She is about thirty, with an oval face, warm light-brown skin, dark brown eyes and shoulder-length dark brown hair parted on the left. She keeps the face of image 1: same age, same features. Plain seamless mid-grey background, one soft key light from the upper left, no text."
```

```toml
[characters.woman.happy]
model = "qwen-image-2.1-turbo"
size = "1024x1024"
refs = ["woman.close"]
prompt = "The same woman from image 1 in the same close-up, smiling broadly: her upper teeth showing, her eyes narrowed and crinkled at the corners, her eyebrows slightly raised. Same face, shoulder-length dark brown hair parted on the left, same jumper neckline. Plain seamless mid-grey background, one soft key light from the upper left."
```

```toml
[characters.woman.thinking]
model = "qwen-image-2.1-turbo"
size = "1024x1024"
refs = ["woman.close"]
prompt = "The same woman from image 1 in the same close-up, thinking hard: her eyes looking up and to her left, her eyebrows drawn slightly together, her lips pressed together. The same face, shoulder-length dark brown hair parted on the left and jumper neckline. Plain mid-grey backdrop, one soft key light from the upper left."
```

##### Every detail of the face named

```toml
[characters.grandfather.close]
model = "qwen-image-2.1-turbo"
size = "1024x1024"
refs = ["grandfather.hero"]
hold = true
prompt = "Close-up head-and-shoulders portrait of the elderly man from image 1: exactly the same face, eyes, eyebrows, hair, beard and glasses, and the same moss-green cardigan collar. He is about seventy-five, with a long narrow face, deep laugh lines, light blue eyes, thick white eyebrows, short white hair combed back, a neat short white beard reaching just below his chin and round tortoiseshell glasses. A calm neutral expression. He keeps the face of image 1: same age, same features. Plain flat mid-grey background, one soft key light from the upper left. Bold clean outlines, flat colour fills, clean 2D animation style."
```

##### Without references: a stranger only

An item without references cannot keep a face it has not seen. Use one for a face only when the
character exists nowhere else yet, or to try an expression on a stranger before you write the item
with references:

```toml
[characters.woman.happy-sketch]
model = "qwen-image-2.1-turbo"
size = "1024x1024"
prompt = "Photorealistic close-up portrait of one woman of about thirty: her face, head and shoulders fill the frame, seen from the front. She has an oval face, warm light-brown skin, dark brown eyes, straight dark eyebrows and shoulder-length dark brown hair parted on the left. She smiles broadly, her upper teeth showing, her eyes crinkled at the corners. She wears an oatmeal knitted jumper with a round neck. Plain mid-grey background, one soft key light from the upper left, natural colours."
```

##### For commercial work

A model whose licence does not allow commercial use (part 3 warns of it) is for trying things out and
for work you will not sell. For commercial pictures, write the item for a model that allows it, in the
form its notes ask for:

```toml
[characters.woman.close]
model = "flux.2-klein-4b"
size = "1024x1024"
refs = ["woman.hero"]
hold = true
prompt = "Close-up portrait of the woman from image 1: her face, head and shoulders fill the frame, seen from the front, a calm neutral expression, lips closed. A woman of about thirty, oval face, warm light-brown skin, dark brown eyes, shoulder-length dark brown hair parted on the left. Same face, hair and oatmeal jumper neckline. Plain mid-grey background, one soft key light from the upper left."
```

```toml
[characters.grandfather.surprised]
model = "qwen-image-edit-2511"
size = "1024x1024"
refs = ["grandfather.close"]
prompt = "Change only the expression of the man in image 1: his eyebrows raised high, his eyes wide open, his mouth slightly open in a small round shape. Keep the same face, the same short white beard, the same glasses, hair and cardigan collar, the same framing, plain mid-grey background and light."
```
