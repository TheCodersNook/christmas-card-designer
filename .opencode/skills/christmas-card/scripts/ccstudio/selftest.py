"""End-to-end self-test: compositions in, checked PDFs and previews out."""
from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from . import check as gate, compose, config, deck as deck_mod, export as export_mod, faces, samples
from . import see, sheet
from .spec import CardSpec


FRONT = {
    "name": "Quiet hero",
    "side": "front",
    "slots": [{"photo": 0, "x": 0.07, "y": 0.08, "w": 0.86, "h": 0.50, "treatment": "border"}],
    "zones": [
        {"roles": ["greeting"], "x": 0.07, "y": 0.62, "w": 0.86, "h": 0.10, "align": "center"},
        {"roles": ["family"], "x": 0.07, "y": 0.725, "w": 0.86, "h": 0.055},
        {"roles": ["message"], "x": 0.07, "y": 0.79, "w": 0.86, "h": 0.075},
        {"roles": ["signature", "year"], "x": 0.07, "y": 0.872, "w": 0.86, "h": 0.058},
    ],
    "ornaments": [{"kind": "holly", "density": 0.5}],
    "lines": [{"x1": 0.42, "y1": 0.60, "x2": 0.58, "y2": 0.60, "token": "accent", "weight": 1}],
}

BACK = {
    "name": "Back",
    "side": "back",
    "slots": [],
    "zones": [
        {"roles": ["message"], "x": 0.12, "y": 0.24, "w": 0.76, "h": 0.34, "align": "center"},
        {"roles": ["signature"], "x": 0.12, "y": 0.62, "w": 0.76, "h": 0.09},
        {"roles": ["year"], "x": 0.12, "y": 0.75, "w": 0.76, "h": 0.05},
    ],
    "ornaments": [],
    "lines": [{"x1": 0.44, "y1": 0.60, "x2": 0.56, "y2": 0.60, "token": "accent", "weight": 1}],
}

SLIDES = [
    {
        "name": "Cover",
        "slots": [{"photo": 0, "x": 0.52, "y": 0.0, "w": 0.48, "h": 1.0}],
        "zones": [
            {"roles": ["title"], "x": 0.07, "y": 0.28, "w": 0.38, "h": 0.18, "align": "left", "font": "heading"},
            {"roles": ["subtitle"], "x": 0.07, "y": 0.49, "w": 0.36, "h": 0.08, "align": "left"},
            {"roles": ["greeting"], "x": 0.07, "y": 0.68, "w": 0.36, "h": 0.09, "align": "left"},
            {"roles": ["signature"], "x": 0.07, "y": 0.82, "w": 0.36, "h": 0.06, "align": "left"},
        ],
        "ornaments": [],
        "lines": [{"x1": 0.07, "y1": 0.64, "x2": 0.40, "y2": 0.64, "token": "accent", "weight": 1}],
    },
    {
        "name": "Photograph",
        "slots": [{"photo": 1, "x": 0.0, "y": 0.0, "w": 0.56, "h": 1.0}],
        "zones": [
            {"roles": ["message"], "x": 0.63, "y": 0.34, "w": 0.30, "h": 0.24, "align": "left"},
            {"roles": ["caption"], "x": 0.63, "y": 0.62, "w": 0.30, "h": 0.06, "text": "First snow"},
        ],
        "ornaments": [],
        "lines": [],
    },
    {
        "name": "Gallery",
        "slots": [
            {"photo": 0, "x": 0.07, "y": 0.10, "w": 0.26, "h": 0.74},
            {"photo": 1, "x": 0.37, "y": 0.10, "w": 0.26, "h": 0.74},
            {"photo": 2, "x": 0.67, "y": 0.10, "w": 0.26, "h": 0.74},
        ],
        "zones": [{"roles": ["caption"], "x": 0.07, "y": 0.88, "w": 0.86, "h": 0.05, "text": "A quiet year"}],
        "ornaments": [],
        "lines": [],
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
        spec = CardSpec.create(folder, "selftest", copied,
                              direction="classic", size="5x7")
        spec.text.update({"greeting": "Merry Christmas", "family": "The Test Family",
                          "message": "A year of small adventures and a great deal of snow.",
                          "signature": "with love, Anna and Tom", "year": "2026"})
        spec.save()

        issues, _ = compose.install(spec, {"front": FRONT, "back": BACK})
        errors = [i for i in issues if i.level == "error"]
        ok("compositions pass the rulebook", not errors,
           "; ".join(i.message for i in errors[:2]))
        ok("composition is saved", len(spec.front_compositions) == 1 and spec.back() is not None)

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

        deck_folder = root / "deck"
        deck_folder.mkdir()
        deck_photos = []
        for path in demo[:3]:
            dest = deck_folder / path.name
            shutil.copy2(path, dest)
            deck_photos.append(dest.name)
        dspec = deck_mod.DeckSpec.create(deck_folder, "selftest-deck", deck_photos,
                                         direction="editorial")
        dspec.text.update({"title": "The Test Family", "subtitle": "2026 in photographs",
                           "greeting": "Merry Christmas", "message": "A quieter year, mostly at home.",
                           "signature": "with love, Anna and Tom", "year": "2026"})
        dspec.save()
        dissues, count = deck_mod.install(dspec, {"slides": SLIDES})
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
