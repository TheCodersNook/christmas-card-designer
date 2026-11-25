# Prompt for a model outside OpenCode

Paste this into any agent that can run shell commands in this folder.

---

You are working in the Christmas Card Studio. It makes print-ready Christmas
cards and 16:9 presentations from a family's own photographs.

There are **no templates**. Read `studio/RULES.md` and run `./ccb brief` before
you design. Then write compositions — photograph slots, text zones, ornaments and
rules as fractions of the page — and let the engine validate them.

Rules you must not break:

1. Run only `./ccb ...`; never call the engine's Python directly.
2. Never modify a photograph. Never invent names, dates or family details.
3. Text never overlaps a photograph; slots and zones never overlap.
4. If the gate reports an error, fix the composition. Do not raise a limit.
5. Output is a PDF (plus PNGs). Never call it a `.pptx`.
6. You may only say you saw an image if your model can read images and you
   actually opened `out/see/photos.jpg` or `out/see/front.png`. Otherwise read
   `out/see/visual.md` and say you are working from measurements.

The loop:

```
./ccb new <photos...> --name <name> --direction <direction> [words...]
./ccb brief cards/<name>
./ccb see cards/<name>              # photos.jpg, or visual.md
# write design.json: 2-3 fronts + a back
./ccb layout cards/<name> --file design.json
./ccb check cards/<name>            # must be 0 errors
./ccb see cards/<name>              # look at front.png
./ccb render cards/<name>
./ccb qa cards/<name>               # must PASS
```

For a presentation use `./ccb deck new|brief|layout|check|see|render|qa` and a
`slides.json` with `{"slides": [...]}`. Every slide is a composition; there are
no slide kinds.

When you finish, report: the folder, the physical size, the DPI, the QA result,
the compositions you chose and why, and anything still open.
