"""End-to-end self test with generated photographs - no sample files needed."""
from __future__ import annotations

import shutil
import tempfile
import time
from pathlib import Path

from . import auto, check as gate, config, export as export_mod, layouts, samples, sheet as sheet_mod
from .photos import load
from .spec import CardSpec


def run(keep: bool = False) -> int:
    started = time.time()
    tmp = Path(tempfile.mkdtemp(prefix="ccb-selftest-"))
    failures: list[str] = []
    checks: list[str] = []

    def ok(label: str, condition: bool, detail: str = "") -> None:
        checks.append(f"  {'ok  ' if condition else 'FAIL'} {label}{(' - ' + detail) if detail and not condition else ''}")
        if not condition:
            failures.append(label + (f" ({detail})" if detail else ""))

    try:
        photo_paths = samples.write_demo_photos(tmp / "inputs")
        ok("six demo photographs drawn", len(photo_paths) == 6, str(len(photo_paths)))
        photos = [load(p) for p in photo_paths]
        ok("every demo photograph loads", all(p.megapixels > 0.4 for p in photos))
        ok("shapes differ", len({p.orientation for p in photos}) >= 2)

        folder = tmp / "cards" / "selftest"
        spec = CardSpec.create(folder, "selftest", [str(p) for p in photo_paths],
                               style="classic", size="5x7")
        spec.text.update({
            "greeting": "Merry Christmas",
            "family": "The Selftest Family",
            "message": "Wishing you a warm, bright Christmas and a happy new year from all of us.",
            "signature": "with love, Anna and Tom",
            "year": "2026",
        })
        spec.save()

        plan_started = time.time()
        designs = auto.plan(spec)
        plan_seconds = time.time() - plan_started
        ok("six designs planned", len(designs) == 6, str(len(designs)))
        ok("every design places every photograph",
           all(len(d.slots) == len(photos) for d in designs))
        ok("scores are sane", all(30 <= d.score <= 100 for d in designs))
        ok("designs differ", len({d.engine for d in designs}) == len(designs))

        for design in designs:
            report = gate.check(spec, design, dpi=300)
            if report["errors"]:
                failures.append(f"{design.engine}: {report['errors'][0]}")
        ok("gate is clean for every design", not any(f for f in failures if ":" in f))

        sheet_path = sheet_mod.build_sheet(spec, designs, folder / "out" / "designs.jpg")
        ok("contact sheet written", sheet_path.exists() and sheet_path.stat().st_size > 20_000)

        for style_key in config.STYLES:
            spec.design["style"] = style_key
            style_designs = layouts.build(spec, photos)
            if not style_designs or len(style_designs[0].slots) != len(photos):
                failures.append(f"style {style_key} could not place every photograph")
        ok("all eight styles place every photograph", not any("style " in f for f in failures))
        spec.design["style"] = "classic"
        spec.save()

        manifest = export_mod.export(spec, designs[0], fmt="pdf", dpi=300)
        problems = export_mod.verify_files(spec, manifest)
        ok("PDF page size and page count verified", not problems, "; ".join(problems))
        pages = manifest["files"][0].get("pages", [])
        ok("PDF is two pages (front and back)", len(pages) == 2, str(len(pages)))
        ok("PDF page is trim + bleed", abs(pages[0]["w_in"] - 5.25) < 0.01 and abs(pages[0]["h_in"] - 7.25) < 0.01,
           f"{pages[0]['w_in']}x{pages[0]['h_in']}")

        png = export_mod.export(spec, designs[0], fmt="png", dpi=150, back=False)
        item = png["files"][0]
        expected = list(export_mod.render.canvas_px(spec, 150, True)[:2])
        ok("PNG is exactly trim + bleed at 150 DPI", item["px"] == expected, f"{item['px']} vs {expected}")
        ok("PNG DPI metadata", export_mod.verify_files(spec, png) == [])

        german = "Fröhliche Weihnachten"
        spec.text["greeting"] = german
        spec.save()
        report = gate.check(spec, designs[0])
        ok("accented characters survive the gate", not report["errors"], "; ".join(report["errors"]))
        spec.text["greeting"] = "Merry Christmas"
        spec.save()

        elapsed = time.time() - started
        print("\n".join(checks))
        print(f"  ---- {len(failures)} failure(s), {plan_seconds:.2f}s to plan six designs, {elapsed:.1f}s total")
        if failures:
            print("\nFAIL:")
            for failure in failures:
                print(f"  - {failure}")
            return 1
        print("\nselftest: PASS")
        return 0
    finally:
        if keep:
            print(f"\nkept the test card at {tmp}")
        else:
            shutil.rmtree(tmp, ignore_errors=True)
