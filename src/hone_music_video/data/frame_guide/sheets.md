### Sheets

A sheet puts finished pictures on one page: a turnaround, an expression grid, a pose grid, an object
board, a place board. It is **composed by Pillow, with no model and no prompt**, as soon as every image
it names is done, and composing it again from the same pictures gives the same file. Write sheets last:
their `images` must be items above them.

#### The fields

| Field | Meaning |
|---|---|
| `layout` | `four-view-turnaround` (front, three-quarter, side, back in tall cells), `expression-grid` (square head-and-shoulders cells, four to a row), `pose-grid` (full figures, three to a row), `object-detail-board` (one large view and the others beside it), `environment-board` (wide views, two to a row), `before-after` (two images with their states as labels), `sequence-strip` (frames in a row, numbered), `contact-grid` (any images), `character-model-sheet` (full figures in a row, face close-ups below, a text panel) |
| `images` | item ids, in the order they are placed |
| `labels` | one per image, in the same order (optional) |
| `columns` | images per row; for `character-model-sheet`, how many are full figures |
| `heading`, `notes` | text printed on the sheet (the only text Hone Frame draws) |
| `page`, `fit`, `background`, `spacing`, `margin`, `palette`, `show_meta` | page size, `contain` or `cover`, colour, gaps, colour swatches, the model and seed under each picture |

#### What makes a good sheet

- **The same size and background** for every picture of a sheet: make a turnaround's views at the hero's
  size, on the hero's background, or the cells will not line up.
- **The order a reader expects:** front, three-quarter, side, back; neutral before expressions.
- **Labels instead of text in pictures:** models draw letters badly; a sheet's labels and heading are
  drawn by Pillow and are always readable.
- A sheet shows the **current** version of each image. Use an older version, or redo one, and the sheet
  is composed again.

#### Examples

```toml
[sheets.woman-turnaround]
layout = "four-view-turnaround"
images = ["woman.hero", "woman.three-quarter", "woman.side", "woman.back"]
labels = ["Front", "3/4", "Side", "Back"]
heading = "Anna: turnaround"
```

```toml
[sheets.woman-model-sheet]
layout = "character-model-sheet"
images = ["woman.hero", "woman.three-quarter", "woman.side", "woman.back", "woman.close", "woman.happy"]
labels = ["Front", "3/4", "Side", "Back", "Neutral", "Happy"]
columns = 4
heading = "Anna"
notes = "About thirty; shoulder-length dark brown hair parted on the left; silver watch on the left wrist."
show_meta = true
```

```toml
[sheets.kitchen-board]
layout = "environment-board"
images = ["kitchen.wide", "kitchen.reverse", "kitchen.high", "kitchen.evening"]
labels = ["Wide", "Reverse", "High", "Evening"]
```
