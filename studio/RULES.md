# The rulebook

This studio has no templates. There are no six designs to choose from and no
`layout` setting. Instead there is this document and `studio/rules.json`: a set of
detailed rules that say what paper is, what a composition is made of, what type
may do, how photographs are cropped, how faces are protected, and how far the
agent may invent. The agent reads the rules and writes a composition for each
card and each slide. The engine checks that composition against the numbers and
renders it, or refuses and explains why.

You can tune all of it. Edit `rules.json` to change a number, a palette, a type
scale or a whole direction; edit this file when you want the *judgement* to
change, because the agent reads this file too. Restart the command (or just run
it again) and the next composition follows the new rules. Nothing about the
look is compiled into the code.

```
studio/rules.json   the numbers: paper, limits, type scale, palettes, directions
studio/RULES.md     this file: the reasoning, the vocabulary, the latitude
```

`./ccb brief <card>` prints the parts of the rulebook that matter for that page,
with real measurements, so the agent does not have to guess.

---

## 1. Canvas and coordinates

Every composition is written in **fractions of the trim page**, with `(0, 0)` at
the top-left and `(1, 1)` at the bottom-right. Fractions are resolution-free:
the same composition renders at 96 DPI on screen and at 300 DPI for print.

- A card is a trim size from `paper.sizes` (`5x7`, `4x6`, `5x5`, `a6`, `a2`),
  portrait or landscape.
- A print card also has a **bleed** of `paper.bleed_in` (default 0.125 in) on
  every side. Full-bleed photographs may run to the edge of the page; the trim
  box is what you see when it is cut.
- A presentation slide is always 16:9, 13.333 x 7.5 in, no bleed, no crop marks.
- Text and important detail belong inside the direction's margin; photographs
  may deliberately break it. The gate warns about text outside the margin and
  treats a photograph outside it as intentional.

Sizes (`x, y, w, h`) are top-left and extent, not centre and radius. A zone at
`x 0.07, y 0.62, w 0.86, h 0.10` starts 7% from the left and 62% down, and is
86% wide and 10% tall.

---

## 2. A composition

A composition is one page. A card has one or more fronts and optionally one back;
a deck has a list of slides. The shape is the same everywhere:

```json
{
  "name": "Family plate",
  "side": "front",
  "slots": [
    {"photo": 0, "x": 0.05, "y": 0.05, "w": 0.90, "h": 0.48,
     "treatment": "plain", "focus": [0.5, 0.35]}
  ],
  "zones": [
    {"roles": ["greeting"], "x": 0.07, "y": 0.575, "w": 0.86, "h": 0.085,
     "align": "left", "font": "heading"}
  ],
  "ornaments": [{"kind": "holly", "density": 0.5}],
  "lines": [{"x1": 0.07, "y1": 0.55, "x2": 0.93, "y2": 0.55,
             "token": "accent", "weight": 1}],
  "notes": "why this page works"
}
```

- `name` is what appears on the contact sheet and in reports. Name it after the
  idea, not the geometry ("Quiet hero", "Brass plate", "Full-bleed snow").
- `side` is `front` or `back` for a card; omitted for a slide.
- `notes` is free text and is stored with the composition. Use it.

### 2.1 Slots (photographs)

| field | meaning |
| --- | --- |
| `photo` | index into the project's photograph list, in the order `./ccb brief` prints |
| `x, y, w, h` | the rectangle, as fractions |
| `treatment` | optional override: `plain`, `border`, `shadow`, `tilt`, `rounded` |
| `focus` | optional `[x, y]` crop focus in the photograph, 0..1 |

A slot is a window, never a stretch. The engine cover-crops the photograph to the
slot's aspect: it removes the excess from the sides or the top and bottom, then
scales. The crop is chosen around the faces when there are faces (see §5); an
explicit `focus` overrides that.

Treatments are a vocabulary, not a requirement. `border` draws the direction's
keyline; `shadow` lifts the photograph off the paper; `tilt` rotates it a couple
of degrees; `rounded` softens the corners by `direction.radius`. Use one idea at
a time: a tilted photograph with a heavy shadow and a border is noise.

Limits: at most `composition.slots.max` (12) slots; a slot's short side at least
`min_side` (0.06); photographs together between `photos.min_coverage` (0.20) and
`max_coverage` (0.84) of the page. A page with no slots is legitimate for a back.

### 2.2 Zones (words)

A zone reserves a rectangle and a stack of roles. Roles are drawn in the order
listed, top to bottom, and fitted as one stack: if the stack does not fit, the
whole stack shrinks together rather than one line dropping out.

| field | meaning |
| --- | --- |
| `roles` | one or more role names from §3, drawn in order |
| `x, y, w, h` | the rectangle |
| `align` | `left`, `center`, `right`; defaults to the direction |
| `valign` | `top`, `center`, `bottom`; how the stack sits in the zone |
| `font` | `heading`, `body` or `script`; overrides the role's family for this zone |
| `scale` | 0.35..2.2, multiplies the role's type scale |
| `caps` | true/false; overrides the direction's capitals for this zone |
| `panel` | true draws a solid panel in the palette's `panel` colour behind the words |
| `text` | literal text for this zone (captions, page numbers); overrides the stored words |

Text never sits on a photograph. The gate rejects a zone that overlaps a slot,
and rejects two zones that overlap each other. That is a hard rule, not a taste
call: a face behind a line of type is a ruined card.

Limits: at most `composition.zones.max` (10) zones; a zone at least
`zones.min_width` (0.16) wide; text inside the direction's margin is a warning,
not an error, because a deliberately inset colophon can work.

### 2.3 Ornaments

`ornaments` is a list of at most `ornaments.max` (4) groups:

```json
{"kind": "snow", "density": 0.35}
```

Kinds: `holly`, `snow`, `stars`, `confetti`, `none`. `density` runs roughly
0..1.6 and overrides the direction's density. If you list ornaments, they
**replace** the direction's decoration; if you list none, the direction's
decoration is used. Ornaments are always kept out of text zones and photographs,
so they cannot cover a face or a word.

### 2.4 Rules (lines)

`lines` is a list of at most `lines.max` (8) straight rules:

```json
{"x1": 0.07, "y1": 0.55, "x2": 0.93, "y2": 0.55, "token": "accent", "weight": 1}
```

`token` is `ink`, `soft`, `accent`, `panel` or `bg`. `weight` is 0.25..3; above
that it is a border, not a rule. A rule is drawn over the paper and over
photographs, under the words. It is a good way to separate a photograph from a
caption column, or to underline a small line of type.

---

## 3. Type

Sizes are fractions of the page's **short side**, so 5x7 and 16:9 behave the
same. The scale for each role lives in `rules.json` under `type.roles`:

| role | default | used for |
| --- | --- | --- |
| `greeting` | 0.082 | Merry Christmas |
| `family` | 0.050 | the family name |
| `message` | 0.027 | the body copy |
| `signature` | 0.031 | with love, ... |
| `year` | 0.021 | 2026 |
| `caption` | 0.017 | a photograph caption |
| `monogram` | 0.150 | initials |
| `title` | 0.110 | a slide or card title |
| `subtitle` | 0.034 | a slide subtitle |
| `eyebrow` | 0.019 | a small label above a title |
| `statement` | 0.064 | one sentence, set large |
| `numeral` | 0.095 | a big number |
| `folio` | 0.017 | a page number |

Each role also has `min_scale`, `max_lines`, `tracking`, `spacing`, `weight`,
`uppercase` and `font` in `rules.json`. `tracking` and `uppercase` may be
`"direction"`, meaning "do what the direction says"; otherwise they are literal.

A zone's `scale` multiplies the role's scale; `font` and `caps` override the
direction for that zone. That is the intended way to depart from a direction
without editing the rulebook: a single caption in the body face, an uppercase
greeting where the direction is sentence case, a title 20% larger than usual.

The fitter measures real glyphs and binary-searches the largest size that fits
the zone, so type never overflows. It also caps a size so the longest word fits
the zone width: words are never broken. If even the smallest size cannot fit, the
copy is ellipsised and the gate warns. The floor is `composition.type_safety`
(`min_pt` 7.0, `min_message_pt` 7.5); below it the gate warns and names the role.

Capitalisation belongs to roman faces. A script name is never shouted, even when
the direction is all capitals.

---

## 4. Directions, palettes and what they are for

A **direction** is not a template. It is a bundle of guidance and defaults:
three typefaces, a palette, an alignment, a margin, a decoration, a border, a
photographic treatment and a paragraph of advice. The agent may follow it
closely or borrow only its palette and typefaces. `./ccb directions` prints them.

| key | character |
| --- | --- |
| `classic` | cream, evergreen, holly, centred; the card people picture |
| `modern` | air, a hairline, tiny stars, left-aligned |
| `traditional` | cranberry, capitals, heavy frame, snow |
| `editorial` | magazine spread, brass, wide margins, plates |
| `nordic` | pale grey-green, small photographs, sparse stars |
| `vintage` | postcard border, one tilted frame, holly |
| `joyful` | bright red, script greeting, confetti, shadows |
| `gallery` | almost all photographs, one thin rule, tiny type |

Tunable fields: `palette`, `heading`, `body`, `script`, `greeting_font`,
`name_font`, `caps`, `weight`, `tracking`, `align`, `margin`, `decoration`,
`density`, `border`, `photo_frame`, `radius`, `texture`, plus `guidance` (the
paragraph the agent reads). Add a direction by adding an object to
`directions`; it appears in `./ccb directions` and in every brief.

A **palette** is six named colours: `bg`, `ink`, `soft`, `accent`, `panel`,
`on_panel`. Type picks the first of `ink`/`soft` with 4.5:1 contrast against its
background; panels use `on_panel`. Add or retune palettes in `palettes`; a
direction refers to one by key.

---

## 5. Faces

The face engine is **YuNet**, a small CNN that returns a box, five landmarks and
a confidence for every face. It is installed by `./ccb faces`, which downloads
`assets/models/face_detection_yunet_2023mar.onnx` (about 340 KB) once. If the
model is missing, the engine falls back to OpenCV's Haar cascade. If OpenCV is
not installed, it reports `none` and crops are centred; it never pretends to have
found a face.

- Detection runs at up to 1024 px on the long side and boxes are mapped back, so
  it is fast on full-resolution photographs.
- Every photograph is scanned when it is loaded and the result is cached by path,
  modification time and size.
- `focus` for a slot defaults to the area-weighted centre of its faces. That is
  why a group photograph keeps its people when the slot is a narrow column: the
  crop moves to them instead of cutting through them.
- The gate checks, for every slot with faces, how much of each face survives the
  crop (`faces.min_crop_keep`, default 65%) and how wide the widest face will
  print (`faces.min_width_in`, default 0.16 in). Both are warnings with exact
  numbers, so the agent can widen a slot or move it rather than guess.
- `./ccb see` draws every detection on the preview and on the photo sheet, and
  writes the positions and scores to `visual.md`/`visual.json`.

The detector does not identify anyone: no names, no embeddings, no recognition,
no network at inference time. It answers "where are the faces", not "who is
this". That is deliberate.

### Tuning the face rules

- Stricter crops: raise `faces.min_crop_keep` to 0.8.
- Smaller faces allowed: lower `faces.min_width_in`.
- Prefer faces low in the frame (a common composition): give a slot `focus`
  explicitly; a face-aware default is a starting point, not a law.
- Re-download after a failed download: `./ccb faces --force`.

---

## 6. What gets checked, and what the codes mean

`./ccb layout` validates before saving; `./ccb check` validates every saved
composition and measures the rendered type. Errors stop the save or fail the
gate; warnings are notes.

| code | level | meaning |
| --- | --- | --- |
| `rect.missing` / `rect.bounds` / `rect.size` | error | a rectangle is incomplete, off-page or empty |
| `photo.range` | error | the slot names a photograph that does not exist |
| `photo.treatment` | error | not in `composition.slots.treatments` |
| `photo.focus` | error | focus is not `[x, y]` inside 0..1 |
| `photo.small` | warn | a slot's short side is below `min_side` |
| `photos.coverage` | warn/error | below the minimum (warn) or above the maximum (error) |
| `overlap.text_photo` | error | text sits on a photograph |
| `overlap.same` | error | two slots or two zones overlap |
| `type.roles` / `type.role` | error | no roles, or a role not in the rulebook |
| `type.align` / `type.valign` / `type.font` | error | not in the allowed vocabulary |
| `type.scale` | error | outside 0.35..2.2 |
| `type.narrow` / `type.small` | warn | the zone is too narrow or small for its copy |
| `type.margin` | warn | text leaves the direction's margin |
| `words.empty` | warn | a placed role has no words |
| `ornaments.*` / `lines.*` | error | unknown kind, too many, off-page, too heavy |
| `faces.crop` | warn | a face keeps less than `min_crop_keep` |
| `faces.small` | warn | the widest face prints below `min_width_in` |
| `photos.unused` | warn | a photograph is not placed anywhere |
| `words.greeting` | warn | no greeting |

The gate also warns about type below the floor, contrast under 3:1, shortened
copy and photographs used above 1.8x their pixels at the export DPI.

---

## 7. Creative latitude

The agent is expected to invent. The rules do not prescribe a layout; they
describe what a layout must not break.

**Free to invent:** the number of slots and their geometry; asymmetric and
full-bleed compositions; overlaps of nothing (slots and zones never overlap);
any number of fronts and one back; panels; rules; ornament kinds and density;
type scale within 0.35..2.2; alignment and valign; fonts from the three families;
captions and page numbers; words, as long as they are the user's words or plainly
invented greetings the user asked for.

**Not free to break:** text on a photograph; a face cut in half without saying so;
type below the floor without saying so; a photograph stretched; a role that does
not exist; a composition that runs off the page; claiming a `.pptx` when the
output is a PDF; claiming to have seen an image when the model cannot read
images.

**How to use the latitude well:**

1. Write **two or three fronts**, not one. Each should argue for a different
   idea: a full-bleed hero, a quiet plate with air, a gallery. Give them names.
2. Write the back as its own composition; a text-only back is normal.
3. Read the brief's face report before choosing crops; put the group photograph
   where it can be large, not in a 0.10-wide strip.
4. Use the direction for coherence, then depart in one place. A page that
   ignores every default at once reads as an accident.
5. When the gate warns, change the composition; do not raise the limits to make
   a warning disappear unless the user asked for that rule to change.

---

## 8. Tuning recipes

- **A different look for every card:** edit a direction's `palette`, `heading`
  and `guidance`. The agent reads the new guidance next time.
- **Bigger type everywhere:** raise the role scales in `type.roles`; the fitter
  still protects overflow.
- **A stricter gate:** raise `type_safety.min_pt`, `faces.min_crop_keep` and
  `photos.min_coverage`.
- **Allow a bold graphic gesture:** raise `lines.max_weight` and
  `ornaments.max`, and add a sentence to §7 saying what you now permit.
- **A new paper size:** add it to `paper.sizes`; it appears in `./ccb sizes`,
  `--size`, and every brief.
- **A house palette:** add it to `palettes` and point a direction at it.
- **No faces at all:** set `faces.min_crop_keep` to 0; the focus still follows
  faces but the gate stops nagging. Or uninstall OpenCV.

Numbers are cheap to change. If you change the *meaning* of a rule, change this
file too, because the agent reads it.

---

## 9. The loop

```
./ccb brief <card>            the rules, the page, the photographs, the faces
read out/see/photos.jpg       if your model can see images (otherwise visual.md)
write design.json             two or three fronts + a back
./ccb layout <card> --file design.json
./ccb check <card>            fix every ERROR; read every warning
./ccb see <card>              look at front.png; look at the faces
./ccb render <card>           PDF/PNG/JPEG at true size
./ccb qa <card>               read the files back
```

The deck loop is the same with `./ccb deck ...` and `slides.json`. There are no
slide kinds; a deck is a sequence of compositions, and the brief suggests a
rhythm (cover, plates, statement, gallery, closing) without enforcing it.

`./ccb see` is how the agent sees its own work. The annotated preview draws the
margin, every slot, every zone and every face box. `visual.md` carries the same
facts in words. A model that cannot read images must say so and work from
`visual.md`; it must not describe a picture it has not seen.

---

## 10. Version

This rulebook describes rulebook version 2. The card format also reads version 1
cards (a `style` and a list of generated `designs`) by migrating them to
directions and compositions, so old work is not lost.
