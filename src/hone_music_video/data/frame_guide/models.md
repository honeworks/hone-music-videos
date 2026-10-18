### The image model: `qwen-image-2.1-turbo`

(From Hone Frame's prompt guide, part 3, and its "What the models say" notes, 2026-10-14.)

Qwen-Image 2.1 Turbo: text-to-image and up to ten reference pictures in 8 steps, at cfg 1.0.

- **Prompt form:** detailed natural-language description, plain sentences; name each reference by its
  number ("the woman from image 1"); quote any text to render.
- **References** are sent in the order of `refs`: the first is image 1, the second image 2. A scene gets
  at most four here; each one adds about 9 s.
- **Negatives do nothing** (cfg 1.0): there is no negative prompt, and "no X" in a prompt tends to draw X.
  Say what is there.
- **One picture per character:** a full body plus a portrait of the same person, or two full-body views
  of one person, added a second copy of that person. Give each character one picture in a scene.
- **Twins:** two characters described with nearly the same words get the same default face; give
  characters who appear together different face traits (face shape, nose, brows, age).
- It draws difficult costumes and creatures from text faithfully (Morvane's snakes in every view, an
  ox-headed mace), better than Z-Image.
- **A picture outweighs the words:** a pendant close-up given for a back view was painted on her back,
  even after redos saying otherwise. Give a picture only the references of what it shows.
- **The reference's side is copied:** a laptop whose only picture showed the back of the lid was drawn
  typed on from behind. Give an object or a person the picture of the side the shot needs.
- **A place drawn from words alone** changes from picture to picture (a flat's window, lamps and desk
  moved between shots); give a recurring place a picture.
- **Text** quoted in the prompt rendered right every time in the stress tests (shop signs, a taped note,
  a headline, a monogram); mirrored or upside-down text never did.
- **Sizes:** it samples at the size asked for. 1664x928 (landscape) and 928x1664 (portrait) look better than
  1024x576; a hero is 832x1248, a close-up or an object 1024x1024, a long animal 1536x1024.
- **Hands and limbs** in still pictures were mostly clean; extra or melting limbs came from the video
  model that animated them.
- **Two bodies in contact** (embracing, grappling) are the weakest case: show one body clearly and the
  other beside it.
- **Seeds:** a new seed of the same prompt can give nearly the same picture; to choose between readings
  of a hard moment, write different shots (`prompts`) rather than more takes.
- Research licence: pictures are not for commercial use.
