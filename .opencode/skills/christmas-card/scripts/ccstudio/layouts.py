"""Six deterministic layout engines.

Each engine turns the photographs and the card shape into photo slots and text
zones, all as fractions of the trim box. No randomness, no model: the same
photographs and settings always give the same six designs.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from . import config
from .photos import Photo


@dataclass
class Slot:
    photo: int                     # index into the card's photo list
    x: float
    y: float
    w: float
    h: float

    def to_dict(self) -> dict[str, Any]:
        return {"photo": self.photo, "x": r4(self.x), "y": r4(self.y), "w": r4(self.w), "h": r4(self.h)}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Slot":
        return Slot(int(d["photo"]), float(d["x"]), float(d["y"]), float(d["w"]), float(d["h"]))


@dataclass
class Zone:
    roles: tuple[str, ...]
    x: float
    y: float
    w: float
    h: float
    panel: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"roles": list(self.roles), "x": r4(self.x), "y": r4(self.y),
                "w": r4(self.w), "h": r4(self.h), "panel": self.panel}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Zone":
        return Zone(tuple(d.get("roles", [])), float(d["x"]), float(d["y"]),
                    float(d["w"]), float(d["h"]), bool(d.get("panel", False)))


@dataclass
class Design:
    engine: str
    label: str
    slots: list[Slot] = field(default_factory=list)
    zones: list[Zone] = field(default_factory=list)
    order: list[int] = field(default_factory=list)
    score: float = 0.0
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "label": self.label,
            "score": round(self.score, 1),
            "slots": [s.to_dict() for s in self.slots],
            "zones": [z.to_dict() for z in self.zones],
            "order": list(self.order),
            "notes": list(self.notes),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Design":
        return Design(
            str(d.get("engine", "custom")),
            str(d.get("label", "Saved design")),
            [Slot.from_dict(s) for s in d.get("slots", [])],
            [Zone.from_dict(z) for z in d.get("zones", [])],
            [int(i) for i in d.get("order", [])],
            float(d.get("score", 0.0)),
            list(d.get("notes", [])),
        )

    @property
    def coverage(self) -> float:
        return sum(s.w * s.h for s in self.slots)


def r4(v: float) -> float:
    return round(float(v), 4)


# ------------------------------------------------------------------ utilities
def grid_rects(area: tuple[float, float, float, float], count: int, gap: float,
               card: tuple[float, float], target: float = 1.12) -> list[tuple[float, float, float, float]]:
    """Cells for `count` photographs, choosing the column count that keeps cells closest to `target`."""
    if count <= 0:
        return []
    x, y, w, h = area
    cw_in, ch_in = card
    best = None
    for cols in range(1, count + 1):
        rows = math.ceil(count / cols)
        cell_w = (w - gap * (cols - 1)) / cols
        cell_h = (h - gap * (rows - 1)) / rows
        if cell_w <= 0 or cell_h <= 0:
            continue
        aspect = (cell_w * cw_in) / (cell_h * ch_in)
        cost = abs(math.log(max(aspect, 1e-6) / target)) + 0.02 * (rows * cols - count) / count
        if best is None or cost < best[0]:
            best = (cost, cols, rows, cell_w, cell_h)
    if best is None:
        return []

    _, cols, rows, cell_w, cell_h = best
    out = []
    for r in range(rows):
        in_row = min(cols, count - r * cols)
        if in_row <= 0:
            break
        if in_row == cols:
            row_w = cell_w
            row_x = x
            count_in_row = cols
        else:
            count_in_row = in_row
            row_w = (w - gap * (in_row - 1)) / in_row
            row_x = x + (w - (row_w * in_row + gap * (in_row - 1))) / 2
        for c in range(count_in_row):
            out.append((row_x + c * (row_w + gap), y + r * (cell_h + gap), row_w, cell_h))
    return out


def _hero_index(spec_hero: str, photos: list[Photo], names: list[str]) -> int:
    if spec_hero:
        for i, name in enumerate(names):
            if name == spec_hero or name.endswith(spec_hero):
                return i
    best = max(range(len(photos)), key=lambda i: (photos[i].interest, photos[i].megapixels))
    return best


def _order(first: int, count: int) -> list[int]:
    return [first] + [i for i in range(count) if i != first]


def _score(design: Design, photos: list[Photo], card: tuple[float, float]) -> Design:
    cw, ch = card
    coverage = design.coverage
    waste = []
    for s in design.slots:
        slot_aspect = (s.w * cw) / max(1e-6, s.h * ch)
        photo_aspect = photos[s.photo].aspect if 0 <= s.photo < len(photos) else 1.0
        waste.append(1 - min(slot_aspect / photo_aspect, photo_aspect / slot_aspect))
    avg_waste = sum(waste) / len(waste) if waste else 0.0
    total_area = sum(s.w * s.h for s in design.slots) or 1.0
    cx = sum((s.x + s.w / 2) * s.w * s.h for s in design.slots) / total_area
    cy = sum((s.y + s.h / 2) * s.w * s.h for s in design.slots) / total_area
    balance = math.hypot(cx - 0.5, cy - 0.47)
    text_area = sum(z.w * z.h for z in design.zones)
    score = 100.0
    score -= 60.0 * abs(coverage - 0.55)
    score -= 42.0 * max(0.0, avg_waste)
    score -= 22.0 * balance
    score -= 9.0 if text_area < 0.15 else 0.0
    score -= 6.0 if coverage > 0.72 else 0.0
    design.score = max(35.0, min(99.0, score))
    design.notes = [
        f"photographs cover {coverage * 100:.0f}% of the card",
        f"average crop loss {avg_waste * 100:.0f}%",
        f"{len(design.slots)} photographs placed",
    ]
    return design


# -------------------------------------------------------------------- engines
def _chrome(style: config.Style) -> tuple[float, float, float]:
    m = style.margin
    return m, m, 1 - m     # left, top, bottom


def _footer(m: float, bottom: float) -> tuple[float, float, float, float]:
    """Message zone and signature zone, anchored to the bottom margin.

    Anchoring (instead of fixed fractions) keeps roomy-margin styles from
    pushing the signature into the trim edge.
    """
    edge = bottom - 0.005
    sign_h = 0.070
    sign_y = edge - sign_h
    msg_h = 0.095
    msg_y = sign_y - 0.014 - msg_h
    return msg_y, msg_h, sign_y, sign_h


def grid(photos: list[Photo], order: list[int], style: config.Style, card: tuple[float, float]) -> Design:
    m, top, _ = _chrome(style)
    gap = 0.012
    msg_y, msg_h, sign_y, sign_h = _footer(m, 1 - m)
    header = Zone(("greeting", "family"), m, top, 1 - 2 * m, 0.125)
    area_y = top + 0.135
    area = (m, area_y, 1 - 2 * m, msg_y - 0.022 - area_y)
    rects = grid_rects(area, len(order), gap, card, target=1.05)
    slots = [Slot(order[i], *rects[i]) for i in range(min(len(order), len(rects)))]
    message = Zone(("message",), m, msg_y, 1 - 2 * m, msg_h)
    sign = Zone(("signature", "year"), m, sign_y, 1 - 2 * m, sign_h)
    return Design("grid", f"Uniform grid - {len(slots)} up", slots, [header, message, sign], order)


def hero(photos: list[Photo], order: list[int], style: config.Style, card: tuple[float, float]) -> Design:
    m, top, _ = _chrome(style)
    width = 1 - 2 * m
    first, rest = order[0], order[1:]
    msg_y, msg_h, sign_y, sign_h = _footer(m, 1 - m)
    header = Zone(("greeting", "family"), m, top, width, 0.125)
    band_y = top + 0.135
    band_h = msg_y - 0.022 - band_y
    hero_h = band_h * (0.62 if len(rest) > 2 else 0.75)
    slots = [Slot(first, m, band_y, width, hero_h)]
    strip_y = band_y + hero_h + 0.014
    strip_h = band_h - hero_h - 0.014
    if rest and strip_h > 0.02:
        rects = grid_rects((m, strip_y, width, strip_h), len(rest), 0.012, card, target=1.0)
        slots += [Slot(rest[i], *rects[i]) for i in range(min(len(rest), len(rects)))]
    message = Zone(("message",), m, msg_y, width, msg_h)
    sign = Zone(("signature", "year"), m, sign_y, width, sign_h)
    return Design("hero", "Hero and strip", slots, [header, message, sign], order)


def mosaic(photos: list[Photo], order: list[int], style: config.Style, card: tuple[float, float]) -> Design:
    m, top, _ = _chrome(style)
    width = 1 - 2 * m
    msg_y, msg_h, sign_y, sign_h = _footer(m, 1 - m)
    header = Zone(("greeting", "family"), m, top, width, 0.125)
    area_y = top + 0.135
    area = (m, area_y, width, msg_y - 0.022 - area_y)
    rects: list[tuple[float, float, float, float]] = []

    def split(rect: tuple[float, float, float, float], n: int, vertical: bool) -> None:
        if n <= 0:
            return
        if n == 1:
            rects.append(rect)
            return
        x, y, w, h = rect
        if vertical:
            ratio = 0.5 + (0.08 if n % 3 == 0 else -0.06)
            left_n = max(1, min(n - 1, round(n * ratio)))
            cut = w * (left_n / n)
            split((x, y, cut - 0.006, h), left_n, not vertical)
            split((x + cut + 0.006, y, w - cut - 0.006, h), n - left_n, not vertical)
        else:
            top_n = max(1, min(n - 1, math.ceil(n / 2)))
            cut = h * (top_n / n)
            split((x, y, w, cut - 0.006), top_n, not vertical)
            split((x, y + cut + 0.006, w, h - cut - 0.006), n - top_n, not vertical)

    split(area, len(order), card[0] >= card[1])
    slots = [Slot(order[i], *rects[i]) for i in range(min(len(order), len(rects)))]
    message = Zone(("message",), m, msg_y, width, msg_h)
    sign = Zone(("signature", "year"), m, sign_y, width, sign_h)
    return Design("mosaic", "Proportional mosaic", slots, [header, message, sign], order)


def editorial(photos: list[Photo], order: list[int], style: config.Style, card: tuple[float, float]) -> Design:
    m, top, bottom = _chrome(style)
    left_w = 0.43 if card[1] >= card[0] else 0.36
    text = Zone(("greeting", "family", "message", "signature", "year"),
                m, top, left_w, bottom - top - 0.01)
    photo_x = m + left_w + 0.03
    area = (photo_x, top, 1 - m - photo_x, bottom - top - 0.01)
    rects = grid_rects(area, len(order), 0.012, card, target=0.92)
    slots = [Slot(order[i], *rects[i]) for i in range(min(len(order), len(rects)))]
    return Design("editorial", "Editorial column", slots, [text], order)


def postcard(photos: list[Photo], order: list[int], style: config.Style, card: tuple[float, float]) -> Design:
    m, top, _ = _chrome(style)
    width = 1 - 2 * m
    first, rest = order[0], order[1:]
    msg_y, msg_h, sign_y, sign_h = _footer(m, 1 - m)
    header = Zone(("greeting", "family"), m, top, width, 0.12)
    band_y = top + 0.13
    band_h = msg_y - 0.022 - band_y
    hero_h = band_h * (0.44 if len(rest) > 3 else 0.52)
    slots = [Slot(first, m, band_y, width, hero_h)]
    strip_y = band_y + hero_h + 0.014
    strip_h = band_h - hero_h - 0.014
    if rest and strip_h > 0.02:
        rects = grid_rects((m, strip_y, width, strip_h), len(rest), 0.012, card, target=1.15)
        slots += [Slot(rest[i], *rects[i]) for i in range(min(len(rest), len(rects)))]
    message = Zone(("message",), m, msg_y, width, msg_h + 0.05)
    sign = Zone(("signature", "year"), m, sign_y, width, sign_h)
    return Design("postcard", "Postcard stack", slots, [header, message, sign], order)


def banner(photos: list[Photo], order: list[int], style: config.Style, card: tuple[float, float]) -> Design:
    m, top, _ = _chrome(style)
    width = 1 - 2 * m
    msg_y, msg_h, sign_y, sign_h = _footer(m, 1 - m)
    header = Zone(("greeting", "family"), m, top, width, 0.13)
    band_y = top + 0.14
    # The panorama runs edge to edge - that is what makes it different from the grid.
    gap = 0.006
    area = (0.0, band_y, 1.0, msg_y - 0.022 - band_y)
    rows = 1 if len(order) <= 3 else 2
    cols = math.ceil(len(order) / rows)
    rects: list[tuple[float, float, float, float]] = []
    cell_h = (area[3] - gap * (rows - 1)) / rows
    for r in range(rows):
        in_row = min(cols, len(order) - r * cols)
        cell_w = (1.0 - gap * (in_row - 1)) / in_row
        for c in range(in_row):
            rects.append((c * (cell_w + gap), area[1] + r * (cell_h + gap), cell_w, cell_h))
    slots = [Slot(order[i], *rects[i]) for i in range(min(len(order), len(rects)))]
    message = Zone(("message",), m, msg_y, width, msg_h)
    sign = Zone(("signature", "year"), m, sign_y, width, sign_h)
    return Design("banner", "Panorama banner", slots, [header, message, sign], order)


ENGINE_FUNCS = {
    "grid": grid,
    "hero": hero,
    "mosaic": mosaic,
    "editorial": editorial,
    "postcard": postcard,
    "banner": banner,
}


def build(spec, photos: list[Photo]) -> list[Design]:
    """Run every engine, score the results and return them best first."""
    if not photos:
        return []
    style = spec.style
    card = spec.card_inches
    names = [str(p) for p in spec.data.get("photos", [])]
    hero = _hero_index(str(spec.data.get("design", {}).get("hero") or ""), photos, names)
    natural = list(range(len(photos)))
    aspect_order = sorted(range(len(photos)), key=lambda i: (-photos[i].aspect, i))
    interest_order = sorted(range(len(photos)), key=lambda i: (-photos[i].interest, i))
    orders = {
        "grid": natural,
        "hero": _order(hero, len(photos)),
        "mosaic": aspect_order,
        "editorial": natural,
        "postcard": _order(hero, len(photos)),
        "banner": natural,
    }
    wanted = str(spec.data.get("design", {}).get("layout") or "auto").lower()
    engines = [wanted] if wanted in ENGINE_FUNCS else list(config.ENGINES)
    designs = []
    for engine in engines:
        try:
            design = ENGINE_FUNCS[engine](photos, orders[engine], style, card)
        except (ValueError, ZeroDivisionError):
            continue
        if len(design.slots) != len(photos):
            continue
        designs.append(_score(design, photos, card))
    designs.sort(key=lambda d: -d.score)
    if wanted in ENGINE_FUNCS:
        return designs
    return designs[: max(1, int(spec.data.get("design", {}).get("variants") or 6))]
