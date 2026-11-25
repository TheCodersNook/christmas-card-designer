"""ccstudio: the rules-driven Christmas card and presentation studio.

  ./ccb doctor                        what is installed, fonts and face engine
  ./ccb samples                       draw six demo photographs into inputs/
  ./ccb add <photo>... [--name x]     start a card (alias: new)
  ./ccb brief <card>                  the rulebook, measurements, faces and words
  ./ccb layout <card> --file x.json   install the compositions the agent wrote
  ./ccb text <card> --greeting x      change the words
  ./ccb check <card>                  the gate (0 errors before an export)
  ./ccb see <card>                    annotated preview + photo sheet + visual.md
  ./ccb sheet <card>                  contact sheet of the saved compositions
  ./ccb render <card>                 print files (PDF, PNG or JPEG)
  ./ccb qa <card>                     read the exported files back and verify them
  ./ccb faces [<photo>...]            install/scan with YuNet (Haar fallback)
  ./ccb deck new <photo>... --name x  start a 16:9 presentation
  ./ccb deck brief|layout|check|see|sheet|render|qa
  ./ccb status | directions | sizes   what exists, and the rulebook's vocabulary
  ./ccb selftest                      end-to-end check with generated photographs

There are no templates. The agent writes compositions against studio/rules.json
and studio/RULES.md; this CLI validates them, renders them and shows its work.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

from . import check as gate, compose, config, deck as deck_mod, export as export_mod, faces as faces_mod
from . import fonts, samples, see as see_mod, sheet as sheet_mod
from .photos import PhotoError, load
from .spec import CardSpec, SpecError, safe_name, unique_card_dir

try:  # Windows consoles are not always UTF-8
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


# --------------------------------------------------------------------- helpers
def _card(arg: str | None) -> CardSpec:
    if arg:
        p = Path(arg)
        if not p.exists() and (config.CARDS_DIR / arg / "card.json").exists():
            p = config.CARDS_DIR / arg
        return CardSpec.load(p)
    folders = sorted(p for p in config.CARDS_DIR.glob("*") if (p / "card.json").exists()) if config.CARDS_DIR.exists() else []
    if not folders:
        raise SpecError("no cards yet: ./ccb new inputs/*.jpg --name my-card")
    if len(folders) > 1:
        raise SpecError("more than one card exists; name one: ./ccb check cards/<name>")
    return CardSpec.load(folders[0])


def _deck(arg: str | None) -> deck_mod.DeckSpec:
    if arg:
        p = Path(arg)
        if not p.exists() and (config.DECKS_DIR / arg / "deck.json").exists():
            p = config.DECKS_DIR / arg
        return deck_mod.DeckSpec.load(p)
    folders = sorted(p for p in config.DECKS_DIR.glob("*") if (p / "deck.json").exists()) if config.DECKS_DIR.exists() else []
    if not folders:
        raise SpecError("no presentations yet: ./ccb deck new inputs/*.jpg --name my-deck")
    if len(folders) > 1:
        raise SpecError("more than one presentation exists; name one: ./ccb deck check decks/<name>")
    return deck_mod.DeckSpec.load(folders[0])


def _copy_into_inputs(path: Path) -> Path:
    inputs = config.ROOT / "inputs"
    inputs.mkdir(parents=True, exist_ok=True)
    if path.parent.resolve() == inputs.resolve():
        return path
    dest = inputs / path.name
    n = 2
    while dest.exists() and dest.stat().st_size != path.stat().st_size:
        dest = inputs / f"{path.stem}-{n}{path.suffix}"
        n += 1
    if not dest.exists():
        shutil.copy2(path, dest)
    return dest


def _photos_for(folder: Path, photos: list[str]) -> list[str]:
    out = []
    for item in photos:
        p = Path(item).expanduser()
        if not p.exists():
            raise SpecError(f"photograph not found: {p}")
        try:
            load(p)  # fail early, with a readable message
        except PhotoError as exc:
            raise SpecError(str(exc)) from exc
        out.append(os.path.relpath(_copy_into_inputs(p), folder))
    return out


def _print_issues(issues: list[compose.Issue]) -> int:
    errors = 0
    for issue in issues:
        print(issue.line())
        errors += issue.level == "error"
    return errors


def _read_json(path: str) -> Any:
    if path == "-":
        return json.load(sys.stdin)
    p = Path(path).expanduser()
    if not p.exists():
        raise SpecError(f"no composition file at {p}")
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SpecError(f"{p} is not valid JSON: {exc}") from exc


def _rel(spec, path: Path) -> str:
    try:
        return str(path.relative_to(spec.folder))
    except ValueError:
        return str(path)


def _card_summary(spec: CardSpec) -> str:
    fronts = spec.front_compositions
    return (f"{spec.name}: {len(spec.photo_paths)} photographs, {len(fronts)} front composition"
            f"{'s' if len(fronts) != 1 else ''}, {1 if spec.back() else 0} back, "
            f"{spec.style.label} / {spec.palette.label}, "
            f"{spec.card_inches[0]:g}x{spec.card_inches[1]:g} in")


# ----------------------------------------------------------------------- cards
def cmd_doctor(a) -> int:
    print("ccb doctor")
    print(f"  python      {sys.version.split()[0]}")
    for name, module in (("Pillow (images)", "PIL"), ("NumPy (analysis)", "numpy"), ("ReportLab (PDF)", "reportlab")):
        try:
            mod = __import__(module)
            print(f"  ok          {name} {getattr(mod, '__version__', '')}")
        except Exception:
            print(f"  MISSING     {name}")
    print(f"  fonts       {fonts.installed()}/{fonts.total()} studio fonts in assets/fonts")
    faces = faces_mod.status()
    print(f"  faces       {faces['detector']}" + (f" (OpenCV {faces['opencv_version']})" if faces["opencv"] else " - install opencv-python-headless"))
    print(f"  rulebook    {config.RULES_PATH}")
    print(f"  cards       {len(list(config.CARDS_DIR.glob('*/card.json'))) if config.CARDS_DIR.exists() else 0} in cards/, "
          f"{len(list(config.DECKS_DIR.glob('*/deck.json'))) if config.DECKS_DIR.exists() else 0} presentation(s) in decks/")
    print(f"  project     {config.ROOT}")
    return 0


def cmd_samples(a) -> int:
    paths = samples.write_demo_photos()
    print(f"wrote {len(paths)} demo photographs to inputs/")
    return 0


def cmd_add(a) -> int:
    name = a.name or Path(a.photos[0]).stem
    folder = unique_card_dir(config.CARDS_DIR, name)
    folder.mkdir(parents=True, exist_ok=True)
    photos = _photos_for(folder, a.photos)
    spec = CardSpec.create(
        folder, safe_name(name), photos,
        direction=a.direction, palette=a.palette, size=a.size,
        orientation="landscape" if a.landscape else "portrait",
    )
    for role in config.TEXT_ROLES:
        value = getattr(a, role, None)
        if value is not None:
            spec.text[role] = str(value).strip()
    spec.save()
    print(f"new card cards/{folder.name}  ({len(photos)} photographs, {spec.style.label}, "
          f"{spec.card_inches[0]:g}x{spec.card_inches[1]:g} in)")
    print(f"\nNext: ./ccb brief cards/{folder.name}")
    print("      then write compositions and install them with ./ccb layout")
    return 0


def cmd_brief(a) -> int:
    spec = _card(a.card)
    text = compose.brief(spec)
    path = spec.folder / "brief.md"
    path.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\nbrief saved: {_rel(spec, path)}")
    return 0


def cmd_layout(a) -> int:
    spec = _card(a.card)
    payload = _read_json(a.file)
    issues, selected = compose.install(spec, payload, select=a.select, append=a.append)
    _print_issues(issues)
    if any(i.level == "error" for i in issues):
        print("\nnot saved: fix the errors above and run layout again")
        return 1
    fronts = spec.front_compositions
    print(f"\nsaved {len(fronts)} front composition(s), {1 if spec.back() else 0} back")
    if fronts:
        print(f"selected front: {fronts[min(selected, len(fronts) - 1)].get('name')}")
    print(f"Next: ./ccb check {spec.folder.relative_to(config.ROOT)}")
    return 0


def cmd_text(a) -> int:
    spec = _card(a.card)
    for role in config.TEXT_ROLES:
        value = getattr(a, role, None)
        if value is not None:
            spec.text[role] = str(value).strip()
    spec.save()
    for role in config.TEXT_ROLES:
        print(f"  {role:<10} {spec.text.get(role) or '(empty)'}")
    return 0


def cmd_check(a) -> int:
    spec = _card(a.card)
    report = gate.check_card(spec, dpi=int(a.dpi or spec.export.get("dpi", 300)))
    ok = gate.print_report(report)
    return 0 if ok else 1


def cmd_sheet(a) -> int:
    spec = _card(a.card)
    if not spec.compositions:
        print("no compositions yet: read ./ccb brief and write some")
        return 1
    path = sheet_mod.build_sheet(spec, out=Path(a.out) if a.out else spec.folder / "out" / "designs.jpg")
    print(f"contact sheet: {_rel(spec, path)}")
    return 0


def cmd_see(a) -> int:
    spec = _card(a.card)
    if not spec.compositions:
        print("no compositions yet: read ./ccb brief and write some")
        return 1
    out = see_mod.write(spec, width=a.width)
    print(f"annotated previews in {_rel(spec, out)}/")
    for name in ("front.png", "back.png", "photos.jpg", "visual.md"):
        if (out / name).exists():
            print(f"  {name}")
    print("\nIf your model can read images, open out/see/photos.jpg before composing")
    print("and out/see/front.png after. Otherwise read out/see/visual.md and say so.")
    return 0


def cmd_render(a) -> int:
    spec = _card(a.card)
    front = spec.front_design()
    if front is None:
        print("no composition yet: ./ccb brief, write one, ./ccb layout")
        return 1
    back = spec.back_design() if (not a.no_back and spec.back_design() is not None) else None
    manifest = export_mod.export(
        spec, front, fmt=a.format, dpi=a.dpi, bleed=not a.no_bleed,
        crop_marks=not a.no_crop, back=bool(back), back_design=back,
        draft=a.draft, out_dir=Path(a.out) if a.out else None,
    )
    print(f"exported {spec.name}:")
    for item in manifest["files"]:
        extra = f", {item['pages']} page(s)" if item.get("pages") else ""
        print(f"  {item['path']} - {item['bytes'] / 1024:.0f} KB{extra}")
    print(f"next: ./ccb qa {spec.folder.relative_to(config.ROOT)}")
    return 0


def cmd_qa(a) -> int:
    spec = _card(a.card)
    dpi = int(a.dpi or spec.export.get("dpi", 300))
    report = gate.check_card(spec, dpi)
    ok = gate.print_report(report)
    problems: list[str] = []
    pdf = spec.folder / "out" / f"{spec.name}.pdf"
    if not pdf.exists():
        problems.append("no PDF yet: run ./ccb render")
    else:
        pages = 1 + (1 if spec.back() and spec.export.get("back", True) else 0)
        w, h = spec.card_inches
        if spec.export.get("bleed", True):
            w, h = w + 2 * config.BLEED_IN, h + 2 * config.BLEED_IN
        problems += deck_mod.verify_files(pdf, pages, (w, h))
    lines = [f"# QA: {spec.name}", "", f"card {spec.card_inches[0]:g} x {spec.card_inches[1]:g} in, {dpi} dpi", ""]
    for error in dict.fromkeys(report["errors"] + problems):
        lines.append(f"- ERROR {error}")
    for warning in dict.fromkeys(report["warnings"]):
        lines.append(f"- WARN {warning}")
    good = ok and not problems
    lines.insert(1, f"\n{'PASS' if good else 'FAIL'}\n")
    out = spec.folder / "out"
    out.mkdir(parents=True, exist_ok=True)
    (out / "qa.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    for problem in problems:
        print(f"ERROR {problem}")
    print(f"qa: {'PASS' if good else 'FAIL'}")
    print(f"details: {_rel(spec, out / 'qa.md')}")
    return 0 if good else 1


def cmd_make(a) -> int:
    if cmd_add(a) != 0:
        return 1
    spec = _card(safe_name(a.name or Path(a.photos[0]).stem))
    text = compose.brief(spec)
    (spec.folder / "brief.md").write_text(text + "\n", encoding="utf-8")
    see_mod.write(spec)
    print(f"\n{brief_head(spec)}")
    print(f"brief: {_rel(spec, spec.folder / 'brief.md')}")
    print(f"photographs: {_rel(spec, spec.folder / 'out' / 'see' / 'photos.jpg')}")
    print("\nNow compose: read the brief and the photo sheet, write compositions, install with")
    print(f"  ./ccb layout cards/{spec.folder.name} --file design.json")
    return 0


def brief_head(spec: CardSpec) -> str:
    w, h = spec.card_inches
    return (f"{spec.name}: {len(spec.photo_paths)} photographs, {w:g}x{h:g} in, "
            f"{spec.style.label} / {spec.palette.label}. Nothing has been composed yet.")


def cmd_faces(a) -> int:
    if not faces_mod.available():
        print("OpenCV is missing. Install it with: pip install opencv-python-headless")
        print("Then run ./ccb faces again.")
        return 1
    try:
        faces_mod.ensure_model(force=a.force)
    except Exception as exc:
        print(f"could not install the YuNet model: {exc}")
    det = faces_mod.status()
    print(f"detector: {det['detector']}  model: {det['model_path']}")
    paths = [Path(p) for p in a.photos]
    if not paths and (config.ROOT / "inputs").exists():
        paths = sorted(p for p in (config.ROOT / "inputs").glob("*.*") if p.suffix)
    if not paths:
        print("no photographs to scan (pass some, or ./ccb samples first)")
        return 0
    for path in paths:
        try:
            photo = load(path)
        except PhotoError as exc:
            print(f"  {path.name}: {exc}")
            continue
        if not photo.faces:
            print(f"  {path.name}: no faces detected")
            continue
        for i, f in enumerate(photo.faces):
            print(f"  {path.name}: face {i + 1} at {f.cx * 100:.0f}%, {f.cy * 100:.0f}% "
                  f"({f.w * 100:.0f}% wide, {f.score:.2f}, {f.source})")
    return 0


# ------------------------------------------------------------------ the rest
def cmd_status(a) -> int:
    cards = sorted(config.CARDS_DIR.glob("*/card.json")) if config.CARDS_DIR.exists() else []
    if cards:
        print("Cards:")
        for path in cards:
            spec = CardSpec.load(path)
            fronts = len(spec.front_compositions)
            label = f"{fronts} front composition{'s' if fronts != 1 else ''}" if fronts else "not composed yet"
            print(f"  {spec.name}")
            print(f"    {len(spec.photo_paths)} photographs, {spec.style.label}, "
                  f"{spec.card_inches[0]:g}x{spec.card_inches[1]:g} in, {label}")
    decks = sorted(config.DECKS_DIR.glob("*/deck.json")) if config.DECKS_DIR.exists() else []
    if decks:
        print("\nPresentations:")
        for path in decks:
            spec = deck_mod.DeckSpec.load(path)
            print(f"  {spec.name}")
            print(f"    {len(spec.photo_paths)} photographs, {spec.style.label} / {spec.palette.label}, "
                  f"{len(spec.compositions)} slide(s)")
    if not cards and not decks:
        print("nothing yet: ./ccb samples, then ./ccb new inputs/*.jpg --name my-card")
    return 0


def cmd_directions(a) -> int:
    for key, st in config.STYLES.items():
        print(f"{key:<12} {st.label}  ({st.palette})")
        print(f"             {st.blurb}")
        print(f"             {st.guidance}")
    print("\nEdit studio/rules.json to change any of this; studio/RULES.md explains every field.")
    return 0


def cmd_sizes(a) -> int:
    for key, (w, h) in config.SIZES.items():
        print(f"{key:<8} {w:g} x {h:g} in")
    print(f"\nbleed {config.BLEED_IN} in; export dpi {config.MIN_DPI}-{config.MAX_DPI}")
    return 0


def cmd_selftest(a) -> int:
    from . import selftest
    return selftest.run()


# ---------------------------------------------------------------------- decks
def cmd_deck_new(a) -> int:
    name = a.name or Path(a.photos[0]).stem
    folder = unique_card_dir(config.DECKS_DIR, name)
    folder.mkdir(parents=True, exist_ok=True)
    photos = _photos_for(folder, a.photos)
    spec = deck_mod.DeckSpec.create(folder, safe_name(name), photos,
                                    direction=a.direction, palette=a.palette)
    for role in deck_mod.DECK_TEXT_ROLES:
        value = getattr(a, role, None)
        if value is not None:
            spec.text[role] = str(value).strip()
    spec.save()
    print(f"new presentation decks/{folder.name}  ({len(photos)} photographs, 16:9, {spec.style.label})")
    print(f"\nNext: ./ccb deck brief decks/{folder.name}")
    return 0


def cmd_deck_brief(a) -> int:
    spec = _deck(a.deck)
    text = deck_mod.brief(spec)
    path = spec.folder / "brief.md"
    path.write_text(text + "\n", encoding="utf-8")
    print(text)
    print(f"\nbrief saved: {_rel(spec, path)}")
    return 0


def cmd_deck_layout(a) -> int:
    spec = _deck(a.deck)
    issues, count = deck_mod.install(spec, _read_json(a.file), append=a.append)
    _print_issues(issues)
    if any(i.level == "error" for i in issues):
        print("\nnot saved: fix the errors above and run layout again")
        return 1
    print(f"\nsaved {count} slides")
    print(f"Next: ./ccb deck check {spec.folder.relative_to(config.ROOT)}")
    return 0


def cmd_deck_text(a) -> int:
    spec = _deck(a.deck)
    for role in deck_mod.DECK_TEXT_ROLES:
        value = getattr(a, role, None)
        if value is not None:
            spec.text[role] = str(value).strip()
    spec.save()
    for role in deck_mod.DECK_TEXT_ROLES:
        print(f"  {role:<10} {spec.text.get(role) or '(empty)'}")
    return 0


def cmd_deck_check(a) -> int:
    spec = _deck(a.deck)
    report = deck_mod.check(spec, dpi=int(a.dpi or spec.export.get("dpi", 150)))
    ok = deck_mod.print_report(report)
    return 0 if ok else 1


def cmd_deck_sheet(a) -> int:
    spec = _deck(a.deck)
    if not spec.compositions:
        print("no slides yet: read ./ccb deck brief and write them")
        return 1
    path = deck_mod.build_sheet(spec, out=Path(a.out) if a.out else spec.folder / "out" / "slides.jpg")
    print(f"contact sheet: {_rel(spec, path)}")
    return 0


def cmd_deck_see(a) -> int:
    spec = _deck(a.deck)
    if not spec.compositions:
        print("no slides yet: read ./ccb deck brief and write them")
        return 1
    out = spec.folder / "out" / "see"
    out.mkdir(parents=True, exist_ok=True)
    stats = compose.load_photo_stats(spec)  # type: ignore[arg-type]
    for i, comp in enumerate(spec.compositions):
        see_mod.annotate(spec, compose.design(comp), a.width, stats).save(
            out / f"slide-{i + 1:02d}.png", optimize=True)
    see_mod.photos_sheet(spec, stats).save(out / "photos.jpg", quality=88)
    (out / "visual.md").write_text(see_mod.visual_md(spec, stats), encoding="utf-8")
    print(f"annotated slides in {_rel(spec, out)}/")
    print("  photos.jpg, slide-01.png ... , visual.md")
    print("\nIf your model can read images, look at them before and after a change.")
    return 0


def cmd_deck_render(a) -> int:
    spec = _deck(a.deck)
    if not spec.compositions:
        print("no slides yet: read ./ccb deck brief and write them")
        return 1
    manifest = deck_mod.export(spec, dpi=a.dpi, png=a.png, out_dir=Path(a.out) if a.out else None)
    print(f"exported {spec.name}:")
    for item in manifest["files"]:
        extra = f", {item['slides']} slides" if item.get("slides") else ""
        print(f"  {item['path']} - {item['bytes'] / 1024:.0f} KB{extra}")
    print(f"next: ./ccb deck qa {spec.folder.relative_to(config.ROOT)}")
    return 0


def cmd_deck_qa(a) -> int:
    spec = _deck(a.deck)
    ok, text = deck_mod.qa(spec, dpi=int(a.dpi or spec.export.get("dpi", 150)))
    print(text)
    return 0 if ok else 1


def cmd_deck_make(a) -> int:
    if cmd_deck_new(a) != 0:
        return 1
    spec = _deck(safe_name(a.name or Path(a.photos[0]).stem))
    text = deck_mod.brief(spec)
    (spec.folder / "brief.md").write_text(text + "\n", encoding="utf-8")
    out = spec.folder / "out" / "see"
    out.mkdir(parents=True, exist_ok=True)
    stats = compose.load_photo_stats(spec)  # type: ignore[arg-type]
    see_mod.photos_sheet(spec, stats).save(out / "photos.jpg", quality=88)
    print(f"\n{spec.name}: {len(spec.photo_paths)} photographs, 16:9, {spec.style.label}. No slides yet.")
    print(f"brief: {_rel(spec, spec.folder / 'brief.md')}")
    print(f"photographs: {_rel(spec, out / 'photos.jpg')}")
    print("\nNow compose the slides, then:")
    print(f"  ./ccb deck layout decks/{spec.folder.name} --file slides.json")
    return 0


# ---------------------------------------------------------------------- parser
def _text_args(p, *, deck: bool = False) -> None:
    if deck:
        p.add_argument("--title", default=None)
        p.add_argument("--subtitle", default=None)
    p.add_argument("--greeting", default=None)
    p.add_argument("--family", default=None)
    p.add_argument("--message", default=None)
    p.add_argument("--signature", default=None)
    p.add_argument("--year", default=None)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="ccb", description="Rules-driven Christmas cards and 16:9 presentations.")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("doctor").set_defaults(func=cmd_doctor)
    sub.add_parser("samples").set_defaults(func=cmd_samples)
    sub.add_parser("status").set_defaults(func=cmd_status)
    sub.add_parser("directions", aliases=["styles"]).set_defaults(func=cmd_directions)
    sub.add_parser("sizes").set_defaults(func=cmd_sizes)
    sub.add_parser("selftest").set_defaults(func=cmd_selftest)

    add = sub.add_parser("new", aliases=["add"], help="start a card from photographs")
    add.add_argument("photos", nargs="+")
    add.add_argument("--name", default=None)
    add.add_argument("--direction", default="classic")
    add.add_argument("--palette", default="")
    add.add_argument("--size", default="5x7")
    add.add_argument("--landscape", action="store_true")
    _text_args(add)
    add.set_defaults(func=cmd_add)

    brief = sub.add_parser("brief", help="the rulebook, measurements, faces and words")
    brief.add_argument("card", nargs="?")
    brief.set_defaults(func=cmd_brief)

    layout = sub.add_parser("layout", help="validate and install compositions")
    layout.add_argument("card", nargs="?")
    layout.add_argument("--file", required=True, help="composition JSON, or - for stdin")
    layout.add_argument("--select", type=int, default=None, help="1-based front to render")
    layout.add_argument("--append", action="store_true")
    layout.set_defaults(func=cmd_layout)

    text = sub.add_parser("text", help="change the words")
    text.add_argument("card", nargs="?")
    _text_args(text)
    text.set_defaults(func=cmd_text)

    check = sub.add_parser("check", help="the gate")
    check.add_argument("card", nargs="?")
    check.add_argument("--dpi", type=int, default=None)
    check.set_defaults(func=cmd_check)

    sheet = sub.add_parser("sheet", help="contact sheet of saved compositions")
    sheet.add_argument("card", nargs="?")
    sheet.add_argument("--out", default=None)
    sheet.set_defaults(func=cmd_sheet)

    see = sub.add_parser("see", help="annotated preview, photo sheet and visual report")
    see.add_argument("card", nargs="?")
    see.add_argument("--width", type=int, default=1400)
    see.set_defaults(func=cmd_see)

    render = sub.add_parser("render", help="write the print files")
    render.add_argument("card", nargs="?")
    render.add_argument("--format", choices=["pdf", "png", "jpeg"], default=None)
    render.add_argument("--dpi", type=int, default=None)
    render.add_argument("--out", default=None)
    render.add_argument("--no-bleed", action="store_true")
    render.add_argument("--no-crop", action="store_true")
    render.add_argument("--no-back", action="store_true")
    render.add_argument("--draft", action="store_true")
    render.set_defaults(func=cmd_render)

    qa = sub.add_parser("qa", help="verify the exported files")
    qa.add_argument("card", nargs="?")
    qa.add_argument("--dpi", type=int, default=None)
    qa.set_defaults(func=cmd_qa)

    make = sub.add_parser("make", help="start a card, write its brief, show the photographs")
    make.add_argument("photos", nargs="+")
    make.add_argument("--name", default=None)
    make.add_argument("--direction", default="classic")
    make.add_argument("--palette", default="")
    make.add_argument("--size", default="5x7")
    make.add_argument("--landscape", action="store_true")
    _text_args(make)
    make.set_defaults(func=cmd_make)

    face = sub.add_parser("faces", help="install YuNet and scan photographs")
    face.add_argument("photos", nargs="*")
    face.add_argument("--force", action="store_true", help="download the model again")
    face.set_defaults(func=cmd_faces)

    deck = sub.add_parser("deck", help="16:9 presentations")
    dsub = deck.add_subparsers(dest="deck_cmd", required=True)

    dn = dsub.add_parser("new")
    dn.add_argument("photos", nargs="+")
    dn.add_argument("--name", default=None)
    dn.add_argument("--direction", default="editorial")
    dn.add_argument("--palette", default="")
    _text_args(dn, deck=True)
    dn.set_defaults(func=cmd_deck_new)

    db = dsub.add_parser("brief")
    db.add_argument("deck", nargs="?")
    db.set_defaults(func=cmd_deck_brief)

    dl = dsub.add_parser("layout")
    dl.add_argument("deck", nargs="?")
    dl.add_argument("--file", required=True)
    dl.add_argument("--append", action="store_true")
    dl.set_defaults(func=cmd_deck_layout)

    dt = dsub.add_parser("text")
    dt.add_argument("deck", nargs="?")
    _text_args(dt, deck=True)
    dt.set_defaults(func=cmd_deck_text)

    dc = dsub.add_parser("check")
    dc.add_argument("deck", nargs="?")
    dc.add_argument("--dpi", type=int, default=None)
    dc.set_defaults(func=cmd_deck_check)

    ds = dsub.add_parser("sheet")
    ds.add_argument("deck", nargs="?")
    ds.add_argument("--out", default=None)
    ds.set_defaults(func=cmd_deck_sheet)

    dv = dsub.add_parser("see")
    dv.add_argument("deck", nargs="?")
    dv.add_argument("--width", type=int, default=1400)
    dv.set_defaults(func=cmd_deck_see)

    dr = dsub.add_parser("render")
    dr.add_argument("deck", nargs="?")
    dr.add_argument("--dpi", type=int, default=None)
    dr.add_argument("--png", action="store_true")
    dr.add_argument("--out", default=None)
    dr.set_defaults(func=cmd_deck_render)

    dq = dsub.add_parser("qa")
    dq.add_argument("deck", nargs="?")
    dq.add_argument("--dpi", type=int, default=None)
    dq.set_defaults(func=cmd_deck_qa)

    dm = dsub.add_parser("make")
    dm.add_argument("photos", nargs="+")
    dm.add_argument("--name", default=None)
    dm.add_argument("--direction", default="editorial")
    dm.add_argument("--palette", default="")
    _text_args(dm, deck=True)
    dm.set_defaults(func=cmd_deck_make)
    return p


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except (SpecError, PhotoError, config.RulesError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
