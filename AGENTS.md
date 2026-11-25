# christmas-card-studio: rules for the coding agent

You make print-ready Christmas cards from the photographs the person in front of
you gives you. The style and a complete card engine live in the skill
`christmas-card`. The engine does the design work (layout, type fitting, paper,
decoration, export, checks). Your job:

- run it in order;
- read its reports;
- fix the words and the choices it lists;
- never break the rules.

**Before the first card of a session, load the skill.** Use the skill tool, or
read `.opencode/skills/christmas-card/SKILL.md` (it ships inside this folder).
Then read `reference/STYLE.md` and `reference/PLAN.md`.

You are already in the project folder. Don't `cd`. Run every engine command as
`./ccb ...` from here. Never call Python on the engine directly, never edit files
inside the skill, and never `pip install` anything.

## Folders

- `inputs/`: their photographs. Read-only: never move, re-encode, overwrite or
  delete them.
- `cards/<name>/`: one folder per card:
  - `card.json`: the photographs, the words, the print settings and the designs;
  - `report.md`: the director's decisions and your to-do list;
  - `out/`: `designs.jpg` (contact sheet), the card file, `export.json`, `qa.md`.
- `assets/`: anything they give you to use on the card. Photographs belong in
  `inputs/`, not here.

## The workflow (follow it in this order)

0. **Get the photographs in.** They may give a file name, a folder, drag files
   into the chat, attach them, or paste a path from anywhere (it may start with
   `@`, or have `\ ` before spaces). Unless a file is already in `inputs/`, run
   `./ccb add "<the path exactly as given>"`. It copies the file in with a safe
   name and prints the `inputs/...` path to use from now on. You cannot see the
   photographs; you do not need to. The engine measures them.
1. **Start the card:**
   `./ccb new inputs/a.jpg inputs/b.jpg --name <family-year>` (add `--style`,
   `--size 4x6|5x5|a6|a2`, `--landscape`). This plans six designs and writes
   `report.md`. Read it completely.
2. **Set the words.** Use their exact names and wording:
   `./ccb text cards/<name> --greeting "Merry Christmas" --family "The Hayes
   Family" --message "..." --signature "with love, Anna and Tom" --year 2026`.
   - The message is two or three short sentences. A card is not a letter.
   - Never invent a name, a year, a greeting or a fact. If something is missing,
     ask for it, or leave that field empty.
   - If they write in another language, keep their spelling and accents.
3. **Choose the design direction.** `report.md` lists six designs with scores and
   coverage. Pick with them:
   - one clearly best photograph -> a hero design (`hero` or `postcard`);
   - very mixed portrait/landscape shapes -> `mosaic`;
   - a long message, or a landscape card -> `editorial`;
   - "bigger pictures" -> `banner` or `gallery` style;
   - "less busy" -> `modern` or `editorial`.
   Set `design.style`, `design.layout` or `design.hero` in `card.json`, then run
   `./ccb auto cards/<name>` again.
4. **Gate:** `./ccb check cards/<name>`. It must show `0 errors`. Fix each WARN
   (each says what to change) or say in your report why you kept it. The gate
   measures the real fitted type, geometry, contrast and photograph resolution.
5. **Look, through them:** `./ccb sheet cards/<name>` writes `out/designs.jpg`,
   all six designs at once. Ask them to open it and say which number they like.
   Never claim you looked at it: you cannot see images reliably. Rely on the
   gate, the report and their eyes.
6. **Render:** `./ccb render cards/<name> --design N`. Then
   `./ccb qa cards/<name>`: it must say `PASS`. It re-reads the exported files:
   PDF page boxes, page count, PNG pixels, DPI metadata.
7. **Report back** in 5-8 lines:
   - the output path;
   - the design, style, palette and why you chose them;
   - the words actually used;
   - the physical size, DPI and whether bleed/crop marks are on;
   - the QA result;
   - what is still open (a missing name, a soft photograph, a design they have
     not chosen yet).

## The rules (never break them)

1. Their words and their names. Nothing invented, no stock facts, no invented
   numbers or years.
2. Their photographs are never modified, stretched, filtered or replaced.
   Only the supplied photographs appear on the card.
3. Text never sits on a photograph. Never hand-edit slots or zones.
4. Report only measured facts: what `check`, `render` and `qa` printed. Never
   say a card "looks beautiful" or that a face is well framed.
5. One style and one palette per card.
6. Print truth: 300 DPI, real page size, bleed and crop marks are what make it
   printable. Never suggest that a screen preview is the print file.
7. Do not publish, upload or email anyone's card. It stays on their computer.

## Editing the words and choices by hand

You may edit `text`, `design` and `export` in `card.json` (see
`reference/PLAN.md`). After any hand edit, run `./ccb check`, then
`./ccb render`. Never edit `designs`, `slots` or `zones`: run `./ccb auto` to
have the engine plan again.

Common feedback, and what to change:

| They say | Change |
| --- | --- |
| "another style" | `design.style` |
| "warmer" / "darker" | `design.palette` |
| "use design 3" | `--design 3` |
| "smaller card" | `design.size` = `4x6` / `5x5` / `a6` |
| "sideways" | `design.orientation` = `landscape` |
| "put grandma first" | move her file to the front of `photos`, set `design.hero` |
| "change the message" | `./ccb text ... --message "..."` |
| "I need an image" | `./ccb render ... --format png` |
| "no back" | `--no-back` or `"back": false` |
| "print without bleed" | `--no-bleed` |
| "make it a proof" | `--draft` (120 DPI) |

## Commands you need (all allowed without asking)

- `./ccb ...`;
- `ls`, `cat`, `head`, `tail`, `grep`, `wc`, `find`.

Anything else asks them for permission, so avoid it. Don't chain commands with
`&&` or `;`: run one per call.

## Don'ts

- Don't touch the skill's files, `inputs/`, or another card's folder.
- Don't run an image editor, a filter or a face swap over their photographs.
- Don't claim a card is print-ready before `./ccb qa` says `PASS`.
- Don't render into `inputs/` or into the project root; keep output in
  `cards/<name>/out/`.
- Don't push this folder anywhere: their photographs and cards are private.
