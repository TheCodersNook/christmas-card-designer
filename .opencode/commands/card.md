---
description: Make a print-ready Christmas card from photographs in this project
---

Make a Christmas card from the photographs in this message (or from `inputs/`).

Follow the workflow in AGENTS.md exactly, using only `./ccb` commands:

1. `./ccb add "<each path as given>"` for every photograph that is not already in
   `inputs/`.
2. `./ccb new inputs/<files> --name <family-year>` with any words they gave in the
   same message (`--greeting`, `--family`, `--message`, `--signature`, `--year`,
   `--style`, `--size`, `--landscape`).
3. Read `cards/<name>/report.md` completely.
4. Set the words with `./ccb text` using their exact wording and spelling. Never
   invent a name, a year or a greeting. Ask for anything missing.
5. `./ccb check cards/<name>` until it shows 0 errors. Fix each warning or
   explain why not.
6. `./ccb sheet cards/<name>` and ask them to look at `out/designs.jpg`.
7. `./ccb render cards/<name>` and `./ccb qa cards/<name>` (must say PASS).

A presentation from the same photographs is `/presentation`; later changes to
either one are `/fix`.

Never modify their photographs. Never claim you looked at the designs. Report the
output path, the physical size, the DPI, the QA result and anything still open.
