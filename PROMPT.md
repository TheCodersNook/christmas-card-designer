# Prompt for a model outside OpenCode

Paste this into any agent that can run shell commands in this folder.

---

You are working in the Christmas Cards and Presentation Maker. It makes
print-ready Christmas cards and 16:9 presentations from a family's own
photographs.

There are **no templates and no presets**: no style to pick, no palette library,
no type scale. Read `studio/RULES.md` and run `./ccb brief` before you design.
Then write a six-colour palette, set every word's size and typeface yourself, and
compose each page from primitives — a background, colour fields and shapes,
photograph slots, text zones, rules. Nothing is drawn that you did not declare:
no frame, no decoration, no texture.

Rules you must not break:

1. Run only `./ccb ...`; never call the engine's Python directly.
2. Never modify a photograph. Never invent names, dates or family details.
3. Text sits on paper unless the zone sets `over_photo`; zones never overlap.
4. Every zone sets its own `size` and `font`; the palette must be readable.
5. If the gate reports an error, fix the composition. Do not raise a limit.
6. Output is a PDF (plus PNGs). Never call it a `.pptx`.
7. You may only say you saw an image if your model can read images and you
   actually opened `out/see/photos.jpg` or `out/see/front.png`. Otherwise read
   `out/see/visual.md` and say you are working from measurements.

The loop:

```
./ccb new <photos...> --name <name> [words...]
./ccb brief cards/<name>
./ccb see cards/<name>              # photos.jpg, or visual.md
# write design.json: system.palette + 2-3 fronts + a back
./ccb layout cards/<name> --file design.json
./ccb check cards/<name>            # must be 0 errors
./ccb see cards/<name>              # look at front.png
./ccb render cards/<name>
./ccb qa cards/<name>               # must PASS
```

For a presentation use `./ccb deck new|brief|layout|check|see|render|qa` and a
`slides.json` with `{"system": {...}, "slides": [...]}`. Every slide is a
composition; there are no slide kinds.

When you finish, report: the folder, the physical size, the DPI, the QA result,
the palette and typography you chose and why, and anything still open.
