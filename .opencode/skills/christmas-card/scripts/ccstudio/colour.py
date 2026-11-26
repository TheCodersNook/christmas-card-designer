"""Colour maths: hex, mixing, luminance and contrast.

Nothing here knows about a house palette. It is used to check that the colours a
composition declares are readable, and to sample colours out of the photographs
so a palette can be built from the pictures on the fly.
"""
from __future__ import annotations


def hex_of(rgb: tuple[float, float, float]) -> str:
    r, g, b = (max(0, min(255, int(round(v)))) for v in rgb)
    return f"#{r:02x}{g:02x}{b:02x}"


def rgb_of(value: str) -> tuple[float, float, float]:
    h = str(value).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return float(int(h[0:2], 16)), float(int(h[2:4], 16)), float(int(h[4:6], 16))
    except (ValueError, IndexError):
        return 0.0, 0.0, 0.0


def is_hex(value: str) -> bool:
    text = str(value or "").strip()
    if not text.startswith("#") or len(text) not in (4, 7):
        return False
    try:
        int(text[1:], 16)
    except ValueError:
        return False
    return True


def mix(a: str, b: str, t: float) -> str:
    """Mix two hex colours; t=0 is a, t=1 is b."""
    t = max(0.0, min(1.0, float(t)))
    ra, ga, ba = rgb_of(a)
    rb, gb, bb = rgb_of(b)
    return hex_of((ra + (rb - ra) * t, ga + (gb - ga) * t, ba + (bb - ba) * t))


def _lin(c: float) -> float:
    c = max(0.0, min(1.0, c / 255.0))
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def luminance(color: str) -> float:
    r, g, b = rgb_of(color)
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


def away_from(color: str, bg: str, target: float) -> str:
    """Push a colour toward black or white until it reaches `target` against bg."""
    if contrast(color, bg) >= target:
        return color
    toward = "#000000" if luminance(bg) > 0.5 else "#FFFFFF"
    if contrast(color, toward) < contrast(color, bg):
        toward = "#FFFFFF" if toward == "#000000" else "#000000"
    best = color
    for i in range(1, 21):
        trial = mix(color, toward, i / 20)
        best = trial
        if contrast(trial, bg) >= target:
            return trial
    return best


def toward(color: str, target: str, amount: float) -> str:
    return mix(color, target, amount)
