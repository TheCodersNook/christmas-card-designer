"""The gate: geometry, typography and print checks before anything is exported."""
from __future__ import annotations

from typing import Any

from . import config, layouts, render, typefit
from .photos import PhotoError, load
from .spec import CardSpec


def _overlap(a: dict[str, float], b: dict[str, float]) -> float:
    x = max(0.0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    y = max(0.0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    return x * y


def geometry(spec: CardSpec, design: layouts.Design) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    n = len(spec.photo_paths)
    seen = [s.photo for s in design.slots]
    if sorted(seen) != list(range(n)):
        missing = [i for i in range(n) if i not in seen]
        errors.append(f"{design.engine}: photographs used {sorted(set(seen))}, expected 0..{n - 1}"
                      + (f" (missing {missing})" if missing else ""))
    for slot in design.slots:
        if slot.x < -1e-6 or slot.y < -1e-6 or slot.x + slot.w > 1 + 1e-6 or slot.y + slot.h > 1 + 1e-6:
            errors.append(f"{design.engine}: photograph slot {slot.photo} leaves the card")
        if slot.w <= 0.01 or slot.h <= 0.01:
            errors.append(f"{design.engine}: photograph slot {slot.photo} is too small to see")
    for zone in design.zones:
        if zone.x < -1e-6 or zone.y < -1e-6 or zone.x + zone.w > 1 + 1e-6 or zone.y + zone.h > 1 + 1e-6:
            errors.append(f"{design.engine}: text zone {zone.roles} leaves the card")
        for slot in design.slots:
            if _overlap({"x": zone.x, "y": zone.y, "w": zone.w, "h": zone.h},
                        {"x": slot.x, "y": slot.y, "w": slot.w, "h": slot.h}) > 1e-6:
                errors.append(f"{design.engine}: text {zone.roles} sits on top of a photograph")
    m = spec.style.margin
    for zone in design.zones:
        if zone.x < m - 0.02 or zone.y < m - 0.02 or zone.x + zone.w > 1 - m + 0.02 or zone.y + zone.h > 1 - m + 0.02:
            warnings.append(f"{design.engine}: {zone.roles} comes closer to the trim edge than the "
                            f"{m * 100:.0f}% margin")
    if not design.zones:
        errors.append(f"{design.engine}: no room for words")
    return errors, warnings


def typography(spec: CardSpec, design: layouts.Design) -> tuple[list[str], list[str], dict[str, Any]]:
    """Render small and read the real measured type back."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        result = render.render_front(spec, design, dpi=110, bleed=False, texture=False)
    except Exception as exc:  # a broken photograph should not crash the gate
        errors.append(f"{design.engine}: could not draw the design ({exc})")
        return errors, warnings, {}
    blocks = result.metrics.get("blocks", [])
    short_px = min(result.metrics["trim_px"])
    dpi = result.metrics["dpi"]
    for block in blocks:
        if block.get("truncated"):
            warnings.append(f"{design.engine}: the {block['role']} was shortened to fit")
        if block["role"] in ("message", "signature") and block["size_px"] < short_px * 0.016:
            warnings.append(f"{design.engine}: the {block['role']} prints at {block['pt']:.1f} pt, smaller than "
                            f"is comfortable; shorten it")
        contrast = block.get("color", {}).get("contrast", 9)
        if contrast < 3.0:
            warnings.append(f"{design.engine}: {block['role']} contrast is {contrast}:1")
    if not blocks:
        errors.append(f"{design.engine}: no text reached the card")
    if spec.text.get("message") and not any(b["role"] == "message" for b in blocks):
        warnings.append(f"{design.engine}: the message could not be placed")
    facts = {
        "blocks": blocks,
        "smallest_pt": min((b["pt"] for b in blocks), default=0),
        "largest_pt": max((b["pt"] for b in blocks), default=0),
        "dpi_probe": dpi,
    }
    return errors, warnings, facts


def photo_resolution(spec: CardSpec, design: layouts.Design, dpi: int) -> list[str]:
    warnings = []
    cw, ch = spec.card_inches
    for slot in design.slots:
        try:
            photo = load(spec.photo_paths[slot.photo])
        except PhotoError as exc:
            warnings.append(str(exc))
            continue
        need_w = slot.w * cw * dpi
        need_h = slot.h * ch * dpi
        target = need_w / need_h
        src = photo.aspect
        if src > target:
            available = photo.height * target
        else:
            available = photo.width
        scale = need_w / max(1.0, available)
        if scale > 1.8:
            warnings.append(f"{photo.path.name} is used at {scale:.1f}x its pixels in this design "
                            f"({photo.width}x{photo.height}); it will look soft at {dpi} DPI")
    return warnings


def check(spec: CardSpec, design: layouts.Design | None = None, dpi: int = 300) -> dict[str, Any]:
    design = design or (layouts.Design.from_dict(spec.current_design()) if spec.current_design() else None)
    if design is None:
        return {"errors": ["no designs yet - run ./ccb auto"], "warnings": [], "facts": {}}
    errors, warnings = geometry(spec, design)
    e2, w2, facts = typography(spec, design)
    errors += e2
    warnings += w2
    warnings += photo_resolution(spec, design, dpi)
    text = spec.text
    if not any(typefit.clean(text.get(r, "")) for r in config.TEXT_ROLES):
        errors.append("the card has no words: fill in greeting, family or message")
    if not typefit.clean(text.get("greeting", "")) and not typefit.clean(text.get("family", "")):
        warnings.append("there is no greeting or family name - the front will feel anonymous")
    facts.update({
        "design": design.label,
        "engine": design.engine,
        "score": design.score,
        "photos": len(spec.photo_paths),
        "coverage": round(design.coverage, 3),
        "card_in": list(spec.card_inches),
        "style": spec.style.label,
        "palette": spec.palette.label,
        "dpi": dpi,
    })
    return {"errors": errors, "warnings": warnings, "facts": facts}


def print_report(report: dict[str, Any]) -> bool:
    facts = report.get("facts", {})
    if facts:
        print(f"design  {facts.get('design')} ({facts.get('engine')}), score {facts.get('score')}")
        print(f"card    {facts.get('card_in', ['?', '?'])[0]} x {facts.get('card_in', ['?', '?'])[1]} in, "
              f"{facts.get('style')} / {facts.get('palette')}")
        print(f"photos  {facts.get('photos')} covering {facts.get('coverage', 0) * 100:.0f}% of the card")
        if facts.get("smallest_pt"):
            print(f"type    {facts['smallest_pt']:.1f}-{facts['largest_pt']:.1f} pt")
    for warning in report.get("warnings", []):
        print(f"WARN  {warning}")
    for error in report.get("errors", []):
        print(f"ERROR {error}")
    if not report.get("errors"):
        print("gate: 0 errors")
    return not report.get("errors")
