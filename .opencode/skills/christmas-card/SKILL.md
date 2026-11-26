---
name: christmas-card
description: A preset-free Christmas studio. It turns a family's own photographs into print-ready Christmas cards and 16:9 presentations by reading an editable playbook (studio/rules.json + studio/RULES.md) and writing every page from scratch — its own six-colour palette, its own typefaces, sizes, weights and tracking, its own geometry. Includes measured typography, YuNet face detection with landmarks, face-aware cropping, a gate that refuses unreadable palettes, text on photographs without consent and cut faces, annotated previews so the agent can see photographs and its own work, true-size 300 DPI PDF/PNG/JPEG with bleed and crop marks, and 16:9 PDF/PNG decks. Use it whenever someone gives photographs and asks for a Christmas card, holiday card, family card, photo card, card to print, "make our card", a matching back, a Christmas presentation, slideshow, year-in-review deck, or names this skill.
---

# christmas-card: a playbook for cards and presentations

The photographs are the work. Everything else — the palette, the type, the
margin, the rule, the holly — exists so the photographs look printed on purpose.

Two outputs share one engine and one playbook: a **card** (small, 300 DPI, bleed
and crop marks) and a **presentation** (16:9, no bleed). Both are lists of
**compositions**: photograph slots, text zones, rules and shapes in fractions of
the page.

**There are no presets.** The studio does not pick colours, typefaces, sizes or a
design for you. It gives you `studio/rules.json` (the numbers),
`studio/RULES.md` (the judgement and the latitude), and an engine that validates
and renders what you write. You design; the gate refuses what breaks the rules.

## Read before you design

1. `studio/RULES.md` — all of it. It is short enough and it is the brief.
2. `./ccb brief <card>` — the playbook for that page, the photographs, their six
   most common colours, the faces, the words, the vocabulary, and the shape of
   the file.
3. `./ccb see <card>` and open `out/see/photos.jpg` (or read `visual.md` if your
   model cannot see images). Know where the faces are before placing a crop.

## Design

**The palette.** Six `#hex` colours: `bg`, `ink`, `soft`, `accent`, `panel`,
`on_panel`. Pull them out of the photographs (the brief prints their colours) or
out of the mood you were asked for. Ink on bg and on_panel on panel must reach
4.5:1; the gate refuses 2.5:1 or worse. Leave the palette out and the engine
samples one from photograph 0 — that is a fallback, not a decision.

**The type.** Each zone sets its own `size` (a fraction of the short side:
0.088 is a big greeting on a 5x7, 0.018 a caption), `font` (`playfair`,
`cormorant`, `montserrat`, `lato`, `instrument`, `greatvibes`), `weight`,
`tracking` in em, `leading`, `caps`, `italic`, `align`, `valign`. There is no
role scale: decide the hierarchy, then the numbers.

**The page.** A background (`{photo, scrim, scrim_from, scrim_reach}` or
`{fill}` or `{gradient}`), shapes (`{kind, x, y, w, h, fill, opacity, rotate,
layer}`), slots (`{photo, x, y, w, h, treatment?, focus?, clip?, rotate?, layer?,
bleed?}`), zones (`{word, x, y, w, h, size, font, ...}`), rules and optional
`chrome`. Everything takes a `layer`.

- Coordinates are fractions from the top-left of the trim page.
- The engine adds no chrome: no border, decoration or texture unless asked.
- Text sits on paper unless the zone says `over_photo`; then it is coloured for
  the photograph underneath. Two zones never overlap.
- Make each front a different idea; the gate warns about repeated skeletons.
- Let the faces choose the crop (omit `focus`) unless you have a better idea.
- Spend boldness in one place: a full-bleed photo, a colour field, a clipped
  portrait, a collage, a rotated spine of type.
- Give every composition a name and a `notes` line.

Then `./ccb layout <card> --file design.json`. Errors mean it was not saved.
Warnings are exact numbers: a face keeping 40%, copy shrunk from 0.088 to 0.071,
a photograph used at 2.1x its pixels. Fix the composition, not the limits.

## Prove it

`./ccb check` (0 errors) → `./ccb see` (look at `front.png`; boxes mark zones
and faces) → `./ccb render` → `./ccb qa` (PASS). For a deck:
`./ccb deck check|see|render|qa`.

Report the folder, size, DPI, QA result, and the palette and typography you
chose. Never say you saw an image you did not open, and never call a PDF a
PowerPoint.

## Tuning

The person can tune the limits: type range, contrast floor, coverage, paper, the
face rules, and §7 of `RULES.md` (what may be invented). The look itself is not
in a file to edit — it is in the compositions. Edit the rules files, not the
Python.
