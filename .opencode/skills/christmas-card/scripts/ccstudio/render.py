"""Drawing a card front and back at print resolution.

The preview and the export go through this one code path; only the DPI changes.
Photographs are cover-cropped (never stretched), text is measured to fit its
zone, and decoration avoids both.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from typing import Any

from PIL import Image, ImageDraw, ImageFilter

from . import config, decorate, layouts, photos as photo_mod, typefit
from .spec import CardSpec


@dataclass
class RenderResult:
    image: Image.Image
    metrics: dict[str, Any] = field(default_factory=dict)


def canvas_px(spec: CardSpec, dpi: int, bleed: bool) -> tuple[int, int, int]:
    """(canvas_w, canvas_h, bleed_px) in pixels for a real print size."""
    w_in, h_in = spec.card_inches
    b = int(round(config.BLEED_IN * dpi)) if bleed else 0
    return int(round(w_in * dpi)) + 2 * b, int(round(h_in * dpi)) + 2 * b, b


def _paper(region: Image.Image, seed: int) -> Image.Image:
    """A quiet, deterministic paper texture: fine grain plus a soft vignette."""
    import random
    rng = random.Random(seed)
    grain = Image.new("L", (region.width // 3 or 1, region.height // 3 or 1))
    grain.putdata([rng.randint(112, 143) for _ in range(grain.width * grain.height)])
    grain = grain.resize(region.size, Image.BILINEAR).filter(ImageFilter.GaussianBlur(0.6))
    overlay = Image.merge("RGB", (grain, grain, grain))
    out = Image.blend(region, overlay, 0.055)
    vignette = Image.new("L", region.size, 0)
    ImageDraw.Draw(vignette).ellipse(
        (-region.width * 0.15, -region.height * 0.15, region.width * 1.15, region.height * 1.15), fill=255
    )
    vignette = vignette.filter(ImageFilter.GaussianBlur(min(region.size) // 12))
    shade = Image.new("RGB", region.size, (0, 0, 0))
    return Image.composite(out, Image.blend(out, shade, 0.045), vignette)


def render_front(spec: CardSpec, design: layouts.Design | dict[str, Any], dpi: int,
                 bleed: bool = True, texture: bool | None = None,
                 page: str = "front") -> RenderResult:
    if isinstance(design, dict):
        design = layouts.Design.from_dict(design)
    style = spec.style
    palette = spec.palette
    w_in, h_in = spec.card_inches
    canvas_w, canvas_h, b = canvas_px(spec, dpi, bleed)
    trim_w, trim_h = int(round(w_in * dpi)), int(round(h_in * dpi))
    short = min(trim_w, trim_h)

    canvas = Image.new("RGB", (canvas_w, canvas_h), palette.bg)
    art = canvas.crop((b, b, b + trim_w, b + trim_h))
    if (style.texture if texture is None else texture):
        art = _paper(art, hash(spec.name) & 0xFFFF)
    draw = ImageDraw.Draw(art)

    # Where decoration may not go: photograph slots and text zones.
    keepout = [(s.x * trim_w, s.y * trim_h, s.w * trim_w, s.h * trim_h) for s in design.slots]
    keepout += [(z.x * trim_w, z.y * trim_h, z.w * trim_w, z.h * trim_h) for z in design.zones]
    # A composition may name its own ornaments; that replaces the direction's
    # decoration (creative control) instead of piling both on.
    if design.ornaments:
        _draw_ornaments(draw, style, palette, trim_w, trim_h, keepout, design, spec.name)
    else:
        decorate.decorate(draw, style, palette, trim_w, trim_h, keepout, seed=_seed(spec.name))

    loaded: dict[int, photo_mod.Photo] = {}
    photo_rects: list[list[int]] = []
    for slot in design.slots:
        photo = _photo(spec, slot.photo, loaded)
        if photo is None:
            _placeholder(draw, slot, trim_w, trim_h, short, palette, spec.photo_paths[slot.photo].name)
            continue
        x, y = int(round(slot.x * trim_w)), int(round(slot.y * trim_h))
        w, h = max(2, int(round(slot.w * trim_w))), max(2, int(round(slot.h * trim_h)))
        # Face-aware crop: the people decide where a slot looks, unless the
        # composition set an explicit focus.
        fx, fy = slot.focus if slot.focus else photo.face_focus
        tile = photo_mod.cover(photo.image, w, h, focus_x=fx, focus_y=fy)
        treatment = (slot.treatment or style.photo_frame or "plain").lower()
        frame_w = max(1, int(round(short * 0.0022))) if treatment == "border" else 0
        if frame_w:
            tile = photo_mod.frame(tile, palette.panel, frame_w)
        if style.radius > 0 and treatment != "plain":
            tile = photo_mod.rounded(tile, style.radius * short)
        if treatment == "shadow":
            tile = photo_mod.shadowed(tile, spread=max(2, int(short * 0.008)), opacity=52)
            x -= int(short * 0.008)
            y -= int(short * 0.008)
        if treatment == "tilt":
            tile = photo_mod.tilt(tile, -2.1 if slot.photo % 2 else 2.1)
            x = int(x + (w - tile.width) / 2)
            y = int(y + (h - tile.height) / 2)
        art.paste(tile, (x, y), tile if tile.mode == "RGBA" else None)
        photo_rects.append([x, y, tile.width, tile.height])

    # The printed border goes over the photographs, so a full-bleed panorama
    # still reads as a framed card instead of a cropped picture.
    decorate.border(draw, style, palette, trim_w, trim_h, style.margin * short)
    for line in design.lines:
        _draw_line(draw, line, palette, trim_w, trim_h, short)

    blocks: list[dict[str, Any]] = []
    for zone in design.zones:
        blocks.extend(_draw_zone(art, draw, zone, spec, trim_w, trim_h, short, palette, style, dpi))

    canvas.paste(art, (b, b))
    return RenderResult(canvas, {
        "page": page,
        "design": design.label,
        "engine": design.engine,
        "card_in": [w_in, h_in],
        "trim_px": [trim_w, trim_h],
        "bleed_px": b,
        "dpi": dpi,
        "photo_rects": photo_rects,
        "blocks": blocks,
        "zones": [z.to_dict() for z in design.zones],
        "slots": [s.to_dict() for s in design.slots],
    })


def _seed(name: str) -> int:
    return abs(hash(name)) % 100_000


def _draw_ornaments(draw: ImageDraw.ImageDraw, style: config.Style, palette: config.Palette,
                    trim_w: int, trim_h: int, keepout: list[tuple[float, float, float, float]],
                    design: layouts.Design, name: str) -> None:
    for i, item in enumerate(design.ornaments):
        kind = str(item.get("kind", "none")).lower()
        if kind not in ("holly", "snow", "stars", "confetti"):
            continue
        density = item.get("density", style.density)
        try:
            density = max(0.0, min(1.6, float(density)))
        except (TypeError, ValueError):
            density = style.density
        variant = replace(style, decoration=kind, density=density)
        decorate.decorate(draw, variant, palette, trim_w, trim_h, keepout,
                          seed=_seed(name) + 97 * (i + 1))


def _draw_line(draw: ImageDraw.ImageDraw, line: dict[str, Any], palette: config.Palette,
               trim_w: int, trim_h: int, short: int) -> None:
    try:
        x1, y1 = float(line["x1"]) * trim_w, float(line["y1"]) * trim_h
        x2, y2 = float(line["x2"]) * trim_w, float(line["y2"]) * trim_h
        weight = float(line.get("weight", 1.0))
    except (KeyError, TypeError, ValueError):
        return
    color = palette.token(str(line.get("token", "accent")))
    width = max(1, int(round(short * 0.0016 * max(0.25, min(3.0, weight)))))
    draw.line((x1, y1, x2, y2), fill=color, width=width)


def _photo(spec: CardSpec, index: int, cache: dict[int, photo_mod.Photo]) -> photo_mod.Photo | None:
    if index in cache:
        return cache[index]
    paths = spec.photo_paths
    if not (0 <= index < len(paths)):
        return None
    try:
        photo = photo_mod.load(paths[index])
    except photo_mod.PhotoError:
        return None
    cache[index] = photo
    return photo


def _placeholder(draw: ImageDraw.ImageDraw, slot: layouts.Slot, trim_w: int, trim_h: int,
                 short: int, palette: config.Palette, label: str) -> None:
    x, y = slot.x * trim_w, slot.y * trim_h
    w, h = slot.w * trim_w, slot.h * trim_h
    draw.rectangle((x, y, x + w, y + h), fill=palette.panel, outline=palette.accent,
                   width=max(1, int(short * 0.002)))
    font = typefit.BOOK.font("lato", short * 0.014, 400)
    text = "photograph missing"
    draw.text((x + w / 2, y + h / 2), text, font=font, fill=palette.on_panel, anchor="mm")
    draw.text((x + w / 2, y + h / 2 + short * 0.022), label[:32], font=font, fill=palette.on_panel, anchor="mm")


def _draw_zone(art: Image.Image, draw: ImageDraw.ImageDraw, zone: layouts.Zone, spec: CardSpec,
               trim_w: int, trim_h: int, short: int, palette: config.Palette,
               style: config.Style, dpi: int) -> list[dict[str, Any]]:
    x, y = zone.x * trim_w, zone.y * trim_h
    w, h = zone.w * trim_w, zone.h * trim_h
    if w < 8 or h < 8:
        return []
    text = spec.text
    items = [(role, zone.text or text.get(role, "")) for role in zone.roles]
    items = [(r, t) for r, t in items if typefit.clean(t)]
    if not items:
        return []
    if zone.panel:
        draw.rounded_rectangle((x, y, x + w, y + h), radius=short * 0.012, fill=palette.panel)
    pad = short * 0.012
    chosen = zone.align or style.align
    align = "right" if chosen == "right" else ("left" if chosen == "left" else "center")
    blocks = typefit.fit_stack(items, style, w - 2 * pad, h - 2 * pad, short,
                              scale=max(0.35, min(2.2, zone.scale)),
                              book=typefit.BOOK, font=zone.font, align=zone.align,
                              caps=zone.caps)
    color = typefit.readable_text(palette.panel if zone.panel else palette.bg,
                                  palette.on_panel if zone.panel else palette.ink,
                                  palette.ink, palette.soft, "#FFFFFF", "#111111")
    total = sum(b.height for b in blocks)
    free = max(0.0, (h - 2 * pad) - total)
    if zone.valign == "top":
        top = y + pad
    elif zone.valign == "bottom":
        top = y + h - pad - total
    else:
        top = y + pad + free / 2
    minimum_gap = max(2.0, (min((b.size for b in blocks), default=12)) * 0.30)
    # A roomy zone (an editorial column) spreads its paragraphs instead of
    # leaving a block of empty paper at the bottom.
    if len(blocks) > 1 and free > minimum_gap * (len(blocks) - 1) * 1.8:
        gap = min(free / (len(blocks) - 1), short * 0.05)
    else:
        gap = minimum_gap
    out = []
    for block in blocks:
        box = (x + pad, top, w - 2 * pad, block.height)
        used = typefit.draw_block(draw, block, box, color, align=align, valign=zone.valign)
        out.append({
            "role": block.role,
            "size_px": block.size,
            "pt": round(block.size * 72 / max(1, dpi), 1),
            "lines": len(block.lines),
            "truncated": block.truncated,
            "zone": [round(zone.x, 4), round(zone.y, 4), round(zone.w, 4), round(zone.h, 4)],
            "used_px": [round(v, 1) for v in used],
            "box_px": [round(x + pad, 1), round(y + pad, 1), round(w - 2 * pad, 1), round(h - 2 * pad, 1)],
            "color": {"hex": color, "contrast": round(typefit.contrast(
                palette.panel if zone.panel else palette.bg, color), 2)},
        })
        top += block.height + gap
    return out


def render_back(spec: CardSpec, dpi: int, bleed: bool = True, texture: bool | None = None) -> RenderResult:
    style = spec.style
    palette = spec.palette
    w_in, h_in = spec.card_inches
    canvas_w, canvas_h, b = canvas_px(spec, dpi, bleed)
    trim_w, trim_h = int(round(w_in * dpi)), int(round(h_in * dpi))
    short = min(trim_w, trim_h)

    canvas = Image.new("RGB", (canvas_w, canvas_h), palette.bg)
    art = canvas.crop((b, b, b + trim_w, b + trim_h))
    if (style.texture if texture is None else texture):
        art = _paper(art, (hash(spec.name) + 7) & 0xFFFF)
    draw = ImageDraw.Draw(art)
    m = style.margin
    keepout: list[tuple[float, float, float, float]] = []
    decorate.decorate(draw, style, palette, trim_w, trim_h, keepout, seed=_seed(spec.name) + 3)
    decorate.border(draw, style, palette, trim_w, trim_h, m * short)

    paths = spec.photo_paths
    strip_photos = paths[:3] if len(paths) >= 3 else []
    text = dict(spec.text)
    text.setdefault("greeting", "")
    family = text.get("family", "")
    monogram = _initials(family or spec.name)

    zones: list[layouts.Zone] = []
    top = m + 0.055
    monogram_h = 0.20
    zones.append(layouts.Zone(("monogram",), m, top, 1 - 2 * m, monogram_h))
    top += monogram_h + 0.005
    zones.append(layouts.Zone(("family",), m, top, 1 - 2 * m, 0.075))
    top += 0.095
    if strip_photos:
        rows = 1
        gap = 0.012
        cell_w = (1 - 2 * m - gap * (len(strip_photos) - 1)) / len(strip_photos)
        cell_h = cell_w * 1.15
        for i, path in enumerate(strip_photos):
            x = m + i * (cell_w + gap)
            tile = photo_mod.cover(_safe_load(path).image, int(cell_w * trim_w), int(cell_h * trim_h), focus_y=0.42)
            if style.radius > 0:
                tile = photo_mod.rounded(tile, style.radius * short)
            art.paste(tile, (int(x * trim_w), int(top * trim_h)), tile if tile.mode == "RGBA" else None)
        top += cell_h + 0.03
    message_h = max(0.10, 0.80 - top)
    zones.append(layouts.Zone(("message",), m, top, 1 - 2 * m, message_h))
    top += message_h + 0.01
    zones.append(layouts.Zone(("signature", "year"), m, min(top, 1 - m - 0.075), 1 - 2 * m, 0.07))

    blocks: list[dict[str, Any]] = []
    for zone in zones:
        if zone.roles == ("monogram",):
            blocks.extend(_draw_monogram(art, draw, zone, monogram, trim_w, trim_h, short, palette, style, dpi))
        else:
            blocks.extend(_draw_zone(art, draw, zone, spec, trim_w, trim_h, short, palette, style, dpi))
    canvas.paste(art, (b, b))
    return RenderResult(canvas, {
        "page": "back",
        "card_in": [w_in, h_in],
        "trim_px": [trim_w, trim_h],
        "bleed_px": b,
        "dpi": dpi,
        "blocks": blocks,
    })


def _safe_load(path) -> photo_mod.Photo:
    try:
        return photo_mod.load(path)
    except photo_mod.PhotoError:
        img = Image.new("RGB", (600, 700), "#DDD8CC")
        return photo_mod.Photo(path, img, img.width, img.height, 0.0, 0.8, 0.0)


def _initials(name: str) -> str:
    words = [w for w in typefit.clean(name).split() if w]
    letters = [w[0].upper() for w in words if w[0].isalnum()]
    return "".join(letters[:2]) or "M"


def _draw_monogram(art: Image.Image, draw: ImageDraw.ImageDraw, zone: layouts.Zone, text: str,
                   trim_w: int, trim_h: int, short: int, palette: config.Palette,
                   style: config.Style, dpi: int) -> list[dict[str, Any]]:
    x, y = zone.x * trim_w, zone.y * trim_h
    w, h = zone.w * trim_w, zone.h * trim_h
    family = style.heading if style.name_font != "script" else style.script
    block = typefit.fit(text, "monogram", family, style.weight, False, False, 0.04, 1.0,
                        w * 0.5, h * 0.9, min(w, h) * 0.9, min_size=short * 0.05)
    color = typefit.readable_text(palette.bg, palette.accent, palette.ink)
    used = typefit.draw_block(draw, block, (x, y, w, h), color, align="center", valign="center")
    cx = x + w / 2
    cy = used[1] + used[3] + short * 0.012
    draw.line((cx - short * 0.05, cy, cx + short * 0.05, cy), fill=palette.accent,
              width=max(1, int(short * 0.0018)))
    return [{
        "role": "monogram",
        "size_px": block.size,
        "pt": round(block.size * 72 / max(1, dpi), 1),
        "lines": 1,
        "truncated": block.truncated,
        "zone": [round(zone.x, 4), round(zone.y, 4), round(zone.w, 4), round(zone.h, 4)],
        "used_px": [round(v, 1) for v in used],
        "box_px": [round(x, 1), round(y, 1), round(w, 1), round(h, 1)],
        "color": {"hex": color, "contrast": round(typefit.contrast(palette.bg, color), 2)},
    }]


def preview(spec: CardSpec, design: layouts.Design | dict[str, Any], width_px: int = 760) -> RenderResult:
    w_in, _ = spec.card_inches
    dpi = max(48, int(width_px / w_in))
    return render_front(spec, design, dpi, bleed=False, texture=True)
