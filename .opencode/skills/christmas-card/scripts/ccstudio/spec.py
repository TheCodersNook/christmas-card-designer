"""cards/<name>/card.json: the one file a designer edits.

It holds the photographs, the words, the print settings and the generated
designs. Everything else in the folder is an output.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from . import config


DEFAULT_TEXT = {
    "greeting": "Merry Christmas",
    "family": "",
    "message": "",
    "signature": "",
    "year": "",
}

DEFAULT_DESIGN = {
    "style": "classic",
    "palette": "",          # empty = the style's own palette
    "size": "5x7",
    "orientation": "portrait",
    "layout": "auto",       # auto | one of config.ENGINES
    "hero": "",             # file name of the photo to feature
    "order": [],            # photo file names, front of the list first
    "variants": 6,
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

    # ---------------------------------------------------------------- loading
    @classmethod
    def load(cls, path: str | Path) -> "CardSpec":
        p = Path(path).expanduser()
        if p.is_dir():
            p = p / "card.json"
        if not p.exists():
            raise SpecError(f"no card.json at {p} (run ./ccb new <photos...> first)")
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
            "designs": [],
            "selected": 0,
            "notes": [],
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
        return self.data.setdefault("design", dict(DEFAULT_DESIGN))

    @property
    def export(self) -> dict[str, Any]:
        return self.data.setdefault("export", dict(DEFAULT_EXPORT))

    @property
    def designs(self) -> list[dict[str, Any]]:
        return self.data.setdefault("designs", [])

    @property
    def selected(self) -> int:
        try:
            return max(0, int(self.data.get("selected", 0)))
        except (TypeError, ValueError):
            return 0

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
        p = resolve(self.folder, slot_photo)
        return p

    @property
    def style(self) -> config.Style:
        return config.style(self.design.get("style"))

    @property
    def palette(self) -> config.Palette:
        return config.palette(self.design.get("palette") or self.style.palette)

    @property
    def card_inches(self) -> tuple[float, float]:
        w, h = config.size(self.design.get("size"))
        if str(self.design.get("orientation", "portrait")).lower().startswith("land"):
            w, h = h, w
        return w, h

    def current_design(self) -> dict[str, Any] | None:
        if not self.designs:
            return None
        return self.designs[max(0, min(len(self.designs) - 1, self.selected))]

    # ------------------------------------------------------------------ write
    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalise(data: dict[str, Any], path: Path) -> dict[str, Any]:
    data.setdefault("name", path.parent.name)
    photos = data.get("photos") or []
    if not isinstance(photos, list):
        raise SpecError("'photos' must be a list of file names")
    data["photos"] = [str(p) for p in photos]
    text = data.get("text") if isinstance(data.get("text"), dict) else {}
    data["text"] = {**DEFAULT_TEXT, **{k: _s(v) for k, v in text.items() if k in DEFAULT_TEXT}}
    design = data.get("design") if isinstance(data.get("design"), dict) else {}
    data["design"] = {**DEFAULT_DESIGN, **design}
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
    if not isinstance(data.get("designs"), list):
        data["designs"] = []
    data.setdefault("selected", 0)
    return data


def _s(v: Any) -> str:
    return "" if v is None else str(v).strip()


def resolve(folder: Path, item: str | Path) -> Path:
    """Photo paths are stored relative to the project folder, but absolute ones work too."""
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
