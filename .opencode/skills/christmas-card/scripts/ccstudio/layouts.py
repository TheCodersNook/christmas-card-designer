"""The composition model.

A composition is described by numbers, not by a named template: a background,
colour fields and shapes, photograph slots, text zones, ornaments and rules, all
as fractions of the trim box, each with a layer. The same small structures drive
cards and presentation slides; ``compose`` validates them against the studio
rulebook before anything is rendered.
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
    layer: int = 0                 # paint order; higher sits on top
    rotate: float = 0.0            # degrees, positive turns clockwise on the card
    clip: str = ""                 # "", rect, rounded, arch, circle, oval
    bleed: bool = False            # run past the trim edge into the bleed

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"photo": self.photo, "x": r4(self.x), "y": r4(self.y),
                             "w": r4(self.w), "h": r4(self.h)}
        if self.treatment:
            d["treatment"] = self.treatment
        if self.focus:
            d["focus"] = [r4(self.focus[0]), r4(self.focus[1])]
        if self.layer:
            d["layer"] = self.layer
        if abs(self.rotate) > 1e-6:
            d["rotate"] = round(self.rotate, 2)
        if self.clip:
            d["clip"] = self.clip
        if self.bleed:
            d["bleed"] = True
        return d

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Slot":
        focus = d.get("focus")
        return Slot(
            int(d.get("photo", 0)), float(d["x"]), float(d["y"]), float(d["w"]), float(d["h"]),
            str(d.get("treatment", "")),
            (float(focus[0]), float(focus[1])) if isinstance(focus, (list, tuple)) and len(focus) >= 2 else None,
            int(d.get("layer", 0) or 0),
            float(d.get("rotate", 0.0) or 0.0),
            str(d.get("clip", "") or ""),
            bool(d.get("bleed", False)),
        )


@dataclass
class Zone:
    """One piece of copy, set exactly as the composition asks.

    There is no named type scale: the zone carries its own size (a fraction of
    the page's short side), typeface, weight, tracking and leading.
    """
    word: str                      # which copy: greeting, family, message, caption, ...
    x: float
    y: float
    w: float
    h: float
    size: float = 0.0             # fraction of the short side (0 = not set yet)
    font: str = "lato"            # a typeface installed in assets/fonts
    weight: int = 400
    italic: bool = False
    tracking: float = 0.0          # em
    leading: float = 1.2           # multiple of the size
    caps: bool = False
    align: str = "left"
    valign: str = "center"
    panel: str = ""                # "", "panel" or any palette token
    text: str = ""                 # overrides the card's words (captions, folios)
    layer: int = 0
    rotate: float = 0.0
    color: str = ""                # "", or a palette token / hex
    over_photo: bool = False       # this text is meant to sit on a photograph
    panel_opacity: float = 1.0
    panel_pad: float = 0.0         # fraction of the zone's short side

    @property
    def roles(self) -> tuple[str, ...]:
        """Compatibility with the reporter: a zone carries exactly one piece."""
        return (self.word,)

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {"word": self.word, "x": r4(self.x), "y": r4(self.y),
                             "w": r4(self.w), "h": r4(self.h),
                             "size": round(self.size, 4), "font": self.font}
        if self.weight != 400:
            d["weight"] = int(self.weight)
        if self.italic:
            d["italic"] = True
        if abs(self.tracking) > 1e-6:
            d["tracking"] = round(self.tracking, 4)
        if abs(self.leading - 1.2) > 1e-6:
            d["leading"] = round(self.leading, 3)
        if self.caps:
            d["caps"] = True
        if self.align != "left":
            d["align"] = self.align
        if self.valign != "center":
            d["valign"] = self.valign
        if self.panel:
            d["panel"] = self.panel
        if self.text:
            d["text"] = self.text
        if self.layer:
            d["layer"] = self.layer
        if abs(self.rotate) > 1e-6:
            d["rotate"] = round(self.rotate, 2)
        if self.color:
            d["color"] = self.color
        if self.over_photo:
            d["over_photo"] = True
        if self.panel_opacity < 0.999:
            d["panel_opacity"] = round(self.panel_opacity, 3)
        if self.panel_pad:
            d["panel_pad"] = round(self.panel_pad, 4)
        return d

    @staticmethod
    def _panel(value: Any) -> str:
        if value is True:
            return "panel"
        if value in (False, None, ""):
            return ""
        return str(value)

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Zone":
        word = d.get("word")
        if word is None:
            legacy = d.get("roles") or []
            word = legacy[0] if legacy else ""
        return Zone(
            str(word),
            float(d["x"]), float(d["y"]), float(d["w"]), float(d["h"]),
            float(d.get("size", 0.0) or 0.0),
            str(d.get("font") or "lato"),
            int(d.get("weight", 400) or 400),
            bool(d.get("italic", False)),
            float(d.get("tracking", 0.0) or 0.0),
            float(d.get("leading", 1.2) or 1.2),
            bool(d.get("caps", False)),
            str(d.get("align", "left")),
            str(d.get("valign", "center")),
            Zone._panel(d.get("panel", False)),
            str(d.get("text", "")),
            int(d.get("layer", 0) or 0),
            float(d.get("rotate", 0.0) or 0.0),
            str(d.get("color", "") or ""),
            bool(d.get("over_photo", False)),
            float(d.get("panel_opacity", 1.0) or 1.0),
            float(d.get("panel_pad", 0.0) or 0.0),
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
    background: dict[str, Any] = field(default_factory=dict)
    shapes: list[dict[str, Any]] = field(default_factory=list)
    chrome: dict[str, Any] = field(default_factory=dict)

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
            "background": dict(self.background),
            "shapes": list(self.shapes),
            "chrome": dict(self.chrome),
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Design":
        notes = d.get("notes") or []
        if isinstance(notes, str):
            notes = [notes]
        background = d.get("background")
        chrome = d.get("chrome")
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
            dict(background) if isinstance(background, dict) else {},
            [dict(s) for s in d.get("shapes", []) if isinstance(s, dict)],
            dict(chrome) if isinstance(chrome, dict) else {},
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
