"""decks/<name>/deck.json: a 16:9 presentation written as compositions.

Each slide is the same kind of free composition a card uses: slots, zones,
ornaments and rules in fractions of the slide. There are no fixed slide kinds.
The engine validates, renders, exports and verifies; the agent composes.
"""
from __future__ import annotations

import io
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as pdfcanvas

from . import compose, config, render, typefit
from .layouts import Design
from .spec import SpecError, resolve, safe_name, unique_card_dir


DEFAULT_TEXT = {
    "title": "",
    "subtitle": "",
    "greeting": "Merry Christmas",
    "message": "",
    "signature": "",
    "year": "",
}
DECK_TEXT_ROLES = ("title", "subtitle", "greeting", "message", "signature", "year")

DEFAULT_DESIGN = {
    "direction": "editorial",
    "palette": "brass",
    "compositions": [],
}
DEFAULT_EXPORT = {"format": "pdf", "dpi": 150, "png": False}

SLIDE_IN = config.CANVAS_16X9


@dataclass
class DeckSpec:
    path: Path
    data: dict[str, Any]

    # ------------------------------------------------------------------ load
    @classmethod
    def load(cls, path: str | Path) -> "DeckSpec":
        p = Path(path).expanduser()
        if p.is_dir():
            p = p / "deck.json"
        if not p.exists():
            raise SpecError(f"no deck.json at {p} (run ./ccb deck new <photos...> first)")
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise SpecError(f"{p} is not valid JSON: {exc}") from exc
        return cls(p.resolve(), normalise(data, p))

    @classmethod
    def create(cls, folder: Path, name: str, photos: list[str], **design) -> "DeckSpec":
        data = {
            "name": name,
            "photos": photos,
            "text": dict(DEFAULT_TEXT),
            "design": {**DEFAULT_DESIGN, **{k: v for k, v in design.items() if v not in (None, "")}},
            "export": dict(DEFAULT_EXPORT),
        }
        folder.mkdir(parents=True, exist_ok=True)
        spec = cls(folder / "deck.json", normalise(data, folder / "deck.json"))
        spec.save()
        return spec

    # ---------------------------------------------------------------- access
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
    def slides(self) -> list[dict[str, Any]]:
        return self.compositions

    @property
    def photo_paths(self) -> list[Path]:
        return [resolve(self.folder, item) for item in self.data.get("photos", [])]

    def photo_for(self, index: int) -> Path:
        paths = self.photo_paths
        return paths[max(0, min(len(paths) - 1, index))]

    @property
    def style(self) -> config.Style:
        return config.style(self.design.get("direction"))

    @property
    def palette(self) -> config.Palette:
        return config.palette(self.design.get("palette") or self.style.palette)

    @property
    def card_inches(self) -> tuple[float, float]:
        return SLIDE_IN

    def save(self) -> None:
        self.path.write_text(json.dumps(self.data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def normalise(data: dict[str, Any], path: Path) -> dict[str, Any]:
    data.setdefault("name", path.parent.name)
    data["photos"] = [str(p) for p in (data.get("photos") or [])]
    text = data.get("text") if isinstance(data.get("text"), dict) else {}
    data["text"] = {**DEFAULT_TEXT, **{k: ("" if v is None else str(v).strip())
                                      for k, v in text.items() if k in DEFAULT_TEXT}}
    design = data.get("design") if isinstance(data.get("design"), dict) else {}
    design = {**DEFAULT_DESIGN, **design}
    if isinstance(design.get("slides"), list) and not design.get("compositions"):
        design["compositions"] = design.pop("slides")
    design.pop("slides", None)
    if "style" in design and not design.get("direction"):
        design["direction"] = design.pop("style")
    data["design"] = design
    if not isinstance(design.get("compositions"), list):
        design["compositions"] = []
    export = data.get("export") if isinstance(data.get("export"), dict) else {}
    export = {**DEFAULT_EXPORT, **export}
    try:
        export["dpi"] = max(96, min(600, int(export.get("dpi", 150))))
    except (TypeError, ValueError):
        export["dpi"] = 150
    data["export"] = export
    return data


class _View:
    """Makes a deck look enough like a card for the one renderer."""

    def __init__(self, spec: DeckSpec, page: int):
        self.card_inches = SLIDE_IN
        self.style = spec.style
        self.palette = spec.palette
        self.photo_paths = spec.photo_paths
        self.text = spec.text
        self.name = f"{spec.name}-{page:02d}"


def render_slide(spec: DeckSpec, comp: dict[str, Any], dpi: int, page: int = 1) -> render.RenderResult:
    return render.render_front(_View(spec, page), compose.design(comp), dpi, bleed=False,
                               texture=None, page=f"slide {page}")


def install(spec: DeckSpec, payload: Any, append: bool = False) -> tuple[list[compose.Issue], int]:
    comps = compose.normalise_payload(payload)
    stats = compose.load_photo_stats(spec)  # type: ignore[arg-type]
    issues: list[compose.Issue] = []
    for i, comp in enumerate(comps):
        comp.pop("side", None)
        issues.extend(compose.validate_composition(comp, spec, SLIDE_IN, stats))  # type: ignore[arg-type]
    if any(i.level == "error" for i in issues):
        return issues, 0
    if append:
        spec.compositions.extend(comps)
    else:
        spec.design["compositions"] = comps
    spec.save()
    return issues, len(spec.compositions)


def brief(spec: DeckSpec) -> str:
    dpi = int(spec.export.get("dpi", 150) or 150)
    lines = [
        f"# Presentation brief: {spec.name}",
        "",
        f"Canvas       13.333 x 7.5 in (16:9), {dpi} dpi = 2000 x 1125 px; no bleed, no crop marks",
        f"Direction    {spec.style.label} - {spec.style.blurb}",
        f"             {spec.style.guidance}",
        f"Palette      {spec.palette.label}  bg {spec.palette.bg}  ink {spec.palette.ink}  accent {spec.palette.accent}  panel {spec.palette.panel}",
        "",
        "## The rulebook",
        compose.rule_digest(),
        "",
        "## Photographs",
    ]
    stats = compose.load_photo_stats(spec)  # type: ignore[arg-type]
    for i, path in enumerate(spec.photo_paths):
        photo = stats[i] if i < len(stats) else None
        if photo is None:
            lines.append(f"  [{i}] {path.name}  (unreadable)")
            continue
        lines.append(f"  [{i}] {path.name}  {photo.width}x{photo.height}  {photo.orientation}  "
                     f"interest {photo.interest:.2f}  {len(photo.faces)} face(s)")
    lines += ["", "## Words"]
    for role in DECK_TEXT_ROLES:
        lines.append(f"  {role:<10} {spec.text.get(role) or '(empty)'}")
    lines += [
        "",
        "## What to write",
        "Write every slide yourself: there are no slide kinds to pick from, and the engine",
        "draws only what you declare (no frame, no decoration, no texture unless asked).",
        "Two slides should not share a skeleton: vary the background, the column, the crop",
        "shape, the scale of the type. A deck reads well with a cover, one slide per strong",
        "photograph, a statement, a gallery for the rest and a closing - that is advice.",
        "Every photograph should appear once; no more than six in one gallery.",
        "Each slide is {name, background, shapes, slots, zones, ornaments, lines, chrome};",
        "use a zone's 'text' field for captions and page numbers. A full-bleed photograph",
        "behind a scrim, with the title on it ('over_photo': true), is the strongest cover.",
        "Coordinates are fractions of the 16:9 page; faces are kept whole by the",
        "face-aware crop. ./ccb deck layout validates before saving.",
        "",
        "Then ./ccb deck check, ./ccb deck see, ./ccb deck render, ./ccb deck qa.",
        "",
        "## Shape of the file",
        json.dumps({"slides": [{"name": "Cover", "slots": [], "zones": [], "ornaments": [], "lines": []}]}, indent=2),
    ]
    return "\n".join(lines)


def typography(spec: DeckSpec, comps: list[dict[str, Any]]) -> tuple[list[str], list[str], dict[str, Any]]:
    errors: list[str] = []
    warnings: list[str] = []
    blocks_all = []
    for i, comp in enumerate(comps):
        design = compose.design(comp)
        try:
            result = render_slide(spec, comp, 90, i + 1)
        except Exception as exc:
            errors.append(f"{design.label}: could not draw the slide ({exc})")
            continue
        for block in result.metrics.get("blocks", []):
            block["slide"] = i + 1
            blocks_all.append(block)
            if block.get("truncated"):
                warnings.append(f"slide {i + 1}: the {block['role']} was shortened to fit")
            if block["role"] in ("message", "caption", "subtitle") and block["pt"] < 7.5:
                warnings.append(f"slide {i + 1}: the {block['role']} prints at {block['pt']:.1f} pt")
            if block.get("color", {}).get("contrast", 9) < 3.0:
                warnings.append(f"slide {i + 1}: {block['role']} contrast is {block['color']['contrast']}:1")
    facts = {
        "blocks": blocks_all,
        "smallest_pt": min((b["pt"] for b in blocks_all), default=0),
        "largest_pt": max((b["pt"] for b in blocks_all), default=0),
    }
    return errors, warnings, facts


def check(spec: DeckSpec, comps: list[dict[str, Any]] | None = None, dpi: int = 150) -> dict[str, Any]:
    comps = comps if comps is not None else spec.compositions
    if not comps:
        return {"errors": ["no slides yet - read ./ccb deck brief and write them"],
                "warnings": [], "facts": {}}
    errors: list[str] = []
    warnings: list[str] = []
    stats = compose.load_photo_stats(spec)  # type: ignore[arg-type]
    for comp in comps:
        issues = compose.validate_composition(comp, spec, SLIDE_IN, stats)  # type: ignore[arg-type]
        errors += [f"{comp.get('name', 'slide')}: {i.message}" for i in issues if i.level == "error"]
        warnings += [f"{comp.get('name', 'slide')}: {i.message}" for i in issues if i.level == "warn"]
    e2, w2, facts = typography(spec, comps)
    errors += e2
    warnings += w2
    used = {int(s.get("photo")) for c in comps for s in c.get("slots", [])
            if isinstance(s, dict) and str(s.get("photo", "")).lstrip("-").isdigit()}
    for i, path in enumerate(spec.photo_paths):
        if i not in used:
            warnings.append(f"photograph {i} ({path.name}) is not on any slide")
    if not str(spec.text.get("title", "")).strip():
        warnings.append("the deck has no title")
    facts.update({
        "slides": len(comps),
        "photos": len(spec.photo_paths),
        "canvas_in": list(SLIDE_IN),
        "style": spec.style.label,
        "palette": spec.palette.label,
        "dpi": dpi,
    })
    return {"errors": errors, "warnings": warnings, "facts": facts}


def print_report(report: dict[str, Any]) -> bool:
    facts = report.get("facts", {})
    if facts:
        print(f"deck    {facts.get('slides')} slides, {facts.get('photos')} photographs")
        print(f"screen  {facts.get('canvas_in', ['?', '?'])[0]:g} x {facts.get('canvas_in', ['?', '?'])[1]:g} in (16:9), "
              f"{facts.get('dpi')} DPI")
        print(f"theme   {facts.get('style')} / {facts.get('palette')}")
        if facts.get("smallest_pt"):
            print(f"type    {facts['smallest_pt']:.1f}-{facts['largest_pt']:.1f} pt")
    for warning in dict.fromkeys(report.get("warnings", [])):
        print(f"WARN  {warning}")
    for error in dict.fromkeys(report.get("errors", [])):
        print(f"ERROR {error}")
    if not report.get("errors"):
        print("gate: 0 errors")
    return not report.get("errors")


def export(spec: DeckSpec, comps: list[dict[str, Any]] | None = None, dpi: int | None = None,
           png: bool | None = None, out_dir: Path | None = None) -> dict[str, Any]:
    comps = comps if comps is not None else spec.compositions
    if not comps:
        raise SpecError("no slides to render")
    dpi = max(96, min(600, int(dpi or spec.export.get("dpi") or 150)))
    png = bool(spec.export.get("png", False) if png is None else png)
    out = Path(out_dir) if out_dir else spec.folder / "out"
    out.mkdir(parents=True, exist_ok=True)
    pages = [render_slide(spec, comp, dpi, i + 1) for i, comp in enumerate(comps)]
    width_pt, height_pt = SLIDE_IN[0] * 72.0, SLIDE_IN[1] * 72.0
    pdf_path = out / f"{spec.name}.pdf"
    c = pdfcanvas.Canvas(str(pdf_path), pagesize=(width_pt, height_pt), pageCompression=1)
    c.setTitle(spec.text.get("title") or spec.name)
    c.setAuthor("CCB Christmas Card Studio")
    c.setSubject("16:9 Christmas presentation")
    c.setCreator("CCB - the Christmas card studio for OpenCode")
    for page in pages:
        buf = io.BytesIO()
        page.image.save(buf, format="PNG", optimize=False)
        buf.seek(0)
        c.drawImage(ImageReader(buf), 0, 0, width=width_pt, height=height_pt,
                    preserveAspectRatio=False, mask=None)
        c.showPage()
    c.save()

    written = [{"path": str(pdf_path.relative_to(spec.folder)), "format": "pdf",
                "bytes": pdf_path.stat().st_size, "slides": len(pages)}]
    if png:
        folder = out / "slides"
        folder.mkdir(parents=True, exist_ok=True)
        for i, page in enumerate(pages):
            path = folder / f"slide-{i + 1:02d}.png"
            page.image.save(path, format="PNG", optimize=True)
            written.append({"path": str(path.relative_to(spec.folder)), "format": "png",
                            "px": [page.image.width, page.image.height], "bytes": path.stat().st_size})
    manifest = {
        "name": spec.name,
        "generated_with": "ccb",
        "design": "free composition",
        "canvas_in": list(SLIDE_IN),
        "dpi": dpi,
        "slides": [
            {"index": i + 1, "name": comp.get("name", f"Slide {i + 1}"),
             "blocks": page.metrics.get("blocks", [])}
            for i, (comp, page) in enumerate(zip(comps, pages))
        ],
        "files": written,
    }
    (out / "export.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest


def verify_files(pdf: Path, pages: int, inches: tuple[float, float] = SLIDE_IN) -> list[str]:
    problems = []
    if not pdf.exists() or pdf.stat().st_size < 1000:
        return [f"missing or empty PDF: {pdf}"]
    raw = pdf.read_bytes()
    found = raw.count(b"/Type /Page") + raw.count(b"/Type/Page")
    found -= raw.count(b"/Type /Pages") + raw.count(b"/Type/Pages")
    if found != pages:
        problems.append(f"PDF has {found} pages, expected {pages}")
    boxes = set(re.findall(rb"/MediaBox\s*\[\s*0\s+0\s+([\d.]+)\s+([\d.]+)\s*\]", raw))
    expected = (round(inches[0] * 72, 1), round(inches[1] * 72, 1))
    if boxes and not any(abs(float(w) - expected[0]) < 1.5 and abs(float(h) - expected[1]) < 1.5
                         for w, h in boxes):
        problems.append(f"page boxes {sorted(boxes)} are not {expected[0]}x{expected[1]} pt")
    return problems


def qa(spec: DeckSpec, dpi: int = 150) -> tuple[bool, str]:
    comps = spec.compositions
    report = check(spec, comps, dpi)
    problems = [] if report["errors"] else []
    pdf = spec.folder / "out" / f"{spec.name}.pdf"
    if not pdf.exists():
        problems.append("no PDF yet: run ./ccb deck render")
    elif comps:
        problems += verify_files(pdf, len(comps))
    facts = report.get("facts", {})
    ok = not report["errors"] and not problems
    lines = [f"# QA: {spec.name} presentation", "",
             f"{'PASS' if ok else 'FAIL'} - {len(comps)} slides, {dpi} DPI", "",
             f"- slides: {len(comps)}",
             f"- direction: {spec.style.label} / {spec.palette.label}",
             f"- dpi: {dpi}"]
    for error in dict.fromkeys(report["errors"] + problems):
        lines.append(f"- ERROR {error}")
    for warning in dict.fromkeys(report["warnings"]):
        lines.append(f"- WARN {warning}")
    out = spec.folder / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "qa.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ok, "\n".join(lines)


def build_sheet(spec: DeckSpec, comps: list[dict[str, Any]] | None = None,
                out: Path | None = None, tile_w: int = 640) -> Path:
    comps = comps if comps is not None else spec.compositions
    if not comps:
        raise ValueError("no slides to show yet")
    out = Path(out) if out else spec.folder / "out" / "slides.jpg"
    out.parent.mkdir(parents=True, exist_ok=True)
    tiles = []
    for i, comp in enumerate(comps):
        result = render_slide(spec, comp, 90, i + 1)
        image = result.image.copy()
        image.thumbnail((tile_w, tile_w), Image.LANCZOS)
        tiles.append((comp, image))
    cols = 2
    rows = (len(tiles) + cols - 1) // cols
    gap = 12
    label_h = 26
    tw = max(t.width for _, t in tiles)
    th = max(t.height for _, t in tiles)
    sheet = Image.new("RGB", (cols * tw + gap * (cols + 1),
                             rows * (th + label_h) + gap * (rows + 1)), (238, 236, 231))
    draw = ImageDraw.Draw(sheet)
    font = typefit.BOOK.font("lato", 16, 700)
    for i, (comp, tile) in enumerate(tiles):
        col, row = i % cols, i // cols
        x = gap + col * (tw + gap) + (tw - tile.width) // 2
        y = gap + row * (th + label_h + gap)
        sheet.paste(tile, (x, y))
        draw.text((x, y + tile.height + 4), f"{i + 1:02d}  {comp.get('name', 'slide')}", font=font,
                  fill=(40, 46, 42))
    sheet.save(out, quality=90, optimize=True)
    return out


def write_report(spec: DeckSpec) -> Path:
    stats = compose.load_photo_stats(spec)  # type: ignore[arg-type]
    lines = [f"# {spec.name} - presentation", "",
             f"{len(spec.photo_paths)} photographs, {len(spec.compositions)} slides, "
             f"{spec.style.label} / {spec.palette.label}.", ""]
    for i, comp in enumerate(spec.compositions):
        design = compose.design(comp)
        lines.append(f"## {i + 1}. {design.label}")
        lines.append(f"{len(design.slots)} photographs, {design.coverage * 100:.0f}% of the slide.")
        for slot in design.slots:
            photo = stats[slot.photo] if 0 <= slot.photo < len(stats) else None
            if photo:
                lines.append(f"- photo {slot.photo}: {photo.path.name}, {len(photo.faces)} face(s)")
        lines.append("")
    path = spec.folder / "report.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path
