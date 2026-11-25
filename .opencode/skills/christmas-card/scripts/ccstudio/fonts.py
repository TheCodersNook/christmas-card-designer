"""Fonts: the studio ships no binaries, so setup downloads the OFL files once.

`./ccb fonts` fetches the eight families into assets/fonts/ (about 6 MB). Until
then the engine falls back to whatever TrueType font it can find, and `doctor`
says so plainly.
"""
from __future__ import annotations

import sys
import urllib.request
from pathlib import Path

from . import config

BASE = "https://raw.githubusercontent.com/google/fonts/main/ofl/"

# (local file name, url path under ofl/)
FONT_FILES: list[tuple[str, str]] = [
    ("PlayfairDisplay[wght].ttf", "playfairdisplay/PlayfairDisplay%5Bwght%5D.ttf"),
    ("PlayfairDisplay-Italic[wght].ttf", "playfairdisplay/PlayfairDisplay-Italic%5Bwght%5D.ttf"),
    ("CormorantGaramond[wght].ttf", "cormorantgaramond/CormorantGaramond%5Bwght%5D.ttf"),
    ("CormorantGaramond-Italic[wght].ttf", "cormorantgaramond/CormorantGaramond-Italic%5Bwght%5D.ttf"),
    ("Montserrat[wght].ttf", "montserrat/Montserrat%5Bwght%5D.ttf"),
    ("Lato-Light.ttf", "lato/Lato-Light.ttf"),
    ("Lato-Regular.ttf", "lato/Lato-Regular.ttf"),
    ("Lato-Bold.ttf", "lato/Lato-Bold.ttf"),
    ("Lato-Italic.ttf", "lato/Lato-Italic.ttf"),
    ("GreatVibes-Regular.ttf", "greatvibes/GreatVibes-Regular.ttf"),
    ("InstrumentSerif-Regular.ttf", "instrumentserif/InstrumentSerif-Regular.ttf"),
    ("InstrumentSerif-Italic.ttf", "instrumentserif/InstrumentSerif-Italic.ttf"),
    ("OFL.txt", "lato/OFL.txt"),
]

LICENCE_NOTE = """Fonts in this folder
-------------------
Playfair Display, Cormorant Garamond, Montserrat, Lato, Great Vibes and
Instrument Serif are drawn by their respective designers and released under the
SIL Open Font License 1.1. They come from the Google Fonts repository:
https://github.com/google/fonts

The OFL allows free use, modification and redistribution, including bundling
inside documents and printed work. The fonts may not be sold on their own.
"""


def installed() -> int:
    return sum(1 for name, _ in FONT_FILES if name.endswith(".ttf") and (config.FONT_DIR / name).exists())


def total() -> int:
    return sum(1 for name, _ in FONT_FILES if name.endswith(".ttf"))


def ensure(force: bool = False, quiet: bool = False) -> int:
    """Download the missing font files. Returns how many are present afterwards."""
    config.FONT_DIR.mkdir(parents=True, exist_ok=True)
    for name, remote in FONT_FILES:
        target = config.FONT_DIR / name
        if target.exists() and not force and target.stat().st_size > 1000:
            continue
        url = BASE + remote
        if not quiet:
            print(f"  fetching {name}")
        try:
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
        except Exception as exc:  # network, 404, proxy ...
            print(f"  could not fetch {name}: {exc}", file=sys.stderr)
            continue
        if len(data) < 1000:
            print(f"  {name} looked empty, skipped", file=sys.stderr)
            continue
        target.write_bytes(data)
    note = config.FONT_DIR / "FONT-CREDITS.md"
    if not note.exists():
        note.write_text(LICENCE_NOTE, encoding="utf-8")
    return installed()


def status() -> str:
    have, want = installed(), total()
    if have == 0:
        return "no studio fonts yet - run ./ccb fonts (the engine falls back to a system font)"
    if have < want:
        return f"{have}/{want} studio fonts - run ./ccb fonts to finish the set"
    return f"{want}/{want} studio fonts in assets/fonts"


def find_any_ttf() -> Path | None:
    """Last-resort font lookup so a card can always be rendered."""
    roots = [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"),
             Path.home() / "Library" / "Fonts", Path("C:/Windows/Fonts")]
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*.ttf"))[:200]:
            try:
                if path.stat().st_size > 20_000:
                    return path
            except OSError:
                continue
    return None
