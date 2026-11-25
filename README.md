# Christmas Card Studio

Your photographs, your words, a card you can actually print.

An [OpenCode](https://opencode.ai) project that turns your family photographs into
print-ready Christmas cards: six designs composed for you, eight styles, five trim
sizes, and a true-size 300 DPI PDF with bleed and crop marks. Everything runs on
your own computer. No account, no upload, no cloud service, no image ever leaves
the machine.

The design judgement lives in a small deterministic engine (Python, Pillow,
ReportLab), not in the model. That means a free OpenCode model is enough: it runs
the steps, gets the names right, and takes your feedback. It also means the same
photographs and settings always produce the same card, and a card renders in
seconds.

```
$ ./ccb make inputs/*.jpg --name hayes-2026 \
      --greeting "Merry Christmas" --family "The Hayes Family" \
      --message "Wishing you a quiet, bright Christmas." \
      --signature "with love, Anna and Tom" --year 2026

  1* Panorama banner          banner     score  86.3  cover  50%
  2  Uniform grid - 6 up      grid       score  80.5  cover  42%
  ...
gate: 0 errors
contact sheet: cards/hayes-2026/out/designs.jpg
exported hayes-2026:
  out/hayes-2026.pdf, 2 pages at 5.25 x 7.25 in, 1928 KB
qa: PASS
```

## Three commands to a card

**macOS / Linux**

```bash
git clone https://github.com/TheCodersNook/christmas-card-designer.git
cd christmas-card-designer
./setup.sh                       # Python packages + the fonts (about 6 MB)
./ccb samples                    # six demo illustrations, so you can try it now
./ccb make inputs/*.jpg --name demo --family "The Hayes Family"
```

**Windows** - use WSL (Ubuntu). In PowerShell: `wsl --install`, restart, open
Ubuntu, then:

```bash
sudo apt update && sudo apt install -y python3 python3-venv
cd ~/christmas-card-designer   &&   ./setup.sh
```

Your Windows files appear under `/mnt/c/Users/<you>/...`, so a folder of
photographs in Downloads is `/mnt/c/Users/<you>/Downloads/christmas`.

Then open the project in OpenCode and type one line:

```text
/card inputs/*.jpg --family "The Hayes Family" --greeting "Merry Christmas"
```

Prefer to work by hand? The engine is a normal command line; `PROMPT.md` has the
full prompt, `AGENTS.md` the workflow the agent follows.

## What it makes

- **Six designs per card**, from six different layout engines, ranked by
  photograph coverage, crop loss, visual balance and text room. You pick one.
- **A front and a back.** The reverse carries a monogram, the family name, a
  three-photograph strip, the message, the signature and the year. Anything empty
  simply collapses.
- **Decoration drawn as vectors** at print resolution: snow, stars, holly,
  confetti, rules and frames. It keeps out of the photographs and the words.
- **Measured typography.** The largest size that fits the reserved zone, wrapped
  word by word, never breaking a name in half, never overlapping a photograph.
- **Print output:** PDF at the exact page size, 300 DPI, optional 0.125 in bleed
  with vector crop marks. PNG and JPEG at the same physical size when you want an
  image instead.

## The six layout engines

| Engine | What it does |
| --- | --- |
| **Uniform grid** | Photographs in an even grid, text above and below. Reflows the column count for the card's shape. |
| **Hero and strip** | One photograph given real space, the rest as a strip beneath it. |
| **Proportional mosaic** | A recursive split whose cells follow the photographs' own portrait and landscape shapes. |
| **Editorial column** | A text column beside a photographic plate; the most magazine-like. |
| **Postcard stack** | A large hero, a photo strip and a roomy message block on the front. |
| **Panorama banner** | An edge-to-edge band of photographs, closed by the printed border. |

All six are deterministic: no random layouts, no model deciding where a
photograph goes. The planner scores every candidate, throws away designs that
cannot place every photograph, and keeps the strongest spread.

## The eight styles

| Style | Look |
| --- | --- |
| **Classic Christmas** | Cream stock, deep green, holly in the corners, a double rule. |
| **Modern Minimalist** | Lots of air, left-aligned caps, a few small stars. |
| **Traditional Holiday** | Cranberry paper, capitals, snow falling behind a framed grid. |
| **Luxury Editorial** | Wide margins, brass hairlines, photographs as plates. |
| **Scandinavian** | Pale grey-green, small photographs, quiet stars. |
| **Vintage Christmas** | Warm paper, postcard frame, tilted photographs, holly. |
| **Playful Festive** | Bright red, a script greeting, confetti and shadowed snapshots. |
| **Photo-First** | Nearly all photographs, a thin rule, one small line of type. |

Six palettes - evergreen, cranberry, midnight, nordic, brass, peppermint - and
five trim sizes: 5 x 7, 4 x 6, 5 x 5, A6 and A2, portrait or landscape.

## Paper and print

| Output | Details |
| --- | --- |
| PDF | Exact trim size plus optional 0.125 in bleed, one page per side, vector crop marks outside the trim. |
| PNG | Lossless RGB at the chosen DPI, DPI metadata, optional bleed. |
| JPEG | Quality 95, 4:4:4 subsampling, DPI metadata, optional bleed. |

300 DPI by default (96-1200 allowed). A 5 x 7 card with bleed is 1575 x 2175 px
at 300 DPI. Photographs are always cover-cropped, never stretched. Type is
rasterised into the artwork, so the PDF cannot substitute a missing font and what
you see is what prints. The PDF is RGB; for a press that demands CMYK, convert it
in the printer's RIP.

`./ccb qa` reads the exported files back - real PDF page boxes, page count, PNG
pixel dimensions and DPI metadata - instead of trusting the render. `./ccb check`
gates every design first: no text over a photograph, no photograph used far above
its own resolution, measured contrast on every text block.

## In OpenCode

1. Put your photographs in `inputs/`, or drag them into the chat.
2. In this folder run `opencode`, then pick a free model with `/models`.
3. Type `/card inputs/*.jpg --family "The Hayes Family"`. Add the words you want.
4. Look at `cards/<name>/out/designs.jpg` and choose a number.
5. `/fix use design 2, shorter message, midnight palette` - or just do it yourself.

`/status` lists every card and its files, `/styles` shows the looks and papers.

## Commands

| Command | What it does |
| --- | --- |
| `./ccb doctor` | Python, packages, fonts, how many cards exist |
| `./ccb fonts` | download the OFL fonts into `assets/fonts/` |
| `./ccb samples` | draw six demo illustrations into `inputs/` |
| `./ccb add <photo>...` | copy photographs into `inputs/` with safe names |
| `./ccb new <photo>... --name x` | start a card and plan its designs |
| `./ccb auto [card]` | re-plan the designs, rewrite `report.md` |
| `./ccb text [card] --family "..."` | change the words only |
| `./ccb check [card]` | the gate: geometry, type, contrast, resolution |
| `./ccb sheet [card]` | contact sheet of all six designs |
| `./ccb render [card] --design N` | write the print files and verify them |
| `./ccb qa [card]` | verify the exported files, write `out/qa.md` |
| `./ccb make <photo>...` | plan, gate, sheet, export and QA in one go |
| `./ccb status` / `styles` / `sizes` | what exists and what it can print |
| `./ccb selftest` | end-to-end test with generated photographs |

## What is in here

```
christmas-card-designer/
├── AGENTS.md                    the workflow the AI follows
├── PROMPT.md                    what to type in OpenCode
├── setup.sh                     one-time setup (packages + fonts)
├── ccb                          runs the engine
├── opencode.json                what the agent may run without asking
├── inputs/                      your photographs (never modified, never committed)
├── cards/<name>/                one card: card.json, report.md, out/
└── .opencode/
    ├── commands/                /card, /fix, /status, /styles
    └── skills/christmas-card/
        ├── SKILL.md             the studio's taste and rules
        ├── reference/           STYLE.md, PLAN.md (schema + every command)
        └── scripts/ccstudio/    the engine: layouts, type, decoration, export
```

`card.json` is the only file you edit: photographs, words, style, paper, export
settings. The engine writes the designs, the report, the contact sheet and the
print files.

## Honest limits

- **No face detection in this engine.** Crops are centred with a slight upward
  bias, and the "hero" photograph is chosen from resolution, detail and contrast.
  Check the contact sheet: if a crop cuts someone's head, choose another design or
  reorder the photographs.
- **A small photograph stays small.** The gate warns when a picture is being used
  far above its own resolution; it cannot invent detail.
- **2 to 20 photographs.** One is a portrait, fifty is a contact sheet; the
  layouts are built for family-card numbers.
- **No CMYK.** The PDF is RGB at the right physical size.
- **The fonts are downloaded, not stored here** (SIL Open Font License, about
  6 MB). `./ccb fonts` fetches them once; until then a system font is used.
- **The demo photographs are flat illustrations** drawn by `./ccb samples`, so
  the project ships without stock pictures or strangers' faces.
- **You cannot see the card through the agent.** It reports what the gate
  measured; looking at `out/designs.jpg` and the PDF is your job - and the reason
  the contact sheet exists.

## Credits

Typefaces (Playfair Display, Cormorant Garamond, Montserrat, Lato, Great Vibes,
Instrument Serif) are under the SIL Open Font License 1.1 and come from
[Google Fonts](https://github.com/google/fonts). Pillow, NumPy and ReportLab are
used under their BSD-style licences. See `NOTICE.md`.

Built to be read, changed and printed. Use it for your own cards.
