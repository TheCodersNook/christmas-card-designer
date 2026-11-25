"""Seeing: annotated previews and a visual report for the agent.

A model that can read images should open ``out/see/front.png`` and
``out/see/photos.jpg``. A model that cannot gets ``out/see/visual.md``: the same
measurements, face positions and warnings in words. Neither claims more than the
detector and the renderer actually measured.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw

from . import compose, config, faces as faces_mod, layouts, photos as photo_mod, render, typefit
from .spec import CardSpec

ACCENT = (176, 141, 79)
INK = (30, 40, 36)
FACE = (200, 40, 40)
ZONE = (40, 110, 200)
SLOT = (20, 120, 80)


def _font(px: int):
    try:
        return typefit.BOOK.font("lato", max(11, int(px)), 700)
    except Exception:
        return None


def annotate(spec: CardSpec, design: layouts.Design, width: int = 1400,
             stats: list[photo_mod.Photo] | None = None) -> Image.Image:
    w_in, _ = spec.card_inches
    dpi = max(48, int(width / max(0.1, w_in)))
    result = render.render_front(spec, design, dpi, bleed=False, texture=False)
    art = result.image.convert("RGB").copy()
    draw = ImageDraw.Draw(art)
    W, H = art.size
    short = min(W, H)
    label_font = _font(short * 0.017)
    m = spec.style.margin
    draw.rectangle((m * W, m * H, (1 - m) * W, (1 - m) * H), outline=ACCENT, width=max(1, int(short * 0.002)))

    stats = stats or compose.load_photo_stats(spec)
    for i, slot in enumerate(design.slots):
        x, y, w, h = slot.x * W, slot.y * H, slot.w * W, slot.h * H
        draw.rectangle((x, y, x + w, y + h), outline=SLOT, width=max(1, int(short * 0.0025)))
        _tag(draw, (x + 4, y + 3), f"photo {slot.photo}", SLOT, label_font)
        if 0 <= slot.photo < len(stats):
            photo = stats[slot.photo]
            if photo.faces:
                fx, fy = slot.focus or photo.face_focus
                box = faces_mod.crop_box(photo.width, photo.height, max(1, int(w)), max(1, int(h)),
                                         float(fx), float(fy))
                for face in photo.faces:
                    bx = x + ((face.x * photo.width - box[0]) / max(1, box[2])) * w
                    by = y + ((face.y * photo.height - box[1]) / max(1, box[3])) * h
                    bw = (face.w * photo.width / max(1, box[2])) * w
                    bh = (face.h * photo.height / max(1, box[3])) * h
                    draw.rectangle((bx, by, bx + bw, by + bh), outline=FACE, width=max(1, int(short * 0.003)))
                _tag(draw, (x + w - 4, y + 3), f"{len(photo.faces)} face"
                     f"{'s' if len(photo.faces) != 1 else ''}", FACE, label_font, right=True)

    for i, zone in enumerate(design.zones):
        x, y, w, h = zone.x * W, zone.y * H, zone.w * W, zone.h * H
        draw.rectangle((x, y, x + w, y + h), outline=ZONE, width=max(1, int(short * 0.0018)))
        _tag(draw, (x + 4, y + 3), "+".join(zone.roles), ZONE, label_font)

    _tag(draw, (8, H - short * 0.03), f"{design.label}  {w_in:g} in wide", (255, 255, 255),
         label_font, bg=(30, 40, 36))
    return art


def _tag(draw: ImageDraw.ImageDraw, xy: tuple[float, float], text: str, color: tuple[int, int, int],
         font, right: bool = False, bg: tuple[int, int, int] = (255, 255, 255)) -> None:
    if font is None:
        return
    w = draw.textlength(text, font=font)
    x, y = xy
    if right:
        x -= w
    pad = 3
    draw.rectangle((x - pad, y - pad, x + w + pad, y + font.size + pad), fill=bg)
    draw.text((x, y), text, font=font, fill=color)


def photos_sheet(spec: CardSpec, stats: list[photo_mod.Photo] | None = None,
                 tile: int = 520, columns: int = 3) -> Image.Image:
    stats = stats or compose.load_photo_stats(spec)
    if not stats:
        img = Image.new("RGB", (tile, int(tile * 0.5)), (245, 242, 235))
        ImageDraw.Draw(img).text((20, 20), "no readable photographs", fill=(40, 40, 40))
        return img
    rows = (len(stats) + columns - 1) // columns
    pad = 18
    height = int(tile * 0.72)
    sheet = Image.new("RGB", (columns * tile + pad * (columns + 1),
                              rows * (height + 46) + pad * (rows + 1)), (246, 243, 236))
    draw = ImageDraw.Draw(sheet)
    font = _font(tile * 0.036)
    for i, photo in enumerate(stats):
        col, row = i % columns, i // columns
        x = pad + col * (tile + pad)
        y = pad + row * (height + 46 + pad)
        thumb = photo.image.copy()
        thumb.thumbnail((tile, height), Image.LANCZOS)
        tw, th = thumb.size
        ox, oy = x + (tile - tw) // 2, y + (height - th) // 2
        sheet.paste(thumb, (ox, oy))
        for face in photo.faces:
            draw.rectangle((ox + face.x * tw, oy + face.y * th,
                            ox + (face.x + face.w) * tw, oy + (face.y + face.h) * th),
                           outline=FACE, width=max(2, int(tile * 0.006)))
        label = f"[{i}] {photo.path.name[:32]}  {photo.width}x{photo.height}"
        if photo.faces:
            label += f"  {faces_mod.describe(photo.faces)}"
        draw.text((x, y + height + 6), label, font=font, fill=INK)
    return sheet


def visual_md(spec: CardSpec, stats: list[photo_mod.Photo] | None = None) -> str:
    stats = stats or compose.load_photo_stats(spec)
    det = faces_mod.status()
    lines = [f"# What is on the card: {spec.name}", ""]
    if not det["opencv"]:
        lines += ["OpenCV is not installed, so no faces were detected. Run ./ccb faces after installing it.", ""]
    elif not det["model"]:
        lines += ["The YuNet model is not installed; Haar was used if it was available. Run ./ccb faces.", ""]
    lines += [
        f"Direction {spec.style.label}; palette {spec.palette.label}.",
        f"Photographs: {len(stats)}. Detector: {det['detector']}.",
        "",
        "## Photographs",
    ]
    for i, photo in enumerate(stats):
        faces = "; ".join(
            f"face at {f.cx * 100:.0f}%, {f.cy * 100:.0f}% ({f.w * 100:.0f}% wide, score {f.score:.2f})"
            for f in photo.faces) or "no faces"
        lines.append(f"- [{i}] {photo.path.name}: {photo.width}x{photo.height}, {photo.orientation}, "
                     f"interest {photo.interest:.2f}; {faces}")
    for comp in spec.compositions:
        design = compose.design(comp)
        lines += ["", f"## {design.label} ({comp.get('side', 'front')})", ""]
        lines.append(f"Photographs cover {design.coverage * 100:.0f}% of the page; "
                     f"{len(design.slots)} slots, {len(design.zones)} text zones.")
        for i, slot in enumerate(design.slots):
            photo = stats[slot.photo] if 0 <= slot.photo < len(stats) else None
            face_note = ""
            if photo and photo.faces:
                fx, fy = slot.focus or photo.face_focus
                box = faces_mod.crop_box(photo.width, photo.height,
                                        max(1, int(slot.w * 1200)), max(1, int(slot.h * 1600)),
                                        float(fx), float(fy))
                keep = min(faces_mod.keep_ratio(f, box, photo.width, photo.height) for f in photo.faces)
                face_note = f", faces keep {keep * 100:.0f}%"
            lines.append(f"- slot {i + 1}: photo {slot.photo} at "
                         f"x {slot.x:.3f} y {slot.y:.3f} w {slot.w:.3f} h {slot.h:.3f}{face_note}")
        for i, zone in enumerate(design.zones):
            lines.append(f"- zone {i + 1}: {', '.join(zone.roles)} at "
                         f"x {zone.x:.3f} y {zone.y:.3f} w {zone.w:.3f} h {zone.h:.3f}; "
                         f"align {zone.align or spec.style.align}, scale {zone.scale:g}")
        issues = compose.validate_composition(comp, spec, spec.card_inches, stats)
        for issue in issues:
            lines.append(f"- {issue.level.upper()} {issue.code}: {issue.message}")
    lines += [
        "",
        "## How to look",
        "If your model can read images, open out/see/front.png (annotated: green = photograph,",
        "blue = text zone, red = face) and out/see/photos.jpg before changing a composition.",
        "If it cannot, rely on this file and say so rather than pretending to see the picture.",
        "",
    ]
    return "\n".join(lines)


def write(spec: CardSpec, width: int = 1400) -> Path:
    out = spec.folder / "out" / "see"
    out.mkdir(parents=True, exist_ok=True)
    stats = compose.load_photo_stats(spec)
    front = spec.front_design()
    if front is not None:
        annotate(spec, front, width, stats).save(out / "front.png", optimize=True)
    back = spec.back_design()
    if back is not None:
        annotate(spec, back, width, stats).save(out / "back.png", optimize=True)
    photos_sheet(spec, stats).save(out / "photos.jpg", quality=88, optimize=True)
    (out / "visual.md").write_text(visual_md(spec, stats), encoding="utf-8")
    (out / "visual.json").write_text(json.dumps({
        "photos": [
            {"name": p.path.name, "width": p.width, "height": p.height,
             "faces": [{"x": round(f.x, 4), "y": round(f.y, 4), "w": round(f.w, 4),
                        "h": round(f.h, 4), "score": round(f.score, 3)} for f in p.faces]}
            for p in stats],
        "compositions": [c.get("name", "composition") for c in spec.compositions],
        "detector": faces_mod.status(),
    }, indent=2) + "\n", encoding="utf-8")
    return out
