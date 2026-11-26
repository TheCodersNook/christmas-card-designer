# Christmas Cards and Presentation Maker

Your photographs, your words: a card you can print, and a 16:9 presentation you
can project. An [OpenCode](https://opencode.ai) project that designs both from
your own pictures, on your own computer.

**Nothing is a preset.** There is no style picker, no palette library, no layout
setting and no fixed type scale. The studio ships a detailed playbook and a
composition engine. The agent reads the playbook, chooses the colours and the
typefaces, sets every size itself, writes the page — and the engine checks the
numbers and renders it.

```
/card inputs/*.jpg --family "The Hayes Family" --greeting "Merry Christmas"
/presentation inputs/*.jpg --title "The Hayes Family" --subtitle "2026"
/fix make the greeting smaller and give the cabin photo a caption
```

---

## What makes it different

- **A playbook, not a catalogue.** `studio/rules.json` holds paper, palette
  rules, type limits and the primitives. `studio/RULES.md` explains every field
  and says what may be invented. Nothing about the look is compiled into the
  code, and there are no named designs to fall back on.
- **Its own colours, every time.** Each card and deck declares six `#hex`
  colours — paper, ink, soft ink, accent, panel, panel ink — with contrast rules
  the engine enforces. `./ccb brief` prints the six most common colours of every
  photograph, so the palette can come out of the pictures. With no palette at
  all, the engine samples one so the card can still render.
- **Its own typography, every time.** A zone carries its size (a fraction of the
  page's short side), typeface, weight, tracking, leading, case and alignment.
  There is no role scale to obey: a 0.088 Playfair greeting beside a 0.018 Lato
  caption is a decision, not a preset. Six OFL typefaces are installed (Playfair
  Display, Cormorant Garamond, Montserrat, Lato, Instrument Serif, Great Vibes).
- **Compositions, not layouts.** A page is a background (flat, gradient, or a
  full-bleed photograph under a scrim), colour fields and shapes, photograph
  slots that can be clipped into an arch or a circle, tilted, layered into a
  collage, text zones that can sit on a photograph or run down an edge, rules,
  and optional chrome. Every element has a layer. Nothing is added that the
  composition did not ask for.
- **Each page is its own.** The agent writes two or three genuinely different
  fronts; the gate warns when two share a skeleton (`composition.repeat`) or when
  a page is only a photograph and a stack of text (`composition.plain`).
- **A gate, not blind faith.** Every rectangle is checked for bounds, overlaps,
  margins, coverage, type sizes, palette contrast and print resolution. Errors
  stop the save with the rule named; warnings carry exact numbers.
- **Face-aware cropping.** YuNet (a small CNN, five landmarks, confidence) finds
  faces. Crops move to keep people whole, and the gate says when a face would be
  cut or printed too small. `./ccb faces` installs the 340 KB model once.
- **The agent can see.** `./ccb see` writes an annotated preview (margin, slots,
  zones, face boxes), a photo contact sheet with face boxes, and a `visual.md`
  with the same measurements in words. If the model can read images it looks; if
  not, it says so and works from the report.
- **True-size output.** 300 DPI PDF with bleed and crop marks for print; PDF plus
  optional per-slide PNGs for a deck. No `.pptx` is produced or claimed.

Everything is local. No account, no upload, no cloud, no image leaves the
machine. The face engine does not recognise anyone: boxes and landmarks only.

---

## Install

Requires Python 3.10+ and [OpenCode](https://opencode.ai).

```bash
cd christmas-cards-and-presentation-maker
./setup.sh          # Python packages, OFL fonts, doctor
./ccb faces         # optional: the YuNet face model (340 KB, once)
./ccb samples       # six demo photographs in inputs/
```

`./setup.sh` uses `uv` when available and falls back to a virtual environment.
The fonts are downloaded once under the SIL Open Font License. If OpenCV is not
installed, cards still work with centred crops; `./ccb faces` tells you what is
missing.

Then in this folder:

```bash
opencode
```

Pick a model and type `/card`, `/presentation` or `/fix`. The commands are in
`.opencode/commands/` and install automatically.

---

## The loop

```bash
./ccb brief cards/hayes            # the playbook, the photos, their colours, the faces, the words
# the agent looks at out/see/photos.jpg, then writes design.json
./ccb layout cards/hayes --file design.json
./ccb check cards/hayes            # 0 errors before anything is printed
./ccb see cards/hayes              # annotated front + faces + visual.md
./ccb render cards/hayes           # PDF / PNG / JPEG at true size
./ccb qa cards/hayes               # reads the files back and verifies them
```

For a presentation:

```bash
./ccb deck new inputs/*.jpg --name hayes-2026 --title "The Hayes Family"
./ccb deck brief decks/hayes-2026
# the agent writes slides.json
./ccb deck layout decks/hayes-2026 --file slides.json
./ccb deck check decks/hayes-2026
./ccb deck see decks/hayes-2026
./ccb deck render decks/hayes-2026 --png
./ccb deck qa decks/hayes-2026
```

A card can hold several fronts and one back; `--select` picks which front is
rendered. A deck is any number of slides, each one composition. There are no
fixed slide kinds.

`./ccb make inputs/*.jpg --name hayes` is the one-command start: it copies the
photographs, writes card.json, writes the brief and the photo sheet, and stops
there. The design is the next step, because it is the part that should be
designed rather than generated.

---

## Tuning it

| you want | edit |
| --- | --- |
| bigger or smaller type allowed | `type.sizes` in `studio/rules.json` |
| stricter or looser readability | `palette.min_text_contrast` |
| stricter or looser checks | `composition.*` in `rules.json` |
| a new paper size | `paper.sizes` in `rules.json` |
| more text on a page | `composition.zones.max` |
| a new principle the agent must follow | `studio/RULES.md`, section 7 |

`./ccb palette` prints the current card's colours, the colours in its
photographs and the installed typefaces; `./ccb sizes` prints the paper. The
playbook is read at startup, so a change applies to the next command.

The agent's brief is generated from the same file: change a number and the brief
changes. That is the whole point — you are tuning the studio, not editing Python.

---

## Output

```
cards/<name>/
  card.json            photos, words, system palette, compositions
  brief.md             the playbook for this page
  report.md            what was composed
  out/
    <name>.pdf         print PDF: trim + bleed, crop marks, 1 or 2 pages
    <name>.png/.jpg    front (and -back) at true size
    designs.jpg        contact sheet of every front
    export.json        what was written, with measured type
    qa.md              PASS/FAIL, warnings, page-size verification
    see/front.png      annotated: margin, slots, zones, face boxes
    see/photos.jpg     every photograph with face boxes
    see/visual.md      the same facts in words
decks/<name>/
  deck.json, brief.md, report.md
  out/<name>.pdf      13.333 x 7.5 in, 16:9
  out/slides/*.png    one per slide (with --png)
  out/qa.md, slides.jpg, export.json, see/
```

Print sizes: 5x7, 4x6, 5x5, A6, A2, portrait or landscape; bleed 0.125 in; crop
marks optional (`--no-crop`). Deck slides are always 2000 x 1125 px at 150 DPI
by default.

---

## The commands

| command | what it does |
| --- | --- |
| `/card` | photograph → card: brief, see the photos, choose a palette and type, compose 2-3 fronts + a back, gate, preview, print PDF |
| `/presentation` | photograph → 16:9 deck: brief, see the photos, compose slides, gate, contact sheet, PDF + PNGs |
| `/fix` | change words, palette, typography, crops or layout of a card **or** a deck, then re-check and re-render |
| `/palette` | show the card's colours, the colours in its photographs and the installed typefaces |

On the command line: `doctor`, `samples`, `new`/`add`, `brief`, `layout`,
`text`, `check`, `see`, `sheet`, `render`, `qa`, `faces`, `fonts`, `palette`,
`deck ...`, `status`, `sizes`, `selftest`.

---

## Requirements

- Python 3.10+, Pillow, NumPy, ReportLab
- OpenCV (`opencv-python-headless`) and the YuNet model for face detection —
  optional, but recommended
- The studio's OFL fonts (downloaded by `setup.sh`)
- No network at render time; the model and fonts are downloaded once

`./ccb selftest` checks the whole chain with generated photographs: rules,
palettes, compositions, faces, print PDF, deck PDF and the annotated previews.

---

## Project layout

```
.opencode/
  commands/                 card.md, presentation.md, fix.md, palette.md, status.md
  skills/christmas-card/
    SKILL.md                how the agent works
    reference/              PLAN.md (the schema and the loop)
    scripts/ccstudio/       the engine (no design presets)
      config.py             loads studio/rules.json
      colour.py             hex, mixing, contrast
      compose.py            brief, palette checks, composition checks, install
      faces.py              YuNet / Haar, face-aware focus
      see.py                annotated previews and visual report
      render.py             one renderer for cards and slides
      deck.py               slides as compositions
      ...
studio/
  rules.json                the numbers
  RULES.md                  the judgement, in full
```

Licence: MIT for the code, SIL OFL for the fonts, CC0 for the demo
illustrations. Your photographs and cards stay yours.
