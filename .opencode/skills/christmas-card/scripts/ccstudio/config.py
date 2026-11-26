"""The studio rulebook, loaded from studio/rules.json.

There are no presets here: no named styles, no palette catalogue, no fixed type
scale. The JSON file says what paper is available, what a palette must satisfy,
what sizes and weights type may take, which pieces of copy exist, and the limits
of every primitive. The agent writes the palette, the typography and the
composition for each card on the fly; `config` only turns the numbers into small
objects the rest of the engine can use.
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
    if not isinstance(data, dict) or "paper" not in data or "type" not in data:
        raise RulesError(f"{path} must contain 'paper', 'type', 'palette' and 'composition'")
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
PALETTE_RULES = RULES.get("palette", {})
PARTS: dict[str, str] = {
    str(key): str(value) for key, value in TYPE.get("parts", {}).items()
}
TEXT_PARTS = ("greeting", "family", "message", "signature", "year")
DECK_TEXT_PARTS = ("title", "subtitle", "greeting", "message", "signature", "year")
PALETTE_KEYS = tuple(str(v) for v in PALETTE_RULES.get(
    "keys", ["bg", "ink", "soft", "accent", "panel", "on_panel"]))
CANVAS_16X9 = (40 / 3, 7.5)


@dataclass(frozen=True)
class Palette:
    """Six colours the agent chose for this card (or that the photographs gave)."""
    bg: str
    ink: str
    soft: str
    accent: str
    panel: str
    on_panel: str
    label: str = "from your photographs"

    def colors(self) -> dict[str, str]:
        return {
            "bg": self.bg, "ink": self.ink, "soft": self.soft,
            "accent": self.accent, "panel": self.panel, "on_panel": self.on_panel,
        }

    def token(self, name: str) -> str:
        return getattr(self, name, self.ink)


def palette(data: dict[str, Any] | None, label: str = "yours") -> Palette:
    """Build a Palette from a validated six-colour mapping."""
    src = data or {}
    return Palette(
        str(src.get("bg", "#FFFFFF")), str(src.get("ink", "#111111")),
        str(src.get("soft", "#555555")), str(src.get("accent", "#111111")),
        str(src.get("panel", "#111111")), str(src.get("on_panel", "#FFFFFF")),
        label,
    )


def size(key: str | None) -> tuple[float, float]:
    return SIZES.get((key or "5x7").lower(), next(iter(SIZES.values())))


def size_label(key: str, landscape: bool = False) -> str:
    w, h = size(key)
    w, h = (h, w) if landscape else (w, h)
    return f"{w:g} x {h:g} in"


def limit(section: str, key: str, default: Any) -> Any:
    return COMPOSE.get(section, {}).get(key, default)


def type_limit(key: str, default: Any) -> Any:
    return TYPE.get(key, default)


def part_description(part: str) -> str:
    return PARTS.get(part, "")
