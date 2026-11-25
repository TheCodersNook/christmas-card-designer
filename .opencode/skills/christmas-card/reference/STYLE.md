# What makes a card look designed

A Christmas card is a small printed object, not a web page. These are the rules
the engine follows, and the reasons behind them. Read this before choosing a
style for someone.

## The four decisions that matter

1. **One hero.** A card with six equal photographs reads as a contact sheet. A
   card with one photograph given twice the space reads as a card. The `hero`,
   `postcard` and `banner` engines do this; choose one of them when one
   photograph is clearly the best.
2. **Air beats filling.** Photographs should cover roughly 45-60% of the card;
   the rest is margin, rule and type. `./ccb check` reports coverage. Above 72%
   the card becomes a collage; below 35% it looks unfinished.
3. **Type is measured, not guessed.** Greeting, family, message, signature and
   year are fitted to their zones: the largest size that fits, then shrunk only
   if it must be. Nothing is allowed to overflow, and no word is broken in half.
   A message that prints under 8 pt is too long for a card - shorten the copy
   rather than shrinking it.
4. **The margin is physical.** Margins and gutters are a fraction of the card's
   short side, so a 4x6 and a 5x7 look like the same designer made them.

## The eight styles

| Key | Look | Fonts | Decoration | Border |
| --- | --- | --- | --- | --- |
| `classic` | cream stock, deep green, holly | Playfair Display + Lato | holly sprigs in two corners | double rule |
| `modern` | lots of air, left-aligned | Montserrat + Lato | a few small stars | single rule |
| `traditional` | cranberry paper, capitals, snow | Cormorant Garamond + Great Vibes | snow behind the grid | thick frame |
| `editorial` | magazine spread, wide margins | Playfair Display + Lato | none | hairline rule |
| `nordic` | pale grey-green, quiet | Montserrat + Cormorant | sparse stars | none |
| `vintage` | warm paper, tilted frames | Cormorant Garamond + Great Vibes | holly, postcard frame | postcard |
| `joyful` | red and cream, script greeting | Great Vibes + Lato | confetti | none |
| `gallery` | photographs nearly edge to edge | Lato (caps) | none | thin rule |

Style changes case, tracking, spacing, border, photo treatment and decoration -
never colour alone. Use the palette for colour.

## The six palettes

`evergreen` (cream, deep green, brick red) - the safe classic.
`cranberry` (off-white, wine, warm grey) - traditional, good with snow.
`midnight` (navy, cream, brass) - elegant, heavy ink, best with `modern` or
`editorial`.
`nordic` (pale grey-green, charcoal) - quiet, good for a small card.
`brass` (ivory, black, bronze) - luxury editorial.
`peppermint` (warm white, ink blue, bright red) - playful, good with `joyful`.

## The six engines, and when each wins

- **grid** - the honest default for 3-9 photographs of equal importance. Works
  at every size; on landscape cards it reflows the columns automatically.
- **hero** - when one photograph is the reason for the card (a new baby, a
  wedding, the whole family together). The rest become a strip.
- **mosaic** - when the photographs have very different shapes: cells are cut to
  match portrait and landscape pictures instead of cropping everything square.
- **editorial** - when the message matters as much as the pictures, and for
  landscape cards. Text in a column, photographs as a plate.
- **postcard** - a big hero, a strip of the rest, and a full message block; the
  most "holiday card" of the six.
- **banner** - an edge-to-edge panorama; the printed border closes over the
  photographs so the card reads as framed. Best with 3-8 photographs.

## Print rules the engine enforces

- 300 DPI by default (96-1200 allowed). The PDF page is trim + 2 x 0.125 in
  bleed; crop marks sit in the bleed, outside the trim.
- Photographs are cover-cropped: no stretching, ever. A crop can lose edges; the
  scorer counts that loss and prefers gentler crops.
- A photograph used above about 1.8x its own pixels is reported as soft. Do not
  hide that warning; tell them which photograph and why.
- Text colour is chosen from the palette by measured contrast (4.5:1 where it
  can), not by eye.
- Empty text fields are omitted and the rest re-fits; a card with no message
  simply has a larger greeting.

## Words

- Greeting: 2-4 words. "Merry Christmas", "Happy Christmas", "Seasons
  Greetings", "Merry Christmas & a Happy New Year".
- Family: the name as they write it. Capitals come from the style.
- Message: two or three short sentences, first person plural, no exclamation
  marks stacked.
- Signature: "with love, Anna and Tom" - lower case reads warmer than
  "With Love".
- Year: four digits, no apostrophe.

Never invent a name to fill a field. An empty field is better than a wrong one.

## House notes

Add lasting preferences here with the date, for example:

- 2026-11-25: always leave the year off the front; it belongs on the back.
