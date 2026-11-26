"""Painting a page at print resolution.

The renderer has no house style of its own. It paints exactly what the
composition declares, in layer order: a background (flat colour, gradient or a
full-bleed photograph with a scrim), an optional paper grain, colour fields and
shapes, photograph slots (cropped around faces, clipped, rotated), rules, and
text zones. Nothing is added that the composition did not ask for — no frame,
no decoration, no texture.

Photographs are cover-cropped (never stretched); text is measured to fit its
zone; type that is deliberately placed on a photograph is coloured for
contrast against what is actually underneath it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

import numpy as np
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


# --------------------------------------------------------------------- colour
def _color(palette: config.Palette, name: str | None, default: str = "#000000") -> str:
    if not name:
        return default
    if str(name).startswith("#"):
        return str(name)
    return palette.token(str(name))


def _rgba(hex_color: str, opacity: float = 1.0) -> tuple[int, int, int, int]:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        r, g, b = 0, 0, 0
    return r, g, b, int(round(255 * max(0.0, min(1.0, opacity))))


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


def _paste_layer(canvas: Image.Image, layer: Image.Image, at: tuple[int, int] = (0, 0)) -> None:
    """Composite an RGBA layer onto an RGB canvas using its alpha as the mask."""
    canvas.paste(layer.convert("RGB"), at, layer.getchannel("A"))


def _sample_bg(canvas: Image.Image, box: tuple[float, float, float, float]) -> str:
    """The average colour under a rectangle, as a hex string."""
    x, y, w, h = (int(round(v)) for v in box)
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(canvas.width, x + max(1, w)), min(canvas.height, y + max(1, h))
    if x1 <= x0 or y1 <= y0:
        return "#FFFFFF"
    region = canvas.crop((x0, y0, x1, y1)).convert("L").resize((1, 1), Image.BOX)
    v = region.getpixel((0, 0))
    return f"#{v:02x}{v:02x}{v:02x}"


# --------------------------------------------------------------------- paper
def _paper(region: Image.Image, seed: int) -> Image.Image:
    """A quiet, deterministic paper texture: fine grain plus a soft vignette."""
    import random
    rng = random.Random(seed)
    grain = Image.new("L", (max(1, region.width // 3), max(1, region.height // 3)))
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


def _gradient(size: tuple[int, int], a: str, b: str, angle: float) -> Image.Image:
    w, h = size
    ys, xs = np.mgrid[0:h, 0:w].astype(np.float32)
    rad = math.radians(angle)
    t = (xs / max(1, w)) * math.cos(rad) + (ys / max(1, h)) * math.sin(rad)
    lo, hi = float(t.min()), float(t.max())
    t = (t - lo) / max(1e-6, hi - lo)
    ca, cb = _rgba(a), _rgba(b)
    arr = np.zeros((h, w, 3), dtype=np.float32)
    for i in range(3):
        arr[:, :, i] = ca[i] + (cb[i] - ca[i]) * t
    return Image.fromarray(arr.astype(np.uint8), "RGB")


# ---------------------------------------------------------------- background
def paint_background(canvas: Image.Image, spec: CardSpec, design: layouts.Design,
                     palette: config.Palette, trim_w: int, trim_h: int,
                     ox: int, oy: int) -> dict[str, Any]:
    bg = design.background or {}
    facts: dict[str, Any] = {}
    if bg.get("photo") is not None:
        index = int(bg.get("photo", 0))
        photo = _photo(spec, index, {})
        if photo is not None:
            # The background covers the bleed too: that is what full-bleed means.
            tile = photo_mod.cover(photo.image, canvas.width, canvas.height,
                                   focus_x=float(photo.face_focus[0]), focus_y=float(photo.face_focus[1]))
            canvas.paste(tile, (0, 0))
            facts["photo"] = index
            scrim = _clamp01(float(bg.get("scrim", 0.0) or 0.0))
            if scrim > 0:
                colour = _color(palette, str(bg.get("scrim_color") or "panel"))
                where = str(bg.get("scrim_from") or "bottom").lower()
                reach = _clamp01(float(bg.get("scrim_reach", 0.65) or 0.65))
                alpha = _scrim_mask(canvas.size, scrim, where, max(0.08, reach))
                layer = Image.new("RGBA", canvas.size, _rgba(colour))
                layer.putalpha(alpha)
                _paste_layer(canvas, layer)
            return facts
    gradient = bg.get("gradient")
    if isinstance(gradient, (list, tuple)) and len(gradient) >= 2:
        angle = float(bg.get("angle", 90) or 90)
        canvas.paste(_gradient(canvas.size, _color(palette, str(gradient[0])),
                               _color(palette, str(gradient[1])), angle), (0, 0))
        facts["gradient"] = [str(gradient[0]), str(gradient[1])]
        return facts
    if bg.get("fill"):
        canvas.paste(_color(palette, str(bg["fill"])), (0, 0, canvas.width, canvas.height))
        facts["fill"] = str(bg["fill"])
        return facts
    facts["fill"] = "bg"
    return facts


def _scrim_mask(size: tuple[int, int], strength: float, where: str,
                reach: float = 0.65) -> Image.Image:
    """A soft fade: full strength at the named edge, gone by `reach` of the page."""
    w, h = size
    strength = _clamp01(strength)
    if where == "full":
        return Image.new("L", size, int(255 * strength))
    # 1.0 at the edge the scrim comes from, 0.0 at the opposite edge.
    if where in ("left", "right"):
        ramp = np.tile(np.linspace(1.0, 0.0, w, dtype=np.float32)[None, :], (h, 1))
        if where == "right":
            ramp = ramp[:, ::-1]
    else:
        ramp = np.tile(np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None], (1, w))
        if where == "top":
            ramp = ramp[::-1, :]
    alpha = np.clip((np.clip(ramp / max(0.05, reach), 0.0, 1.0) ** 0.9) * 255.0 * strength,
                    0, 255).astype(np.uint8)
    return Image.fromarray(alpha, "L")


# --------------------------------------------------------------------- shapes
def paint_shape(canvas: Image.Image, shape: dict[str, Any], palette: config.Palette,
                trim_w: int, trim_h: int, ox: int, oy: int) -> None:
    kind = str(shape.get("kind", "rect")).lower()
    try:
        x = ox + float(shape["x"]) * trim_w
        y = oy + float(shape["y"]) * trim_h
        w = float(shape["w"]) * trim_w
        h = float(shape["h"]) * trim_h
    except (KeyError, TypeError, ValueError):
        return
    if w <= 0 or h <= 0:
        return
    colour = _color(palette, str(shape.get("fill") or "accent"))
    opacity = _clamp01(float(shape.get("opacity", 1.0) or 1.0))
    if kind == "band":
        x, w = 0.0, float(canvas.width)
    fill = _rgba(colour, opacity)
    layer = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(layer)
    if kind in ("circle", "ellipse"):
        draw.ellipse((x, y, x + w, y + h), fill=fill)
    elif kind == "arch":
        r = min(w / 2.0, h)
        draw.rectangle((x, y + r, x + w, y + h), fill=fill)
        draw.pieslice((x, y, x + w, y + 2 * r), 180, 360, fill=fill)
    elif kind in ("panel", "rounded"):
        radius = float(shape.get("radius", 0.04) or 0.0) * min(trim_w, trim_h)
        draw.rounded_rectangle((x, y, x + w, y + h), radius=max(0, radius), fill=fill)
    elif kind == "line":
        weight = max(1, int(min(trim_w, trim_h) * 0.0016 * float(shape.get("weight", 1) or 1)))
        draw.line((x, y, x + w, y + h), fill=fill, width=weight)
    else:
        draw.rectangle((x, y, x + w, y + h), fill=fill)
    rotate = float(shape.get("rotate", 0.0) or 0.0)
    if abs(rotate) > 0.01:
        layer = layer.rotate(-rotate, center=(x + w / 2, y + h / 2), resample=Image.BICUBIC)
    _paste_layer(canvas, layer)


# ---------------------------------------------------------------------- slots
def _mask_for(size: tuple[int, int], clip: str, radius_px: float = 0.0) -> Image.Image | None:
    w, h = size
    if not clip or clip == "rect":
        return None
    mask = Image.new("L", size, 0)
    draw = ImageDraw.Draw(mask)
    clip = clip.lower()
    if clip in ("circle", "oval"):
        draw.ellipse((0, 0, w - 1, h - 1), fill=255)
    elif clip == "arch":
        r = min(w / 2.0, h)
        draw.rectangle((0, r, w - 1, h - 1), fill=255)
        draw.pieslice((0, 0, w - 1, 2 * r), 180, 360, fill=255)
    else:  # rounded
        r = max(1, int(radius_px or min(w, h) * 0.04))
        draw.rounded_rectangle((0, 0, w - 1, h - 1), radius=r, fill=255)
    return mask


def paint_slot(canvas: Image.Image, spec: CardSpec, slot: layouts.Slot,
               palette: config.Palette, trim_w: int, trim_h: int, short: int,
               ox: int, oy: int, bleed_px: int, radius_frac: float = 0.03) -> list[int] | None:
    photo = _photo(spec, slot.photo, {})
    x = ox + slot.x * trim_w
    y = oy + slot.y * trim_h
    w = slot.w * trim_w
    h = slot.h * trim_h
    if photo is None:
        _placeholder(canvas, (x, y, w, h), short, palette, spec.photo_paths[slot.photo].name)
        return None
    # A slot that touches the trim edge may run into the bleed.
    if slot.bleed:
        if slot.x <= 0.005:
            x, w = x - bleed_px, w + bleed_px
        if slot.y <= 0.005:
            y, h = y - bleed_px, h + bleed_px
        if slot.x + slot.w >= 0.995:
            w += bleed_px
        if slot.y + slot.h >= 0.995:
            h += bleed_px
    w, h = max(2, int(round(w))), max(2, int(round(h)))
    fx, fy = slot.focus if slot.focus else photo.face_focus
    tile = photo_mod.cover(photo.image, w, h, focus_x=fx, focus_y=fy)
    treatment = (slot.treatment or "plain").lower()
    radius = max(0.0, radius_frac) * short
    frame_w = max(1, int(round(short * 0.0022))) if treatment == "border" else 0
    if treatment == "shadow":
        tile = photo_mod.shadowed(tile, spread=max(2, int(short * 0.008)), opacity=52)
    if treatment == "tilt":
        tile = photo_mod.tilt(tile, -2.1 if slot.photo % 2 else 2.1)
    if frame_w:
        tile = photo_mod.frame(tile.convert("RGB"), palette.panel, frame_w)
    mask = _mask_for(tile.size, slot.clip, radius)
    rotate = float(slot.rotate or 0.0)
    if abs(rotate) > 0.01:
        tile = tile.convert("RGBA").rotate(-rotate, expand=True, resample=Image.BICUBIC)
        if mask is not None:
            mask = _mask_for(tile.size, slot.clip, radius) if slot.clip not in ("arch", "circle", "oval") else None
    if mask is not None:
        tile = tile.convert("RGBA")
        tile.putalpha(mask)
    px = int(round(x + (w - tile.width) / 2))
    py = int(round(y + (h - tile.height) / 2))
    if tile.mode == "RGBA":
        _paste_layer(canvas, tile, (px, py))
    else:
        canvas.paste(tile, (px, py))
    return [px, py, tile.width, tile.height]


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


def _placeholder(canvas: Image.Image, box: tuple[float, float, float, float], short: int,
                 palette: config.Palette, label: str) -> None:
    x, y, w, h = box
    draw = ImageDraw.Draw(canvas)
    draw.rectangle((x, y, x + w, y + h), fill=palette.panel, outline=palette.accent,
                   width=max(1, int(short * 0.002)))
    font = typefit.BOOK.font("lato", short * 0.014, 400)
    draw.text((x + w / 2, y + h / 2), "photograph missing", font=font, fill=palette.on_panel, anchor="mm")
    draw.text((x + w / 2, y + h / 2 + short * 0.022), label[:32], font=font,
              fill=palette.on_panel, anchor="mm")


# ---------------------------------------------------------------------- lines
def paint_line(canvas: Image.Image, line: dict[str, Any], palette: config.Palette,
               trim_w: int, trim_h: int, short: int, ox: int, oy: int) -> None:
    try:
        x1 = ox + float(line["x1"]) * trim_w
        y1 = oy + float(line["y1"]) * trim_h
        x2 = ox + float(line["x2"]) * trim_w
        y2 = oy + float(line["y2"]) * trim_h
        weight = float(line.get("weight", 1.0))
    except (KeyError, TypeError, ValueError):
        return
    color = _color(palette, str(line.get("token", "accent")), palette.ink)
    width = max(1, int(round(short * 0.0016 * max(0.25, min(3.0, weight)))))
    ImageDraw.Draw(canvas).line((x1, y1, x2, y2), fill=color, width=width)


# ---------------------------------------------------------------------- zones
def paint_zone(canvas: Image.Image, zone: layouts.Zone, spec: CardSpec,
               trim_w: int, trim_h: int, short: int, palette: config.Palette,
               dpi: int, ox: int, oy: int) -> list[dict[str, Any]]:
    x, y = ox + zone.x * trim_w, oy + zone.y * trim_h
    w, h = zone.w * trim_w, zone.h * trim_h
    if w < 8 or h < 8:
        return []
    text = zone.text or spec.text.get(zone.word, "")
    if not typefit.clean(text):
        return []
    size_px = max(4.0, float(zone.size) * short)
    pad = short * 0.006 + float(zone.panel_pad) * min(w, h)
    inner_w = max(6.0, w - 2 * pad)
    inner_h = max(6.0, h - 2 * pad)
    block = typefit.fit(text, zone.word, zone.font, zone.weight, zone.italic, zone.caps,
                        zone.tracking, zone.leading, inner_w, inner_h, size_px,
                        align=zone.align or "left", book=typefit.BOOK)
    if not block.lines:
        return []
    if zone.panel:
        panel_hex = _color(palette, zone.panel)
        overlay = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
        radius = short * 0.012
        ImageDraw.Draw(overlay).rounded_rectangle(
            (x - pad * 0.5, y - pad * 0.5, x + w + pad * 0.5, y + h + pad * 0.5),
            radius=max(0, int(radius)), fill=_rgba(panel_hex, zone.panel_opacity))
        _paste_layer(canvas, overlay)
        bg_hex = panel_hex
        color = readable_zone_color(bg_hex, zone, palette, on_panel=True)
    else:
        bg_hex = _sample_bg(canvas, (x, y, w, h))
        color = readable_zone_color(bg_hex, zone, palette, on_panel=False)
    total = block.height
    free = max(0.0, inner_h - total)
    if zone.valign == "top":
        top = pad
    elif zone.valign == "bottom":
        top = h - pad - total
    else:
        top = pad + free / 2
    align = "right" if zone.align == "right" else ("left" if zone.align == "left" else "center")

    out: list[dict[str, Any]] = []
    rotate = float(zone.rotate or 0.0)
    if abs(rotate) > 0.01:
        margin = int(short * 0.04)
        layer = Image.new("RGBA", (int(w) + margin * 2, int(h) + margin * 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(layer)
        _place_block(draw, block, margin, margin, w, h, pad, top, color, align, out,
                     zone, dpi, bg_hex)
        layer = layer.rotate(-rotate, expand=True, resample=Image.BICUBIC)
        _paste_layer(canvas, layer, (int(x + w / 2 - layer.width / 2),
                                     int(y + h / 2 - layer.height / 2)))
        return out
    draw = ImageDraw.Draw(canvas)
    _place_block(draw, block, x, y, w, h, pad, top, color, align, out, zone, dpi, bg_hex)
    return out


def readable_zone_color(bg_hex: str, zone: layouts.Zone, palette: config.Palette,
                        on_panel: bool = False) -> str:
    if zone.color:
        return _color(palette, zone.color)
    if on_panel:
        return typefit.readable_text(bg_hex, palette.on_panel, "#FFFFFF", "#111111", palette.ink)
    return typefit.readable_text(bg_hex, palette.ink, palette.soft, "#FFFFFF", "#111111")


def _place_block(draw: ImageDraw.ImageDraw, block, x: float, y: float, w: float, h: float,
                 pad: float, top: float, color: str, align: str,
                 out: list[dict[str, Any]], zone: layouts.Zone, dpi: int,
                 bg_hex: str) -> None:
    box = (x + pad, y + top, max(1.0, w - 2 * pad), block.height)
    used = typefit.draw_block(draw, block, box, color, align=align, valign="top")
    out.append({
        "role": block.role,
        "word": block.role,
        "font": zone.font,
        "weight": zone.weight,
        "size": round(zone.size, 4),
        "requested_px": round(block.requested, 1),
        "size_px": block.size,
        "pt": round(block.size * 72 / max(1, dpi), 1),
        "lines": len(block.lines),
        "truncated": block.truncated,
        "shrunk": block.shrunk,
        "zone": [round(zone.x, 4), round(zone.y, 4), round(zone.w, 4), round(zone.h, 4)],
        "used_px": [round(v, 1) for v in used],
        "box_px": [round(x + pad, 1), round(y + top, 1), round(max(1.0, w - 2 * pad), 1), round(h, 1)],
        "layer": zone.layer,
        "color": {"hex": color, "bg": bg_hex,
                  "contrast": round(typefit.contrast(bg_hex, color), 2)},
    })


# -------------------------------------------------------------------- drawing
def render_front(spec: CardSpec, design: layouts.Design | dict[str, Any], dpi: int,
                 bleed: bool = True, texture: bool | None = None,
                 page: str = "front") -> RenderResult:
    if isinstance(design, dict):
        design = layouts.Design.from_dict(design)
    palette = spec.palette
    w_in, h_in = spec.card_inches
    canvas_w, canvas_h, b = canvas_px(spec, dpi, bleed)
    trim_w, trim_h = int(round(w_in * dpi)), int(round(h_in * dpi))
    short = min(trim_w, trim_h)
    ox = oy = b

    canvas = Image.new("RGB", (canvas_w, canvas_h), palette.bg)
    bg_facts = paint_background(canvas, spec, design, palette, trim_w, trim_h, ox, oy)

    chrome = design.chrome or {}
    wants_texture = bool(chrome.get("texture", False)) if texture is None else bool(texture)
    if wants_texture and not bg_facts.get("photo"):
        region = canvas.crop((ox, oy, ox + trim_w, oy + trim_h))
        canvas.paste(_paper(region, hash(spec.name) & 0xFFFF), (ox, oy))

    keepout: list[tuple[float, float, float, float]] = [
        (ox + s.x * trim_w, oy + s.y * trim_h, s.w * trim_w, s.h * trim_h) for s in design.slots
    ]
    keepout += [(ox + z.x * trim_w, oy + z.y * trim_h, z.w * trim_w, z.h * trim_h) for z in design.zones]

    decoration = str(chrome.get("decoration") or "none").lower()
    if design.ornaments:
        _draw_ornaments(canvas, palette, trim_w, trim_h, keepout, design, spec.name, ox, oy)
    if decoration not in ("", "none"):
        density = float(chrome.get("density", 0.5) or 0.0)
        decorate.decorate(canvas, decoration, density, palette,
                          trim_w, trim_h, keepout, seed=_seed(spec.name) + 11,
                          offset=(ox, oy))
    border = str(chrome.get("border") or "none").lower()
    if border not in ("", "none") and not bg_facts.get("photo"):
        inset = float(config.limit("margin", "border", 0.055)) * short
        decorate.border(canvas, border, palette, trim_w, trim_h, inset, offset=(ox, oy))

    photo_rects: list[list[int]] = []
    blocks: list[dict[str, Any]] = []
    ops: list[tuple[int, int, str, Any]] = []
    for shape in design.shapes:
        ops.append((int(shape.get("layer", 0) or 0), 0, "shape", shape))
    for slot in design.slots:
        ops.append((slot.layer, 1, "slot", slot))
    for line in design.lines:
        ops.append((int(line.get("layer", 0) or 0), 2, "line", line))
    for zone in design.zones:
        ops.append((zone.layer, 3, "zone", zone))
    ops.sort(key=lambda item: (item[0], item[1]))

    for layer, _, kind, item in ops:
        if kind == "shape":
            paint_shape(canvas, item, palette, trim_w, trim_h, ox, oy)
        elif kind == "slot":
            rect = paint_slot(canvas, spec, item, palette, trim_w, trim_h, short, ox, oy, b,
                              float(config.limit("slots", "radius", 0.03)))
            if rect:
                photo_rects.append(rect)
        elif kind == "line":
            paint_line(canvas, item, palette, trim_w, trim_h, short, ox, oy)
        else:
            blocks.extend(paint_zone(canvas, item, spec, trim_w, trim_h, short, palette,
                                     dpi, ox, oy))

    return RenderResult(canvas, {
        "page": page,
        "design": design.label,
        "engine": design.engine,
        "card_in": [w_in, h_in],
        "trim_px": [trim_w, trim_h],
        "bleed_px": b,
        "dpi": dpi,
        "background": bg_facts,
        "shapes": len(design.shapes),
        "layers": sorted({item[0] for item in ops}),
        "photo_rects": photo_rects,
        "blocks": blocks,
        "zones": [z.to_dict() for z in design.zones],
        "slots": [s.to_dict() for s in design.slots],
    })


def _seed(name: str) -> int:
    return abs(hash(name)) % 100_000


def _draw_ornaments(canvas: Image.Image, palette: config.Palette,
                    trim_w: int, trim_h: int, keepout: list[tuple[float, float, float, float]],
                    design: layouts.Design, name: str, ox: int, oy: int) -> None:
    for i, item in enumerate(design.ornaments):
        kind = str(item.get("kind", "none")).lower()
        if kind not in ("holly", "snow", "stars", "confetti"):
            continue
        try:
            density = max(0.0, min(1.6, float(item.get("density", 0.5))))
        except (TypeError, ValueError):
            density = 0.5
        decorate.decorate(canvas, kind, density, palette, trim_w, trim_h, keepout,
                          seed=_seed(name) + 97 * (i + 1), offset=(ox, oy))


def preview(spec: CardSpec, design: layouts.Design | dict[str, Any], width_px: int = 760) -> RenderResult:
    w_in, _ = spec.card_inches
    dpi = max(48, int(width_px / w_in))
    return render_front(spec, design, dpi, bleed=False, texture=None)
