---
description: Make a 16:9 Christmas presentation from photographs, designed against the rulebook
---

Make a 16:9 presentation from the photographs in this message (or `inputs/`).

1. `./ccb deck new <each path> --name <family-year> --direction <editorial|...>`
   with `--title`, `--subtitle`, `--greeting`, `--message`, `--signature`,
   `--year`. Use their exact wording.
2. `./ccb deck brief decks/<name>` and read it, plus `studio/RULES.md`.
3. `./ccb deck see decks/<name>`; open `out/see/photos.jpg` if your model can
   read images, otherwise read `visual.md` and say so.
4. Write `slides.json`: `{"slides": [ ... ]}`. Every slide is a composition you
   write from scratch — there are no slide kinds and the engine adds nothing you
   did not declare. No two slides should share a skeleton: vary the background
   (including a full-bleed photograph behind a scrim), the column, the crop
   shape, the scale of the type. A good rhythm is cover, one photograph per
   slide, a statement, a gallery for the rest, a closing, with every photograph
   used once and no more than six in a gallery. Captions and page numbers go in
   a zone's `text` field.
5. `./ccb deck layout decks/<name> --file slides.json`. Fix every error and
   retry; read the warnings.
6. `./ccb deck check decks/<name>` until 0 errors.
7. `./ccb deck see decks/<name>` and look at the annotated slides. If you cannot
   see them, say so.
8. `./ccb deck render decks/<name> --png`, then `./ccb deck qa decks/<name>`
   (must PASS).
9. Report the PDF path, the slide count, the size (13.333 x 7.5 in), the DPI and
   the QA result. It is a PDF + PNGs, never a `.pptx`.

Never modify their photographs. Never claim to have looked at an image you did
not open.
