---
description: Change an existing card or presentation (words, style, photographs, format)
---

Fix whatever the note that follows this command is about. The project can hold
cards (`cards/<name>/`) and presentations (`decks/<name>/`), and a note may be
about either.

1. Run `./ccb status`. It lists every card and every presentation with the files
   already written. If the note names one, use that one; if only one exists, use
   it; if both exist and the note is ambiguous, ask which.
2. **A card** is changed through `cards/<name>/card.json` (`text`, `design`,
   `export`) or `./ccb text`. Never hand-edit `designs`, `slots` or `zones`: run
   `./ccb auto` to plan again. Then run `./ccb check cards/<name>` (must show
   0 errors), `./ccb render cards/<name>` and `./ccb qa cards/<name>` (must PASS).
3. **A presentation** is changed through `decks/<name>/deck.json` (`text`,
   `captions`, `design`, `export`) or `./ccb deck text`. Never hand-edit the
   slide plan: run `./ccb deck plan` to plan the slides again. Then run
   `./ccb deck check decks/<name>`, `./ccb deck sheet`, `./ccb deck render` and
   `./ccb deck qa` (must PASS).
4. A note about photographs ("use the cabin one", "put grandma first", "drop the
   blurry one") changes the `photos` list order, `design.hero` (a card) or the
   `photos` list and `captions` (a presentation). Never touch the image files.
5. What the note means:

| They say | Card | Presentation |
| --- | --- | --- |
| "warmer" / "darker" | `design.palette` | `design.palette` |
| "another style" | `design.style`, then `./ccb auto` | `design.style`, then `./ccb deck plan` |
| "use design 3" | `./ccb render --design 3` | a deck has one plan: change words or photographs instead |
| "smaller card" | `design.size` (`4x6`, `5x5`, `a6`) | always 16:9; change the DPI instead |
| "sideways" | `design.orientation = landscape` | always landscape; nothing to change |
| "change the words" | `./ccb text ...` | `./ccb deck text ...` |
| "caption this one" | a card has no captions | add it under `captions` in `deck.json` |
| "no back page" | `"back": false` in `export` | a deck has no back page |
| "I need an image" | `./ccb render --format png` | `./ccb deck render --png` |
| "make it a proof" | `./ccb render --draft` | `./ccb deck render --dpi 96` |

6. If the note is a lasting preference ("always leave the year off"), add it to
   `.opencode/skills/christmas-card/reference/STYLE.md` under "House notes" with
   today's date.
7. Report what changed, the gate result, the file paths and what is still open,
   in 3-6 lines.
