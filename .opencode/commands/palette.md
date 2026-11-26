---
description: Show a card's colours, the colours in its photographs and the installed typefaces
---

Run `./ccb palette` (or `./ccb palette cards/<name>`, and `./ccb sizes`), then
summarise briefly:

- the six current colours and where they came from (written by the agent, or
  sampled from photograph 0 because no palette was set);
- the photographs' most common colours, with the hex values, as evidence for a
  better palette;
- the six installed typefaces and the type limits from `studio/rules.json`
  (sizes, weights, tracking, leading);
- the paper sizes, the bleed and the DPI range;
- the face rules and the type floor, in one line each.

Then say plainly that none of this is a preset: the palette and the typography
are written per card by the agent, and the person can tune the limits in
`studio/rules.json` or the principles in `studio/RULES.md`. If the palette is
still sampled, offer to write a deliberate one from the photographs' colours and
the mood they want. Do not change files unless they ask.
