"""Measured type: wrapping, fitting and drawing inside a reserved zone.

Text is never dropped on top of a photograph and never overflows its zone. The
largest size that fits is found by binary search; if even the smallest readable
size does not fit, the copy shrinks in the zone and then ellipsises.
"""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass
from pathlib import Path

from PIL import ImageDraw, ImageFont

from . import config

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

# Sizes are a fraction of the card's short side (at export resolution).
ROLE_SIZES = {
    "greeting": 0.082,
    "family": 0.050,
    "message": 0.027,
    "signature": 0.031,
    "year": 0.021,
    "caption": 0.017,
    "monogram": 0.150,
}

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


def fit(text: str, role: str, family: str, weight: int, italic: bool, uppercase: bool,
        tracking_em: float, line_spacing: float, width: float, height: float,
        max_size: float, min_size: float = 0.0, max_lines: int = 8,
        align: str = "center", book: FontBook | None = None) -> Block:
    book = book or BOOK
    text = clean(text)
    if uppercase:
        text = text.upper()
    min_size = max(5.0, min_size or max_size * 0.55)
    if not text:
        return Block(role, book.font(family, min_size, weight, italic), int(min_size), [], min_size * line_spacing,
                     0.0, align)

    def build(size: float) -> tuple[ImageFont.FreeTypeFont, list[str], float]:
        font = book.font(family, size, weight, italic)
        tracking = tracking_em * size
        return font, wrap(text, font, width, tracking), tracking

    lo, hi = min_size, max(6.0, max_size)
    best: Block | None = None
    for _ in range(11):
        mid = (lo + hi) / 2
        font, lines, tracking = build(mid)
        lh = _line_height(font, mid, line_spacing)
        widest = max((measure(l, font, tracking) for l in lines), default=0.0)
        if lines and len(lines) <= max_lines and len(lines) * lh <= height + 0.5 and widest <= width + 0.5:
            best = Block(role, font, int(round(mid)), lines, lh, tracking, align)
            lo = mid
        else:
            hi = mid
    if best:
        return best

    font, lines, tracking = build(min_size)
    lh = _line_height(font, min_size, line_spacing)
    truncated = False
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        lines[-1] = ellipsise(lines[-1], font, width, tracking)
        truncated = True
    if len(lines) * lh > height and lines:
        lh = max(6.0, height / len(lines))
    return Block(role, font, int(min_size), lines, lh, tracking, align, truncated)


def fit_stack(roles: list[tuple[str, str]], zones_style: config.Style, width: float, height: float,
              short: float, scale: float = 1.0, book: FontBook | None = None) -> list[Block]:
    """Fit greeting/family/message/... into one zone, shrinking the whole stack together."""
    book = book or BOOK
    items = [(role, clean(text)) for role, text in roles if clean(text)]
    if not items or width < 8 or height < 8:
        return []
    style = zones_style

    def family_for(role: str) -> str:
        if role == "greeting":
            return style.script if style.greeting_font == "script" else (style.heading if style.greeting_font == "heading" else style.body)
        if role == "family":
            return style.script if style.name_font == "script" else (style.heading if style.name_font == "heading" else style.body)
        if role == "signature" and style.name_font == "script":
            return style.script
        return style.body

    def italic_for(role: str) -> bool:
        return role == "signature" and style.name_font != "script"

    def build(k: float) -> list[Block]:
        blocks = []
        for role, text in items:
            size = ROLE_SIZES.get(role, 0.03) * short * scale * k
            family = family_for(role)
            # Capitals belong to the roman faces; a script name is never shouted.
            uppercase = role in ("greeting", "family", "year") and style.caps and family != style.script
            tracking = style.tracking if role in ("greeting", "family", "year") else 0.0
            weight = style.weight if role in ("greeting", "family") else 400
            # Never break a word: cap the size so the longest word fits the zone.
            display = text.upper() if uppercase else text
            longest = max(display.split(), key=len, default="")
            probe = book.font(family, 100, weight, italic_for(role))
            pw = measure(longest, probe, tracking * 100)
            if pw > 1:
                size = min(size, width / pw * 100 * 0.98)
            lines_cap = {"greeting": 3, "family": 2, "message": 14, "signature": 2, "year": 1}.get(role, 4)
            blocks.append(fit(text, role, family, weight, italic_for(role), uppercase, tracking,
                              1.12 if role in ("greeting", "family") else 1.42,
                              width, height, max(5.0, size), max(5.0, size * 0.5), lines_cap,
                              "left" if style.align == "left" else "center", book=book))
        return blocks

    for k in (1.0, 0.94, 0.88, 0.82, 0.76, 0.70, 0.64, 0.58, 0.52, 0.46, 0.40):
        blocks = build(k)
        gap = max(2.0, min((b.size for b in blocks), default=12) * 0.35)
        total = sum(b.height for b in blocks) + gap * (len(blocks) - 1)
        if total <= height:
            return blocks
    blocks = build(0.36)
    gap = max(2.0, min((b.size for b in blocks), default=12) * 0.2)
    share = max(1.0, (height - gap * max(0, len(blocks) - 1)) / max(1, len(blocks)))
    out = []
    for b in blocks:
        if b.height > share:
            b.line_height = max(4.0, share / max(1, len(b.lines)))
        out.append(b)
    return out


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


# ------------------------------------------------------------------- contrast
def _lin(c: float) -> float:
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(hex_color: str) -> float:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def contrast(a: str, b: str) -> float:
    la, lb = luminance(a), luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def readable_text(bg: str, *candidates: str) -> str:
    """The first candidate with 4.5:1, else the highest-contrast candidate."""
    for c in candidates:
        if contrast(bg, c) >= 4.5:
            return c
    return max(candidates, key=lambda c: contrast(bg, c))


def measure_text_role(role: str, style: config.Style, short: float) -> int:
    return int(round(ROLE_SIZES.get(role, 0.03) * short * 1.0))
