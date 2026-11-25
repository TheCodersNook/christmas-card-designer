"""decks/<name>/deck.json: a Christmas presentation made from the same photographs.

A deck is not a card. A card is one printed object; a deck is a sequence that
somebody stands in front of: a cover, a statement, a few photographs held large
enough to be the point, a grid for the rest, and a closing. It is 16:9, there is
no bleed and no crop marks, and every slide is composed with the same measured
type and the same decoration as the cards.

Nothing here is generated or invented: the words come from deck.json and the
photographs are cover-cropped in memory, never altered.
"""
from __future__ import annotations

import io
import json
import math
import zlib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

from . import config, decorate, layouts, photos as photo_mod, render, typefit
from .spec import safe_name

# 16:9, the shape of every projector and every screen.
SLIDE_W_IN = 40 / 3          # 13.333 in = 960 pt
SLIDE_H_IN = 7.5             # 540 pt
SLIDE_ASPECT = SLIDE_W_IN / SLIDE_H_IN

DECK_TEXT = {
    "title": "",
    "subtitle": "",
    "greeting": "",
    "message": "",
    "signature": "",
    "year": "",
}

DEFAULT_DESIGN = {
    "style": "editorial",
    "palette": "",
    "hero": "",
}

DEFAULT_EXPORT = {
    "format": "pdf",
    "dpi": 150,
    "jpeg_quality": 92,
    "png_slides": False,
}

# Sizes are fractions of the slide's short side, like the card's type.
DECK_SIZES = {
    "title": 0.110,
    "statement": 0.064,
    "subtitle": 0.034,
    "eyebrow": 0.019,
    "caption": 0.024,
    "signature": 0.042,
    "message": 0.026,
    "year": 0.017,
    "numeral": 0.095,
    "folio": 0.017,
}

ROLE_LINES = {
    "title": 3, "statement": 4, "subtitle": 2, "eyebrow": 1, "caption": 3,
    "signature": 2, "message": 3, "year": 1, "numeral": 1, "folio": 1,
}

ROLE_WEIGHT = {"title": "heading", "statement": "heading", "numeral": "heading",
               "signature": "heading", "eyebrow": "body", "folio": "body"}

# Some slide roles read a different field of deck.json.
ROLE_TEXT_KEY = {"eyebrow": "greeting", "statement": "message", "caption": "caption"}

DECK_KIND_LABELS = {
    "cover": "Cover",
    "statement": "Statement",
    "hero": "Photograph",
    "grid": "Gallery",
    "closing": "Closing",
}


class DeckError(ValueError):
    pass


# --------------------------------------------------------------------- the plan
@dataclass
class DeckZone:
    roles: tuple[str, ...]
    x: float
    y: float
    w: float
    h: float
    text: str = ""
    align: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"roles": list(self.roles), "x": r4(self.x), "y": r4(self.y), "w": r4(self.w),
                "h": r4(self.h), "text": self.text, "align": self.align}

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "DeckZone":
        return DeckZone(tuple(d.get("roles", [])), float(d["x"]), float(d["y"]), float(d["w"]),
                        float(d["h"]), str(d.get("text") or ""), str(d.get("align") or ""))


@dataclass
class Slide:
    kind: str
    label: str
    slots: list[layouts.Slot] = field(default_factory=list)
    zones: list[DeckZone] = field(default_factory=list)
    photos: list[int] = field(default_factory=list)
    caption: str = ""
    numeral: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "label": self.label,
            "photos": list(self.photos),
            "caption": self.caption,
            "numeral": self.numeral,
            "slots": [s.to_dict() for s in self.slots],
            "zones": [z.to_dict() for z in self.zones],
        }

    @staticmethod
    def from_dict(d: dict[str, Any]) -> "Slide":
        return Slide(
            str(d.get("kind", "grid")),
            str(d.get("label", "Slide")),
            [layouts.Slot.from_dict(s) for s in d.get("slots", [])],
            [DeckZone.from_dict(z) for z in d.get("zones", [])],
            [int(i) for i in d.get("photos", [])],
            str(d.get("caption") or ""),
            str(d.get("numeral") or ""),
        )


def r4(value: float) -> float:
    return round(float(value), 4)


# ----------------------------------------------------------------- the deck.json
class DeckSpec:
    def __init__(self, path: Path, data: dict[str, Any]):
        self.path = Path(path).resolve()
        self.data = data

    @classmethod
    def load(cls, path: str | Path) -> "DeckSpec":
        p = Path(path).expanduser()
        if p.is_dir():
            p = p / "deck.json"
        if not p.exists():
            raise DeckError(f"no deck.json at {p} (run ./ccb deck new <photographs> first)")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DeckError(f"{p} is not valid JSON: {exc}") from exc
        if not isinstance(data, dict):
            raise DeckError(f"{p} must contain a JSON object")
        return cls(p, _normalise(data, p))

    @classmethod
    def create(cls, folder: Path, name: str, photos: list[str], **design) -> "DeckSpec":
        data = {
            "name": name,
            "photos": photos,
            "text": dict(DECK_TEXT),
            "captions": {},
            "design": {**DEFAULT_DESIGN, **{k: v for k, v in design.items() if v not in (None, "")}},
            "export": dict(DEFAULT_EXPORT),
            "slides": [],
            "notes": [],
        }
        folder.mkdir(parents=True, exist_ok=True)
        spec = cls(folder / "deck.json", _normalise(data, folder / "deck.json"))
        spec.save()
        return spec

    @property
    def folder(self) -> Path:
        return self.path.parent

    @property
    def name(self) -> str:
        return str(self.data.get("name") or self.folder.name)

    @property
    def text(self) -> dict[str, str]:
        return self.data.setdefault("text", dict(DECK_TEXT))

    @property
    def captions(self) -> dict[str, str]:
        return self.data.setdefault("captions", {})

    @property
    def design(self) -> dict[str, Any]:
        return self.data.setdefault("design", dict(DEFAULT_DESIGN))

    @property
    def export(self) -> dict[str, Any]:
        return self.data.setdefault("export", dict(DEFAULT_EXPORT))

    @property
    def slides(self) -> list[dict[str, Any]]:
        return self.data.setdefault("slides", [])

    @property
    def style(self) -> config.Style:
        return config.style(self.design.get("style"))

    @property
    def palette(self) -> config.Palette:
        return config.palette(self.design.get("palette") or self.style.palette)

    @property
    def photo_paths(self) -> list[Path]:
        out = []
        for item in self.data.get("photos", []):
            item_path = Path(str(item)).expanduser()
            out.append(item_path if item_path.is_absolute() else (self.folder / item_path).resolve())
        return out

    def caption_for(self, path: Path) -> str:
        for key in (path.name, path.stem):
            value = self.captions.get(key)
            if value:
                return typefit.clean(str(value))
        return ""

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _normalise(data: dict[str, Any], path: Path) -> dict[str, Any]:
    data.setdefault("name", path.parent.name)
    photos = data.get("photos") or []
    if not isinstance(photos, list):
        raise DeckError("'photos' must be a list of file names")
    data["photos"] = [str(p) for p in photos]
    text = data.get("text") if isinstance(data.get("text"), dict) else {}
    data["text"] = {**DECK_TEXT, **{k: ("" if v is None else str(v).strip()) for k, v in text.items() if k in DECK_TEXT}}
    captions = data.get("captions") if isinstance(data.get("captions"), dict) else {}
    data["captions"] = {str(k): str(v) for k, v in captions.items()}
    design = data.get("design") if isinstance(data.get("design"), dict) else {}
    data["design"] = {**DEFAULT_DESIGN, **design}
    export = data.get("export") if isinstance(data.get("export"), dict) else {}
    export = {**DEFAULT_EXPORT, **export}
    try:
        export["dpi"] = max(config.MIN_DPI, min(config.MAX_DPI, int(export["dpi"])))
    except (TypeError, ValueError):
        export["dpi"] = 150
    data["export"] = export
    if not isinstance(data.get("slides"), list):
        data["slides"] = []
    return data


def unique_deck_dir(root: Path, name: str) -> Path:
    base = safe_name(name)
    candidate = root / base
    n = 2
    while candidate.exists():
        candidate = root / f"{base}-{n}"
        n += 1
    return candidate


# ------------------------------------------------------------------- the words
def resolved_words(spec: DeckSpec) -> dict[str, str]:
    """The cover must never say the same thing twice."""
    text = spec.text
    title = typefit.clean(text.get("title", ""))
    greeting = typefit.clean(text.get("greeting", ""))
    subtitle = typefit.clean(text.get("subtitle", ""))
    year = typefit.clean(text.get("year", ""))
    if not title:
        title, greeting = greeting, ""
    if subtitle and year and subtitle.lower() == year.lower():
        year = ""
    return {
        "title": title,
        "eyebrow": greeting,
        "subtitle": subtitle or year,
        # The cover shows the year only when it is not already the subtitle.
        "cover_year": year if subtitle else "",
        "statement": typefit.clean(text.get("message", "")),
        "message": typefit.clean(text.get("message", "")),
        "signature": typefit.clean(text.get("signature", "")),
        "year": year,
    }


# -------------------------------------------------------------------- planning
def _hero_index(spec: DeckSpec, photos: list[photo_mod.Photo]) -> int:
    name = str(spec.design.get("hero") or "")
    if name:
        for i, photo in enumerate(photos):
            if photo.path.name == name or photo.path.name.endswith(name):
                return i
    return max(range(len(photos)), key=lambda i: (photos[i].interest, photos[i].megapixels))


def _chunks(items: list[int], size: int = 6) -> list[list[int]]:
    if not items:
        return []
    if len(items) <= size:
        return [items]
    groups = math.ceil(len(items) / size)
    per = math.ceil(len(items) / groups)
    return [items[i:i + per] for i in range(0, len(items), per)]


def _cover(spec: DeckSpec, words: dict[str, str], photo: int) -> Slide:
    zones = [
        DeckZone(("eyebrow",), 0.075, 0.135, 0.395, 0.045, text=words["eyebrow"], align="left"),
        DeckZone(("title",), 0.075, 0.195, 0.395, 0.390, text=words["title"], align="left"),
        DeckZone(("subtitle",), 0.075, 0.615, 0.395, 0.100, text=words["subtitle"], align="left"),
        DeckZone(("year",), 0.075, 0.835, 0.395, 0.035, text=words["cover_year"], align="left"),
    ]
    return Slide("cover", "Cover", [layouts.Slot(photo, 0.545, 0.0, 0.455, 1.0)], zones, [photo])


def _statement(spec: DeckSpec, words: dict[str, str]) -> Slide:
    zones = [
        DeckZone(("eyebrow",), 0.14, 0.145, 0.72, 0.045, text=words["eyebrow"], align="center"),
        DeckZone(("statement",), 0.145, 0.225, 0.71, 0.450, text=words["statement"], align="center"),
        DeckZone(("year",), 0.14, 0.805, 0.72, 0.040, text=words["year"], align="center"),
    ]
    return Slide("statement", "Statement", [], zones, [])


def _hero(spec: DeckSpec, words: dict[str, str], photo: int, number: int) -> Slide:
    caption = spec.caption_for(spec.photo_paths[photo])
    numeral = f"{number:02d}"
    zones = [
        DeckZone(("numeral",), 0.075, 0.115, 0.300, 0.150, text=numeral, align="left"),
        DeckZone(("caption",), 0.075, 0.330, 0.335, 0.330, text=caption, align="left"),
        DeckZone(("eyebrow",), 0.075, 0.720, 0.335, 0.045, text=words["eyebrow"], align="left"),
        DeckZone(("year",), 0.075, 0.795, 0.335, 0.035, text=words["year"], align="left"),
    ]
    return Slide("hero", f"Photograph {number:02d}", [layouts.Slot(photo, 0.475, 0.0, 0.525, 1.0)],
                 zones, [photo], caption=caption, numeral=numeral)


def _grid_rects(area: tuple[float, float, float, float], count: int) -> list[tuple[float, float, float, float]]:
    x, y, w, h = area
    gap = 0.016
    if count <= 2:
        cols = max(1, count)
    elif count == 3:
        cols = 3
    else:
        cols = 2 if count == 4 else 3
    rows = math.ceil(count / cols)
    cell_w = (w - gap * (cols - 1)) / cols
    cell_h = (h - gap * (rows - 1)) / rows
    out = []
    for r in range(rows):
        in_row = min(cols, count - r * cols)
        row_w = (w - gap * (in_row - 1)) / in_row if in_row else cell_w
        row_x = x + (w - (row_w * in_row + gap * (in_row - 1))) / 2
        for c in range(in_row):
            out.append((row_x + c * (row_w + gap), y + r * (cell_h + gap), row_w, cell_h))
    return out


def _grid(spec: DeckSpec, words: dict[str, str], photos: list[int], number: int) -> Slide:
    heading = words["subtitle"] or words["title"]
    zones = [
        DeckZone(("eyebrow",), 0.075, 0.055, 0.55, 0.038, text=words["eyebrow"], align="left"),
        DeckZone(("subtitle",), 0.075, 0.095, 0.70, 0.085, text=heading, align="left"),
    ]
    captions = {i: spec.caption_for(spec.photo_paths[i]) for i in photos}
    has_caption = any(captions.values())
    caption_h = 0.055 if has_caption else 0.0
    area = (0.075, 0.215, 0.850, 0.655 - caption_h)
    rects = _grid_rects(area, len(photos))
    slots = [layouts.Slot(photos[i], *rects[i]) for i in range(min(len(photos), len(rects)))]
    for i, (slot, rect) in enumerate(zip(slots, rects)):
        text = captions.get(photos[i], "")
        if text:
            zones.append(DeckZone(("caption",), rect[0], rect[1] + rect[3] + 0.008, rect[2],
                                  max(0.035, caption_h - 0.008), text=text, align="center"))
    return Slide("grid", f"Gallery {number:02d}", slots, zones, list(photos), numeral=f"{number:02d}")


def _closing(spec: DeckSpec, words: dict[str, str]) -> Slide:
    signature = words["signature"] or words["title"]
    zones = [
        DeckZone(("eyebrow",), 0.14, 0.235, 0.72, 0.045, text=words["eyebrow"], align="center"),
        DeckZone(("signature",), 0.14, 0.315, 0.72, 0.240, text=signature, align="center"),
        DeckZone(("year",), 0.14, 0.715, 0.72, 0.040, text=words["year"], align="center"),
    ]
    return Slide("closing", "Closing", [], zones, [])


def plan(spec: DeckSpec) -> list[Slide]:
    paths = spec.photo_paths
    if not paths:
        raise DeckError("the presentation has no photographs (run ./ccb deck new <photos...>)")
    photos: list[photo_mod.Photo] = []
    for path in paths:
        try:
            photos.append(photo_mod.load(path))
        except photo_mod.PhotoError as exc:
            raise DeckError(str(exc)) from exc

    words = resolved_words(spec)
    hero = _hero_index(spec, photos)
    rest = sorted((i for i in range(len(photos)) if i != hero), key=lambda i: (-photos[i].interest, i))
    slides: list[Slide] = [_cover(spec, words, hero)]
    if words["statement"]:
        slides.append(_statement(spec, words))

    numbered = 1
    for index in rest[:2]:
        slides.append(_hero(spec, words, index, numbered))
        numbered += 1
    for chunk in _chunks(rest[2:]):
        slides.append(_grid(spec, words, chunk, numbered))
        numbered += 1
    slides.append(_closing(spec, words))

    for slide in slides:
        if not slide.numeral:
            slide.numeral = ""
    spec.data["slides"] = [s.to_dict() for s in slides]
    spec.save()
    write_report(spec, slides)
    return slides


def load_slides(spec: DeckSpec, replan: bool = False) -> list[Slide]:
    if replan or not spec.slides:
        return plan(spec)
    return [Slide.from_dict(d) for d in spec.slides]


def summary(slides: list[Slide], spec: DeckSpec) -> str:
    kinds: dict[str, int] = {}
    for slide in slides:
        kinds[slide.kind] = kinds.get(slide.kind, 0) + 1
    parts = []
    for kind in ("cover", "statement", "hero", "grid", "closing"):
        if kinds.get(kind):
            count = kinds[kind]
            parts.append(DECK_KIND_LABELS[kind].lower() + (f" x{count}" if count > 1 else ""))
    return (f"{len(slides)} slides: {', '.join(parts)}\n"
            f"theme  {spec.style.label} / {spec.palette.label}, {len(spec.photo_paths)} photographs, "
            f"16:9 at {spec.export.get('dpi', 150)} DPI")


# -------------------------------------------------------------------- drawing
def _seed(text: str) -> int:
    return zlib.crc32(text.encode("utf-8")) % 100_000


def _family(role: str, style: config.Style) -> str:
    if role in ("title", "statement", "numeral"):
        return style.heading
    if role == "signature":
        return style.script if style.name_font == "script" else style.heading
    if role == "subtitle":
        return style.body if style.align == "left" else style.heading
    return style.body


def _fit_role(text: str, role: str, zone: DeckZone, style: config.Style, width: int,
              height: int, short: int, k: float, align: str) -> typefit.Block:
    family = _family(role, style)
    size = DECK_SIZES.get(role, 0.024) * short * k
    italic = role == "signature" and style.name_font != "script"
    uppercase = role in ("eyebrow", "year") or (
        role == "title" and style.caps and family != style.script
    )
    tracking = 0.16 if role == "eyebrow" else (0.12 if role == "year" else
                                               (style.tracking if role == "title" else 0.0))
    weight = getattr(style, "weight", 500) if ROLE_WEIGHT.get(role) == "heading" else 400
    spacing = 1.10 if role in ("title", "statement", "signature", "numeral") else 1.34
    return typefit.fit(
        text, role, family, weight, italic, uppercase, tracking, spacing,
        zone.w * width, zone.h * height, size, min_size=max(6.0, size * 0.40),
        max_lines=ROLE_LINES.get(role, 3), align=align,
    )


def _draw_zone(draw: ImageDraw.ImageDraw, zone: DeckZone, spec: DeckSpec, width: int, height: int,
               short: int, dpi: int) -> list[dict[str, Any]]:
    palette, style = spec.palette, spec.style
    x, y, w, h = zone.x * width, zone.y * height, zone.w * width, zone.h * height
    if w < 8 or h < 8:
        return []
    items = []
    for role in zone.roles:
        raw = zone.text or spec.text.get(ROLE_TEXT_KEY.get(role, role), "")
        text = typefit.clean(raw)
        if text:
            items.append((role, text))
    if not items:
        return []
    align = zone.align or ("left" if style.align == "left" else "center")
    blocks: list[typefit.Block] = []
    for k in (1.0, 0.94, 0.88, 0.82, 0.76, 0.70, 0.64, 0.58, 0.52, 0.46, 0.40):
        blocks = [_fit_role(text, role, zone, style, width, height, short, k, align)
                  for role, text in items]
        gap = max(2.0, min((b.size for b in blocks), default=12) * 0.32)
        if sum(b.height for b in blocks) + gap * (len(blocks) - 1) <= h:
            break
    gap = max(2.0, min((b.size for b in blocks), default=12) * 0.30)
    total = sum(b.height for b in blocks) + gap * (len(blocks) - 1)
    if total > h:
        share = max(1.0, (h - gap * max(0, len(blocks) - 1)) / max(1, len(blocks)))
        for block in blocks:
            if block.height > share:
                block.line_height = max(4.0, share / max(1, len(block.lines)))
        total = sum(b.height for b in blocks) + gap * (len(blocks) - 1)
    top = y + max(0.0, (h - total) / 2)
    out = []
    for block in blocks:
        color = typefit.readable_text(palette.bg, palette.ink, palette.accent)
        if block.role in ("eyebrow", "year", "numeral", "folio"):
            color = typefit.readable_text(palette.bg, palette.accent, palette.ink)
        used = typefit.draw_block(draw, block, (x, top, w, block.height), color,
                                  align=align, valign="top")
        out.append({
            "role": block.role,
            "size_px": block.size,
            "pt": round(block.size * 72 / max(1, dpi), 1),
            "lines": len(block.lines),
            "truncated": block.truncated,
            "zone": [r4(zone.x), r4(zone.y), r4(zone.w), r4(zone.h)],
            "used_px": [round(v, 1) for v in used],
            "box_px": [round(x, 1), round(y, 1), round(w, 1), round(h, 1)],
            "color": {"hex": color, "contrast": round(typefit.contrast(palette.bg, color), 2)},
        })
        top += block.height + gap
    return out


def render_slide(spec: DeckSpec, slide: Slide, dpi: int, texture: bool = True) -> render.RenderResult:
    palette, style = spec.palette, spec.style
    width = int(round(SLIDE_W_IN * dpi))
    height = int(round(SLIDE_H_IN * dpi))
    short = min(width, height)

    art = Image.new("RGB", (width, height), palette.bg)
    if texture:
        art = render._paper(art, _seed(f"{spec.name}:{slide.label}"))
    draw = ImageDraw.Draw(art)

    keepout = [(s.x * width, s.y * height, s.w * width, s.h * height) for s in slide.slots]
    keepout += [(z.x * width, z.y * height, z.w * width, z.h * height) for z in slide.zones]
    decorate.decorate(draw, style, palette, width, height, keepout,
                      seed=_seed(f"{slide.kind}:{spec.name}"))

    photo_rects: list[list[int]] = []
    for slot in slide.slots:
        if not (0 <= slot.photo < len(spec.photo_paths)):
            continue
        try:
            photo = photo_mod.load(spec.photo_paths[slot.photo])
        except photo_mod.PhotoError:
            continue
        x, y = int(round(slot.x * width)), int(round(slot.y * height))
        w, h = max(2, int(round(slot.w * width))), max(2, int(round(slot.h * height)))
        tile = photo_mod.cover(photo.image, w, h, focus_y=0.42)
        keyline = max(1, int(round(short * 0.0018)))
        tile = photo_mod.frame(tile, palette.bg, keyline)
        if style.radius > 0:
            tile = photo_mod.rounded(tile, style.radius * short * 1.5)
        art.paste(tile, (x, y), tile if tile.mode == "RGBA" else None)
        photo_rects.append([x, y, tile.width, tile.height])

    # The printed hairline where the paper meets the photograph.
    if slide.kind in ("cover", "hero") and slide.slots:
        line_x = int(round(slide.slots[0].x * width))
        draw.line((line_x, 0, line_x, height), fill=palette.accent, width=max(1, int(short * 0.0015)))

    if slide.kind == "statement":
        cy = int(0.745 * height)
        draw.line((int(0.455 * width), cy, int(0.545 * width), cy), fill=palette.accent,
                  width=max(1, int(short * 0.0016)))
    elif slide.kind == "hero" and not slide.caption:
        # With no caption the left column is two small lines; a hairline ties
        # the numeral to them instead of leaving a hole in the slide.
        line_x = int(0.0855 * width)
        draw.line((line_x, int(0.30 * height), line_x, int(0.69 * height)), fill=palette.accent,
                  width=max(1, int(short * 0.0012)))
    elif slide.kind == "closing":
        for yy in (0.295, 0.585):
            cy = int(yy * height)
            draw.line((int(0.44 * width), cy, int(0.56 * width), cy), fill=palette.accent,
                      width=max(1, int(short * 0.0012)))

    blocks: list[dict[str, Any]] = []
    for zone in slide.zones:
        blocks.extend(_draw_zone(draw, zone, spec, width, height, short, dpi))

    # A quiet folio so a deck can be referred to by number.
    if slide.numeral and slide.kind in ("grid", "closing"):
        folio = f"{slide.numeral} / {len(spec.slides) or 0}"
        font = typefit.BOOK.font("lato", max(9, int(short * DECK_SIZES["folio"])), 400)
        color = typefit.readable_text(palette.bg, palette.soft, palette.ink)
        text_w = font.getlength(folio)
        fx, fy = int(0.94 * width - text_w), int(0.955 * height)
        draw.text((fx, fy), folio, font=font, fill=color, anchor="ls")
        blocks.append({
            "role": "folio",
            "size_px": font.size,
            "pt": round(font.size * 72 / max(1, dpi), 1),
            "lines": 1,
            "truncated": False,
            "zone": [0.8, 0.93, 0.125, 0.04],
            "used_px": [round(fx, 1), round(fy - font.size, 1), round(text_w, 1), round(font.size, 1)],
            "box_px": [round(fx, 1), round(fy - font.size, 1), round(text_w, 1), round(font.size, 1)],
            "color": {"hex": color, "contrast": round(typefit.contrast(palette.bg, color), 2)},
        })

    return render.RenderResult(art, {
        "page": slide.label,
        "kind": slide.kind,
        "slide_in": [SLIDE_W_IN, SLIDE_H_IN],
        "slide_px": [width, height],
        "dpi": dpi,
        "photo_rects": photo_rects,
        "blocks": blocks,
        "slots": [s.to_dict() for s in slide.slots],
        "zones": [z.to_dict() for z in slide.zones],
    })


# ---------------------------------------------------------------------- export
def export(spec: DeckSpec, slides: list[Slide], dpi: int | None = None, png: bool | None = None,
           quality: int | None = None, out_dir: Path | None = None) -> dict[str, Any]:
    dpi = max(config.MIN_DPI, min(config.MAX_DPI, int(dpi or spec.export.get("dpi") or 150)))
    png = bool(spec.export.get("png_slides") if png is None else png)
    quality = int(quality or spec.export.get("jpeg_quality") or 92)
    out = Path(out_dir) if out_dir else spec.folder / "out"
    out.mkdir(parents=True, exist_ok=True)
    stem = spec.name

    pages = [(slide, render_slide(spec, slide, dpi)) for slide in slides] if slides else []
    if not pages:
        raise DeckError("nothing to export: the presentation has no slides")

    pdf_path = out / f"{stem}.pdf"
    _write_pdf(spec, pages, pdf_path)
    files: list[dict[str, Any]] = [{
        "path": _rel(spec, pdf_path),
        "format": "pdf",
        "bytes": pdf_path.stat().st_size,
        "dpi": dpi,
        "pages": [{"side": f"{i + 1}. {slide.label}", "w_in": SLIDE_W_IN, "h_in": SLIDE_H_IN}
                  for i, (slide, _) in enumerate(pages)],
    }]

    if png:
        png_dir = out / "slides"
        png_dir.mkdir(parents=True, exist_ok=True)
        for i, (slide, result) in enumerate(pages, start=1):
            path = png_dir / f"slide-{i:02d}.png"
            result.image.save(path, format="PNG", dpi=(dpi, dpi), optimize=True)
            files.append({"path": _rel(spec, path), "format": "png", "bytes": path.stat().st_size,
                          "px": [result.image.width, result.image.height], "dpi": dpi,
                          "page": i, "side": slide.label})

    manifest = {
        "name": spec.name,
        "generated_with": "ccb deck",
        "kind": "presentation",
        "theme": {"style": spec.style.label, "palette": spec.palette.label},
        "dpi": dpi,
        "slide_in": [SLIDE_W_IN, SLIDE_H_IN],
        "slide_px": [int(round(SLIDE_W_IN * dpi)), int(round(SLIDE_H_IN * dpi))],
        "slides": [{"kind": s.kind, "label": s.label, "photos": [spec.photo_paths[i].name
                                                                for i in s.photos if 0 <= i < len(spec.photo_paths)]}
                   for s in slides],
        "files": files,
        "blocks": [b for _, result in pages for b in result.metrics.get("blocks", [])],
    }
    (out / "export.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return manifest


def _rel(spec: DeckSpec, path: Path) -> str:
    try:
        return str(path.relative_to(spec.folder))
    except ValueError:
        return str(path)


def _write_pdf(spec: DeckSpec, pages: list[tuple[Slide, render.RenderResult]], path: Path) -> None:
    page_w, page_h = SLIDE_W_IN * 72.0, SLIDE_H_IN * 72.0
    c = pdfcanvas.Canvas(str(path), pagesize=(page_w, page_h), pageCompression=1)
    c.setTitle(f"{spec.text.get('title') or spec.name} - Christmas presentation")
    c.setAuthor("CCB Christmas Card Studio")
    c.setSubject("Christmas presentation made from family photographs")
    c.setCreator("CCB - the Christmas studio for OpenCode")
    for _, result in pages:
        buf = io.BytesIO()
        result.image.save(buf, format="PNG", optimize=False)
        buf.seek(0)
        c.drawImage(ImageReader(buf), 0, 0, width=page_w, height=page_h,
                    preserveAspectRatio=False, mask=None)
        c.showPage()
    c.save()


def verify_files(spec: DeckSpec, manifest: dict[str, Any]) -> list[str]:
    problems: list[str] = []
    for item in manifest.get("files", []):
        path = (spec.folder / item["path"]).resolve()
        if not path.exists():
            problems.append(f"{item['path']} is missing")
            continue
        if path.stat().st_size < 2000:
            problems.append(f"{item['path']} is suspiciously small")
        if item["format"] == "pdf":
            problems.extend(_verify_pdf(path, item))
        else:
            with Image.open(path) as img:
                if item.get("px") and list(img.size) != list(item["px"]):
                    problems.append(f"{path.name}: {img.size[0]}x{img.size[1]} px, expected {item['px']}")
                dpi_meta = img.info.get("dpi")
                if dpi_meta and abs(float(dpi_meta[0]) - float(item.get("dpi", 0))) > 1.5:
                    problems.append(f"{path.name}: {dpi_meta[0]:.0f} DPI metadata, expected {item['dpi']}")
    return problems


def _verify_pdf(path: Path, item: dict[str, Any]) -> list[str]:
    import re
    problems = []
    raw = path.read_bytes()
    pages = raw.count(b"/Type /Page") + raw.count(b"/Type/Page")
    pages -= raw.count(b"/Type /Pages") + raw.count(b"/Type/Pages")
    if pages != len(item.get("pages", [])):
        problems.append(f"{path.name}: {pages} slides, expected {len(item.get('pages', []))}")
    boxes = re.findall(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", raw)
    if not boxes:
        problems.append(f"{path.name}: no MediaBox found")
    else:
        for w, h in {(round(float(a), 2), round(float(b), 2)) for a, b in boxes}:
            if abs(w - SLIDE_W_IN * 72) > 1.0 or abs(h - SLIDE_H_IN * 72) > 1.0:
                problems.append(f"{path.name}: page is {w / 72:.2f} x {h / 72:.2f} in, expected "
                                f"{SLIDE_W_IN:.2f} x {SLIDE_H_IN:.2f} in")
    return problems


# ----------------------------------------------------------------------- gate
def _overlap(a: DeckZone, b: layouts.Slot) -> float:
    x = max(0.0, min(a.x + a.w, b.x + b.w) - max(a.x, b.x))
    y = max(0.0, min(a.y + a.h, b.y + b.h) - max(a.y, b.y))
    return x * y


def check(spec: DeckSpec, slides: list[Slide] | None = None, dpi: int = 150) -> dict[str, Any]:
    slides = slides or load_slides(spec)
    errors: list[str] = []
    warnings: list[str] = []
    paths = spec.photo_paths

    kinds = [s.kind for s in slides]
    if "cover" not in kinds:
        errors.append("the presentation has no cover slide")
    if "closing" not in kinds:
        warnings.append("the presentation has no closing slide")
    if len(slides) < 3:
        warnings.append(f"only {len(slides)} slides: a deck reads better with a cover, a middle and a closing")

    used = sorted({i for slide in slides for i in slide.photos})
    if paths and used != list(range(len(paths))):
        missing = [paths[i].name for i in range(len(paths)) if i not in used]
        errors.append("these photographs never appear: " + ", ".join(missing))

    for n, slide in enumerate(slides, start=1):
        if not slide.slots and slide.kind not in ("statement", "closing"):
            errors.append(f"slide {n} ({slide.label}) has no photographs")
        for slot in slide.slots:
            if slot.x < -1e-6 or slot.y < -1e-6 or slot.x + slot.w > 1 + 1e-6 or slot.y + slot.h > 1 + 1e-6:
                errors.append(f"slide {n}: a photograph leaves the slide")
            if slot.w <= 0.02 or slot.h <= 0.02:
                errors.append(f"slide {n}: a photograph is too small to see")
        for zone in slide.zones:
            if zone.x < -1e-6 or zone.y < -1e-6 or zone.x + zone.w > 1 + 1e-6 or zone.y + zone.h > 1 + 1e-6:
                errors.append(f"slide {n}: text leaves the slide")
            for slot in slide.slots:
                if _overlap(zone, slot) > 1e-6:
                    errors.append(f"slide {n}: text sits on top of a photograph")
        words = [typefit.clean(z.text or " ".join(
            spec.text.get(ROLE_TEXT_KEY.get(r, r), "") for r in z.roles)) for z in slide.zones]
        if not any(words):
            warnings.append(f"slide {n} ({slide.label}) has no words")

    blocks_all: list[dict[str, Any]] = []
    for n, slide in enumerate(slides, start=1):
        try:
            result = render_slide(spec, slide, dpi=110, texture=False)
        except Exception as exc:  # a broken photograph must not crash the gate
            errors.append(f"slide {n} could not be drawn ({exc})")
            continue
        blocks = result.metrics.get("blocks", [])
        blocks_all.extend(blocks)
        short_px = min(result.metrics["slide_px"])
        for block in blocks:
            if block.get("truncated"):
                warnings.append(f"slide {n}: the {block['role']} was shortened to fit")
            if block["role"] in ("caption", "message", "signature") and block["size_px"] < short_px * 0.015:
                warnings.append(f"slide {n}: the {block['role']} is {block['pt']:.1f} pt, smaller than "
                                f"is comfortable; shorten it")
            contrast = block.get("color", {}).get("contrast", 9)
            if contrast < 3.0:
                warnings.append(f"slide {n}: {block['role']} contrast is {contrast}:1")

    for slide in slides:
        for slot in slide.slots:
            if not (0 <= slot.photo < len(paths)):
                continue
            try:
                photo = photo_mod.load(paths[slot.photo])
            except photo_mod.PhotoError:
                continue
            need_w = slot.w * SLIDE_W_IN * dpi
            need_h = slot.h * SLIDE_H_IN * dpi
            target = need_w / max(1.0, need_h)
            available = photo.height * target if photo.aspect > target else photo.width
            scale = need_w / max(1.0, available)
            if scale > 1.8:
                warnings.append(f"{photo.path.name} is used at {scale:.1f}x its pixels on "
                                f"{slide.label.lower()}; it will look soft")

    if not any(typefit.clean(v) for v in spec.text.values()):
        errors.append("the presentation has no words: set a title, a greeting or a message")

    counts: dict[str, int] = {}
    for slide in slides:
        counts[slide.kind] = counts.get(slide.kind, 0) + 1
    facts = {
        "kind": "presentation",
        "slides": len(slides),
        "kinds": counts,
        "photos": len(paths),
        "theme": f"{spec.style.label} / {spec.palette.label}",
        "slide_in": [SLIDE_W_IN, SLIDE_H_IN],
        "smallest_pt": min((b["pt"] for b in blocks_all), default=0),
        "largest_pt": max((b["pt"] for b in blocks_all), default=0),
        "dpi": dpi,
    }
    return {"errors": errors, "warnings": warnings, "facts": facts}


def print_report(report: dict[str, Any]) -> bool:
    facts = report.get("facts", {})
    counts = facts.get("kinds", {})
    parts = [f"{DECK_KIND_LABELS[k].lower()} x{counts[k]}" for k in
             ("cover", "statement", "hero", "grid", "closing") if counts.get(k)]
    if facts:
        print(f"deck    {facts['slides']} slides: {', '.join(parts)}")
        print(f"screen  {facts['slide_in'][0]:.2f} x {facts['slide_in'][1]:.2f} in (16:9), {facts['dpi']} DPI")
        print(f"theme   {facts['theme']}, {facts['photos']} photographs")
        if facts.get("smallest_pt"):
            print(f"type    {facts['smallest_pt']:.1f}-{facts['largest_pt']:.1f} pt")
    for warning in report.get("warnings", []):
        print(f"WARN  {warning}")
    for error in report.get("errors", []):
        print(f"ERROR {error}")
    if not report.get("errors"):
        print("gate: 0 errors")
    return not report.get("errors")


# ---------------------------------------------------------------------- sheet
def build_sheet(spec: DeckSpec, slides: list[Slide], out: Path, tile_w: int = 620) -> Path:
    if not slides:
        raise DeckError("no slides to draw")
    cols = 2
    rows = math.ceil(len(slides) / cols)
    margin, gap, label_h, header_h = 34, 26, 54, 84
    tiles = []
    for slide in slides:
        result = render_slide(spec, slide, dpi=96)
        img = result.image.convert("RGB")
        scale = tile_w / img.width
        tiles.append(img.resize((tile_w, int(round(img.height * scale))), Image.LANCZOS))
    tile_h = tiles[0].height
    width = margin * 2 + cols * tile_w + (cols - 1) * gap
    height = margin * 2 + header_h + rows * (tile_h + label_h) + (rows - 1) * gap
    sheet = Image.new("RGB", (width, height), "#12161B")
    draw = ImageDraw.Draw(sheet)
    title_font = typefit.BOOK.font("lato", 30, 700)
    sub_font = typefit.BOOK.font("lato", 17, 400)
    label_font = typefit.BOOK.font("lato", 18, 700)
    small_font = typefit.BOOK.font("lato", 15, 400)
    draw.text((margin, margin - 6), spec.name.replace("-", " ").title(), font=title_font, fill="#F4F1E8")
    draw.text((margin, margin + 32),
              f"{spec.style.label}  ·  {spec.palette.label}  ·  16:9  ·  "
              f"{len(spec.photo_paths)} photographs  ·  {len(slides)} slides",
              font=sub_font, fill="#98A2AC")
    for i, (slide, tile) in enumerate(zip(slides, tiles)):
        col, row = i % cols, i // cols
        x = margin + col * (tile_w + gap)
        y = margin + header_h + row * (tile_h + label_h + gap)
        sheet.paste(tile, (x, y))
        draw.rectangle((x, y + tile_h, x + tile_w, y + tile_h + label_h), fill="#1A2027")
        draw.text((x + 12, y + tile_h + 8), f"{i + 1:02d}. {slide.label}", font=label_font, fill="#F4F1E8")
        detail = f"{len(slide.slots)} photograph{'s' if len(slide.slots) != 1 else ''}"
        if slide.caption:
            detail += "  ·  captioned"
        draw.text((x + 12, y + tile_h + 31), detail, font=small_font, fill="#98A2AC")
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, format="JPEG", quality=88, optimize=True)
    return out


# --------------------------------------------------------------------- report
def write_report(spec: DeckSpec, slides: list[Slide]) -> str:
    style, palette = spec.style, spec.palette
    words = resolved_words(spec)
    lines = [f"# {spec.name}: presentation", "",
             f"- Theme: **{style.label}** - {style.blurb}",
             f"- Palette: **{palette.label}**",
             f"- Screen: **{SLIDE_W_IN:.2f} x {SLIDE_H_IN:.2f} in** (16:9), "
             f"PDF at {spec.export.get('dpi', 150)} DPI",
             f"- Photographs: **{len(spec.photo_paths)}**",
             f"- Slides: **{len(slides)}**", ""]

    lines += ["## Words", "", "| Field | Copy |", "| --- | --- |"]
    for role in ("title", "subtitle", "greeting", "message", "signature", "year"):
        lines.append(f"| {role} | {spec.text.get(role) or '_(empty)_'} |")
    lines.append("")

    lines += ["## Slides", "", "| # | Kind | Photographs | Caption |", "| --- | --- | --- | --- |"]
    for i, slide in enumerate(slides, start=1):
        names = ", ".join(spec.photo_paths[j].name for j in slide.photos if 0 <= j < len(spec.photo_paths))
        lines.append(f"| {i} | {slide.label} | {names or '-'} | {slide.caption or '-'} |")
    lines.append("")

    if spec.captions:
        lines += ["## Captions", ""]
        for name, text in spec.captions.items():
            lines.append(f"- `{name}`: {text}")
        lines.append("")

    todo = []
    if not words["title"]:
        todo.append("Add a title (the cover needs one line to hold it together).")
    if not words["statement"]:
        todo.append("Add a message: it becomes the statement slide and the closing thought.")
    if not words["signature"]:
        todo.append("Add a signature so the closing slide is signed.")
    if not words["eyebrow"]:
        todo.append("Add a greeting (\"Merry Christmas\") if you want it on the cover.")
    if not spec.captions:
        todo.append("Optional: add captions in `deck.json` under `captions` to name the photographs.")
    lines += ["## To do", ""] + ([f"- {item}" for item in todo] if todo else
                                 ["- Nothing: the presentation is ready to render."])
    lines += ["", "## Next", "",
              f"1. `./ccb deck check {_path(spec)}` - the gate must show 0 errors.",
              f"2. `./ccb deck sheet {_path(spec)}` - look at every slide at once.",
              f"3. `./ccb deck render {_path(spec)}` - write the PDF.",
              f"4. `./ccb deck qa {_path(spec)}` - verify the real pages.", ""]
    text = "\n".join(lines)
    (spec.folder / "report.md").write_text(text, encoding="utf-8")
    return text


def _path(spec: DeckSpec) -> str:
    try:
        return str(spec.folder.relative_to(config.ROOT))
    except ValueError:
        return str(spec.folder)
