---
description: Change an existing Christmas card (style, design, words, format)
---

Change the card according to the note that follows this command.

Rules:

- Change choices in `cards/<name>/card.json` (`text`, `design`, `export`) or use
  `./ccb text`. Never hand-edit `designs`, `slots` or `zones`: run `./ccb auto`.
- Then run `./ccb check cards/<name>` (must show 0 errors) and
  `./ccb render cards/<name>`, followed by `./ccb qa cards/<name>` (must PASS).
- If the note is about photographs ("use the cabin one", "put grandma first"),
  change the `photos` list order or `design.hero`, never the image files.
- If the note is a lasting preference ("always leave the year off"), add it to
  `.opencode/skills/christmas-card/reference/STYLE.md` under "House notes" with
  today's date.
- Report what changed and what is still open in 3-6 lines.
