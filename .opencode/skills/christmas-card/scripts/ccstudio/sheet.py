"""A contact sheet of the compositions that have actually been written."""
from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

from . import compose, render, typefit
from .spec import CardSpec


def build_sheet(spec: CardSpec, designs=None, out: Path | None = None,
                tile_w: int = 620) -> Path:
    if designs is None:
        designs = [compose.design(c) for c in spec.compositions]
    if not designs:
        raise ValueError("no compositions to show yet")
    out = Path(out) if out else spec.folder / "out" / "designs.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    tiles = []
    for design in designs:
        result = render.preview(spec, design, width_px=tile_w)
        tiles.append((design, result.image))
    cols = 2 if len(tiles) <= 4 else 3
    rows = (len(tiles) + cols - 1) // cols
    gap = 18
    label_h = 34
    tw = max(t.width for _, t in tiles)
    th = max(t.height for _, t in tiles)
    sheet = Image.new("RGB", (cols * tw + gap * (cols + 1),
                             rows * (th + label_h) + gap * (rows + 1)), (243, 240, 233))
    draw = ImageDraw.Draw(sheet)
    font = typefit.BOOK.font("lato", 19, 700)
    small = typefit.BOOK.font("lato", 15, 400)
    selected = spec.front()
    for i, (design, tile) in enumerate(tiles):
        col, row = i % cols, i // cols
        x = gap + col * (tw + gap) + (tw - tile.width) // 2
        y = gap + row * (th + label_h + gap)
        sheet.paste(tile, (x, y))
        is_selected = selected is not None and design.label == str(selected.get("name") or design.label)
        draw.text((x, y + tile.height + 5), design.label[:46], font=font,
                  fill=(30, 40, 36) if is_selected else (70, 76, 72))
        meta = f"{len(design.slots)} photos, {design.coverage * 100:.0f}% coverage"
        draw.text((x, y + tile.height + 5), meta, font=small, fill=(120, 120, 112), anchor="ra")
        if is_selected:
            draw.rectangle((x - 2, y - 2, x + tile.width + 2, y + tile.height + 2),
                           outline=(176, 141, 79), width=3)
    sheet.save(out, quality=90, optimize=True)
    return out
