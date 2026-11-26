---
description: Make a print-ready Christmas card from photographs, designed from scratch against the playbook
---

Make a Christmas card from the photographs in this message (or `inputs/`).

1. `./ccb new <each path> --name <family-year>` with their words (`--greeting`,
   `--family`, `--message`, `--signature`, `--year`, `--size`, `--landscape`).
   Use their exact wording and spelling.
2. `./ccb brief cards/<name>` and read all of it. `studio/RULES.md` is the
   playbook; the brief prints the numbers, the photographs' own colours and the
   faces that apply to this page.
3. `./ccb see cards/<name>`; open `out/see/photos.jpg` if your model can read
   images, otherwise read `out/see/visual.md` and say so. Note the face
   positions and which photographs are strong.
4. Choose the system. Write a six-colour `system.palette` (`bg`, `ink`, `soft`,
   `accent`, `panel`, `on_panel`, all `#hex`) that belongs to these photographs;
   the brief sampled their colours for you. Then decide the hierarchy and the
   typefaces.
5. Write `design.json` with **two or three fronts and one back**. Every zone
   carries one word plus its own `size`, `font`, `weight`, `tracking` and
   `leading`; there is no scale to fall back on. Each front is a page composed
   from scratch — a background, shapes, slots, zones, lines — and a different
   idea, not the same page with new words. Nothing is drawn for you: if you want
   a border, a decoration or paper grain, put it in `chrome`.
6. `./ccb layout cards/<name> --file design.json`. Every error names a rule:
   fix the composition and retry until it saves. Read the warnings, especially
   `composition.repeat`, `composition.plain` and any copy that had to shrink.
7. `./ccb check cards/<name>` until 0 errors. Address every warning or explain
   it (a text-only back with 0% photo coverage is fine; a face keeping 40% is
   not).
8. `./ccb see cards/<name>` and look at `out/see/front.png` (slots green, zones
   blue, faces red). If you cannot see it, say so.
9. `./ccb render cards/<name>` then `./ccb qa cards/<name>` (must PASS).
10. Give them `out/designs.jpg` to choose from (`./ccb layout ... --select N` for
    a different front), the PDF path, the size, the DPI, the palette and the QA
    result.

Never modify their photographs. Never claim to have looked at an image you did
not open. Never invent a name, a year or a greeting.

A presentation is `/presentation`; later changes are `/fix`.
