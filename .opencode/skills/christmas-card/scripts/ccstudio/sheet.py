"""The contact sheet: every candidate design on one page, with its score."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from . import layouts, render, typefit
from .spec import CardSpec


def build_sheet(spec: CardSpec, designs: list[layouts.Design], out: Path, tile_w: int = 620) -> Path:
    if not designs:
        raise ValueError("no designs to draw")
    cols = 2 if len(designs) > 1 else 1
    rows = (len(designs) + cols - 1) // cols
    margin, gap, label_h, header_h = 34, 26, 66, 86
    tiles = []
    for design in designs:
        result = render.preview(spec, design, width_px=tile_w)
        img = result.image.convert("RGB")
        scale = tile_w / img.width
        img = img.resize((tile_w, int(round(img.height * scale))), Image.LANCZOS)
        tiles.append(img)
    tile_h = max(t.height for t in tiles)
    width = margin * 2 + cols * tile_w + (cols - 1) * gap
    height = margin * 2 + header_h + rows * (tile_h + label_h) + (rows - 1) * gap
    sheet = Image.new("RGB", (width, height), "#12161B")
    draw = ImageDraw.Draw(sheet)
    title_font = typefit.BOOK.font("lato", 30, 700)
    sub_font = typefit.BOOK.font("lato", 17, 400)
    label_font = typefit.BOOK.font("lato", 19, 700)
    small_font = typefit.BOOK.font("lato", 16, 400)
    draw.text((margin, margin - 6), spec.name.replace("-", " ").title(), font=title_font, fill="#F4F1E8")
    draw.text((margin, margin + 32),
              f"{spec.style.label}  ·  {spec.palette.label}  ·  "
              f"{spec.card_inches[0]:g} x {spec.card_inches[1]:g} in  ·  "
              f"{len(spec.photo_paths)} photographs  ·  {len(designs)} designs",
              font=sub_font, fill="#98A2AC")
    for i, (design, tile) in enumerate(zip(designs, tiles)):
        col, row = i % cols, i // cols
        x = margin + col * (tile_w + gap)
        y = margin + header_h + row * (tile_h + label_h + gap)
        selected = i == spec.selected
        if selected:
            draw.rectangle((x - 5, y - 5, x + tile_w + 5, y + tile_h + 5), outline="#C9A227", width=3)
        sheet.paste(tile, (x, y))
        draw.rectangle((x, y + tile_h, x + tile_w, y + tile_h + label_h), fill="#1A2027")
        draw.text((x + 12, y + tile_h + 9), f"{i + 1}. {design.label}", font=label_font, fill="#F4F1E8")
        note = "SELECTED  ·  " if selected else ""
        draw.text((x + 12, y + tile_h + 36), f"{note}score {design.score:.1f}  ·  {design.engine}",
                  font=small_font, fill="#C9A227" if selected else "#98A2AC")
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, format="JPEG", quality=88, optimize=True)
    return out
