---
description: Make a print-ready Christmas card from photographs, designed against the rulebook
---

Make a Christmas card from the photographs in this message (or `inputs/`).

1. `./ccb new <each path> --name <family-year> --direction <classic|editorial|...>`
   with their words (`--greeting`, `--family`, `--message`, `--signature`,
   `--year`, `--size`, `--landscape`). Use their exact wording and spelling.
2. `./ccb brief cards/<name>` and read all of it. `studio/RULES.md` is the
   design brief; the brief prints the numbers that apply to this page.
3. `./ccb see cards/<name>`; open `out/see/photos.jpg` if your model can read
   images, otherwise read `out/see/visual.md` and say so. Note the face
   positions and which photographs are strong.
4. Write `design.json` with **two or three fronts and one back**. Each is a
   composition: slots, zones, ornaments, lines. Name each one and add notes.
   Follow a direction for coherence, then take one deliberate liberty.
5. `./ccb layout cards/<name> --file design.json`. Every error names a rule:
   fix the composition and retry until it saves. Read the warnings.
6. `./ccb check cards/<name>` until 0 errors. Address every warning or explain
   it (a text-only back with 0% photo coverage is fine; a face keeping 40% is
   not).
7. `./ccb see cards/<name>` and look at `out/see/front.png` (slots green, zones
   blue, faces red). If you cannot see it, say so.
8. `./ccb render cards/<name>` then `./ccb qa cards/<name>` (must PASS).
9. Give them `out/designs.jpg` to choose from (`./ccb layout ... --select N` for
   a different front), the PDF path, the size, the DPI and the QA result.

Never modify their photographs. Never claim to have looked at an image you did
not open. Never invent a name, a year or a greeting.

A presentation is `/presentation`; later changes are `/fix`.
