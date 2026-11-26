"""Measured type: wrapping, fitting and drawing a piece of copy in its zone.

Every zone names its own size, face, weight, tracking and leading; there are no
named type roles and no house scale. The size the composition asks for is the
size that is set. If the copy cannot fit even after stepping down to a floor, it
is ellipsised, and the gate reports it.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from PIL import ImageDraw, ImageFont

from . import config
from .colour import contrast, luminance, readable_text  # re-exported for the renderer

# family key -> files. Variable fonts get their weight axis set per use.
FAMILIES: dict[str, dict] = {
    "playfair": {"label": "Playfair Display", "regular": "PlayfairDisplay[wght].ttf",
                 "italic": "PlayfairDisplay-Italic[wght].ttf", "variable": True},
    "cormorant": {"label": "Cormorant Garamond", "regular": "CormorantGaramond[wght].ttf",
                  "italic": "CormorantGaramond-Italic[wght].ttf", "variable": True},
    "montserrat": {"label": "Montserrat", "regular": "Montserrat[wght].ttf",
                   "italic": "", "variable": True},
    "lato": {"label": "Lato", "variable": False, "italic": "Lato-Italic.ttf",
             "weights": {300: "Lato-Light.ttf", 400: "Lato-Regular.ttf",
                         700: "Lato-Bold.ttf", 900: "Lato-Black.ttf"}},
    "greatvibes": {"label": "Great Vibes", "regular": "GreatVibes-Regular.ttf",
                   "italic": "", "variable": False},
    "instrument": {"label": "Instrument Serif", "regular": "InstrumentSerif-Regular.ttf",
                   "italic": "InstrumentSerif-Italic.ttf", "variable": False},
}

FONT_CHOICES = [(k, v["label"]) for k, v in FAMILIES.items()]
FAMILY_KEYS = tuple(FAMILIES)

CHAR_MAP = {
    "\u2018": "'", "\u2019": "'", "\u201a": "'", "\u201b": "'",
    "\u201c": '"', "\u201d": '"', "\u201e": '"',
    "\u2013": "-", "\u2014": "-", "\u2212": "-", "\u2026": "...",
    "\u00a0": " ", "\u202f": " ", "\u2009": " ", "\u200b": "", "\u00b4": "'", "\u0060": "'",
}
ALLOWED = set("&@#%()[]{},.;:!?'\"-/\\|+*=<>$€£°·•*")


def clean(text: str) -> str:
    """Normalise pasted copy and strip glyphs the bundled fonts cannot draw."""
    if not text:
        return ""
    text = str(text).replace("\r\n", "\n").replace("\r", "\n")
    for a, b in CHAR_MAP.items():
        text = text.replace(a, b)
    out = []
    for ch in text:
        if ch in "\n\t":
            out.append("\n" if ch == "\n" else " ")
        elif ord(ch) < 128 or ch in ALLOWED:
            out.append(ch)
        else:
            cat = unicodedata.category(ch)
            if (cat[0] in "LNP" or cat[0] == "S") and ord(ch) <= 0x024F:
                out.append(ch)
    lines = [" ".join(line.split()) for line in "".join(out).split("\n")]
    return "\n".join(lines).strip()


class FontBook:
    def __init__(self, font_dir: Path | None = None):
        self.font_dir = Path(font_dir or config.FONT_DIR)
        self._cache: dict[tuple, ImageFont.FreeTypeFont] = {}
        self.missing: set[str] = set()

    def available(self, family: str) -> bool:
        meta = FAMILIES.get(family) or FAMILIES["lato"]
        names = [meta.get("regular", "")]
        names += list((meta.get("weights") or {}).values())
        names.append(meta.get("italic", ""))
        return any((self.font_dir / n).exists() for n in names if n)

    def _pick(self, family: str, weight: int, italic: bool) -> tuple[str, bool]:
        meta = FAMILIES.get(family) or FAMILIES["lato"]
        if meta.get("variable"):
            name = meta["italic"] if italic and meta.get("italic") else meta["regular"]
            return name, True
        if italic and meta.get("italic"):
            return meta["italic"], False
        weights = meta.get("weights") or {}
        if weights:
            nearest = min(weights, key=lambda w: (abs(w - weight), -w))
            return weights[nearest], False
        return meta["regular"], False

    def font(self, family: str, size: float, weight: int = 400, italic: bool = False) -> ImageFont.FreeTypeFont:
        size_i = max(4, int(round(size)))
        key = (family, size_i, int(weight), bool(italic))
        if key in self._cache:
            return self._cache[key]
        name, variable = self._pick(family, weight, italic)
        path = self.font_dir / name
        if not path.exists():
            self.missing.add(name)
            path = self._fallback(family)
        if path is None:
            font = ImageFont.load_default(size=size_i)
            variable = False
        else:
            try:
                font = ImageFont.truetype(str(path), size_i)
            except OSError:
                font = ImageFont.load_default(size=size_i)
                variable = False
            if variable:
                _set_weight(font, weight)
        self._cache[key] = font
        return font

    def _fallback(self, family: str) -> Path | None:
        order = [family, "playfair", "lato", "montserrat", "cormorant", "instrument", "greatvibes"]
        for fam in order:
            meta = FAMILIES.get(fam)
            if not meta:
                continue
            for name in [meta.get("regular", ""), *((meta.get("weights") or {}).values())]:
                candidate = self.font_dir / name if name else None
                if candidate and candidate.exists():
                    return candidate
        return None


def _set_weight(font: ImageFont.FreeTypeFont, weight: int) -> None:
    try:
        axes = font.get_variation_axes()
    except Exception:
        return
    if not axes:
        return
    values = []
    for axis in axes:
        name = axis.get("name", b"")
        if isinstance(name, bytes):
            name = name.decode("utf-8", "ignore")
        values.append(float(weight) if str(name).lower() in {"weight", "wght"} else float(axis.get("default", 0.0)))
    try:
        font.set_variation_by_axes(values)
    except Exception:
        pass


BOOK = FontBook()


def measure(line: str, font: ImageFont.FreeTypeFont, tracking: float = 0.0) -> float:
    if not line:
        return 0.0
    return font.getlength(line) + (tracking * max(0, len(line) - 1))


def wrap(text: str, font: ImageFont.FreeTypeFont, max_width: float, tracking: float = 0.0) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if not paragraph.strip():
            continue
        current = ""
        for word in paragraph.split(" "):
            if not word:
                continue
            candidate = f"{current} {word}".strip()
            if measure(candidate, font, tracking) <= max_width:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            if measure(word, font, tracking) <= max_width:
                current = word
                continue
            piece = ""
            for ch in word:
                if measure(piece + ch, font, tracking) <= max_width or not piece:
                    piece += ch
                else:
                    lines.append(piece)
                    piece = ch
            current = piece
        if current:
            lines.append(current)
    return lines


def ellipsise(line: str, font: ImageFont.FreeTypeFont, max_width: float, tracking: float) -> str:
    out = line
    while out and measure(out + "...", font, tracking) > max_width:
        out = out[:-1]
    return (out.rstrip() + "...") if out else ""


@dataclass
class Block:
    role: str
    font: ImageFont.FreeTypeFont
    size: int
    lines: list[str]
    line_height: float
    tracking: float
    align: str
    truncated: bool = False
    requested: float = 0.0      # the size the composition asked for, in px
    shrunk: bool = False        # stepped down to fit the zone

    @property
    def height(self) -> float:
        return self.line_height * len(self.lines)

    @property
    def width(self) -> float:
        return max((measure(l, self.font, self.tracking) for l in self.lines), default=0.0)

    def metrics(self) -> tuple[int, int]:
        try:
            return self.font.getmetrics()
        except Exception:
            return self.size, int(self.size * 0.25)


def _line_height(font: ImageFont.FreeTypeFont, size: float, spacing: float) -> float:
    """Real line height: script faces reach far past their nominal size, and an
    extra line of separation is what keeps a name off the greeting above it."""
    try:
        ascent, descent = font.getmetrics()
    except Exception:
        ascent, descent = int(size), int(size * 0.25)
    return max(size * spacing, (ascent + descent) * 1.02)


def fit(text: str, word: str, family: str, weight: int, italic: bool, uppercase: bool,
        tracking_em: float, leading: float, width: float, height: float,
        size: float, align: str = "left", min_scale: float = 0.6,
        book: FontBook | None = None) -> Block:
    """Set one piece of copy at the size the composition asked for.

    If it will not fit, it steps down (no smaller than ``min_scale`` of the
    requested size) and then ellipsises; the gate reports either.
    """
    book = book or BOOK
    text = clean(text)
    if uppercase:
        text = text.upper()
    size = max(5.0, float(size))
    floor = max(5.0, size * max(0.2, min(1.0, min_scale)))
    if not text:
        return Block(word, book.font(family, floor, weight, italic), int(round(floor)), [],
                     floor * leading, 0.0, align, requested=size)

    def build(at: float) -> tuple[ImageFont.FreeTypeFont, list[str], float]:
        font = book.font(family, at, weight, italic)
        tracking = tracking_em * at
        return font, wrap(text, font, max(8.0, width), tracking), tracking

    def fits(at: float) -> bool:
        font, lines, tracking = build(at)
        lh = _line_height(font, at, leading)
        widest = max((measure(l, font, tracking) for l in lines), default=0.0)
        return bool(lines) and len(lines) * lh <= height + 0.5 and widest <= width + 0.5

    chosen = size if fits(size) else floor
    if not fits(size):
        lo, hi = floor, size
        for _ in range(12):
            mid = (lo + hi) / 2
            if fits(mid):
                lo = mid
            else:
                hi = mid
        chosen = lo
    font, lines, tracking = build(chosen)
    lh = _line_height(font, chosen, leading)
    truncated = False
    room = max(1, int((height + 0.5) // max(1.0, lh)))
    if len(lines) > room:
        lines = lines[:room]
        lines[-1] = ellipsise(lines[-1], font, max(8.0, width), tracking)
        truncated = True
    if lines and len(lines) * lh > height:
        lh = max(4.0, height / len(lines))
    return Block(word, font, int(round(chosen)), lines, lh, tracking, align, truncated,
                 requested=size, shrunk=chosen < size - 0.5)


def draw_block(draw: ImageDraw.ImageDraw, block: Block, box: tuple[float, float, float, float],
               color: str, align: str | None = None, valign: str = "center") -> tuple[float, float, float, float]:
    x, y, w, h = box
    if not block.lines:
        return (x, y, 0.0, 0.0)
    align = align or block.align
    total = block.height
    top = y if valign == "top" else (y + h - total if valign == "bottom" else y + (h - total) / 2)
    ascent, descent = block.metrics()
    left = x + w
    right = x
    for i, line in enumerate(block.lines):
        lw = measure(line, block.font, block.tracking)
        lx = x if align == "left" else (x + w - lw if align == "right" else x + (w - lw) / 2)
        baseline = top + i * block.line_height + (block.line_height - (ascent + descent)) / 2 + ascent
        if block.tracking:
            cx = lx
            for ch in line:
                draw.text((cx, baseline), ch, font=block.font, fill=color, anchor="ls")
                cx += block.font.getlength(ch) + block.tracking
        else:
            draw.text((lx, baseline), line, font=block.font, fill=color, anchor="ls")
        left, right = min(left, lx), max(right, lx + lw)
    return (left, top, max(0.0, right - left), max(0.0, min(y + h, top + total) - top))



