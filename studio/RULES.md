# The playbook

This studio has **no presets**. There is no style to pick, no palette catalogue,
no type scale to obey and no layout setting. There are two files: this one, which
says what good work has to satisfy and what you are free to invent, and
`studio/rules.json`, which holds every number the engine enforces. You read
them, then you design each card and each slide from scratch — the colours, the
typefaces, the sizes, the geometry, the words' arrangement. The engine checks
your page and renders it, or refuses and tells you which rule it broke.

You can tune the whole thing. Edit `rules.json` to change a limit; edit this
file when you want the *judgement* to change, because the agent reads both.
Nothing about the look is compiled into the code.

```
studio/rules.json   the numbers: paper, palette rules, type limits, primitives
studio/RULES.md     this file: the reasoning, the vocabulary, the latitude
```

`./ccb brief <card>` prints the parts of the playbook that matter for that page,
with real measurements and the colours in the photographs, so nothing has to be
guessed.

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
- Words belong inside the safe margin (`composition.margin.safe`, 0.045 of the
  page); photographs may deliberately break it. The gate warns about text outside
  it and treats a photograph outside it as intentional.

Sizes (`x, y, w, h`) are top-left and extent, not centre and radius. A zone at
`x 0.07, y 0.62, w 0.86, h 0.10` starts 7% from the left and 62% down, and is
86% wide and 10% tall.

---

## 2. The card's own system

Every card and deck carries a `system` in its JSON. It has one required part —
the palette — and one optional note.

```json
"system": {
  "palette": {"bg": "#F4EEE1", "ink": "#1D2A22", "soft": "#5C6A5E",
              "accent": "#A02B32", "panel": "#1D2A22", "on_panel": "#F4EEE1"},
  "note": "cream stock, pine ink, one cranberry accent, chosen beside the kitchen photo"
}
```

### 2.1 The palette

Six colours, all `#hex`, no names and no library:

| key | what it is for |
| --- | --- |
| `bg` | the paper: the page fill when the composition has no background |
| `ink` | the main type colour, and a default line colour |
| `soft` | secondary type: captions, folios, quiet labels |
| `accent` | the one strong colour: rules, shapes, a monogram, an ornament |
| `panel` | a dark (or strongly coloured) field for panels, bands and scrims |
| `on_panel` | type on `panel`; usually the paper colour |

Rules the engine enforces (`palette.*` in `rules.json`):

- `ink` on `bg`, and `on_panel` on `panel`, must reach `min_text_contrast`
  (4.5:1). Below 2.5:1 the layout is refused; between 2.5 and 4.5 it warns and
  prints the ratio. The renderer still auto-picks a readable colour for a zone
  with no `color`, so a weak palette is a design error, not an unreadable print.
- `accent` must be visibly different from `bg` (1.3:1), or rules and ornaments
  disappear.

**Where the colours come from.** You decide. `./ccb brief` prints the six most
common colours of each photograph, with hex values, and `./ccb palette` prints
them again with the current palette. Pull the paper out of the wall colour, the
accent out of a coat or a bauble, the ink out of the shadows. If you write no
palette at all, the engine samples one from the first photograph so the card can
still render — the brief says so, and it is a starting point, not a decision.

A palette can be any temperature: cream and pine, bone and oxblood, slate and
brass, near-black and one saturated colour. What it must not be is six unrelated
colours. Two neutrals, one strong colour and three tints of the neutrals is a
reliable shape, but it is advice.

### 2.2 Typography

There is **no named type scale**. A zone declares its own typography:

```json
{"word": "greeting", "x": 0.075, "y": 0.545, "w": 0.85, "h": 0.13,
 "size": 0.088, "font": "playfair", "weight": 600, "tracking": -0.014,
 "leading": 1.04, "caps": false, "italic": false, "align": "left"}
```

| field | meaning |
| --- | --- |
| `size` | cap height scale as a **fraction of the page's short side**; `0.088` on a 5x7 card is a large greeting, `0.018` a caption. Range 0.012–0.50. Required. |
| `font` | a typeface key: `playfair`, `cormorant`, `montserrat`, `lato`, `greatvibes`, `instrument`. Defaults to `type.default_font` (`lato`). |
| `weight` | 100–900. Variable faces interpolate; Lato snaps to Light/Regular/Bold/Black. |
| `italic` | true or false, where the face has an italic. |
| `tracking` | letter-spacing in em: negative tightens, positive opens. −0.06 to 0.45. |
| `leading` | line height as a multiple of the size; 0.85–2.4. A display line usually wants 1.0–1.1, body copy 1.4–1.55. |
| `caps` | upper-case the copy. Never applies to `greatvibes`. |
| `align` | `left`, `center`, `right`. |
| `valign` | how the block sits in its rectangle: `top`, `center`, `bottom`. |

The six typefaces shipped are physical assets (SIL OFL, fetched once by
`./ccb fonts`): Playfair Display and Cormorant Garamond (serifs), Montserrat and
Lato (sans), Instrument Serif (a high-contrast display serif with a true italic),
Great Vibes (script). They are a shelf, not a style: any of them can carry any
job. Cormorant at 0.09 is not the same card as Montserrat at 0.09.

**Hierarchy is a judgement, not a rule.** Nothing says a greeting must be 3× the
body. On a card 2.5–4× is comfortable; on a slide 3–5×; a quiet card can run
1.8× and be better for it. What the rulebook does enforce is that the copy fits,
that no type prints below the floor, and that it stays readable over what is
behind it.

Two practical constraints:

1. **A zone carries one piece of copy.** For a greeting over a name over a
   signature, place three zones — each with its own size, face and weight. That
   is the point of having no scale: the greeting can be Playfair 600 while the
   name is Lato 400 tracked wide, without inventing a role for either.
2. **Long words are never broken.** If the longest word will not fit the zone
   width at the size you chose, the engine steps the size down (down to 60% of
   what you asked) and reports it; it never hyphenates.

### 2.3 Copy parts

`type.parts` in `rules.json` names the pieces of copy a card can carry. These are
content keys, not styles: they say *which words*, never how they look.

| part | what it holds |
| --- | --- |
| `greeting` | the main wish |
| `family` | the family name, or who it is from |
| `message` | the letter: a few sentences of news |
| `signature` | the sign-off |
| `year` | the year |
| `caption` | one line naming a photograph, a place, a date |
| `monogram` | initials |
| `title` `subtitle` | a slide's two opening lines |
| `eyebrow` | a small label above a title |
| `statement` | one sentence set large |
| `numeral` | a big number |
| `folio` | a page number or running foot |

A zone may instead carry its own words: `{"word": "note", "text": "..."}`. Any
label works when `text` is present; without `text`, the word must be one of the
parts above.

---

## 3. A composition

A composition is one page. A card has one or more fronts and optionally one back;
a deck has a list of slides.

```json
{
  "name": "Full bleed",
  "side": "front",
  "background": {"photo": 0, "scrim": 0.58, "scrim_from": "bottom",
                 "scrim_reach": 0.52, "scrim_color": "panel"},
  "shapes": [{"kind": "circle", "x": 0.62, "y": -0.16, "w": 0.58, "h": 0.58,
              "fill": "accent", "opacity": 0.9}],
  "slots": [{"photo": 1, "x": 0.40, "y": 0.47, "w": 0.47, "h": 0.34,
             "clip": "rounded", "rotate": 2.2, "layer": 3}],
  "zones": [{"word": "greeting", "x": 0.075, "y": 0.545, "w": 0.85, "h": 0.13,
             "size": 0.088, "font": "playfair", "weight": 600,
             "tracking": -0.014, "leading": 1.04, "align": "left",
             "over_photo": true}],
  "lines": [{"x1": 0.075, "y1": 0.705, "x2": 0.42, "y2": 0.705,
             "token": "accent", "weight": 1.2}],
  "ornaments": [],
  "chrome": {"border": "none"},
  "notes": "why this page works"
}
```

- `name` is what appears on the contact sheet and in reports. Name it after the
  idea ("Arch on pine", "Three snapshots"), not the geometry.
- `side` is `front` or `back` for a card; omitted for a slide.
- `notes` is free text and is stored with the composition.

**The engine adds nothing you did not ask for.** There is no house frame, no
house decoration, no paper grain unless the composition turns it on. A page is
only what its background, shapes, photographs, rules and words make it.

### 3.1 Background

```json
"background": {"photo": 0, "scrim": 0.9, "scrim_from": "bottom",
               "scrim_reach": 0.62, "scrim_color": "panel"}
"background": {"fill": "accent"}
"background": {"gradient": ["bg", "panel"], "angle": 90}
```

A background is the whole page, bleed included. `photo` makes it a full-bleed
photograph; `scrim` (0..1) fades a colour over it from one edge so type can sit
on the picture; `scrim_reach` (0.05..1) says how far in the fade reaches full
strength; `scrim_from` is `bottom`, `top`, `left`, `right` or `full`. `fill` is a
flat colour; `gradient` is two colours and an angle in degrees.

### 3.2 Shapes

Flat colour fields, under or over everything by `layer`: `rect`, `band`,
`circle`, `ellipse`, `arch`, `panel` (rounded), `rounded`, `line`. They may run
off the page — a disc cut by the trim is a real design move — and take `opacity`,
`rotate` and a `radius` (fraction of the short side, for `panel`/`rounded`).
`arch` is the rounded-top plate; `band` is full width regardless of `x`.

### 3.3 Layers

Every slot, zone, shape and rule has a `layer` (default 0, from −5 to 5). Paint
order is: background, then everything sorted by layer. Within one layer, shapes
go first, then photographs, then rules, then words. Two photographs may overlap,
but only if they sit on different layers — that is a deliberate collage rather
than an accident. Type may sit on a photograph only when the zone says
`"over_photo": true`; the engine samples what is actually underneath and picks
the text colour for contrast.

### 3.4 Slots (photographs)

| field | meaning |
| --- | --- |
| `photo` | index into the project's photographs, in the order `./ccb brief` prints |
| `x, y, w, h` | the rectangle, as fractions |
| `treatment` | optional: `plain`, `border`, `shadow`, `tilt`, `rounded` |
| `focus` | optional `[x, y]` crop focus in the photograph, 0..1 |
| `clip` | optional: `rect`, `rounded`, `arch`, `circle`, `oval` |
| `rotate` | optional, ±12°; turns the print on the page |
| `layer` | paint order, −5..5; two overlapping slots need different layers |
| `bleed` | `true` runs a slot that touches the trim edge into the bleed |

A slot is a window, never a stretch. The engine cover-crops the photograph to the
slot's aspect, choosing the crop around the faces (see §6); an explicit `focus`
overrides that.

Treatments are a vocabulary, not a requirement. `border` draws a keyline in the
palette's `panel`; `shadow` lifts the photograph off the paper; `tilt` rotates it
a couple of degrees; `rounded` softens the corners by
`composition.slots.radius`. Use one idea at a time: a tilted photograph with a
heavy shadow and a border is noise.

Limits: at most `composition.slots.max` (12) slots; a slot's short side at least
`min_side` (0.06); photographs together between `photos.min_coverage` (0.20) and
`max_coverage` (0.84) of the page. A page with no slots is legitimate for a back.

### 3.5 Zones (words)

A zone reserves a rectangle for one piece of copy and sets its typography (§2.2).

| field | meaning |
| --- | --- |
| `word` | which copy (§2.3), or any label when `text` is present |
| `x, y, w, h` | the rectangle |
| `size, font, weight, italic, tracking, leading, caps` | the type (§2.2) |
| `align`, `valign` | horizontal and vertical placement |
| `panel` | `true`/`"panel"` or any palette token: a solid field behind the words |
| `panel_opacity`, `panel_pad` | its opacity, and extra padding as a fraction of the zone's short side |
| `color` | a palette token or `#hex`; omit to let the engine choose a readable ink |
| `rotate` | up to ±90° for a spine of type down an edge |
| `layer` | paint order |
| `over_photo` | the words are meant to sit on a photograph |
| `text` | literal copy for this zone, overriding the card's words |

Text sits on paper by default, and the gate rejects a zone that overlaps a slot
unless it declares `over_photo`. Then the overlap is deliberate: the engine
samples the average colour under the zone and colours the type for contrast, and
the gate reports that contrast. Two zones never overlap each other.

`over_photo` on a face is a judgement call: light type over a dark coat is fine,
over a forehead it is not. `./ccb see` shows the face boxes so you can check.

Limits: at most `composition.zones.max` (14) zones; a zone at least
`zones.min_width` (0.16) wide; text inside the safe margin is a warning, not an
error, because a deliberately inset colophon can work.

### 3.6 Rules (lines)

`lines` is a list of at most `lines.max` (8) straight rules:

```json
{"x1": 0.07, "y1": 0.55, "x2": 0.93, "y2": 0.55, "token": "accent", "weight": 1}
```

`token` is `ink`, `soft`, `accent`, `panel` or `bg`. `weight` is 0.25..3; above
that it is a border, not a rule. A rule is drawn over the paper and over
photographs, under the words. It is a good way to separate a photograph from a
caption column, or to underline a small line of type.

### 3.7 Ornaments and chrome (both opt-in)

```json
"ornaments": [{"kind": "snow", "density": 0.35}]
"chrome": {"border": "double", "decoration": "holly", "density": 0.4, "texture": true}
```

Ornament kinds: `holly`, `snow`, `stars`, `confetti`. `density` runs roughly
0..1.6. Ornaments are always kept out of text zones and photographs, so they
cannot cover a face or a word. A composition that lists no ornaments has none.

`chrome.border` is `none`, `rule`, `double`, `frame` or `postcard`;
`chrome.decoration` is any ornament kind; `chrome.texture` turns on the quiet
paper grain. Nothing here is applied unless you write it: a card with no `chrome`
and no `ornaments` is flat colour, photographs and type, which is usually the
stronger choice.

---

## 4. Fitting, colour and the floor

The fitter measures real glyphs. It sets the size you asked for, wraps to the
zone width, and if the copy would spill it steps down (never below 60% of your
size), then ellipsises. Both are reported by `check` with the word and the size,
so the fix is to shorten the copy or give the zone more room, not to guess.

- The floor is `composition.type_safety.min_pt` (7 pt in print). Below it the
  gate warns and names the copy.
- A zone with no `color` gets `ink` or `soft` — whichever is readable on what is
  actually behind it — or `on_panel` on a panel. Panels and type-on-photographs
  are sampled, not assumed.
- Capitalisation belongs to roman faces. `greatvibes` is never shouted, even
  when the zone says `caps`.

---

## 5. Photographs and faces

The face engine is **YuNet**, a small CNN that returns a box, five landmarks and
a confidence for every face. `./ccb faces` installs
`assets/models/face_detection_yunet_2023mar.onnx` (about 340 KB) once. Without
the model it falls back to OpenCV's Haar cascade; without OpenCV it reports
`none` and crops are centred. It never pretends to have found a face.

- Detection runs at up to 1024 px on the long side and boxes are mapped back.
- Every photograph is scanned when it is loaded, and the result is cached by
  path, modification time and size.
- `focus` for a slot defaults to the area-weighted centre of its faces, so a
  group photograph keeps its people when the slot is a narrow column.
- The gate checks, for every slot with faces, how much of each face survives the
  crop (`faces.min_crop_keep`, 65%) and how wide the widest face prints
  (`faces.min_width_in`, 0.16 in). Both are warnings with exact numbers.
- `./ccb see` draws every detection on the preview and the photo sheet and
  writes the positions and scores to `visual.md`/`visual.json`.

The detector does not identify anyone: no names, no embeddings, no recognition,
no network at inference time. It answers "where are the faces".

---

## 6. What gets checked

`./ccb layout` validates before saving; `./ccb check` validates every saved page
and measures the rendered type. Errors stop the save or fail the gate; warnings
are notes with numbers.

| code | level | meaning |
| --- | --- | --- |
| `rect.missing` / `rect.bounds` / `rect.size` | error | a rectangle is incomplete, off-page or empty |
| `photo.range` | error | the slot names a photograph that does not exist |
| `photo.treatment` / `photo.clip` | error | not in the vocabulary |
| `photo.focus` | error | focus is not `[x, y]` inside 0..1 |
| `photo.small` | warn | a slot's short side is below `min_side` |
| `photos.coverage` | warn/error | below the minimum (warn) or above the maximum (error) |
| `overlap.text_photo` | error | text sits on a photograph without `over_photo` |
| `overlap.same` | error | two zones overlap, or two slots overlap on the same layer |
| `background.*` | error | unknown background photo, colour, scrim value or direction |
| `shapes.*` | error | unknown shape, fill, opacity, rotation or layer |
| `palette.keys` | error | the system palette is not six valid `#hex` colours |
| `palette.contrast` | warn/error | ink or panel type is not readable enough |
| `type.word` | error | the zone names copy the rulebook does not have and sets no `text` |
| `type.size` | error | missing, or outside `type.sizes` |
| `type.font` | error | not an installed typeface |
| `type.weight` / `type.tracking` / `type.leading` | error | outside the stated ranges |
| `type.align` / `type.valign` / `type.color` / `type.panel` | error | outside the vocabulary |
| `type.narrow` / `type.small` | warn | the zone is too narrow or small for its copy |
| `type.margin` | warn | text leaves the safe margin |
| `type.over_photo` | warn | `over_photo` is set but no picture is underneath |
| `type.rotate` / `type.layer` | error | outside the allowed range |
| `words.empty` | warn | a placed part has no words |
| `composition.repeat` | warn | two fronts share the same skeleton |
| `composition.plain` | warn | a front is only a photograph and a stack of text |
| `ornaments.*` / `lines.*` / `chrome.*` | error | unknown kind, too many, off-page, too heavy |
| `faces.crop` | warn | a face keeps less than `min_crop_keep` |
| `faces.small` | warn | the widest face prints below `min_width_in` |
| `photos.unused` | warn | a photograph is not placed anywhere |
| `words.greeting` | warn | no greeting |

The gate also reports, from the rendered page: copy that had to shrink, copy that
was shortened, type below the floor, and type whose measured contrast is under
3:1.

---

## 7. Creative latitude

The agent is expected to invent. The rules do not prescribe a layout; they
describe what a layout must not break.

**Free to invent:** the entire palette; the typefaces, sizes, weights, tracking
and leading of every word; the background (flat, gradient, full-bleed
photograph, scrim); colour fields and shapes, including ones cut by the trim; the
number of slots and their geometry; clipping and tilting prints; collages of
overlapping photographs on different layers; type on a photograph, rotated type,
panels, the colour of the ink; asymmetric and full-bleed compositions; the number
of fronts and one back; rules; ornaments and chrome, or none at all; captions and
page numbers; words, as long as they are the user's words or plainly invented
greetings the user asked for.

**Not free to break:** text on a photograph without `over_photo`; a face cut in
half without saying so; type below the floor without saying so; a photograph
stretched; a word that is not a part and has no `text`; a palette that cannot be
read; a composition that runs off the page; claiming a `.pptx` when the output is
a PDF; claiming to have seen an image when the model cannot read images.

**Do not reach for the same page twice.** Two fronts for one card should differ
in skeleton, not only in words: a different background, a different arrangement
of the photographs, a different place for the words, a different typographic
idea. The gate warns when two fronts share a geometry (`composition.repeat`) and
when a front is nothing but a photograph and a stack of text
(`composition.plain`).

**How to use the latitude well:**

1. Write **two or three fronts**, not one. Each should argue for a different
   idea: a full-bleed hero, a quiet plate with air, a collage. Give them names.
2. Write the back as its own composition; a text-only back is normal.
3. Decide the hierarchy before the geometry: what is the one biggest thing on
   this page, and what is the smallest thing anyone needs to read? Then pick
   sizes, then place the words.
4. Let one colour do the loud work. A page with a strong paper, a strong accent
   and quiet ink reads as designed; four competing colours do not.
5. Use the photographs' own colours as evidence, not decoration.
6. When the gate warns, change the composition; do not raise the limits to make
   a warning disappear unless the user asked for that rule to change.

---

## 8. Tuning recipes

- **Change how bold the whole studio is:** raise `type.sizes.max` and
  `lines.max_weight`; raise `photos.max_coverage`.
- **A stricter gate:** raise `type_safety.min_pt`, `faces.min_crop_keep`,
  `palette.min_text_contrast` and `photos.min_coverage`.
- **A new paper size:** add it to `paper.sizes`; it appears in `./ccb sizes`,
  `--size`, and every brief.
- **More room for words:** raise `composition.zones.max` and `zones.min_width`.
- **No faces at all:** set `faces.min_crop_keep` to 0; focus still follows faces
  but the gate stops nagging. Or uninstall OpenCV.
- **A different house look:** add a paragraph to §7 saying what you now permit.
  There is no palette or style list to edit — that is the point.

Numbers are cheap to change. If you change the *meaning* of a rule, change this
file too, because the agent reads it.

---

## 9. The loop

```
./ccb brief <card>            the playbook, the page, the photographs, the colours, the faces
read out/see/photos.jpg       if your model can see images (otherwise visual.md)
write design.json             a system palette + two or three fronts + a back
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
safe margin, every slot, every zone and every face box. `visual.md` carries the
same facts in words. A model that cannot read images must say so and work from
`visual.md`; it must not describe a picture it has not seen.

---

## 10. Version

This playbook describes rulebook version 4.

- **4** removed every preset. There are no directions, no named palettes and no
  type roles any more: a card declares its own six-colour palette (or samples one
  from its photographs), and each zone carries its own size, typeface, weight,
  tracking and leading. Typefaces are a shelf of six installed fonts, not a
  style. The brief prints the photographs' own colours, and `./ccb palette`
  shows the palette and where the colours came from.
- **3** added backgrounds, shapes, layers, clipping, rotation, type on
  photographs and opt-in chrome, and stopped the renderer applying a style's
  border, decoration or texture on its own.
- **2** replaced the layout engines and fixed designs with rulebook checks and
  free compositions.

Old cards are migrated on load: a `direction`, a named `palette` and `roles` are
dropped, and each zone takes the first word it named. They will need their
typography set before they render as intended.
