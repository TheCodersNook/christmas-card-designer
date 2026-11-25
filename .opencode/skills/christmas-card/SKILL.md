---
name: christmas-card
description: The Christmas studio as one self-contained skill. It turns a family's own photographs into print-ready Christmas cards - a greeting, a family name, a message and a signature composed with six deterministic layout engines, eight card styles, six palettes, five trim sizes, decoration that avoids faces, and a true-size 300 DPI PDF/PNG/JPEG export with bleed and crop marks - and into 16:9 Christmas presentations: a cover, a statement, numbered photographic plates, a gallery and a closing, exported as a 150 DPI PDF plus optional PNGs. It ships its own engine (Python + Pillow + ReportLab, runs anywhere), so it works outside OpenCode too. Use it whenever someone gives photographs and asks for a Christmas card, a holiday card, a family card, a photo card, a card to print, "make our card", a matching back page, a Christmas presentation, a slideshow, a year-in-review deck, or names this skill.
---

# christmas-card: a card and presentation studio, end to end

The photographs are the work. Everything else - the greeting, the paper, the
margin, the rule, the holly - exists so the photographs look like they were
printed (or projected) on purpose.

Two outputs share one engine, one set of styles and the same rules: a **card**
(a small printed object, 300 DPI, bleed and crop marks) and a **presentation**
(16:9, one idea per slide, no bleed).

The judgements that make a card look designed are in the engine, not in the
model: measured typography, physical spacing, cover crops, deterministic
decoration, and a gate that refuses overlaps. A free model is enough. Your job
is to run the engine, read its report, fix the copy, and choose the design.

**Read before the first card in a session:** `reference/STYLE.md` (what makes a
card look designed), `reference/PLAN.md` (the card.json schema and every
command) and `AGENTS.md` (the workflow).

## Never break these

1. **Their words, their names.** Never invent a family name, a year, a greeting
   or a fact. If a field is missing, ask for it or leave it out; empty fields
   collapse instead of leaving gaps.
2. **Photographs are never altered.** `inputs/` is read-only. The engine
   cover-crops in memory; it never stretches, filters, whitens or replaces a
   photograph. Do not run an image editor over their files.
3. **Text never sits on a face.** Every engine reserves text zones before any
   photograph is placed, and the gate fails if a zone and a slot overlap. Never
   hand-edit `slots` or `zones` to squeeze text over a picture.
4. **Print truth.** The PDF page is the real physical size plus the 0.125 in
   bleed, with crop marks outside the trim. Never claim a size you did not
   export at 300 DPI. `./ccb qa` reads the exported files back; the gate is what
   you report, not your impression.
5. **One style, one palette.** A card has one style and one palette. Do not mix
   two decoration sets to "fill space".
6. **Leave the margin.** Text stays inside the style's margin. Full-bleed
   photographs are a deliberate engine choice (the panorama), not something to
   copy into other designs.
7. **Nothing is promised that cannot be measured.** Do not say a photograph is
   sharp, a face is well framed, or a card "looks great". You cannot see it:
   say what the report measured, and ask them to look at `out/designs.jpg`.
8. **No stock or generated imagery in their card.** Only the photographs they
   supplied, plus vector decoration the engine draws.
9. **A presentation is not a card.** It is always 16:9, has no bleed, no crop
   marks, no back page and no trim size, and its deliverable is a PDF (plus PNGs
   when asked) - never promise a `.pptx`.

## The vocabulary

- **Six layout engines**, all deterministic:
  - `grid` - a uniform grid of photographs, text above and below;
  - `hero` - one large hero photograph and a strip of the rest;
  - `mosaic` - a recursive proportional split, cells shaped by the photographs;
  - `editorial` - a text column beside a photographic plate;
  - `postcard` - a big hero, a photo strip and a roomy message block;
  - `banner` - an edge-to-edge panorama band, framed by the printed border.

  With `layout: "auto"` the engine runs all six, scores them (photograph
  coverage, crop loss, visual balance, text room) and keeps the best `variants`.
- **Eight styles** (`./ccb styles`): Classic Christmas, Modern Minimalist,
  Traditional Holiday, Luxury Editorial, Scandinavian, Vintage Christmas,
  Playful Festive, Photo-First. A style changes fonts, case, tracking, spacing,
  border, photo treatment and decoration - not just colour.
- **Six palettes**: evergreen, cranberry, midnight, nordic, brass, peppermint.
- **Type roles**: `greeting`, `family`, `message`, `signature`, `year`. All but
  the greeting are optional; the greeting is what a card is for.
- **Five slide kinds** for presentations: `cover`, `statement`, `hero` (a
  numbered photographic plate), `grid` (the gallery), `closing`. The planner uses
  each photograph exactly once and keeps the strongest for the cover.

## The fast path

```
./ccb samples                                   # six demo illustrations, no files needed
./ccb make inputs/*.jpg --name hayes-2026 \
    --greeting "Merry Christmas" --family "The Hayes Family" \
    --message "Wishing you a quiet, bright Christmas." \
    --signature "with love, Anna and Tom" --year 2026
```

One command: copies the photographs into `inputs/`, writes
`cards/hayes-2026/card.json`, plans six designs, runs the gate, writes the
contact sheet, exports the card and verifies the files. Follow it with
`./ccb check` and `./ccb render` whenever you change anything.

For the presentation from the same photographs:

```
./ccb deck make inputs/*.jpg --name hayes-2026 \
    --title "The Hayes Family" --subtitle "2026 in photographs" \
    --greeting "Merry Christmas" --message "A year of small adventures." \
    --signature "with love, Anna and Tom" --year 2026
```

It plans the slides, gates them, writes `out/slides.jpg`, exports the 16:9 PDF
and verifies it. Add `--png` for one image per slide.

## The run (gates in order)

0. **Get the photographs in.** They may give a folder, a list, drag files into
   the chat, or paste paths (possibly starting with `@`, possibly escaped). Run
   `./ccb add "<path>"` for each, or pass them straight to `./ccb new`. The
   originals are never modified.
1. **Start the card:** `./ccb new <photos...> --name <family-year> --style classic
   --size 5x7 [--landscape]`. This plans designs and writes `report.md`.
2. **Get the words right.** Read `cards/<name>/report.md`. Set them with
   `./ccb text cards/<name> --greeting "..." --family "..." --message "..."
   --signature "..." --year "..."`, or edit `text` in `card.json`. Keep the
   message to two or three sentences: it is a card, not a letter.
3. **Read the plan.** `report.md` lists the photographs, the six designs, their
   scores and every to-do. A good card usually has a hero photograph; set
   `design.hero` to that file name when the automatic choice is wrong, or
   reorder `photos` so the best picture comes first.
4. **Gate:** `./ccb check cards/<name>`. It must show `0 errors`. Fix each
   warning or say why you kept it. The gate measures geometry, real fitted type
   sizes, contrast and whether a photograph is being used far above its own
   resolution.
5. **Look before you render:** `./ccb sheet cards/<name>` writes
   `out/designs.jpg` - all six designs at once. Ask them to look at it, and ask
   which number they prefer. Never claim you looked at it yourself.
6. **Choose and render:** `./ccb render cards/<name> --design 2`. Add
   `--format png` or `--format jpeg` when they want images rather than a PDF,
   `--no-back` for a one-sided card, `--draft` for a 120 DPI proof.
7. **Verify:** `./ccb qa cards/<name>`. It re-reads the files: PDF page boxes,
   page count, PNG pixel dimensions, DPI metadata. It must say `PASS`.
8. **Report back** in 5-8 lines: the design chosen and why, the words used, the
   output path, the physical size and DPI, and what is still open (a missing
   name, a low-resolution photograph, a design they have not chosen yet).

## Where it runs

- **In this project:** everything through `./ccb` from the project folder (see
  `README.md` for setup on macOS, Linux and Windows/WSL).
- **Any terminal:** `PYTHONPATH=.opencode/skills/christmas-card/scripts python -m
  ccstudio ...` after `pip install numpy pillow reportlab`.
- **claude.ai or another sandbox:** `pip install numpy pillow reportlab`, then
  the same `-m ccstudio` commands. Fonts are downloaded by `./ccb fonts`; with
  no fonts the engine falls back to a system TrueType font and `./ccb doctor`
  says so.

## When they give feedback

| They say | Do this |
| --- | --- |
| "try another style" / "less classic" | `--style modern` (or `editorial`, `nordic`, `vintage`, `joyful`, `gallery`) in `card.json`, then `./ccb auto` |
| "warmer" / "darker" / "more Christmassy" | change `design.palette` (evergreen, cranberry, midnight, nordic, brass, peppermint) |
| "use design 3" | `./ccb render cards/<name> --design 3` |
| "bigger photos" | pick the `banner`, `gallery` or `editorial` layout, or `--style gallery` |
| "less busy" | `--style modern` or `../card/out` padding: use `editorial`; drop photographs they do not need |
| "put grandma first" | move that file to the front of `photos`, set `design.hero`, then `./ccb auto` |
| "change the wording" | `./ccb text ...`, then `./ccb check` and `./ccb render` |
| "smaller card" / "different paper" | `--size 4x6`, `5x5`, `a6`, `a2`, or `--landscape` |
| "I want an image, not a PDF" | `./ccb render cards/<name> --format png` |
| "no back page" | `"back": false` in `export`, or `./ccb render --no-back` |
| "bleed/crop marks" | `--no-bleed` to drop them; they are on by default |
| "make a slideshow / presentation too" | `./ccb deck make <photos> --name x --title ...` |
| "caption this photograph" | add it under `captions` in `decks/<name>/deck.json`, then `./ccb deck plan` |
| "one image per slide" | `./ccb deck render decks/<name> --png` |
| "bigger / smaller slides" | the deck is fixed at 16:9; change `--dpi` instead |

When a note is a lasting preference ("always leave the year off"), add it to
`reference/STYLE.md` under "House notes" with the date, so it holds next year.
