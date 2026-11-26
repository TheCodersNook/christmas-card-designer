---
description: Change an existing card or presentation (words, palette, type, crops, composition)
---

Change whatever the note that follows this command is about.

1. `./ccb status`. It lists cards and decks and whether they are composed. Pick
   the one the note names; if only one exists, use it; if it is ambiguous, ask.
2. Read `studio/RULES.md`, run `./ccb brief` (or `deck brief`) and look at
   `out/see/front.png` / `photos.jpg` (or `visual.md` if you cannot see images).
3. Edit the composition, not the output. `design.compositions` and
   `design.system` in `card.json` / `deck.json` are what you rewrite;
   `./ccb layout --file design.json` validates and saves. Never hand-edit `out/`.
4. Never raise a rule limit to silence a warning unless they asked for that rule
   to change; change the composition or explain the trade-off.

What the note usually means:

| They say | Do |
| --- | --- |
| words, spelling, a name | `./ccb text` (or `deck text`), then re-check |
| "warmer", "darker", another palette | rewrite `system.palette` in the layout file (or `design.system`), then re-render |
| "more elegant", "bigger type", another face | change the zones' `font`, `weight`, `size`, `tracking`; re-check |
| "bigger greeting", "less air" | change that zone's `size`, `h`, `align`; or the slot geometry |
| "use design 2" | `./ccb layout cards/<name> --file ... --select 2` |
| "the faces are cut" | read `check`; widen/move the slot or set `focus`; re-check |
| "drop the blurry photo" | remove its slot(s); keep every photograph used once |
| "another slide order" | reorder `design.compositions` and `layout` again |
| captions / page numbers | a zone with `text` (card or slide) |
| PNG instead of PDF, more/less DPI | `./ccb render --format png` / `--dpi` |

Then: `layout` if geometry, palette or typography changed → `check` (0 errors) →
`see` (look at the result; faces boxed) → `render` → `qa` (must PASS).

Report what changed, the QA result and anything still open. Never say you saw an
image you did not open, and never call the PDF a PowerPoint.
