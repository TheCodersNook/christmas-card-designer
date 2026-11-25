"""The gate: rulebook checks, measured type, faces and print sanity."""
from __future__ import annotations

from typing import Any

from . import compose, config, layouts, render
from .photos import PhotoError, load
from .spec import CardSpec


def _comp(design: layouts.Design) -> dict[str, Any]:
    data = design.to_dict()
    data["name"] = design.label
    data["side"] = "front"
    return data


def geometry(spec: CardSpec, design: layouts.Design) -> tuple[list[str], list[str]]:
    issues = compose.validate_composition(_comp(design), spec, spec.card_inches,
                                          compose.load_photo_stats(spec))
    errors = [i.message for i in issues if i.level == "error"]
    warnings = [i.message for i in issues if i.level == "warn"]
    if not design.zones:
        errors.append("no room for words: the composition has no text zones")
    return errors, warnings


def typography(spec: CardSpec, design: layouts.Design) -> tuple[list[str], list[str], dict[str, Any]]:
    """Render small and read the real measured type back."""
    errors: list[str] = []
    warnings: list[str] = []
    try:
        result = render.render_front(spec, design, dpi=110, bleed=False, texture=False)
    except Exception as exc:  # a broken photograph should not crash the gate
        errors.append(f"{design.label}: could not draw the composition ({exc})")
        return errors, warnings, {}
    blocks = result.metrics.get("blocks", [])
    short_px = min(result.metrics["trim_px"])
    dpi = result.metrics["dpi"]
    min_pt = float(config.COMPOSE.get("type_safety", {}).get("min_pt", 7.0))
    for block in blocks:
        if block.get("truncated"):
            warnings.append(f"{design.label}: the {block['role']} was shortened to fit")
        if block["role"] in ("message", "signature", "caption") and block["pt"] < min_pt:
            warnings.append(f"{design.label}: the {block['role']} prints at {block['pt']:.1f} pt, "
                            f"below the {min_pt:.1f} pt floor; shorten it or give it a larger zone")
        if block["role"] in ("greeting", "family", "title", "statement") and block["size_px"] < short_px * 0.022:
            warnings.append(f"{design.label}: the {block['role']} is too small to lead the card")
        contrast = block.get("color", {}).get("contrast", 9)
        if contrast < 3.0:
            warnings.append(f"{design.label}: {block['role']} contrast is {contrast}:1")
    if not blocks:
        errors.append(f"{design.label}: no text reached the card")
    for role in config.TEXT_ROLES:
        if spec.text.get(role) and not any(b["role"] == role for b in blocks):
            warnings.append(f"{design.label}: the {role} could not be placed")
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
        target = need_w / max(1.0, need_h)
        src = photo.aspect
        available = photo.height * target if src > target else photo.width
        scale = need_w / max(1.0, available)
        if scale > 1.8:
            warnings.append(f"{photo.path.name} is used at {scale:.1f}x its pixels in this composition "
                            f"({photo.width}x{photo.height}); it will look soft at {dpi} DPI")
    return warnings


def check(spec: CardSpec, design: layouts.Design | None = None, dpi: int = 300) -> dict[str, Any]:
    design = design or spec.front_design()
    if design is None:
        return {"errors": ["no composition yet - read ./ccb brief and write one"],
                "warnings": [], "facts": {}}
    errors, warnings = geometry(spec, design)
    e2, w2, facts = typography(spec, design)
    errors += e2
    warnings += w2
    warnings += photo_resolution(spec, design, dpi)
    if not any(str(t).strip() for t in spec.text.values()):
        errors.append("the card has no words: fill in greeting, family or message")
    if not str(spec.text.get("greeting", "")).strip() and not str(spec.text.get("family", "")).strip():
        warnings.append("there is no greeting or family name - the front will feel anonymous")
    facts.update({
        "design": design.label,
        "engine": "composition",
        "photos": len(spec.photo_paths),
        "coverage": round(design.coverage, 3),
        "card_in": list(spec.card_inches),
        "style": spec.style.label,
        "palette": spec.palette.label,
        "dpi": dpi,
    })
    return {"errors": errors, "warnings": warnings, "facts": facts}


def check_card(spec: CardSpec, dpi: int = 300) -> dict[str, Any]:
    """Check every saved composition, not only the selected front."""
    report = {"errors": [], "warnings": [], "facts": {}}
    if not spec.compositions:
        report["errors"].append("no composition yet - read ./ccb brief and write one")
        return report
    for comp in spec.compositions:
        design = compose.design(comp)
        issues = compose.validate_composition(comp, spec, spec.card_inches,
                                             compose.load_photo_stats(spec))
        report["errors"] += [f"{design.label}: {i.message}" for i in issues if i.level == "error"]
        report["warnings"] += [f"{design.label}: {i.message}" for i in issues if i.level == "warn"]
    front = spec.front_design()
    if front is not None:
        e, w, facts = typography(spec, front)
        report["errors"] += e
        report["warnings"] += w
        report["facts"] = facts
        report["warnings"] += photo_resolution(spec, front, dpi)
        report["facts"].update({
            "design": front.label, "engine": "composition",
            "photos": len(spec.photo_paths), "coverage": round(front.coverage, 3),
            "card_in": list(spec.card_inches), "style": spec.style.label,
            "palette": spec.palette.label, "dpi": dpi,
        })
    report["warnings"] += [i.message for i in compose.validate_card(spec) if i.level == "warn"]
    return report


def print_report(report: dict[str, Any]) -> bool:
    facts = report.get("facts", {})
    if facts:
        print(f"design  {facts.get('design')} (free composition)")
        card = facts.get("card_in", ["?", "?"])
        print(f"card    {card[0]} x {card[1]} in, {facts.get('style')} / {facts.get('palette')}")
        print(f"photos  {facts.get('photos')} covering {facts.get('coverage', 0) * 100:.0f}% of the card")
        if facts.get("smallest_pt"):
            print(f"type    {facts['smallest_pt']:.1f}-{facts['largest_pt']:.1f} pt")
    for warning in dict.fromkeys(report.get("warnings", [])):
        print(f"WARN  {warning}")
    for error in dict.fromkeys(report.get("errors", [])):
        print(f"ERROR {error}")
    if not report.get("errors"):
        print("gate: 0 errors")
    return not report.get("errors")
