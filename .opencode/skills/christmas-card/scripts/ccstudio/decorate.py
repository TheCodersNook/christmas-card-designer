"""Procedural decoration: snow, stars, holly, confetti and borders.

Everything is drawn with a seeded random generator, so the same card always
produces the same snowflakes. Decorations keep out of photograph and text
rectangles instead of sitting on top of someone's face.
"""
from __future__ import annotations

import math
import random
from typing import Iterable

from PIL import ImageDraw

from . import config

Rect = tuple[float, float, float, float]


def _overlaps(a: Rect, b: Rect, pad: float = 0.0) -> bool:
    return not (a[0] + a[2] + pad <= b[0] or b[0] + b[2] + pad <= a[0]
                or a[1] + a[3] + pad <= b[1] or b[1] + b[3] + pad <= a[1])


def _free(r: Rect, keepout: Iterable[Rect], pad: float) -> bool:
    return not any(_overlaps(r, k, pad) for k in keepout)


def _scatter(draw: ImageDraw.ImageDraw, kind: str, palette: config.Palette, style: config.Style,
             width: int, height: int, keepout: list[Rect], seed: int) -> None:
    rng = random.Random(seed)
    short = min(width, height)
    density = max(0.0, min(1.5, style.density))
    if kind == "snow":
        count = int(70 * density) + 10
        for _ in range(count):
            r = rng.uniform(0.0012, 0.0035) * short
            x, y = rng.uniform(0, width), rng.uniform(0, height)
            box = (x - r, y - r, x + r, y + r)
            if not _free(box, keepout, r * 2):
                continue
            color = palette.accent if rng.random() < 0.18 else palette.ink
            draw.ellipse(box, fill=color)
    elif kind == "stars":
        count = int(11 * density) + 3
        for _ in range(count):
            s = rng.uniform(0.006, 0.016) * short
            x, y = rng.uniform(0.02, 0.98) * width, rng.uniform(0.02, 0.98) * height
            box = (x - s, y - s, x + s, y + s)
            if not _free(box, keepout, s):
                continue
            w = max(1, int(short * 0.0011))
            draw.line((x - s, y, x + s, y), fill=palette.accent, width=w)
            draw.line((x, y - s, x, y + s), fill=palette.accent, width=w)
    elif kind == "confetti":
        count = int(34 * density) + 6
        for _ in range(count):
            s = rng.uniform(0.004, 0.011) * short
            x, y = rng.uniform(0.01, 0.99) * width, rng.uniform(0.01, 0.99) * height
            box = (x - s, y - s, x + s, y + s)
            if not _free(box, keepout, s):
                continue
            color = rng.choice([palette.accent, palette.soft, palette.ink])
            if rng.random() < 0.5:
                draw.ellipse(box, fill=color)
            else:
                draw.rectangle(box, fill=color)
    elif kind == "holly":
        corners = [(0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)]
        rng.shuffle(corners)
        for i, (cx, cy) in enumerate(corners[:2 if density < 0.6 else 3]):
            x = cx * width
            y = cy * height
            if 0.0 < cx < 1.0 or 0.0 < cy < 1.0:
                x = width * (0.06 if cx == 0 else 0.94)
                y = height * (0.05 if cy == 0 else 0.95)
            leaf = short * 0.028
            if not _free((x - leaf * 2, y - leaf * 2, x + leaf * 2, y + leaf * 2), keepout, leaf):
                continue
            for angle in (-35, 5, 45):
                _leaf(draw, x, y, leaf, angle, palette.ink)
            for j, off in enumerate((-0.7, 0.2, 1.0)):
                bx = x + off * leaf * 0.9
                by = y + leaf * 0.65 + (0.25 * leaf if j == 1 else 0)
                draw.ellipse((bx - leaf * 0.22, by - leaf * 0.22, bx + leaf * 0.22, by + leaf * 0.22),
                             fill=palette.accent)


def _leaf(draw: ImageDraw.ImageDraw, x: float, y: float, size: float, angle_deg: float, color: str) -> None:
    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    tip = (x + dx * size * 1.6, y + dy * size * 1.6)
    left = (x - dy * size * 0.55, y + dx * size * 0.55)
    right = (x + dy * size * 0.55, y - dx * size * 0.55)
    mid_l = (x + dx * size * 0.7 - dy * size * 0.5, y + dy * size * 0.7 + dx * size * 0.5)
    mid_r = (x + dx * size * 0.7 + dy * size * 0.5, y + dy * size * 0.7 - dx * size * 0.5)
    draw.polygon([left, mid_l, tip, mid_r, right], fill=color)


def decorate(draw: ImageDraw.ImageDraw, style: config.Style, palette: config.Palette,
             width: int, height: int, keepout: list[Rect], seed: int) -> None:
    if style.decoration and style.decoration != "none" and style.density > 0:
        _scatter(draw, style.decoration, palette, style, width, height, keepout, seed)


def border(draw: ImageDraw.ImageDraw, style: config.Style, palette: config.Palette,
           width: int, height: int, margin_px: float) -> None:
    """The printed border, drawn just inside the trim so bleed cannot clip it."""
    short = min(width, height)
    kind = style.border
    if kind == "none":
        return
    inset = max(2.0, margin_px * 0.42)
    lw = max(1, int(round(short * 0.0016)))
    if kind == "rule":
        draw.line((inset, inset * 0.62, width - inset, inset * 0.62), fill=palette.accent, width=lw)
    elif kind == "double":
        draw.rectangle((inset, inset, width - inset, height - inset), outline=palette.ink, width=lw)
        gap = inset * 0.28
        draw.rectangle((inset + gap, inset + gap, width - inset - gap, height - inset - gap),
                       outline=palette.accent, width=max(1, lw // 2))
    elif kind == "frame":
        draw.rectangle((inset, inset, width - inset, height - inset), outline=palette.accent, width=lw * 3)
        draw.rectangle((inset * 1.5, inset * 1.5, width - inset * 1.5, height - inset * 1.5),
                       outline=palette.accent, width=max(1, lw // 2))
    elif kind == "postcard":
        draw.rectangle((inset, inset, width - inset, height - inset), outline=palette.accent, width=lw)
        inner = inset * 1.45
        draw.rectangle((inner, inner, width - inner, height - inner), outline=palette.soft, width=max(1, lw // 2))


def rule(draw: ImageDraw.ImageDraw, x0: float, x1: float, y: float, color: str, width: int) -> None:
    draw.line((x0, y, x1, y), fill=color, width=width)
