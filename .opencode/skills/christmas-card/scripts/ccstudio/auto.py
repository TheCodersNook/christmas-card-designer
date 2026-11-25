"""The automatic art director: plan six designs, explain them, list what is left."""
from __future__ import annotations

from . import config, layouts
from .photos import PhotoError, load
from .spec import CardSpec, SpecError


def load_photos(spec: CardSpec):
    photos = []
    problems = []
    for path in spec.photo_paths:
        try:
            photos.append(load(path))
        except PhotoError as exc:
            problems.append(str(exc))
    return photos, problems


def plan(spec: CardSpec) -> list[layouts.Design]:
    photos, problems = load_photos(spec)
    if problems:
        raise SpecError("these photographs cannot be read:\n  " + "\n  ".join(problems))
    if len(photos) < 2:
        raise SpecError("a card needs at least two photographs (add more with ./ccb add)")
    designs = layouts.build(spec, photos)
    if not designs or len(designs[0].slots) != len(photos):
        raise SpecError("no layout could place every photograph at this card size")
    spec.data["designs"] = [d.to_dict() for d in designs]
    try:
        selected = int(spec.data.get("selected", 0))
    except (TypeError, ValueError):
        selected = 0
    spec.data["selected"] = selected if 0 <= selected < len(designs) else 0
    spec.save()
    write_report(spec, photos, designs)
    return designs


def write_report(spec: CardSpec, photos, designs: list[layouts.Design]) -> str:
    style = spec.style
    palette = spec.palette
    w, h = spec.card_inches
    lines = [f"# {spec.name}", "",
             f"- Style: **{style.label}** - {style.blurb}",
             f"- Palette: **{palette.label}**",
             f"- Card: **{w:g} x {h:g} in** ({spec.design.get('orientation', 'portrait')}), "
             f"export {spec.export.get('format', 'pdf').upper()} at {spec.export.get('dpi', 300)} DPI"
             + (", with bleed and crop marks" if spec.export.get("bleed", True) else ""),
             f"- Photographs: **{len(photos)}**", ""]

    words = [(role, spec.text.get(role, "")) for role in config.TEXT_ROLES]
    lines += ["## Words", "", "| Field | Copy |", "| --- | --- |"]
    for role, value in words:
        lines.append(f"| {role} | {value or '_(empty)_'} |")
    lines.append("")

    lines += ["## Photographs", "", "| File | Pixels | MP | Shape | Interest |", "| --- | --- | --- | --- | --- |"]
    for photo in photos:
        name = photo.path.name
        lines.append(f"| {name} | {photo.width}x{photo.height} | {photo.megapixels:.1f} | "
                     f"{photo.orientation} | {photo.interest:.2f} |")
    lines.append("")

    lines += ["## Designs", "", "| # | Design | Engine | Score | Coverage |", "| --- | --- | --- | --- | --- |"]
    for i, design in enumerate(designs):
        mark = " **(selected)**" if i == spec.selected else ""
        lines.append(f"| {i + 1} | {design.label}{mark} | {design.engine} | {design.score:.1f} | "
                     f"{design.coverage * 100:.0f}% |")
    lines.append("")

    todo = _todo(spec, photos, designs)
    lines += ["## To do", ""] + ([f"- {item}" for item in todo] if todo else ["- Nothing: the card is ready to render."])
    lines += ["", "## Next", "",
              f"1. `./ccb check {_path(spec)}` - the gate must show 0 errors.",
              f"2. `./ccb sheet {_path(spec)}` - look at every design.",
              f"3. `./ccb render {_path(spec)}` - write the print files.",
              f"4. `./ccb qa {_path(spec)}` - verify the exported size and DPI.", ""]
    text = "\n".join(lines)
    (spec.folder / "report.md").write_text(text, encoding="utf-8")
    return text


def _todo(spec: CardSpec, photos, designs: list[layouts.Design]) -> list[str]:
    todo = []
    if not spec.text.get("message"):
        todo.append("Add a message (2-3 sentences) - an empty back looks unfinished.")
    if not spec.text.get("family"):
        todo.append("Add the family name, or the card has no signature.")
    if not spec.text.get("year"):
        todo.append("Add the year (for example 2026).")
    small = [p.path.name for p in photos if p.megapixels < 1.2]
    if small:
        todo.append("These photographs are under 1.2 MP and may print soft: " + ", ".join(small) + ".")
    if len(photos) > 12:
        todo.append("With more than twelve photographs, choose a favourite and set it as design.hero.")
    if designs and designs[0].coverage > 0.7:
        todo.append("The best design is busy; a style with more air (modern, editorial) may suit it better.")
    return todo


def _path(spec: CardSpec) -> str:
    try:
        return str(spec.folder.relative_to(config.ROOT))
    except ValueError:
        return str(spec.folder)


def summary(designs: list[layouts.Design], selected: int = 0) -> str:
    rows = []
    for i, design in enumerate(designs):
        mark = "*" if i == selected else " "
        rows.append(f" {i + 1:>2}{mark} {design.label:<24} {design.engine:<10} score {design.score:5.1f}  "
                    f"cover {design.coverage * 100:3.0f}%")
    return "\n".join(rows)
