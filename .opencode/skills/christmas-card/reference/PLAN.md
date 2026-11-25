# card.json, deck.json and the commands

One card is one folder: `cards/<name>/`. One presentation is `decks/<name>/`.
The JSON file is the only thing that describes the work; everything in `out/` is
produced. There is no `layout` or `designs` setting any more: a card holds
**compositions** the agent wrote.

```
cards/hayes/
  card.json        photographs, words, direction, compositions
  brief.md         what the agent must know before composing
  report.md        what was composed
  out/
    hayes.pdf      print file (or .png/.jpg, plus -back)
    designs.jpg    contact sheet of every front
    export.json    what was written, at what size
    qa.md          verification of the real files
    see/           front.png, back.png, photos.jpg, visual.md, visual.json
decks/hayes-2026/
  deck.json, brief.md, report.md
  out/hayes-2026.pdf, slides/*.png, slides.jpg, export.json, qa.md, see/
```

## card.json

```json
{
  "name": "hayes",
  "photos": ["../inputs/a.jpg", "../inputs/b.jpg"],
  "text": {"greeting": "Merry Christmas", "family": "The Hayes Family",
           "message": "...", "signature": "with love, ...", "year": "2026"},
  "design": {
    "direction": "editorial",
    "palette": "",
    "size": "5x7",
    "orientation": "portrait",
    "selected": 0,
    "compositions": [
      {"name": "Family plate", "side": "front", "slots": [], "zones": [],
       "ornaments": [], "lines": [], "notes": "..."},
      {"name": "Back", "side": "back", "slots": [], "zones": [],
       "ornaments": [], "lines": []}
    ]
  },
  "export": {"format": "pdf", "dpi": 300, "bleed": true,
             "crop_marks": true, "back": true, "jpeg_quality": 95}
}
```

- `direction` names a direction in `studio/rules.json`; it supplies defaults and
  guidance, never geometry.
- `palette` empty means the direction's palette.
- `selected` indexes the **front** compositions.
- `size` and `orientation` come from `paper.sizes`.
- A version-1 card (`style`, top-level `designs`) is migrated on load: the
  designs become front compositions and `style` becomes `direction`.

## deck.json

```json
{
  "name": "hayes-2026",
  "photos": ["../inputs/a.jpg"],
  "text": {"title": "The Hayes Family", "subtitle": "2026 in photographs",
           "greeting": "Merry Christmas", "message": "...",
           "signature": "with love, ...", "year": "2026"},
  "design": {"direction": "editorial", "palette": "brass", "compositions": []},
  "export": {"format": "pdf", "dpi": 150, "png": false}
}
```

`compositions` are the slides, in order. Each is the same object as a card's
composition (`side` is ignored). Text roles for a deck add `title` and
`subtitle`; a zone's `text` field carries captions and page numbers.

## A composition

```json
{
  "name": "Full-bleed cover",
  "side": "front",
  "background": {"photo": 0, "scrim": 0.9, "scrim_from": "bottom",
                 "scrim_reach": 0.62, "scrim_color": "panel"},
  "shapes": [{"kind": "band", "x": 0, "y": 0.86, "w": 1, "h": 0.14,
              "fill": "accent", "layer": 1}],
  "slots": [{"photo": 1, "x": 0.58, "y": 0.10, "w": 0.36, "h": 0.42,
             "clip": "arch", "rotate": 2, "treatment": "shadow", "layer": 2}],
  "zones": [{"roles": ["greeting"], "x": 0.06, "y": 0.60, "w": 0.86,
             "h": 0.10, "align": "left", "over_photo": true},
            {"roles": ["year"], "x": 0.70, "y": 0.88, "w": 0.24, "h": 0.04,
             "align": "right"}],
  "ornaments": [],
  "lines": [{"x1": 0.06, "y1": 0.57, "x2": 0.94, "y2": 0.57,
             "token": "accent", "weight": 1}],
  "chrome": {"border": "none"}
}
```

All fields and limits are in `studio/RULES.md`; the numbers are in
`studio/rules.json`. `./ccb brief` prints the ones that matter for the page.

## Commands

| command | does |
| --- | --- |
| `./ccb doctor` | what is installed, fonts, face engine, rulebook path |
| `./ccb samples` | six generated demo photographs in `inputs/` |
| `./ccb new` / `add` | copy photographs, write card.json (no design) |
| `./ccb brief` | write and print the brief |
| `./ccb layout --file x.json` | validate and install compositions (`--select`, `--append`) |
| `./ccb text` | change the words |
| `./ccb check` | gate every composition + measured type |
| `./ccb see` | annotated previews, photo sheet, visual report |
| `./ccb sheet` | contact sheet of every saved composition |
| `./ccb render` | PDF/PNG/JPEG at true size |
| `./ccb qa` | read the PDF back, verify pages, size and DPI |
| `./ccb faces` | install YuNet; scan photographs |
| `./ccb status` | cards and decks, and whether they are composed |
| `./ccb directions` | the rulebook's directions and guidance |
| `./ccb sizes` | paper sizes and bleed |
| `./ccb selftest` | end-to-end check with generated photographs |
| `./ccb deck new/brief/layout/text/check/see/sheet/render/qa` | the same for slides |

## The gate

`layout` validates before saving; `check` validates every saved composition and
then renders the selected front at 110 DPI to measure real type. Publish only
after `check` shows 0 errors and `qa` says PASS.

Errors: off-page rectangles, text on a photograph without `over_photo`,
overlapping zones, overlapping slots on the same layer, unknown
backgrounds/shapes/roles/treatments/clips/fonts/alignments, coverage above the
maximum, unknown ornament kinds or tokens, rules too heavy. Warnings: coverage
below the minimum, small slots or zones, text outside the safe area, faces cut or
printed too small, type below the floor, low contrast, shortened copy, soft
photographs, repeated skeletons (`composition.repeat`) and pages that are only a
photograph and a stack of text (`composition.plain`).

## Seeing

`see` writes:

- `front.png` — the rendered front with the margin, every slot (green), every
  zone (blue) and every face box (red);
- `photos.jpg` — every photograph, numbered, with face boxes;
- `visual.md` / `visual.json` — the same positions, sizes, face scores and
  warnings in words.

A vision-capable model opens the images. A text-only model reads `visual.md` and
says it cannot see the picture. Neither may invent what is in a photograph.
