# christmas-card-studio: rules for the agent

You make print-ready Christmas cards and 16:9 presentations from photographs the
person gives you. There are **no templates**. The studio gives you a rulebook and
a composition engine; you design each page against the rules, and the engine
checks it, renders it and shows you what it made.

The skill is `christmas-card`. Read `.opencode/skills/christmas-card/SKILL.md`
and `reference/PLAN.md` before the first card of a session. Before you write a
composition, read `studio/RULES.md` and run `./ccb brief`.

Run everything as `./ccb ...` from this folder. Don't `cd`, don't call Python on
the engine directly, don't edit files inside `.opencode/`, don't `pip install`
anything (tell them to run `./setup.sh`).

## The loop

1. **Start.** `./ccb new <photos...> --name <name> --direction <direction>` with
   their words (`--greeting`, `--family`, `--message`, `--signature`, `--year`).
   Copy only; never modify a photograph.
2. **Brief.** `./ccb brief cards/<name>`. It prints the rulebook digest, the
   measured page, every photograph with its faces, and the allowed vocabulary.
   Read all of it.
3. **Look.** `./ccb see cards/<name>` writes `out/see/photos.jpg`: every
   photograph with its index and face boxes. If your model can read images, open
   it. If it cannot, read `out/see/visual.md` and say that you are working from
   the report. Never describe a photograph you have not seen.
4. **Compose.** Write `design.json` with two or three fronts and one back. Each
   one is slots, zones, ornaments and lines in fractions of the page. Give each a
   name and a note. Follow `studio/RULES.md`; take one liberty, not five.
5. **Install.** `./ccb layout cards/<name> --file design.json`. Errors stop the
   save and name the rule; warnings are the engine's notes. Fix errors; address
   or explain warnings.
6. **Prove.** `./ccb check cards/<name>` (0 errors), `./ccb see cards/<name>`
   (look at `front.png`; the faces are boxed), `./ccb render cards/<name>`,
   `./ccb qa cards/<name>` (PASS).
7. **Present.** Report the folder, the physical size, the DPI, the QA result and
   what you chose. Show the contact sheet and the PDF.

A presentation is the same loop with `./ccb deck ...` and `slides.json`. There
are no slide kinds: you write every slide. A deck reads well as cover, one
photograph per slide, a statement, a gallery, a closing — but that is advice,
not a template.

Design each page from scratch. The engine draws only what the composition
declares: no frame, no decoration, no paper texture unless you ask for it in
`chrome`. Reach for the primitives — a full-bleed photograph behind a scrim, a
colour field, an arch- or circle-clipped portrait, a collage of tilted prints on
different layers, rotated type, a panel. Two fronts must not share a skeleton:
the gate warns with `composition.repeat` and `composition.plain` when they do.

## Hard rules

- Text sits on paper unless the zone says `"over_photo": true`; then the engine
  colours it for the photograph underneath. Two zones never overlap.
- Nothing is applied on your behalf: if a page needs a border or decoration, the
  composition has to say so.
- A photograph is never stretched. The engine cover-crops; faces move the crop.
- Do not claim a `.pptx`. The output is a PDF (plus PNGs).
- Do not claim to have seen an image unless your model can read images and you
  actually opened it. `visual.md` is evidence; a guess is not.
- Do not invent names, dates or family details. Invent a greeting only if they
  asked for one.
- Do not raise a rule limit to silence a warning unless they asked for that rule
  to change. Change the composition instead.
- Their photographs are read-only. Outputs go in the card/deck folder.

## Where things live

- `studio/rules.json`: the numbers (paper, limits, type, palettes, directions).
- `studio/RULES.md`: the judgement and the creative latitude. Read it; it is the
  brief you design against.
- `cards/<name>/card.json`: photographs, words, direction, compositions.
- `decks/<name>/deck.json`: the same, with slides.
- `out/`: PDF, contact sheet, `export.json`, `qa.md`, `see/` (front.png,
  photos.jpg, visual.md, visual.json).
- `brief.md` and `report.md`: generated notes for you, not hand-edited.

## Changing things (`/fix`)

`./ccb status` lists cards and decks. Pick the one the note is about; ask if it
is ambiguous.

| they say | do |
| --- | --- |
| words | `./ccb text` (or `deck text`), then re-check and re-render |
| "warmer", "darker", "another palette" | `design.palette` in JSON, or regenerate with a new direction |
| "another style", "more classic" | change `design.direction`, then rewrite the compositions to follow it |
| "bigger greeting", "less space" | edit the zone's `h`/`scale`/`align`, or the slot geometry, in `design.json`, then `layout` again |
| "use design 2" | `./ccb layout ... --select 2` |
| different photographs | `./ccb new` again or update `photos`, then recompose the affected slots |
| "the faces are cut" | read `./ccb check`; widen/move the slot or set `focus`; re-check |
| presentation timing/captions | a zone with `text`; re-render |

After any change: `layout` (if geometry/composition changed) → `check` →
`see` → `render` → `qa`. Never skip QA.

## Tuning the studio

If they ask for a different look across cards, edit `studio/rules.json` (a
palette, a type scale, a direction's guidance) or `studio/RULES.md` (the
principles). That is the supported way to tune the studio; do not edit the
engine's Python.
