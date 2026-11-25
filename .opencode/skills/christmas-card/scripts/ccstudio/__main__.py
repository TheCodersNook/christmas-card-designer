"""ccstudio: the Christmas card engine behind ./ccb.

  ./ccb doctor                        what is installed, and which fonts are ready
  ./ccb fonts                         download the studio's OFL fonts (once)
  ./ccb samples                       draw six demo photographs into inputs/
  ./ccb add <photo>...                copy photographs into inputs/ (originals untouched)
  ./ccb new <photo>... [--name x]     start a card: copy the photographs, write card.json
  ./ccb auto <card.json>              plan six designs and write report.md
  ./ccb make <photo>... | --card x    the whole job: plan, gate, sheet, export, QA
  ./ccb text <card.json> --family x   change the words without editing JSON by hand
  ./ccb check <card.json>             the gate (0 errors before an export)
  ./ccb sheet <card.json>             contact sheet of every design
  ./ccb render <card.json>            write the print files (PDF, PNG or JPEG)
  ./ccb qa <card.json>                read the exported files back and verify them
  ./ccb status | styles | sizes       what exists, what it can do
  ./ccb selftest                      end-to-end check with generated photographs
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from . import auto, check as gate, config, export as export_mod, fonts, layouts, samples
from . import sheet as sheet_mod
from .photos import PhotoError, load
from .spec import CardSpec, SpecError, safe_name, unique_card_dir

try:  # Windows consoles are not always UTF-8
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# --------------------------------------------------------------------- helpers
def _card_arg(arg: str | None) -> CardSpec:
    if arg:
        return CardSpec.load(arg)
    found = sorted(config.CARDS_DIR.glob("*/card.json")) if config.CARDS_DIR.exists() else []
    if not found:
        raise SpecError("no cards yet - start one with ./ccb new <photographs>")
    if len(found) > 1:
        names = ", ".join(p.parent.name for p in found)
        raise SpecError(f"more than one card ({names}); name one, for example ./ccb check cards/{found[0].parent.name}")
    return CardSpec.load(found[0])


def _copy_into_inputs(src: Path) -> Path:
    inputs = config.ROOT / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    src = src.expanduser().resolve()
    ext = src.suffix.lower()
    stem = safe_name(src.stem)
    dst = inputs / f"{stem}{ext}"
    n = 2
    while dst.exists():
        try:
            same = dst.read_bytes() == src.read_bytes()
        except OSError:
            same = False
        if same:
            return dst
        dst = inputs / f"{stem}-{n}{ext}"
        n += 1
    shutil.copyfile(src, dst)
    return dst


def _apply_text(spec: CardSpec, a) -> None:
    for role in config.TEXT_ROLES:
        value = getattr(a, role, None)
        if value is not None:
            spec.text[role] = str(value).strip()


def _design_from_arg(spec: CardSpec, a) -> layouts.Design | None:
    if getattr(a, "design", None):
        index = int(a.design) - 1
        if not (0 <= index < len(spec.designs)):
            raise SpecError(f"design {a.design} does not exist (there are {len(spec.designs)})")
        spec.data["selected"] = index
        spec.save()
    current = spec.current_design()
    return layouts.Design.from_dict(current) if current else None


def _print_files(manifest: dict) -> None:
    for item in manifest.get("files", []):
        extra = ""
        if item["format"] == "pdf":
            pages = item.get("pages", [])
            extra = f", {len(pages)} pages at {pages[0]['w_in']:g} x {pages[0]['h_in']:g} in" if pages else ""
        elif item.get("px"):
            extra = f", {item['px'][0]}x{item['px'][1]} px"
        size = item["bytes"] / 1024
        print(f"  {item['path']}{extra}, {size:.0f} KB")


def _write_qa(spec: CardSpec, manifest: dict, problems: list[str]) -> Path:
    lines = [f"# QA: {spec.name}", "",
             f"- Design: **{manifest.get('design')}** ({manifest.get('engine')})",
             f"- {manifest.get('dpi')} DPI, bleed {manifest.get('bleed_in')} in, "
             f"sides: {', '.join(manifest.get('pages', []))}", ""]
    for item in manifest.get("files", []):
        lines.append(f"- `{item['path']}` - {item['bytes'] / 1024:.0f} KB")
        if item["format"] == "pdf":
            for page in item.get("pages", []):
                lines.append(f"  - {page['side']}: page box {page['w_in']:.2f} x {page['h_in']:.2f} in")
        elif item.get("px"):
            lines.append(f"  - {item['px'][0]} x {item['px'][1]} px")
    lines += ["", "## Result", ""]
    lines += [f"- {p}" for p in problems] if problems else ["- PASS: every exported file matches its declared size, DPI and page count."]
    lines.append("")
    path = spec.folder / "out" / "qa.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


# -------------------------------------------------------------------- commands
def cmd_doctor(a) -> int:
    print("ccb doctor")
    ok = True
    print(f"  python      {sys.version.split()[0]}")
    for module, label in (("PIL", "Pillow (images)"), ("numpy", "NumPy (analysis)"), ("reportlab", "ReportLab (PDF)")):
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "") or getattr(mod, "Version", "")
            print(f"  ok          {label} {version}")
        except ImportError:
            ok = False
            print(f"  MISSING     {label} - run ./setup.sh")
    print(f"  fonts       {fonts.status()}")
    cards = sorted(config.CARDS_DIR.glob("*/card.json")) if config.CARDS_DIR.exists() else []
    print(f"  cards       {len(cards)} in cards/")
    print(f"  project     {config.ROOT}")
    if not ok:
        print("\nInstall the missing Python packages with ./setup.sh (or pip install -r requirements.txt).")
    return 0 if ok else 1


def cmd_fonts(a) -> int:
    print("Downloading the studio fonts (SIL Open Font License, from Google Fonts) ...")
    have = fonts.ensure(force=a.force)
    print(f"  {have}/{fonts.total()} fonts ready in {config.FONT_DIR}")
    if have < fonts.total():
        print("  Some fonts could not be fetched (offline?). The engine will fall back to a system font.")
    return 0 if have else 1


def cmd_samples(a) -> int:
    written = samples.write_demo_photos(config.ROOT / "inputs")
    print("Demo photographs written to inputs/ (flat illustrations, not photographs of anyone):")
    for path in written:
        print(f"  {path.name}")
    print("\nNext: ./ccb new inputs/tree_lights.jpg inputs/couple_snow.jpg inputs/cabin.jpg "
          "inputs/gifts.jpg inputs/snowman.jpg inputs/table.jpg --name demo")
    return 0


def cmd_add(a) -> int:
    if not a.photos:
        print("Name at least one photograph.", file=sys.stderr)
        return 1
    for raw in a.photos:
        src = Path(raw)
        if not src.exists():
            print(f"  not found: {raw}", file=sys.stderr)
            continue
        dst = _copy_into_inputs(src)
        try:
            photo = load(dst)
            detail = f"{photo.width}x{photo.height}, {photo.orientation}"
        except PhotoError as exc:
            detail = f"cannot read: {exc}"
        print(f"  inputs/{dst.name}  ({detail})")
    return 0


def _new_spec(a) -> CardSpec:
    photos = [Path(p).expanduser() for p in a.photos]
    missing = [str(p) for p in photos if not p.exists()]
    if missing:
        raise SpecError("these files were not found: " + ", ".join(missing))
    if not photos:
        raise SpecError("name the photographs, for example ./ccb new inputs/*.jpg --name hayes-2026")

    existing = config.CARDS_DIR / safe_name(a.name) if a.name else None
    if existing and (existing / "card.json").exists():
        spec = CardSpec.load(existing)
        stored = [os.path.relpath(_copy_into_inputs(p), spec.folder) for p in photos]
        spec.data["photos"] = stored
        if a.style:
            spec.design["style"] = a.style
        if a.size:
            spec.design["size"] = a.size
        if a.landscape:
            spec.design["orientation"] = "landscape"
        _apply_text(spec, a)
        spec.save()
        print(f"updated {existing.relative_to(config.ROOT)} with {len(stored)} photographs")
        return spec

    folder = unique_card_dir(config.CARDS_DIR, a.name or photos[0].stem)
    stored = [os.path.relpath(_copy_into_inputs(p), folder) for p in photos]
    spec = CardSpec.create(
        folder, folder.name, stored,
        style=a.style or "classic",
        size=a.size or "5x7",
        orientation="landscape" if a.landscape else "portrait",
    )
    _apply_text(spec, a)
    spec.save()
    print(f"new card {folder.relative_to(config.ROOT)}  ({len(stored)} photographs, "
          f"{spec.style.label}, {spec.card_inches[0]:g}x{spec.card_inches[1]:g} in)")
    return spec


def cmd_new(a) -> int:
    spec = _new_spec(a)
    designs = auto.plan(spec)
    print(auto.summary(designs, spec.selected))
    print(f"\nNext: ./ccb check {spec.folder.relative_to(config.ROOT)}")
    return 0


def cmd_auto(a) -> int:
    spec = _card_arg(a.card)
    designs = auto.plan(spec)
    print(auto.summary(designs, spec.selected))
    print(f"\n{len(designs)} designs written to {spec.folder.relative_to(config.ROOT)}/card.json")
    print(f"notes and to-dos: {spec.folder.relative_to(config.ROOT)}/report.md")
    return 0


def cmd_text(a) -> int:
    spec = _card_arg(a.card)
    _apply_text(spec, a)
    spec.save()
    print("Words now:")
    for role in config.TEXT_ROLES:
        print(f"  {role:<10} {spec.text.get(role) or '(empty)'}")
    report = gate.check(spec)
    gate.print_report(report)
    return 0 if not report["errors"] else 1


def cmd_check(a) -> int:
    spec = _card_arg(a.card)
    design = _design_from_arg(spec, a)
    report = gate.check(spec, design, dpi=int(spec.export.get("dpi", 300)))
    ok = gate.print_report(report)
    if report["warnings"] and a.strict:
        return 1
    return 0 if ok else 1


def cmd_sheet(a) -> int:
    spec = _card_arg(a.card)
    if not spec.designs:
        auto.plan(spec)
    designs = [layouts.Design.from_dict(d) for d in spec.designs]
    out = Path(a.out) if a.out else spec.folder / "out" / "designs.jpg"
    path = sheet_mod.build_sheet(spec, designs, out)
    print(f"contact sheet: {path}")
    return 0


def cmd_render(a) -> int:
    spec = _card_arg(a.card)
    if not spec.designs:
        auto.plan(spec)
    design = _design_from_arg(spec, a)
    if design is None:
        print("No design selected. Run ./ccb auto first.", file=sys.stderr)
        return 1
    report = gate.check(spec, design, dpi=int(a.dpi or spec.export.get("dpi", 300)))
    if report["errors"]:
        gate.print_report(report)
        print("render stopped: fix the errors above first", file=sys.stderr)
        return 1
    manifest = export_mod.export(
        spec, design, fmt=a.format, dpi=a.dpi, bleed=None if a.bleed is None else a.bleed,
        back=False if a.no_back else None, draft=a.draft, out_dir=Path(a.out) if a.out else None,
    )
    print(f"exported {spec.name}:")
    _print_files(manifest)
    problems = export_mod.verify_files(spec, manifest)
    for problem in problems:
        print(f"WARN {problem}")
    print(f"next: ./ccb qa {spec.folder.relative_to(config.ROOT)}")
    return 0 if not problems else 1


def cmd_qa(a) -> int:
    spec = _card_arg(a.card)
    manifest_path = spec.folder / "out" / "export.json"
    if not manifest_path.exists():
        print("nothing exported yet - run ./ccb render first", file=sys.stderr)
        return 1
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    problems = export_mod.verify_files(spec, manifest)
    path = _write_qa(spec, manifest, problems)
    if problems:
        print("QA found problems:")
        for problem in problems:
            print(f"  ERROR {problem}")
        print(f"details: {path}")
        return 1
    print(f"qa: PASS - {len(manifest.get('files', []))} file(s), {manifest.get('dpi')} DPI, "
          f"page size verified on the real files")
    print(f"details: {path}")
    return 0


def cmd_make(a) -> int:
    if a.photos:
        spec = _new_spec(a)
    else:
        spec = _card_arg(a.card)
    designs = auto.plan(spec)
    print(auto.summary(designs, spec.selected))
    design = _design_from_arg(spec, a)
    report = gate.check(spec, design, dpi=int(a.dpi or spec.export.get("dpi", 300)))
    if not gate.print_report(report):
        print("\nthe gate found errors: fix them, then run ./ccb make again", file=sys.stderr)
        return 1
    sheet_path = sheet_mod.build_sheet(spec, designs, spec.folder / "out" / "designs.jpg")
    print(f"\ncontact sheet: {sheet_path}")
    manifest = export_mod.export(
        spec, design, fmt=a.format, dpi=a.dpi, back=False if a.no_back else None, draft=a.draft,
    )
    print(f"\nexported {spec.name}:")
    _print_files(manifest)
    problems = export_mod.verify_files(spec, manifest)
    qa_path = _write_qa(spec, manifest, problems)
    print(f"qa: {'PASS' if not problems else 'PROBLEMS'}")
    for problem in problems:
        print(f"  ERROR {problem}")
    print(f"\nDONE  card:  {spec.folder.relative_to(config.ROOT)}")
    print(f"      sheet: {sheet_path}")
    print(f"      notes: {spec.folder.relative_to(config.ROOT)}/report.md")
    print(f"      qa:    {qa_path}")
    return 0 if not problems else 1


def cmd_status(a) -> int:
    found = sorted(config.CARDS_DIR.glob("*/card.json")) if config.CARDS_DIR.exists() else []
    if not found:
        print("No cards yet. Start one with ./ccb new <photographs> --name <name>")
        return 0
    for path in found:
        try:
            spec = CardSpec.load(path)
        except SpecError as exc:
            print(f"{path.parent.name}: broken ({exc})")
            continue
        current = spec.current_design()
        label = current.get("label") if current else "no designs"
        outs = sorted(p.name for p in (spec.folder / "out").glob("*") if p.is_file()) if (spec.folder / "out").exists() else []
        print(f"{spec.name}")
        print(f"  {len(spec.photo_paths)} photographs, {spec.style.label}, "
              f"{spec.card_inches[0]:g}x{spec.card_inches[1]:g} in, {label}")
        print(f"  files: {', '.join(outs) if outs else 'not rendered yet'}")
    return 0


def cmd_styles(a) -> int:
    print("Styles (key, look, fonts, decoration):")
    for key, style in config.STYLES.items():
        print(f"  {key:<12} {style.label:<20} {style.heading}/{style.body}, {style.decoration or 'plain'}, "
              f"{style.border} border")
        print(f"  {'':<12} {style.blurb}")
    print("\nPalettes: " + ", ".join(f"{p.key} ({p.label})" for p in config.PALETTES.values()))
    return 0


def cmd_sizes(a) -> int:
    print("Trim sizes (portrait, 300 DPI canvas without bleed):")
    for key, (w, h) in config.SIZES.items():
        print(f"  {key:<5} {w:g} x {h:g} in  ->  {int(round(w * 300))} x {int(round(h * 300))} px")
    print(f"\nBleed is {config.BLEED_IN:g} in on every edge when enabled (default).")
    return 0


def cmd_selftest(a) -> int:
    from . import selftest
    return selftest.run(keep=a.keep)


# ------------------------------------------------------------------------ main
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ccb", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sp = p.add_subparsers(dest="cmd", required=True)

    sp.add_parser("doctor", help="check the install and the fonts")
    x = sp.add_parser("fonts", help="download the OFL fonts into assets/fonts")
    x.add_argument("--force", action="store_true")
    sp.add_parser("samples", help="draw six demo photographs into inputs/")
    x = sp.add_parser("add", help="copy photographs into inputs/")
    x.add_argument("photos", nargs="+")

    def text_flags(parser):
        parser.add_argument("--greeting")
        parser.add_argument("--family")
        parser.add_argument("--message")
        parser.add_argument("--signature")
        parser.add_argument("--year")

    def design_flags(parser):
        parser.add_argument("--style", help="style key (./ccb styles)")
        parser.add_argument("--size", help="5x7, 4x6, 5x5, a6 or a2")
        parser.add_argument("--landscape", action="store_true")
        parser.add_argument("--design", type=int, help="which design to use (1-based)")

    x = sp.add_parser("new", help="start a card from photographs")
    x.add_argument("photos", nargs="+")
    x.add_argument("--name", help="folder name under cards/")
    design_flags(x)
    text_flags(x)

    x = sp.add_parser("auto", help="plan the designs and write report.md")
    x.add_argument("card", nargs="?")
    x = sp.add_parser("text", help="change the words on a card")
    x.add_argument("card", nargs="?")
    text_flags(x)
    x = sp.add_parser("check", help="the gate: geometry, type and print checks")
    x.add_argument("card", nargs="?")
    x.add_argument("--design", type=int)
    x.add_argument("--strict", action="store_true", help="treat warnings as errors")
    x = sp.add_parser("sheet", help="contact sheet of every design")
    x.add_argument("card", nargs="?")
    x.add_argument("-o", "--out")
    x = sp.add_parser("render", help="write the print files")
    x.add_argument("card", nargs="?")
    x.add_argument("--design", type=int)
    x.add_argument("--format", choices=["pdf", "png", "jpeg"])
    x.add_argument("--dpi", type=int)
    x.add_argument("--bleed", dest="bleed", action="store_true", default=None)
    x.add_argument("--no-bleed", dest="bleed", action="store_false")
    x.add_argument("--no-back", action="store_true")
    x.add_argument("--draft", action="store_true", help="120 DPI preview of the real files")
    x.add_argument("-o", "--out")
    x = sp.add_parser("qa", help="verify the exported files")
    x.add_argument("card", nargs="?")
    x = sp.add_parser("make", help="plan, gate, sheet, export and QA in one go")
    x.add_argument("photos", nargs="*")
    x.add_argument("--card", help="an existing card folder or card.json")
    x.add_argument("--name")
    design_flags(x)
    text_flags(x)
    x.add_argument("--format", choices=["pdf", "png", "jpeg"])
    x.add_argument("--dpi", type=int)
    x.add_argument("--no-back", action="store_true")
    x.add_argument("--draft", action="store_true")
    sp.add_parser("status", help="what cards exist and where their files are")
    sp.add_parser("styles", help="the eight styles and six palettes")
    sp.add_parser("sizes", help="the trim sizes")
    x = sp.add_parser("selftest", help="end-to-end check with generated photographs")
    x.add_argument("--keep", action="store_true", help="keep the test card for inspection")
    return p


COMMANDS = {
    "doctor": cmd_doctor,
    "fonts": cmd_fonts,
    "samples": cmd_samples,
    "add": cmd_add,
    "new": cmd_new,
    "auto": cmd_auto,
    "text": cmd_text,
    "check": cmd_check,
    "sheet": cmd_sheet,
    "render": cmd_render,
    "qa": cmd_qa,
    "make": cmd_make,
    "status": cmd_status,
    "styles": cmd_styles,
    "sizes": cmd_sizes,
    "selftest": cmd_selftest,
}


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return COMMANDS[args.cmd](args)
    except SpecError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except PhotoError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nstopped", file=sys.stderr)
        return 130


if __name__ == "__main__":
    sys.exit(main())
