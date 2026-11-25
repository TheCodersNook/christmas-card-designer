# What to type in OpenCode

## 1. Open the project

Terminal:

```bash
cd path/to/christmas-card-studio
opencode
```

OpenCode desktop app: open the christmas-card-studio folder as the project.

Pick a cloud-hosted model with `/models`; the free hosted ones need no login.
This project does not use a local model: the layout engine is deterministic
Python, and no image leaves the computer.

## 2. Give it your photographs

Either put them in `inputs/` (drag them into the folder), or drag them straight
into the OpenCode chat, type `@` and pick them, or paste their paths. It copies
them into `inputs/` itself; your originals are never touched. OpenCode may ask
once for permission to read a folder outside the project (Downloads, Photos):
allow it.

## 3. Type one line

```text
/card inputs/family_tree.jpg inputs/couple_snow.jpg inputs/cabin.jpg
```

With the words in the same line:

```text
/card inputs/*.jpg --family "The Hayes Family" --greeting "Merry Christmas" --size 5x7
```

Instead of listing files you can drag them in right after `/card `.

If the slash commands do not show up, paste this instead:

```text
Make our Christmas card from these photographs: <list or paths>.
Load the christmas-card skill (.opencode/skills/christmas-card/SKILL.md), read
AGENTS.md, and follow "The workflow" steps 0 to 7 exactly. Use only ./ccb
commands. Get the words right, never invent them, keep our photographs untouched,
and stop at the gate if it has errors. When done, tell me the file path, the
physical size and DPI, and what is still open.
```

## 4. Look at it, then give feedback

The contact sheet with all six designs is at
`cards/<name>/out/designs.jpg`; the card itself is `cards/<name>/out/<name>.pdf`.
Print it, or send it to a printer, at 100% - never "fit to page".

```text
/fix use design 2, make the message shorter, and try the midnight palette
```

```text
/fix the 2024 photograph is blurry - use the cabin one instead
```

`/status` lists every card, its design and its files.
