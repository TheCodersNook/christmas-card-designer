"""cards/<name>/card.json: photographs, words, the card's own palette and pages.

There is no direction and no preset. A card holds the palette the agent chose
(or one sampled from the photographs), plus free compositions the agent wrote
against the rulebook; ``front`` and ``back`` are compositions with a side.
``selected`` picks which front is rendered.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import colour, config, layouts, photos as photo_mod


DEFAULT_TEXT = {
    "greeting": "Merry Christmas",
    "family": "",
    "message": "",
    "signature": "",
    "year": "",
}

DEFAULT_DESIGN = {
    "size": "5x7",
    "orientation": "portrait",
    # system.palette is written by the agent; left empty, the photographs give
    # the colours and the brief prints them so they can be replaced.
    "system": {},
    "compositions": [],
    "selected": 0,
}

DEFAULT_EXPORT = {
    "format": "pdf",
    "dpi": 300,
    "bleed": True,
    "crop_marks": True,
    "back": True,
    "jpeg_quality": 95,
}


class SpecError(ValueError):
    pass


class CardSpec:
    """A card.json with defaults filled in and paths resolved."""

    def __init__(self, path: Path, data: dict[str, Any]):
        self.path = Path(path).resolve()
        self.data = data
        self._palette: config.Palette | None = None

    # ---------------------------------------------------------------- loading
    @classmethod
    def load(cls, path: str | Path) -> "CardSpec":
        p = Path(path).expanduser()
        if p.is_dir():
            p = p / "card.json"
        if not p.exists():
            raise SpecError(f"no card.json at {p} (run ./ccb add <photos...> first)")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SpecError(f"{p} is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise SpecError(f"{p} must contain a JSON object")
        return cls(p, normalise(data, p))

    @classmethod
    def create(cls, folder: Path, name: str, photos: list[str], **design) -> "CardSpec":
        data = {
            "name": name,
            "photos": photos,
            "text": dict(DEFAULT_TEXT),
            "design": {**DEFAULT_DESIGN, **{k: v for k, v in design.items() if v not in (None, "")}},
            "export": dict(DEFAULT_EXPORT),
        }
        folder.mkdir(parents=True, exist_ok=True)
        spec = cls(folder / "card.json", normalise(data, folder / "card.json"))
        spec.save()
        return spec

    # ----------------------------------------------------------------- access
    @property
    def folder(self) -> Path:
        return self.path.parent

    @property
    def name(self) -> str:
        return str(self.data.get("name") or self.folder.name)

    @property
    def text(self) -> dict[str, str]:
        return self.data.setdefault("text", dict(DEFAULT_TEXT))

    @property
    def design(self) -> dict[str, Any]:
        if not isinstance(self.data.get("design"), dict):
            self.data["design"] = dict(DEFAULT_DESIGN)
        return self.data["design"]

    @property
    def export(self) -> dict[str, Any]:
        if not isinstance(self.data.get("export"), dict):
            self.data["export"] = dict(DEFAULT_EXPORT)
        return self.data["export"]

    @property
    def compositions(self) -> list[dict[str, Any]]:
        return self.design.setdefault("compositions", [])

    @property
    def selected(self) -> int:
        try:
            return max(0, int(self.design.get("selected", 0)))
        except (TypeError, ValueError):
            return 0

    @property
    def front_compositions(self) -> list[dict[str, Any]]:
        return [c for c in self.compositions if str(c.get("side", "front")) == "front"]

    def front(self) -> dict[str, Any] | None:
        fronts = self.front_compositions
        if not fronts:
            return None
        return fronts[max(0, min(len(fronts) - 1, self.selected))]

    def back(self) -> dict[str, Any] | None:
        for comp in self.compositions:
            if str(comp.get("side", "front")) == "back":
                return comp
        return None

    def front_design(self) -> layouts.Design | None:
        comp = self.front()
        return _design(comp) if comp else None

    def back_design(self) -> layouts.Design | None:
        comp = self.back()
        return _design(comp) if comp else None

    @property
    def photo_paths(self) -> list[Path]:
        out = []
        for item in self.data.get("photos", []):
            out.append(resolve(self.folder, item))
        return out

    def photo_for(self, slot_photo: str | int) -> Path:
        photos = self.photo_paths
        if isinstance(slot_photo, int):
            return photos[max(0, min(len(photos) - 1, slot_photo))]
        return resolve(self.folder, slot_photo)

    @property
    def system(self) -> dict[str, Any]:
        if not isinstance(self.design.get("system"), dict):
            self.design["system"] = {}
        return self.design["system"]

    @property
    def palette(self) -> config.Palette:
        """The card's own six colours, or a palette sampled from photograph 0."""
        if self._palette is not None:
            return self._palette
        data = self.system.get("palette")
        if isinstance(data, dict) and all(colour.is_hex(str(data.get(k, ""))) for k in config.PALETTE_KEYS):
            self._palette = config.palette(data, "yours")
        else:
            self._palette = self._sampled_palette()
        return self._palette

    def _sampled_palette(self) -> config.Palette:
        for path in self.photo_paths:
            try:
                photo = photo_mod.load(path)
            except photo_mod.PhotoError:
                continue
            return config.palette(photo_mod.palette_from(photo), "sampled from " + path.name)
        return config.palette(None, "none yet")

    def set_system(self, system: dict[str, Any]) -> None:
        self.design["system"] = system
        self._palette = None

    @property
    def card_inches(self) -> tuple[float, float]:
        w, h = config.size(self.design.get("size"))
        if str(self.design.get("orientation", "portrait")).lower().startswith("land"):
            w, h = h, w
        return w, h

    # ------------------------------------------------------------------ write
    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _design(comp: dict[str, Any]) -> layouts.Design:
    design = layouts.Design.from_dict(comp)
    design.label = str(comp.get("name") or design.label)
    return design


def normalise(data: dict[str, Any], path: Path) -> dict[str, Any]:
    data.setdefault("name", path.parent.name)
    photos = data.get("photos") or []
    if not isinstance(photos, list):
        raise SpecError("'photos' must be a list of file names")
    data["photos"] = [str(p) for p in photos]
    text = data.get("text") if isinstance(data.get("text"), dict) else {}
    data["text"] = {**DEFAULT_TEXT, **{k: _s(v) for k, v in text.items() if k in DEFAULT_TEXT}}

    design = data.get("design") if isinstance(data.get("design"), dict) else {}
    design = {**DEFAULT_DESIGN, **design}
    # A direction or a named palette was a preset; neither exists any more. The
    # colours now come from the card's own system (or from the photographs).
    design.pop("direction", None)
    design.pop("palette", None)
    if not isinstance(design.get("system"), dict):
        design["system"] = {}
    # migrate a v1 card: top-level designs -> compositions
    if isinstance(data.get("designs"), list) and not design.get("compositions"):
        migrated = []
        for i, old in enumerate(data["designs"]):
            if not isinstance(old, dict):
                continue
            comp = {**old, "name": old.get("label") or f"Composition {i + 1}", "side": "front"}
            comp.pop("engine", None)
            migrated.append(comp)
        design["compositions"] = migrated
    data.pop("designs", None)
    data["design"] = design
    if not isinstance(design.get("compositions"), list):
        design["compositions"] = []
    try:
        design["selected"] = max(0, int(design.get("selected", 0)))
    except (TypeError, ValueError):
        design["selected"] = 0

    export = data.get("export") if isinstance(data.get("export"), dict) else {}
    export = {**DEFAULT_EXPORT, **export}
    try:
        export["dpi"] = max(config.MIN_DPI, min(config.MAX_DPI, int(export["dpi"])))
    except (TypeError, ValueError):
        export["dpi"] = 300
    export["format"] = str(export.get("format", "pdf")).lower()
    if export["format"] not in ("pdf", "png", "jpeg", "jpg"):
        export["format"] = "pdf"
    data["export"] = export
    return data


def _s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def resolve(folder: Path, item: str | Path) -> Path:
    """Photo paths are stored relative to the card folder, but absolute ones work too."""
    p = Path(str(item)).expanduser()
    if p.is_absolute():
        return p
    return (folder / p).resolve()


def safe_name(text: str) -> str:
    out = "".join(c if (c.isalnum() or c in "-_") else "-" for c in text.strip().lower())
    while "--" in out:
        out = out.replace("--", "-")
    return out.strip("-_") or "card"


def unique_card_dir(root: Path, name: str) -> Path:
    base = safe_name(name)
    candidate = root / base
    n = 2
    while candidate.exists():
        candidate = root / f"{base}-{n}"
        n += 1
    return candidate
