# card.json, deck.json and the commands

One card is one folder: `cards/<name>/`. One presentation is `decks/<name>/`.
The JSON file is the only thing that describes the work; everything in `out/` is
produced. There is no style, no palette catalogue and no type scale: a card
carries its own six colours, and every zone carries its own typography.

```
cards/hayes/
  card.json        photographs, words, system palette, compositions
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
    "size": "5x7",
    "orientation": "portrait",
    "system": {
      "palette": {"bg": "#F4EEE1", "ink": "#1D2A22", "soft": "#5C6A5E",
                  "accent": "#A02B32", "panel": "#1D2A22", "on_panel": "#F4EEE1"},
      "note": "why these colours"
    },
    "selected": 0,
    "compositions": [
      {"name": "Full bleed", "side": "front", "slots": [], "zones": [],
       "ornaments": [], "lines": [], "notes": "..."},
      {"name": "Note", "side": "back", "slots": [], "zones": [],
       "ornaments": [], "lines": []}
    ]
  },
  "export": {"format": "pdf", "dpi": 300, "bleed": true,
             "crop_marks": true, "back": true, "jpeg_quality": 95}
}
```

- `system.palette` is six `#hex` colours. With none, the engine samples one from
  photograph 0 and the brief says so.
- `selected` indexes the **front** compositions.
- `size` and `orientation` come from `paper.sizes`.
- A layout file may carry `system` alongside the pages; `./ccb layout` installs
  both in one save.

## deck.json

```json
{
  "name": "hayes-2026",
  "photos": ["../inputs/a.jpg"],
  "text": {"title": "The Hayes Family", "subtitle": "2026 in photographs",
           "greeting": "Merry Christmas", "message": "...",
           "signature": "with love, ...", "year": "2026"},
  "design": {"system": {"palette": {"...": "#..."}}, "compositions": []},
  "export": {"format": "pdf", "dpi": 150, "png": false}
}
```

`compositions` are the slides, in order. Each is the same object as a card's
composition (`side` is ignored). A zone's `text` field carries captions and page
numbers.

## A composition

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
  "chrome": {"border": "none"}
}
```

## A zone

```json
{"word": "family", "x": 0.075, "y": 0.737, "w": 0.72, "h": 0.05,
 "size": 0.030, "font": "lato", "weight": 400, "tracking": 0.13, "caps": true,
 "leading": 1.25, "align": "left", "over_photo": true}
```

One piece of copy per zone. `size` is a fraction of the page's short side
(0.012–0.50); `font` is one of `playfair`, `cormorant`, `montserrat`, `lato`,
`instrument`, `greatvibes`; `weight` 100–900; `tracking` −0.06–0.45 em;
`leading` 0.85–2.4. Optional: `italic`, `caps`, `color`, `panel`,
`panel_opacity`, `panel_pad`, `rotate`, `layer`, `over_photo`, `text`, `valign`.

`word` is one of `type.parts` in `rules.json` (`greeting`, `family`, `message`,
`signature`, `year`, `caption`, `monogram`, `title`, `subtitle`, `eyebrow`,
`statement`, `numeral`, `folio`), or any label when the zone carries `text`.

All limits are in `studio/RULES.md`; the numbers are in `studio/rules.json`.
`./ccb brief` prints the ones that matter for the page.

## Commands

| command | does |
| --- | --- |
| `./ccb doctor` | what is installed, fonts, face engine, rulebook version |
| `./ccb samples` | six generated demo photographs in `inputs/` |
| `./ccb new` / `add` | copy photographs, write card.json (no design) |
| `./ccb brief` | write and print the brief |
| `./ccb layout --file x.json` | validate and install a palette and compositions (`--select`, `--append`) |
| `./ccb text` | change the words |
| `./ccb check` | gate every composition + measured type |
| `./ccb see` | annotated previews, photo sheet, visual report |
| `./ccb sheet` | contact sheet of every saved composition |
| `./ccb render` | PDF/PNG/JPEG at true size |
| `./ccb qa` | read the PDF back, verify pages, size and DPI |
| `./ccb palette` | the card's colours, the colours in its photographs, the typefaces |
| `./ccb faces` | install YuNet; scan photographs |
| `./ccb fonts` | download the six OFL typefaces |
| `./ccb status` | cards and decks, and whether they are composed |
| `./ccb sizes` | paper sizes and bleed |
| `./ccb selftest` | end-to-end check with generated photographs |
| `./ccb deck new/brief/layout/text/check/see/sheet/render/qa` | the same for slides |

## The gate

`layout` validates before saving; `check` validates every saved composition and
then renders the selected front at 110 DPI to measure real type. Publish only
after `check` shows 0 errors and `qa` says PASS.

Errors: off-page rectangles, text on a photograph without `over_photo`,
overlapping zones, overlapping slots on the same layer, unknown
backgrounds/shapes/words/treatments/clips/fonts/alignments, missing or
out-of-range type size/weight/tracking/leading, unusable palette colours, coverage
above the maximum, unknown ornament kinds or tokens, rules too heavy. Warnings:
coverage below the minimum, small slots or zones, text outside the safe margin,
faces cut or printed too small, type below the floor, low contrast, shortened or
shrunk copy, soft photographs, repeated skeletons (`composition.repeat`) and
pages that are only a photograph and a stack of text (`composition.plain`).

## Seeing

`see` writes:

- `front.png` — the rendered front with the safe margin, every slot (green),
  every zone (blue) and every face box (red);
- `photos.jpg` — every photograph, numbered, with face boxes;
- `visual.md` / `visual.json` — the same positions, sizes, face scores and
  warnings in words.

A vision-capable model opens the images. A text-only model reads `visual.md` and
says it cannot see the picture. Neither may invent what is in a photograph.
