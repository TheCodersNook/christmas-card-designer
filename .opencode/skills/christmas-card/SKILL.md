---
name: christmas-card
description: A rules-driven Christmas studio. It turns a family's own photographs into print-ready Christmas cards and 16:9 presentations, not from templates but from an editable rulebook (studio/rules.json + studio/RULES.md) and free compositions the agent writes. Includes measured typography, YuNet face detection with landmarks, face-aware cropping, a gate that refuses text on photographs and cut faces, annotated previews so the agent can see photographs and its own work, true-size 300 DPI PDF/PNG/JPEG with bleed and crop marks, and 16:9 PDF/PNG decks. Use it whenever someone gives photographs and asks for a Christmas card, holiday card, family card, photo card, card to print, "make our card", a matching back, a Christmas presentation, slideshow, year-in-review deck, or names this skill.
---

# christmas-card: a rules-driven card and presentation studio

The photographs are the work. Everything else — the greeting, the paper, the
margin, the rule, the holly — exists so the photographs look printed on purpose.

Two outputs share one engine and one rulebook: a **card** (small, 300 DPI, bleed
and crop marks) and a **presentation** (16:9, no bleed). Both are lists of
**compositions**: photograph slots, text zones, ornaments and rules in fractions
of the page.

**There are no templates.** The studio does not pick a design for you. It gives
you `studio/rules.json` (the numbers), `studio/RULES.md` (the judgement and the
latitude), and an engine that validates and renders what you write. The agent
designs; the gate refuses what breaks the rules.

## Read before you design

1. `studio/RULES.md` — all of it. It is short enough and it is the brief.
2. `./ccb brief <card>` — the rulebook for that page, the photographs, faces,
   words, allowed vocabulary, and the shape of the file.
3. `./ccb see <card>` and open `out/see/photos.jpg` (or read `visual.md` if your
   model cannot see images). Know where the faces are before placing a crop.

## Compose

Write two or three fronts and one back as JSON. A slot is
`{photo, x, y, w, h, treatment?, focus?}`. A zone is
`{roles, x, y, w, h, align?, valign?, font?, scale?, caps?, panel?, text?}`.
Ornaments are `{kind, density}`; rules are `{x1, y1, x2, y2, token, weight}`.

- Coordinates are fractions from the top-left of the trim page.
- Text never overlaps a photograph; the gate rejects it.
- Let the faces choose the crop (omit `focus`) unless you have a better idea.
- Follow a direction for coherence, then depart once: a zone's `scale`, `font`,
  `caps`, `align`, a panel, an ornament, a rule.
- Give every composition a name and a `notes` line.

Then `./ccb layout <card> --file design.json`. Errors mean it was not saved.
Warnings are exact numbers: a face keeping 40%, a role at 6.4 pt, a photograph
used at 2.1x its pixels. Fix the composition, not the limits.

## Prove it

`./ccb check` (0 errors) → `./ccb see` (look at `front.png`; boxes mark zones
and faces) → `./ccb render` → `./ccb qa` (PASS). For a deck:
`./ccb deck check|see|render|qa`.

Report the folder, size, DPI, QA result and the design decisions. Never say you
saw an image you did not open, and never call a PDF a PowerPoint.

## Tuning

The person can tune everything: palettes, type scales, margins, the face rules,
the eight directions' guidance, and §7 of `RULES.md` (what may be invented).
Edit those files, not the Python.
