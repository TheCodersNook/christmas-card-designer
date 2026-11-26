"""End-to-end self-test: compositions in, checked PDFs and previews out."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from . import check as gate, compose, config, deck as deck_mod, export as export_mod, faces, samples
from . import see, sheet
from .spec import CardSpec


PALETTE = {
    "bg": "#F6F0E4", "ink": "#20291F", "soft": "#5C6657",
    "accent": "#8C1F26", "panel": "#20291F", "on_panel": "#F6F0E4",
}

FRONT = {
    "name": "Full bleed",
    "side": "front",
    "background": {"photo": 0, "scrim": 0.62, "scrim_from": "bottom", "scrim_reach": 0.55},
    "zones": [
        {"word": "greeting", "x": 0.07, "y": 0.60, "w": 0.80, "h": 0.13,
         "size": 0.085, "font": "playfair", "weight": 600, "tracking": -0.01,
         "leading": 1.05, "align": "left", "over_photo": True},
        {"word": "family", "x": 0.07, "y": 0.745, "w": 0.70, "h": 0.05,
         "size": 0.030, "font": "lato", "weight": 400, "tracking": 0.10,
         "leading": 1.3, "align": "left", "over_photo": True},
        {"word": "signature", "x": 0.07, "y": 0.845, "w": 0.70, "h": 0.05,
         "size": 0.024, "font": "instrument", "weight": 400, "italic": True,
         "leading": 1.25, "align": "left", "over_photo": True},
    ],
    "slots": [], "ornaments": [], "lines": [],
}

BACK = {
    "name": "Note",
    "side": "back",
    "background": {"fill": "bg"},
    "shapes": [{"kind": "band", "x": 0, "y": 0.0, "w": 1.0, "h": 0.055, "fill": "accent"}],
    "zones": [
        {"word": "message", "x": 0.12, "y": 0.20, "w": 0.76, "h": 0.34,
         "size": 0.026, "font": "lato", "weight": 400, "leading": 1.45, "align": "left"},
        {"word": "signature", "x": 0.12, "y": 0.60, "w": 0.60, "h": 0.06,
         "size": 0.030, "font": "instrument", "weight": 400, "italic": True,
         "leading": 1.25, "align": "left"},
        {"word": "year", "x": 0.12, "y": 0.70, "w": 0.40, "h": 0.035,
         "size": 0.018, "font": "lato", "weight": 700, "tracking": 0.18,
         "caps": True, "leading": 1.2, "align": "left", "color": "soft"},
    ],
    "ornaments": [], "lines": [],
    "chrome": {"border": "rule"},
}

SLIDES = [
    {
        "name": "Cover",
        "background": {"photo": 0, "scrim": 0.72, "scrim_from": "left", "scrim_reach": 0.55},
        "zones": [
            {"word": "title", "x": 0.07, "y": 0.24, "w": 0.46, "h": 0.22,
             "size": 0.105, "font": "playfair", "weight": 600, "tracking": -0.012,
             "leading": 1.02, "align": "left", "over_photo": True},
            {"word": "subtitle", "x": 0.07, "y": 0.49, "w": 0.40, "h": 0.06,
             "size": 0.024, "font": "lato", "weight": 400, "tracking": 0.14,
             "caps": True, "leading": 1.3, "align": "left", "over_photo": True},
            {"word": "greeting", "x": 0.07, "y": 0.68, "w": 0.40, "h": 0.09,
             "size": 0.040, "font": "instrument", "weight": 400, "italic": True,
             "leading": 1.1, "align": "left", "over_photo": True},
        ],
        "slots": [], "ornaments": [], "lines": [],
    },
    {
        "name": "Plate",
        "background": {"fill": "bg"},
        "shapes": [{"kind": "arch", "x": 0.04, "y": 0.08, "w": 0.40, "h": 0.84, "fill": "accent"}],
        "slots": [{"photo": 1, "x": 0.055, "y": 0.10, "w": 0.37, "h": 0.80, "clip": "arch"}],
        "zones": [
            {"word": "message", "x": 0.54, "y": 0.28, "w": 0.36, "h": 0.30,
             "size": 0.030, "font": "lato", "weight": 400, "leading": 1.5, "align": "left"},
            {"word": "caption", "x": 0.54, "y": 0.64, "w": 0.36, "h": 0.04,
             "size": 0.018, "font": "lato", "weight": 400, "tracking": 0.12,
             "caps": True, "leading": 1.2, "align": "left", "text": "First snow"},
        ],
        "ornaments": [], "lines": [
            {"x1": 0.54, "y1": 0.61, "x2": 0.90, "y2": 0.61, "token": "accent", "weight": 1},
        ],
    },
    {
        "name": "Three cuts",
        "background": {"fill": "bg"},
        "slots": [
            {"photo": 0, "x": 0.06, "y": 0.14, "w": 0.28, "h": 0.62, "layer": 1},
            {"photo": 1, "x": 0.36, "y": 0.20, "w": 0.28, "h": 0.58, "layer": 2},
            {"photo": 2, "x": 0.66, "y": 0.10, "w": 0.28, "h": 0.62, "layer": 3},
        ],
        "zones": [
            {"word": "caption", "x": 0.06, "y": 0.86, "w": 0.88, "h": 0.04,
             "size": 0.016, "font": "lato", "weight": 400, "tracking": 0.16,
             "caps": True, "leading": 1.2, "align": "center", "text": "A quiet year"},
        ],
        "ornaments": [], "lines": [],
    },
]


def run() -> int:
    failures = 0

    def ok(label: str, condition: bool, note: str = "") -> None:
        nonlocal failures
        print(f"  {'ok  ' if condition else 'FAIL'} {label}{(' - ' + note) if note else ''}")
        failures += 0 if condition else 1

    demo = samples.write_demo_photos()
    print("selftest: rules, compositions, faces, print")
    with tempfile.TemporaryDirectory(prefix="ccb-test-") as tmp:
        root = Path(tmp)
        folder = root / "card"
        folder.mkdir()
        copied = []
        for path in demo[:3]:
            dest = folder / path.name
            shutil.copy2(path, dest)
            copied.append(dest.name)
        spec = CardSpec.create(folder, "selftest", copied, size="5x7")
        spec.text.update({"greeting": "Merry Christmas", "family": "The Test Family",
                          "message": "A year of small adventures and a great deal of snow.",
                          "signature": "with love, Anna and Tom", "year": "2026"})
        spec.save()

        issues, _ = compose.install(spec, {"system": {"palette": PALETTE},
                                           "front": FRONT, "back": BACK})
        errors = [i for i in issues if i.level == "error"]
        ok("compositions pass the rulebook", not errors,
           "; ".join(i.message for i in errors[:2]))
        ok("composition is saved", len(spec.front_compositions) == 1 and spec.back() is not None)
        ok("the palette is the one that was written", spec.palette.ink.lower() == PALETTE["ink"].lower())

        report = gate.check_card(spec, dpi=300)
        ok("gate is clean", not report["errors"], "; ".join(report["errors"][:2]))
        ok("type is measured", report["facts"].get("smallest_pt", 0) > 0,
           f"{report['facts'].get('smallest_pt', 0):.1f} pt floor")

        manifest = export_mod.export(spec, spec.front_design(), dpi=150,
                                     back=True, back_design=spec.back_design())
        pdf = spec.folder / "out" / "selftest.pdf"
        ok("PDF is two pages", pdf.exists() and pdf.stat().st_size > 1000)
        problems = deck_mod.verify_files(pdf, 2, (5 + 2 * config.BLEED_IN, 7 + 2 * config.BLEED_IN))
        ok("PDF page size is trim + bleed", not problems, "; ".join(problems))

        sheet_path = sheet.build_sheet(spec, out=spec.folder / "out" / "designs.jpg")
        ok("contact sheet written", sheet_path.exists())
        seen = see.write(spec, width=900)
        ok("annotated preview written", (seen / "front.png").exists() and (seen / "photos.jpg").exists())
        ok("visual report written", (seen / "visual.md").exists())

        det = faces.status()
        ok("face engine reports honestly", det["detector"] in ("YuNet", "Haar", "none"),
           det["detector"])
        if det["detector"] != "none":
            stats = compose.load_photo_stats(spec)
            ok("face scan ran on every photograph", len(stats) == 3)

        # A palette that cannot be read must be refused, not rendered hopefully.
        bad = compose.validate_system({"palette": {**PALETTE, "ink": "#F8F8F8"}})
        ok("an unreadable palette is caught", any(i.level == "error" for i in bad),
           "; ".join(i.message for i in bad[:1]))

        # A zone without a size is refused: the agent has to decide it.
        nosize = dict(FRONT)
        nosize["zones"] = [{k: v for k, v in FRONT["zones"][0].items() if k != "size"}]
        missing = compose.validate_composition(nosize, spec, spec.card_inches)
        ok("a zone without a size is refused",
           any(i.level == "error" and i.code == "type.size" for i in missing))

        deck_folder = root / "deck"
        deck_folder.mkdir()
        deck_photos = []
        for path in demo[:3]:
            dest = deck_folder / path.name
            shutil.copy2(path, dest)
            deck_photos.append(dest.name)
        dspec = deck_mod.DeckSpec.create(deck_folder, "selftest-deck", deck_photos)
        dspec.text.update({"title": "The Test Family", "subtitle": "2026 in photographs",
                           "greeting": "Merry Christmas", "message": "A quieter year, mostly at home.",
                           "signature": "with love, Anna and Tom", "year": "2026"})
        dspec.save()
        dissues, count = deck_mod.install(dspec, {"system": {"palette": PALETTE}, "slides": SLIDES})
        derrors = [i for i in dissues if i.level == "error"]
        ok("slides pass the rulebook", not derrors, "; ".join(i.message for i in derrors[:2]))
        dreport = deck_mod.check(dspec, dpi=150)
        ok("deck gate is clean", not dreport["errors"], "; ".join(dreport["errors"][:2]))
        deck_mod.export(dspec, dpi=150, png=True)
        dpdf = deck_folder / "out" / "selftest-deck.pdf"
        dprobs = deck_mod.verify_files(dpdf, 3, (40 / 3, 7.5))
        ok("deck PDF is three 16:9 pages", not dprobs, "; ".join(dprobs))
        ok("slide PNGs written", len(list((deck_folder / "out" / "slides").glob("*.png"))) == 3)

    print(f"\nselftest: {'PASS' if failures == 0 else 'FAIL'} ({failures} failure(s))")
    return 0 if failures == 0 else 1
