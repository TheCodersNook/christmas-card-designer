"""Print-ready output: PDF, PNG and JPEG at true physical size."""
from __future__ import annotations

import io
import json
from pathlib import Path
from typing import Any

from PIL import Image
from reportlab.lib.colors import Color
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

from . import config, render
from .spec import CardSpec


class ExportError(RuntimeError):
    pass


def export(spec: CardSpec, design, fmt: str | None = None, dpi: int | None = None,
           bleed: bool | None = None, crop_marks: bool | None = None, back: bool | None = None,
           quality: int | None = None, draft: bool = False, out_dir: Path | None = None,
           back_design=None) -> dict[str, Any]:
    fmt = (fmt or spec.export.get("format") or "pdf").lower()
    if fmt == "jpg":
        fmt = "jpeg"
    if fmt not in ("pdf", "png", "jpeg"):
        raise ExportError(f"unknown format {fmt!r} (use pdf, png or jpeg)")
    dpi = int(dpi or spec.export.get("dpi") or 300)
    if draft:
        dpi = min(dpi, 120)
    dpi = max(config.MIN_DPI, min(config.MAX_DPI, dpi))
    bleed = spec.export.get("bleed", True) if bleed is None else bleed
    crop_marks = spec.export.get("crop_marks", True) if crop_marks is None else crop_marks
    back = spec.export.get("back", True) if back is None else back
    quality = int(quality or spec.export.get("jpeg_quality") or 95)

    out = Path(out_dir) if out_dir else spec.folder / "out"
    out.mkdir(parents=True, exist_ok=True)
    stem = spec.name if not draft else f"{spec.name}-draft"

    front = render.render_front(spec, design, dpi, bleed=bleed)
    pages = [("front", front)]
    if back and back_design is not None:
        pages.append(("back", render.render_front(spec, back_design, dpi, bleed=bleed, page="back")))

    written: list[dict[str, Any]] = []
    if fmt == "pdf":
        path = out / f"{stem}.pdf"
        _write_pdf(spec, pages, path, bleed, crop_marks)
        written.append({"path": _rel(spec, path), "format": "pdf", "bytes": path.stat().st_size,
                        "pages": [{"w_in": _page_in(spec, bleed)[0], "h_in": _page_in(spec, bleed)[1],
                                   "side": side} for side, _ in pages],
                        "trim_px": front.metrics["trim_px"], "dpi": dpi})
    else:
        for side, page in pages:
            suffix = "" if side == "front" else "-back"
            ext = ".png" if fmt == "png" else ".jpg"
            path = out / f"{stem}{suffix}{ext}"
            if fmt == "png":
                page.image.save(path, format="PNG", dpi=(dpi, dpi), optimize=True)
            else:
                page.image.save(path, format="JPEG", quality=quality, subsampling=0,
                                dpi=(dpi, dpi), optimize=True)
            written.append({"path": _rel(spec, path), "format": fmt, "bytes": path.stat().st_size,
                            "px": [page.image.width, page.image.height], "trim_px": page.metrics["trim_px"],
                            "dpi": dpi, "side": side})

    manifest = {
        "name": spec.name,
        "generated_with": "ccb",
        "design": design.label if hasattr(design, "label") else str(design.get("label")),
        "engine": "composition",
        "dpi": dpi,
        "bleed_in": config.BLEED_IN if bleed else 0.0,
        "crop_marks": bool(crop_marks and bleed),
        "pages": [side for side, _ in pages],
        "files": written,
        "blocks": front.metrics.get("blocks", []),
    }
    (out / "export.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def _page_in(spec: CardSpec, bleed: bool) -> tuple[float, float]:
    w, h = spec.card_inches
    extra = 2 * config.BLEED_IN if bleed else 0.0
    return round(w + extra, 4), round(h + extra, 4)


def _rel(spec: CardSpec, path: Path) -> str:
    try:
        return str(path.relative_to(spec.folder))
    except ValueError:
        return str(path)


def _write_pdf(spec: CardSpec, pages: list[tuple[str, render.RenderResult]], path: Path,
               bleed: bool, crop_marks: bool) -> None:
    w_in, h_in = _page_in(spec, bleed)
    page_w, page_h = w_in * 72.0, h_in * 72.0
    c = pdfcanvas.Canvas(str(path), pagesize=(page_w, page_h), pageCompression=1)
    c.setTitle(f"{spec.text.get('family') or spec.name} - Christmas card")
    c.setAuthor("CCB Christmas Card Studio")
    c.setSubject("Print-ready Christmas card")
    c.setCreator("CCB - the Christmas card studio for OpenCode")
    for side, page in pages:
        buf = io.BytesIO()
        page.image.save(buf, format="PNG", optimize=False)
        buf.seek(0)
        c.drawImage(ImageReader(buf), 0, 0, width=page_w, height=page_h,
                    preserveAspectRatio=False, mask=None)
        if crop_marks and bleed:
            _crop_marks(c, spec.card_inches[0], spec.card_inches[1])
        c.showPage()
    c.save()


def _crop_marks(c: pdfcanvas.Canvas, trim_w_in: float, trim_h_in: float) -> None:
    b = config.BLEED_IN * 72.0
    w = (trim_w_in + 2 * config.BLEED_IN) * 72.0
    h = (trim_h_in + 2 * config.BLEED_IN) * 72.0
    c.saveState()
    c.setStrokeColor(Color(0, 0, 0, alpha=0.8))
    c.setLineWidth(0.35)
    length = min(18.0, b * 0.8)
    for x, y, sx, sy in ((b, b, -1, -1), (w - b, b, 1, -1), (b, h - b, -1, 1), (w - b, h - b, 1, 1)):
        c.line(x, y, x + sx * length, y)
        c.line(x, y, x, y + sy * length)
    c.restoreState()


def verify_files(spec: CardSpec, manifest: dict[str, Any]) -> list[str]:
    """Read the files back: real PDF page boxes, real PNG sizes, real DPI metadata."""
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
            problems.extend(_verify_raster(path, item))
    return problems


def _verify_pdf(path: Path, item: dict[str, Any]) -> list[str]:
    problems = []
    raw = path.read_bytes()
    pages = raw.count(b"/Type /Page") + raw.count(b"/Type/Page")
    pages -= raw.count(b"/Type /Pages") + raw.count(b"/Type/Pages")
    if pages != len(item.get("pages", [])):
        problems.append(f"{path.name}: {pages} pages, expected {len(item.get('pages', []))}")
    import re
    boxes = re.findall(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", raw)
    if not boxes:
        problems.append(f"{path.name}: no MediaBox found")
    else:
        w, h = (float(v) for v in boxes[0])
        expected = item["pages"][0]
        if abs(w - expected["w_in"] * 72) > 1.0 or abs(h - expected["h_in"] * 72) > 1.0:
            problems.append(f"{path.name}: page is {w / 72:.2f} x {h / 72:.2f} in, expected "
                            f"{expected['w_in']:.2f} x {expected['h_in']:.2f} in")
    return problems


def _verify_raster(path: Path, item: dict[str, Any]) -> list[str]:
    problems = []
    with Image.open(path) as img:
        dpi = img.info.get("dpi")
        if item.get("px") and list(img.size) != list(item["px"]):
            problems.append(f"{path.name}: {img.size[0]}x{img.size[1]} px, expected {item['px']}")
        if dpi and item.get("dpi") and abs(float(dpi[0]) - float(item["dpi"])) > 1.5:
            problems.append(f"{path.name}: {dpi[0]:.0f} DPI metadata, expected {item['dpi']}")
    return problems
