"""The composition model.

A composition is described by numbers, not by a named template: photograph
slots, text zones, ornaments and rules, all as fractions of the trim box. The
same small structures drive cards and presentation slides; ``compose`` validates
them against the studio rulebook before anything is rendered.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


def r4(v: float) -> float:
    return round(float(v), 4)


@dataclass
class Slot:
    photo: int                     # index into the project's photo list
    x: float
    y: float
    w: float
    h: float
    treatment: str = ""            # "", or one of the rulebook's treatments
    focus: tuple[float, float] | None = None   # crop focus; None = face-aware

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"photo": self.photo, "x": r4(self.x), "y": r4(self.y),
                             "w": r4(self.w), "h": r4(self.h)}
        if self.treatment:
            d["treatment"] = self.treatment
        if self.focus:
            d["focus"] = [r4(self.focus[0]), r4(self.focus[1])]
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Slot":
        focus = d.get("focus")
        return Slot(
            int(d.get("photo", 0)), float(d["x"]), float(d["y"]), float(d["w"]), float(d["h"]),
            str(d.get("treatment", "")),
            (float(focus[0]), float(focus[1])) if isinstance(focus, (list, tuple)) and len(focus) >= 2 else None,
        )


@dataclass
class Zone:
    roles: tuple[str, ...]
    x: float
    y: float
    w: float
    h: float
    panel: bool = False
    align: str = ""                # "", left, center, right
    valign: str = "center"         # top, center, bottom
    font: str = ""                 # "", heading, body, script
    scale: float = 1.0             # multiplies the rulebook's role scales
    caps: bool | None = None       # None = follow the direction
    text: str = ""                 # overrides words (captions, folios)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"roles": list(self.roles), "x": r4(self.x), "y": r4(self.y),
                             "w": r4(self.w), "h": r4(self.h), "panel": self.panel}
        for key in ("align", "font", "text"):
            if getattr(self, key):
                d[key] = getattr(self, key)
        if self.valign != "center":
            d["valign"] = self.valign
        if abs(self.scale - 1.0) > 1e-6:
            d["scale"] = round(self.scale, 3)
        if self.caps is not None:
            d["caps"] = self.caps
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Zone":
        return Zone(
            tuple(str(r) for r in d.get("roles", [])),
            float(d["x"]), float(d["y"]), float(d["w"]), float(d["h"]),
            bool(d.get("panel", False)),
            str(d.get("align", "")),
            str(d.get("valign", "center")),
            str(d.get("font", "")),
            float(d.get("scale", 1.0)),
            bool(d["caps"]) if "caps" in d else None,
            str(d.get("text", "")),
        )


@dataclass
class Design:
    engine: str = "composition"
    label: str = "Composition"
    slots: list[Slot] = field(default_factory=list)
    zones: list[Zone] = field(default_factory=list)
    order: list[int] = field(default_factory=list)
    score: float = 0.0
    notes: list[str] = field(default_factory=list)
    ornaments: list[dict[str, Any]] = field(default_factory=list)
    lines: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "engine": self.engine,
            "label": self.label,
            "score": round(self.score, 1),
            "slots": [s.to_dict() for s in self.slots],
            "zones": [z.to_dict() for z in self.zones],
            "order": list(self.order),
            "notes": list(self.notes),
            "ornaments": list(self.ornaments),
            "lines": list(self.lines),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Design":
        notes = d.get("notes") or []
        if isinstance(notes, str):
            notes = [notes]
        return Design(
            str(d.get("engine", "composition")),
            str(d.get("label") or d.get("name") or "Composition"),
            [Slot.from_dict(s) for s in d.get("slots", [])],
            [Zone.from_dict(z) for z in d.get("zones", [])],
            [int(i) for i in d.get("order", [])],
            float(d.get("score", 0.0)),
            [str(n) for n in notes],
            [dict(o) for o in d.get("ornaments", []) if isinstance(o, dict)],
            [dict(r) for r in d.get("lines", []) if isinstance(r, dict)],
        )

    @property
    def coverage(self) -> float:
        return sum(s.w * s.h for s in self.slots)


def overlaps(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """Area of the intersection of two (x, y, w, h) rectangles."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    dx = min(ax + aw, bx + bw) - max(ax, bx)
    dy = min(ay + ah, by + bh) - max(ay, by)
    return max(0.0, dx) * max(0.0, dy)
