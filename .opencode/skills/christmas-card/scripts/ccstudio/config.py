"""Paper, palettes and the eight card styles.

Every number here is physical: sizes are inches, margins are a fraction of the
card's short side, type sizes are a fraction of the short side at export
resolution. That is why a 5x7 and a 5x5 card look like the same designer made
them.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def project_root() -> Path:
    """The studio folder (set by ./ccb; otherwise the current directory)."""
    env = os.environ.get("CCSTUDIO_HOME")
    return Path(env).expanduser().resolve() if env else Path.cwd().resolve()


ROOT = project_root()
FONT_DIR = ROOT / "assets" / "fonts"
SKILL_DIR = Path(__file__).resolve().parents[2]   # .opencode/skills/christmas-card
CARDS_DIR = ROOT / "cards"

BLEED_IN = 0.125
MIN_DPI, MAX_DPI = 96, 1200

# Trim sizes in inches, portrait. Landscape swaps them.
SIZES: dict[str, tuple[float, float]] = {
    "5x7": (5.0, 7.0),
    "4x6": (4.0, 6.0),
    "5x5": (5.0, 5.0),
    "a6": (4.13, 5.83),
    "a2": (4.25, 5.5),      # A2 invitation
}


@dataclass(frozen=True)
class Palette:
    key: str
    label: str
    bg: str          # card background
    ink: str         # primary text
    soft: str        # secondary text
    accent: str      # decoration / rules
    panel: str       # text panel or photo frame colour
    on_panel: str    # text on the panel

    def colors(self) -> dict[str, str]:
        return {
            "bg": self.bg, "ink": self.ink, "soft": self.soft,
            "accent": self.accent, "panel": self.panel, "on_panel": self.on_panel,
        }


PALETTES: dict[str, Palette] = {
    p.key: p
    for p in (
        Palette("evergreen", "Evergreen", "#F6F1E4", "#1E3A2B", "#4C6152", "#9C1B23", "#1E3A2B", "#F6F1E4"),
        Palette("cranberry", "Cranberry", "#FBF4EF", "#4A1D24", "#7C5257", "#A62B33", "#4A1D24", "#FBF4EF"),
        Palette("midnight", "Midnight", "#0E1B2A", "#EAF0F6", "#AFC0D0", "#C9A227", "#16273A", "#EAF0F6"),
        Palette("nordic", "Nordic", "#EEF1F0", "#25322F", "#5C6D68", "#7E9B91", "#25322F", "#EEF1F0"),
        Palette("brass", "Brass", "#F7F3EC", "#2B2A26", "#6B665C", "#B08D4F", "#2B2A26", "#F7F3EC"),
        Palette("peppermint", "Peppermint", "#FAF7F2", "#22313A", "#5B6E78", "#C0392B", "#22313A", "#FAF7F2"),
    )
}


@dataclass(frozen=True)
class Style:
    key: str
    label: str
    blurb: str
    palette: str
    heading: str          # font family key
    body: str
    script: str
    greeting_font: str    # heading | body | script
    name_font: str        # heading | body | script
    caps: bool            # headings in capitals
    weight: int
    tracking: float       # em
    align: str            # center | left
    margin: float         # fraction of the short side
    decoration: str       # holly | snow | stars | confetti | none
    density: float
    border: str           # double | frame | rule | postcard | none
    photo_frame: str      # border | shadow | tilt | plain
    radius: float         # photo corner radius, fraction of the short side
    texture: bool


STYLES: dict[str, Style] = {
    s.key: s
    for s in (
        Style("classic", "Classic Christmas", "Cream stock, deep green and holly; the card most families picture.",
              "evergreen", "playfair", "lato", "greatvibes", "heading", "heading",
              False, 700, 0.02, "center", 0.07, "holly", 0.5, "double", "border", 0.0, True),
        Style("modern", "Modern Minimalist", "Lots of air, one small rule, tiny stars and left-aligned type.",
              "nordic", "montserrat", "lato", "greatvibes", "heading", "body",
              True, 500, 0.18, "left", 0.085, "stars", 0.18, "rule", "plain", 0.012, False),
        Style("traditional", "Traditional Holiday", "Deep cranberry, capitals, snow falling behind a framed grid.",
              "cranberry", "cormorant", "lato", "greatvibes", "heading", "script",
              True, 700, 0.12, "center", 0.065, "snow", 0.7, "frame", "border", 0.0, True),
        Style("editorial", "Luxury Editorial", "A magazine spread: wide margins, brass rules, photographs as plates.",
              "brass", "playfair", "lato", "greatvibes", "heading", "body",
              True, 500, 0.14, "left", 0.085, "none", 0.0, "rule", "plain", 0.0, False),
        Style("nordic", "Scandinavian", "Pale grey-green, small photographs, a scatter of quiet stars.",
              "nordic", "montserrat", "cormorant", "greatvibes", "heading", "body",
              True, 500, 0.22, "center", 0.075, "stars", 0.4, "none", "plain", 0.008, False),
        Style("vintage", "Vintage Christmas", "Warm paper, a postcard border, tilted frames and holly sprigs.",
              "cranberry", "cormorant", "lato", "greatvibes", "heading", "script",
              False, 600, 0.06, "center", 0.07, "holly", 0.45, "postcard", "tilt", 0.004, True),
        Style("joyful", "Playful Festive", "Bright red, script lettering, confetti and shadowed snapshots.",
              "peppermint", "playfair", "lato", "greatvibes", "script", "body",
              False, 700, 0.0, "center", 0.07, "confetti", 0.8, "none", "shadow", 0.02, False),
        Style("gallery", "Photo-First", "Nearly all photographs, a thin rule and a small line of type.",
              "evergreen", "lato", "lato", "greatvibes", "heading", "heading",
              True, 700, 0.24, "center", 0.05, "none", 0.0, "rule", "shadow", 0.006, False),
    )
}

ENGINES = ("grid", "hero", "mosaic", "editorial", "postcard", "banner")

ENGINE_LABELS = {
    "grid": "Uniform grid",
    "hero": "Hero and strip",
    "mosaic": "Proportional mosaic",
    "editorial": "Editorial column",
    "postcard": "Postcard stack",
    "banner": "Panorama banner",
}

TEXT_ROLES = ("greeting", "family", "message", "signature", "year")


def style(key: str | None) -> Style:
    return STYLES.get((key or "classic").lower(), STYLES["classic"])


def palette(style_or_key: Style | str | None) -> Palette:
    key = style_or_key.palette if isinstance(style_or_key, Style) else (style_or_key or "evergreen")
    return PALETTES.get(str(key).lower(), PALETTES["evergreen"])


def size(key: str | None) -> tuple[float, float]:
    return SIZES.get((key or "5x7").lower(), SIZES["5x7"])


def size_label(key: str, landscape: bool = False) -> str:
    w, h = size(key)
    w, h = (h, w) if landscape else (w, h)
    return f"{w:g} x {h:g} in"
