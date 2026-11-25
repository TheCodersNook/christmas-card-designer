---
description: Change an existing card or presentation (words, direction, crops, type, composition)
---

Change whatever the note that follows this command is about.

1. `./ccb status`. It lists cards and decks and whether they are composed. Pick
   the one the note names; if only one exists, use it; if it is ambiguous, ask.
2. Read `studio/RULES.md`, run `./ccb brief` (or `deck brief`) and look at
   `out/see/front.png` / `photos.jpg` (or `visual.md` if you cannot see images).
3. Edit the composition, not the output. `design.compositions` in `card.json` /
   `deck.json` is what you rewrite; `./ccb layout --file design.json` validates
   and saves. Never hand-edit `out/`.
4. Never raise a rule limit to silence a warning unless they asked for that rule
   to change; change the composition or explain the trade-off.

What the note usually means:

| They say | Do |
| --- | --- |
| words, spelling, a name | `./ccb text` (or `deck text`), then re-check |
| "warmer", "darker", a palette | `design.palette`, then re-render |
| "more classic", "modern", another look | change `design.direction`, then adjust the zones/slots to follow its guidance |
| "bigger greeting", "less air" | change that zone's `h`, `scale`, `align`; or the slot geometry |
| "use design 2" | `./ccb layout cards/<name> --file ... --select 2` |
| "the faces are cut" | read `check`; widen/move the slot or set `focus`; re-check |
| "drop the blurry photo" | remove its slot(s); keep every photograph used once |
| "another slide order" | reorder `design.compositions` and `layout` again |
| captions / page numbers | a zone with `text` (card or slide) |
| PNG instead of PDF, more/less DPI | `./ccb render --format png` / `--dpi` |

Then: `layout` if geometry or composition changed → `check` (0 errors) →
`see` (look at the result; faces boxed) → `render` → `qa` (must PASS).

Report what changed, the QA result and anything still open. Never say you saw an
image you did not open, and never call the PDF a PowerPoint.
