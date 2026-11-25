---
description: List every card and presentation, whether it is composed, and the next step
---

Run `./ccb status` and report per card and per deck: the name, the number of
photographs, the direction and palette, the page size, how many compositions or
slides exist, and whether `out/` already holds a PDF, a contact sheet and QA.

Then give each one the single next step: write the brief, compose it, fix the
gate errors, look at `out/see/front.png`, render, or QA. If a card has more than
one front, say how many and that `--select` chooses one.

If a face model is missing (`./ccb doctor`), say that `./ccb faces` installs it
and that crops are centred until then. Do not change any files.
