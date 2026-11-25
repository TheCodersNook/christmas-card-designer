# card.json and the commands

One card is one folder: `cards/<name>/`. `card.json` is the only file a person
edits. Everything else is produced by the engine.

```
cards/hayes-2026/
├── card.json        the photographs, the words, the print settings, the designs
├── report.md        what the director decided and what is still to do
└── out/
    ├── designs.jpg  every design on one contact sheet
    ├── hayes-2026.pdf   the print file (or .png/.jpg, plus -back)
    ├── export.json  what was written, at what size
    └── qa.md        the verification of the real files
```

## Schema

```json
{
  "name": "hayes-2026",
  "photos": [
    "../../inputs/family_tree.jpg",
    "../../inputs/couple_snow.jpg",
    "../../inputs/cabin.jpg"
  ],
  "text": {
    "greeting": "Merry Christmas",
    "family": "The Hayes Family",
    "message": "Wishing you a quiet, bright Christmas and a new year full of good things.",
    "signature": "with love, Anna and Tom",
    "year": "2026"
  },
  "design": {
    "style": "classic",
    "palette": "",
    "size": "5x7",
    "orientation": "portrait",
    "layout": "auto",
    "hero": "",
    "order": [],
    "variants": 6
  },
  "export": {
    "format": "pdf",
    "dpi": 300,
    "bleed": true,
    "crop_marks": true,
    "back": true,
    "jpeg_quality": 95
  },
  "designs": [ ... written by ./ccb auto ... ],
  "selected": 0
}
```

### text

| Field | Meaning | Limits |
| --- | --- | --- |
| `greeting` | what the card says first | 2-4 words; 3 lines maximum |
| `family` | the family or sender name | 2 lines |
| `message` | the note on the front and back | 2-3 sentences; under ~40 words |
| `signature` | how it is signed | 2 lines |
| `year` | the year | four digits |

Every field is optional except that a card needs at least one of them. Empty
fields collapse and the rest re-fits, so nothing is left as a hole. `./ccb text`
sets them without touching JSON:

```bash
./ccb text cards/hayes-2026 --message "Wishing you a quiet, bright Christmas."
```

### design

| Field | Values | Notes |
| --- | --- | --- |
| `style` | `classic`, `modern`, `traditional`, `editorial`, `nordic`, `vintage`, `joyful`, `gallery` | see `reference/STYLE.md` |
| `palette` | `evergreen`, `cranberry`, `midnight`, `nordic`, `brass`, `peppermint`, or `""` | empty uses the style's own palette |
| `size` | `5x7`, `4x6`, `5x5`, `a6`, `a2` | inches, portrait |
| `orientation` | `portrait`, `landscape` | swaps width and height |
| `layout` | `auto` or one engine: `grid`, `hero`, `mosaic`, `editorial`, `postcard`, `banner` | `auto` runs all six |
| `hero` | a file name from `photos` | the photograph to feature |
| `order` | list of file names | overrides the order photographs were added |
| `variants` | 1-6 | how many designs to keep |

### export

| Field | Values | Notes |
| --- | --- | --- |
| `format` | `pdf`, `png`, `jpeg` | PDF is the print file |
| `dpi` | 96-1200 | 300 for print, 150 for a proof |
| `bleed` | true/false | 0.125 in on every edge |
| `crop_marks` | true/false | vector marks in the bleed, PDF only |
| `back` | true/false | a second page / a `-back` image |
| `jpeg_quality` | 1-100 | 95 with 4:4:4 subsampling |

`designs` and `selected` are written by `./ccb auto`. Do not hand-edit slots or
zones: change the style, layout or photographs and let the engine plan again.
You may hand-edit `selected` (0-based) or use `--design N` (1-based).

## Commands

| Command | What it does |
| --- | --- |
| `./ccb doctor` | Python, packages, fonts, card count |
| `./ccb fonts` | download the OFL fonts into `assets/fonts/` |
| `./ccb samples` | draw six demo illustrations into `inputs/` |
| `./ccb add <photo>...` | copy photographs into `inputs/` with safe names |
| `./ccb new <photo>... --name x` | start a card and plan its six designs |
| `./ccb auto [card]` | re-plan designs, rewrite `report.md` |
| `./ccb text [card] --family "..."` | change words only |
| `./ccb check [card] [--design N] [--strict]` | the gate; 0 errors before export |
| `./ccb sheet [card]` | contact sheet at `out/designs.jpg` |
| `./ccb render [card] --design N` | write PDF/PNG/JPEG and verify them |
| `./ccb qa [card]` | verify the exported files again, write `out/qa.md` |
| `./ccb make <photo>... \| --card x` | plan, gate, sheet, export, QA in one go |
| `./ccb status` | every card and presentation, and its files |
| `./ccb styles` / `./ccb sizes` | what the studio can print |
| `./ccb selftest` | end-to-end test with generated photographs |

A card argument can be a folder (`cards/hayes-2026`) or the JSON file. With one
card in the project you can leave it out entirely.

`render` accepts `--format`, `--dpi`, `--no-bleed`, `--no-back`, `--draft`
(120 DPI proof), `-o <folder>`.

## Exit codes

`0` success, `1` a gate error, a missing file, or a failed verification. A
render refuses to write print files while the gate has errors.

## What the gate checks

- every photograph appears exactly once, and no slot or zone leaves the card;
- no text zone overlaps a photograph slot;
- the real fitted type: which roles reached the card, their point size, whether
  copy had to be shortened, and the measured contrast of every block;
- photographs used far above their own resolution (soft print);
- text present at all, and the card has a greeting or a family name.

Warnings are advice, not failures. `--strict` turns them into failures when you
want a completely quiet card.

# deck.json and the presentation commands

One presentation is one folder: `decks/<name>/`. `deck.json` is the only file a
person edits.

```
decks/hayes-2026/
├── deck.json        the photographs, the words, the captions, the theme, the slide plan
├── report.md        the slide plan and what is still to do
└── out/
    ├── slides.jpg   every slide on one contact sheet
    ├── hayes-2026.pdf    the 16:9 PDF at 13.33 x 7.5 in
    ├── slides/      slide-01.png ... when rendered with --png
    ├── export.json  what was written, at what size
    └── qa.md        the verification of the real pages
```

## Schema

```json
{
  "name": "hayes-2026",
  "photos": ["../../inputs/family_tree.jpg", "../../inputs/cabin.jpg"],
  "text": {
    "title": "The Hayes Family",
    "subtitle": "2026 in photographs",
    "greeting": "Merry Christmas",
    "message": "A year of small adventures and a great deal of snow.",
    "signature": "with love, Anna and Tom",
    "year": "2026"
  },
  "captions": {"cabin.jpg": "First snow", "table.jpg": "Christmas Eve"},
  "design": {
    "style": "editorial",
    "palette": "",
    "hero": ""
  },
  "export": {
    "format": "pdf",
    "dpi": 150,
    "jpeg_quality": 92,
    "png_slides": false
  },
  "slides": [ ... written by ./ccb deck plan ... ]
}
```

### text

| Field | Meaning | Limits |
| --- | --- | --- |
| `title` | the cover line | 5 words; 3 lines |
| `subtitle` | what the deck is | 6 words; 2 lines |
| `greeting` | the seasonal line on the cover and closing | 2-4 words |
| `message` | the statement slide | 2-3 sentences; under ~30 words |
| `signature` | how the closing is signed | 2 lines |
| `year` | the year | four digits |

If there is no `subtitle`, the year takes its place on the cover and is not
repeated. Empty fields collapse. `./ccb deck text` sets them without editing
JSON:

```bash
./ccb deck text decks/hayes-2026 --title "The Hayes Family" --message "..."
```

### captions

A map from photograph file name (or stem) to one line of copy. A caption appears
under the photograph in a gallery and beside it on its own slide. Never invent a
caption: leave it out.

### design

| Field | Values | Notes |
| --- | --- | --- |
| `style` | the same eight styles as a card | `editorial` is the default: brass, wide margins, quiet |
| `palette` | the same six palettes, or `""` | empty uses the style's own |
| `hero` | a file name from `photos` | the photograph on the cover |

### export

| Field | Values | Notes |
| --- | --- | --- |
| `format` | `pdf` | the deliverable |
| `dpi` | 96-1200 | 150 for screens, 200 for print |
| `jpeg_quality` | 1-100 | 92 |
| `png_slides` | true/false | one PNG per slide into `out/slides/` |

`slides` is written by `./ccb deck plan`. Do not hand-edit it: change the words,
the photographs or the captions and plan again.

## Commands

| Command | What it does |
| --- | --- |
| `./ccb deck make <photo>... \| --deck x` | plan, gate, sheet, export and QA in one go |
| `./ccb deck new <photo>... --name x` | start a presentation and plan its slides |
| `./ccb deck plan [deck]` | re-plan the slides, rewrite `report.md` |
| `./ccb deck text [deck] --title "..."` | change the words only |
| `./ccb deck check [deck] [--replan]` | the gate; 0 errors before an export |
| `./ccb deck sheet [deck]` | contact sheet at `out/slides.jpg` |
| `./ccb deck render [deck] [--png]` | write the PDF (and PNGs), verify them |
| `./ccb deck qa [deck]` | verify the exported pages, write `out/qa.md` |

A deck argument can be a folder (`decks/hayes-2026`) or the JSON file. With one
presentation in the project you can leave it out.

## What the deck gate checks

- a cover exists, a closing exists and there is more than one slide;
- every photograph appears exactly once, and no slide or text zone leaves the
  page;
- no text zone overlaps a photograph;
- the real fitted type: point sizes, whether copy had to be shortened, contrast;
- photographs used far above their own resolution on a 16:9 slide;
- there are words at all.

The deck gate is separate from the card gate: `./ccb check` never inspects a
presentation, and `./ccb deck check` never inspects a card.
