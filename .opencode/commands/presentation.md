---
description: Make a 16:9 Christmas presentation from photographs in this project
---

Make a Christmas presentation from the photographs in this message (or from
`inputs/`). A presentation is not a card: it is 16:9, made to be looked at on a
screen or projected, with no bleed and no crop marks.

Follow the "Presentations" workflow in AGENTS.md exactly, using only `./ccb`
commands:

1. `./ccb add "<each path as given>"` for every photograph that is not already in
   `inputs/`.
2. `./ccb deck new inputs/<files> --name <family-year>` with any words they gave
   in the same message (`--title`, `--subtitle`, `--greeting`, `--message`,
   `--signature`, `--year`, `--style`, `--palette`, `--hero`).
3. Read `decks/<name>/report.md` completely.
4. Set the words with `./ccb deck text` using their exact wording and spelling.
   Never invent a name, a year, a greeting or a caption. Ask for anything
   missing.
5. `./ccb deck check decks/<name>` until it shows 0 errors. Fix each warning or
   explain why not.
6. `./ccb deck sheet decks/<name>` and ask them to look at `out/slides.jpg`.
7. `./ccb deck render decks/<name>` and `./ccb deck qa decks/<name>` (must say
   PASS). Add `--png` when they want one image per slide for Keynote, PowerPoint
   or Google Slides.

Never modify their photographs. Never claim you looked at the slides. Report the
output path, the slide count, the page size, the DPI, the QA result and anything
still open.
