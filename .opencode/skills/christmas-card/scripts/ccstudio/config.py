"""The studio rulebook, loaded from studio/rules.json.

Nothing about paper, palette, type or a direction is hardcoded here any more.
The JSON file is the source of truth: edit it (and studio/RULES.md explains every
field), restart the command, and the whole engine follows. `config` only turns
that file into small immutable objects the renderer can use.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def project_root() -> Path:
    """The studio folder (set by ./ccb; otherwise the current directory)."""
    env = os.environ.get("CCSTUDIO_HOME")
    return Path(env).expanduser().resolve() if env else Path.cwd().resolve()


ROOT = project_root()
FONT_DIR = ROOT / "assets" / "fonts"
MODEL_DIR = ROOT / "assets" / "models"
SKILL_DIR = Path(__file__).resolve().parents[2]   # .opencode/skills/christmas-card
CARDS_DIR = ROOT / "cards"
DECKS_DIR = ROOT / "decks"
RULES_PATH = ROOT / "studio" / "rules.json"
SEE_DIRNAME = "see"


class RulesError(RuntimeError):
    pass


def _read_rules(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise RulesError(
            f"the rulebook is missing at {path}\n"
            "It ships in studio/rules.json; restore it or point CCSTUDIO_HOME at the project."
        )
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RulesError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict) or "paper" not in data or "directions" not in data:
        raise RulesError(f"{path} must contain 'paper', 'composition', 'type', 'palettes' and 'directions'")
    return data


RULES = _read_rules(RULES_PATH)

BLEED_IN = float(RULES["paper"].get("bleed_in", 0.125))
MIN_DPI = int(RULES["paper"].get("min_dpi", 96))
MAX_DPI = int(RULES["paper"].get("max_dpi", 1200))
SIZES: dict[str, tuple[float, float]] = {
    str(key): (float(value[0]), float(value[1]))
    for key, value in RULES["paper"].get("sizes", {}).items()
}
if not SIZES:
    SIZES = {"5x7": (5.0, 7.0)}

COMPOSE = RULES.get("composition", {})
TYPE = RULES.get("type", {})
ROLE_RULES: dict[str, dict[str, Any]] = TYPE.get("roles", {})
ROLE_SIZES = {role: float(spec.get("scale", 0.03)) for role, spec in ROLE_RULES.items()}
TEXT_ROLES = ("greeting", "family", "message", "signature", "year")
DECK_TEXT_ROLES = ("title", "subtitle", "greeting", "message", "signature", "year")
CANVAS_16X9 = (40 / 3, 7.5)


@dataclass(frozen=True)
class Palette:
    key: str
    label: str
    bg: str
    ink: str
    soft: str
    accent: str
    panel: str
    on_panel: str

    def colors(self) -> dict[str, str]:
        return {
            "bg": self.bg, "ink": self.ink, "soft": self.soft,
            "accent": self.accent, "panel": self.panel, "on_panel": self.on_panel,
        }

    def token(self, name: str) -> str:
        return getattr(self, name, self.ink)


PALETTES: dict[str, Palette] = {
    str(key): Palette(str(key), str(value.get("label", key)), str(value["bg"]), str(value["ink"]),
                      str(value["soft"]), str(value["accent"]), str(value["panel"]),
                      str(value["on_panel"]))
    for key, value in RULES.get("palettes", {}).items()
}


@dataclass(frozen=True)
class Style:
    key: str
    label: str
    blurb: str
    palette: str
    heading: str
    body: str
    script: str
    greeting_font: str
    name_font: str
    caps: bool
    weight: int
    tracking: float
    align: str
    margin: float
    decoration: str
    density: float
    border: str
    photo_frame: str
    radius: float
    texture: bool
    guidance: str = ""


STYLES: dict[str, Style] = {
    str(key): Style(
        key=str(key),
        label=str(value.get("label", key)),
        blurb=str(value.get("blurb", "")),
        palette=str(value.get("palette", "evergreen")),
        heading=str(value.get("heading", "playfair")),
        body=str(value.get("body", "lato")),
        script=str(value.get("script", "greatvibes")),
        greeting_font=str(value.get("greeting_font", "heading")),
        name_font=str(value.get("name_font", "heading")),
        caps=bool(value.get("caps", False)),
        weight=int(value.get("weight", 500)),
        tracking=float(value.get("tracking", 0.0)),
        align=str(value.get("align", "center")),
        margin=float(value.get("margin", 0.07)),
        decoration=str(value.get("decoration", "none")),
        density=float(value.get("density", 0.0)),
        border=str(value.get("border", "none")),
        photo_frame=str(value.get("photo_frame", "plain")),
        radius=float(value.get("radius", 0.0)),
        texture=bool(value.get("texture", False)),
        guidance=str(value.get("guidance", "")),
    )
    for key, value in RULES.get("directions", {}).items()
}
if not STYLES:
    raise RulesError("studio/rules.json has no directions")
DIRECTIONS = STYLES


def style(key: str | None) -> Style:
    if key and str(key).lower() in STYLES:
        return STYLES[str(key).lower()]
    return next(iter(STYLES.values()))


def palette(style_or_key: Style | str | None) -> Palette:
    key = style_or_key.palette if isinstance(style_or_key, Style) else (style_or_key or "evergreen")
    return PALETTES.get(str(key).lower(), next(iter(PALETTES.values())))


def size(key: str | None) -> tuple[float, float]:
    return SIZES.get((key or "5x7").lower(), next(iter(SIZES.values())))


def size_label(key: str, landscape: bool = False) -> str:
    w, h = size(key)
    w, h = (h, w) if landscape else (w, h)
    return f"{w:g} x {h:g} in"


def role_rules(role: str) -> dict[str, Any]:
    return ROLE_RULES.get(role, {"scale": 0.03, "max_lines": 4, "spacing": 1.4})


def limit(section: str, key: str, default: Any) -> Any:
    return COMPOSE.get(section, {}).get(key, default)
