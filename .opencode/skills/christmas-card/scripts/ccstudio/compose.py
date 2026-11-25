"""Compositions: the brief, the rule checks and the installer.

There is no template here. The agent writes a composition (slots, zones,
ornaments, lines) and this module answers three questions: what does the
rulebook allow, what is wrong with this composition, and what should the agent
know before writing one.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import config, faces as faces_mod, layouts, photos as photo_mod
from .layouts import Design, Slot, Zone, overlaps
from .spec import CardSpec, SpecError


@dataclass
class Issue:
    level: str            # "error" | "warn"
    code: str
    message: str
    where: str = ""

    def line(self) -> str:
        tag = "ERROR" if self.level == "error" else "warn "
        loc = f" [{self.where}]" if self.where else ""
        return f"{tag} {self.code}{loc}  {self.message}"


def design(comp: dict[str, Any]) -> Design:
    d = Design.from_dict(comp)
    d.label = str(comp.get("name") or d.label)
    return d


# --------------------------------------------------------------------- limits
def _rect(where: str, item: dict[str, Any], issues: list[Issue]) -> tuple[float, float, float, float] | None:
    try:
        x, y, w, h = float(item["x"]), float(item["y"]), float(item["w"]), float(item["h"])
    except (KeyError, TypeError, ValueError):
        issues.append(Issue("error", "rect.missing", "needs x, y, w and h as fractions of the page", where))
        return None
    for name, value in (("x", x), ("y", y), ("w", w), ("h", h)):
        if not (0.0 <= value <= 1.0):
            issues.append(Issue("error", "rect.bounds", f"{name}={value} is outside 0..1", where))
    if w <= 0 or h <= 0:
        issues.append(Issue("error", "rect.size", "width and height must be positive", where))
        return None
    if x + w > 1.0001 or y + h > 1.0001:
        issues.append(Issue("error", "rect.bounds", "the rectangle runs off the page", where))
    return x, y, w, h


def validate_composition(comp: dict[str, Any], spec: CardSpec | None = None,
                         canvas: tuple[float, float] | None = None,
                         photo_stats: list[photo_mod.Photo] | None = None) -> list[Issue]:
    issues: list[Issue] = []
    if not isinstance(comp, dict):
        return [Issue("error", "composition.type", "a composition must be a JSON object")]
    name = str(comp.get("name") or "composition")
    slots = comp.get("slots") or []
    zones = comp.get("zones") or []
    if not isinstance(slots, list) or not isinstance(zones, list):
        return [Issue("error", "composition.shape", "slots and zones must be lists", name)]

    style = spec.style if spec else config.style(None)
    card = canvas or (spec.card_inches if spec else (5.0, 7.0))
    count = len(spec.photo_paths) if spec else 99
    if spec is None:
        count = max([int(s.get("photo", 0)) for s in slots if isinstance(s, dict)] + [0]) + 1

    slot_rules = config.COMPOSE.get("slots", {})
    zone_rules = config.COMPOSE.get("zones", {})
    treatments = [str(v) for v in slot_rules.get("treatments", [])]
    alignments = [str(v) for v in zone_rules.get("alignments", [])]
    valigns = [str(v) for v in zone_rules.get("valigns", [])]

    if len(slots) > int(slot_rules.get("max", 12)):
        issues.append(Issue("error", "slots.count", f"{len(slots)} photographs; the maximum is {slot_rules.get('max')}", name))
    if len(zones) > int(zone_rules.get("max", 10)):
        issues.append(Issue("error", "zones.count", f"{len(zones)} text zones; the maximum is {zone_rules.get('max')}", name))

    seen_photos: list[int] = []
    rects: list[tuple[str, tuple[float, float, float, float]]] = []
    for i, slot in enumerate(slots):
        where = f"{name} slot {i + 1}"
        rect = _rect(where, slot, issues)
        try:
            index = int(slot.get("photo"))
        except (TypeError, ValueError):
            issues.append(Issue("error", "photo.missing", "photo must be an index into the project's photographs", where))
            index = -1
        if index >= 0 and not (0 <= index < count):
            issues.append(Issue("error", "photo.range", f"photo {index} does not exist (there are {count})", where))
        if index >= 0:
            seen_photos.append(index)
        treatment = str(slot.get("treatment", "")).lower()
        if treatment and treatment not in treatments:
            issues.append(Issue("error", "photo.treatment", f"unknown treatment '{treatment}'; use {', '.join(treatments)}", where))
        focus = slot.get("focus")
        if focus is not None:
            if not isinstance(focus, (list, tuple)) or len(focus) != 2:
                issues.append(Issue("error", "photo.focus", "focus must be [x, y] fractions", where))
            else:
                for v in focus:
                    if not (0.0 <= float(v) <= 1.0):
                        issues.append(Issue("error", "photo.focus", "focus must be inside 0..1", where))
        if rect:
            if min(rect[2], rect[3]) < float(slot_rules.get("min_side", 0.06)):
                issues.append(Issue("warn", "photo.small", f"a slot {min(rect[2], rect[3]):.2f} of the page is very small", where))
            rects.append((where, rect))

    total_photo = sum(s.w * s.h for s in design({"slots": slots}).slots)
    lo = float(config.COMPOSE.get("photos", {}).get("min_coverage", 0.2))
    hi = float(config.COMPOSE.get("photos", {}).get("max_coverage", 0.84))
    # A text-only back is legitimate; coverage only applies once something is placed.
    if slots and total_photo < lo:
        issues.append(Issue("warn", "photos.coverage", f"photographs cover only {total_photo * 100:.0f}% (aim for {lo * 100:.0f}-{hi * 100:.0f}%)", name))
    if total_photo > hi:
        issues.append(Issue("error", "photos.coverage", f"photographs cover {total_photo * 100:.0f}% (maximum {hi * 100:.0f}%)", name))

    for i, zone in enumerate(zones):
        where = f"{name} zone {i + 1}"
        rect = _rect(where, zone, issues)
        roles = [str(r) for r in zone.get("roles", [])]
        if not roles:
            issues.append(Issue("error", "type.roles", "a text zone needs at least one role", where))
        for role in roles:
            if role not in config.ROLE_RULES:
                issues.append(Issue("error", "type.role", f"'{role}' is not a role in the rulebook", where))
        align = str(zone.get("align", "")).lower()
        if align and align not in alignments:
            issues.append(Issue("error", "type.align", f"align must be one of {', '.join(alignments)}", where))
        valign = str(zone.get("valign", "center")).lower()
        if valign not in valigns:
            issues.append(Issue("error", "type.valign", f"valign must be one of {', '.join(valigns)}", where))
        font = str(zone.get("font", "")).lower()
        if font and font not in ("heading", "body", "script"):
            issues.append(Issue("error", "type.font", "font must be heading, body or script", where))
        try:
            scale = float(zone.get("scale", 1.0))
        except (TypeError, ValueError):
            scale = 1.0
        if not (0.35 <= scale <= 2.2):
            issues.append(Issue("error", "type.scale", "scale must be between 0.35 and 2.2", where))
        if rect:
            if rect[2] < float(zone_rules.get("min_width", 0.16)):
                issues.append(Issue("warn", "type.narrow", "a text zone this narrow will break words", where))
            if rect[2] * rect[3] < float(zone_rules.get("min_area", 0.006)):
                issues.append(Issue("warn", "type.small", "the text zone is very small for its copy", where))
            m = style.margin
            if spec is not None and (rect[0] < m - 0.02 or rect[1] < m - 0.02 or
                                     rect[0] + rect[2] > 1 - m + 0.02 or rect[1] + rect[3] > 1 - m + 0.02):
                issues.append(Issue("warn", "type.margin", f"text leaves the {m:.3f} margin; the direction prefers it inside", where))
            rects.append((where, rect))

    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            wa, ra = rects[i]
            wb, rb = rects[j]
            area = overlaps(ra, rb)
            if area <= 1e-6:
                continue
            text_zone = wa.startswith(name + " zone") or wb.startswith(name + " zone")
            same_kind = wa.split()[-2] == wb.split()[-2]
            if text_zone and not same_kind:
                issues.append(Issue("error", "overlap.text_photo", f"{wa} overlaps {wb}", name))
            elif same_kind:
                issues.append(Issue("error", "overlap.same", f"{wa} overlaps {wb}", name))
            else:
                issues.append(Issue("error", "overlap.rect", f"{wa} overlaps {wb}", name))

    known_roles = {str(r) for z in zones if isinstance(z, dict) for r in z.get("roles", [])}
    if spec is not None:
        for role in known_roles:
            if not str(spec.text.get(role, "")).strip() and not any(
                    isinstance(z, dict) and z.get("text") and role in z.get("roles", []) for z in zones):
                issues.append(Issue("warn", "words.empty", f"role '{role}' is placed but has no words", name))

    ornaments = comp.get("ornaments") or []
    kinds = [str(v) for v in config.COMPOSE.get("ornaments", {}).get("kinds", [])]
    if len(ornaments) > int(config.COMPOSE.get("ornaments", {}).get("max", 4)):
        issues.append(Issue("error", "ornaments.count", "too many ornament groups", name))
    for i, item in enumerate(ornaments):
        kind = str(item.get("kind", "none")).lower() if isinstance(item, dict) else "none"
        if kind not in kinds:
            issues.append(Issue("error", "ornaments.kind", f"unknown ornament '{kind}'", f"{name} ornament {i + 1}"))

    lines = comp.get("lines") or []
    if len(lines) > int(config.COMPOSE.get("lines", {}).get("max", 8)):
        issues.append(Issue("error", "lines.count", "too many rules", name))
    for i, line in enumerate(lines):
        where = f"{name} line {i + 1}"
        if not isinstance(line, dict):
            issues.append(Issue("error", "lines.shape", "a rule is an object with x1, y1, x2, y2", where))
            continue
        for key in ("x1", "y1", "x2", "y2"):
            try:
                v = float(line[key])
            except (KeyError, TypeError, ValueError):
                issues.append(Issue("error", "lines.value", f"missing {key}", where))
                continue
            if not (0.0 <= v <= 1.0):
                issues.append(Issue("error", "lines.value", f"{key} is outside 0..1", where))
        token = str(line.get("token", "accent"))
        if token not in [str(v) for v in config.COMPOSE.get("lines", {}).get("tokens", [])]:
            token = {"ink": "ink", "soft": "soft", "accent": "accent"}.get(token, "accent")
        try:
            weight = float(line.get("weight", 1.0))
        except (TypeError, ValueError):
            weight = 1.0
        if weight > float(config.COMPOSE.get("lines", {}).get("max_weight", 3)):
            issues.append(Issue("error", "lines.weight", "a rule that heavy is a border; use weight 3 or less", where))

    # Face safety, only when we can actually see the photographs.
    if spec is not None and photo_stats is not None:
        for i, slot in enumerate(slots):
            rect = _rect(f"{name} slot {i + 1}", slot, []) if isinstance(slot, dict) else None
            try:
                index = int(slot.get("photo"))
            except (TypeError, ValueError, KeyError):
                continue
            if rect is None or not (0 <= index < len(photo_stats)):
                continue
            photo = photo_stats[index]
            if not photo.faces:
                continue
            where = f"{name} slot {i + 1}"
            tw = max(1, int(round(rect[2] * card[0] * 300)))
            th = max(1, int(round(rect[3] * card[1] * 300)))
            fx, fy = slot.get("focus") or photo.face_focus
            box = faces_mod.crop_box(photo.width, photo.height, tw, th, float(fx), float(fy))
            keep = min(faces_mod.keep_ratio(f, box, photo.width, photo.height) for f in photo.faces)
            threshold = float(config.COMPOSE.get("faces", {}).get("min_crop_keep", 0.65))
            if keep < threshold:
                issues.append(Issue("warn", "faces.crop",
                                    f"a face keeps only {keep * 100:.0f}% inside this crop (aim for {threshold * 100:.0f}%+)", where))
            widest = max(f.w for f in photo.faces)
            printed = widest * photo.width * (box[2] / max(1, photo.width)) / 300.0
            min_in = float(config.COMPOSE.get("faces", {}).get("min_width_in", 0.16))
            if printed < min_in:
                issues.append(Issue("warn", "faces.small", f"a face prints about {printed:.2f} in wide (aim for {min_in:.2f} in+)", where))

    return issues


def load_photo_stats(spec: CardSpec) -> list[photo_mod.Photo]:
    out = []
    for path in spec.photo_paths:
        try:
            out.append(photo_mod.load(path))
        except photo_mod.PhotoError:
            continue
    return out


def validate_card(spec: CardSpec) -> list[Issue]:
    issues: list[Issue] = []
    stats = load_photo_stats(spec)
    if not spec.compositions:
        issues.append(Issue("error", "composition.none", "no composition yet: write one with ./ccb brief, then ./ccb layout"))
        return issues
    if not spec.front_compositions:
        issues.append(Issue("error", "composition.front", "no composition has side 'front'"))
    for comp in spec.compositions:
        issues.extend(validate_composition(comp, spec, spec.card_inches, stats))
    used = {int(s.get("photo")) for c in spec.compositions for s in c.get("slots", [])
            if isinstance(s, dict) and str(s.get("photo", "")).lstrip("-").isdigit()}
    for i, photo in enumerate(stats):
        if i not in used:
            issues.append(Issue("warn", "photos.unused", f"photograph {i} ({photo.path.name}) is not placed", ""))
    if not "".join(spec.text.values()).strip():
        issues.append(Issue("error", "words.empty", "the card has no words at all"))
    if not str(spec.text.get("greeting", "")).strip():
        issues.append(Issue("warn", "words.greeting", "no greeting set"))
    return issues


# ------------------------------------------------------------------ installing
def normalise_payload(payload: Any) -> list[dict[str, Any]]:
    if isinstance(payload, dict):
        if "compositions" in payload and isinstance(payload["compositions"], list):
            comps = payload["compositions"]
        elif "slides" in payload and isinstance(payload["slides"], list):
            comps = payload["slides"]
        elif "front" in payload or "back" in payload:
            comps = []
            for side in ("front", "back"):
                comp = payload.get(side)
                if isinstance(comp, dict):
                    comp = {**comp, "side": side}
                    comps.append(comp)
            extra = payload.get("alternates") or payload.get("variants") or []
            if isinstance(extra, list):
                for comp in extra:
                    if isinstance(comp, dict):
                        comps.append({**comp, "side": "front"})
        elif any(k in payload for k in ("slots", "zones")):
            comps = [payload]
        else:
            comps = list(payload.values()) if all(isinstance(v, dict) for v in payload.values()) else []
    elif isinstance(payload, list):
        comps = payload
    else:
        raise SpecError("a composition must be a JSON object (or an object with 'front' and 'back')")
    out = []
    for i, comp in enumerate(comps):
        if not isinstance(comp, dict):
            raise SpecError(f"composition {i + 1} is not an object")
        comp = dict(comp)
        comp["name"] = str(comp.get("name") or f"Composition {i + 1}")
        comp["side"] = str(comp.get("side") or "front").lower()
        if comp["side"] not in ("front", "back"):
            comp["side"] = "front"
        out.append(comp)
    if not out:
        raise SpecError("the file contains no compositions")
    return out


def install(spec: CardSpec, payload: Any, select: int | None = None, append: bool = False) -> tuple[list[Issue], int]:
    comps = normalise_payload(payload)
    stats = load_photo_stats(spec)
    issues: list[Issue] = []
    for comp in comps:
        issues.extend(validate_composition(comp, spec, spec.card_inches, stats))
    if any(i.level == "error" for i in issues):
        return issues, 0
    if append:
        spec.compositions.extend(comps)
    else:
        spec.design["compositions"] = comps
    fronts = [i for i, c in enumerate(comps) if c["side"] == "front"] if not append else list(range(len(spec.compositions)))
    index = 0 if select is None else max(1, select) - 1
    index = min(max(0, index), max(0, len(fronts) - 1))
    spec.design["selected"] = index
    spec.save()
    return issues, index


# ---------------------------------------------------------------------- brief
def rule_digest() -> str:
    comp = config.COMPOSE
    sizes = ", ".join(f"{k} ({v[0]:g}x{v[1]:g} in)" for k, v in config.SIZES.items())
    roles = ", ".join(f"{k} {v.get('scale', 0):g}" for k, v in config.ROLE_RULES.items())
    return "\n".join([
        f"paper        {sizes}",
        f"bleed        {config.BLEED_IN} in, export dpi 96-{config.MAX_DPI}",
        f"margins      {comp.get('margin', {}).get('recommended_min', 0.045)}-{comp.get('margin', {}).get('recommended_max', 0.12)} (each direction has its own)",
        f"photographs  {comp.get('photos', {}).get('min_coverage', 0.2)}-{comp.get('photos', {}).get('max_coverage', 0.84)} of the page, max {comp.get('slots', {}).get('max', 12)} slots",
        f"treatments   {', '.join(comp.get('slots', {}).get('treatments', []))}",
        f"text zones   max {comp.get('zones', {}).get('max', 10)}; align {', '.join(comp.get('zones', {}).get('alignments', []))}; valign {', '.join(comp.get('zones', {}).get('valigns', []))}",
        f"ornaments    {', '.join(comp.get('ornaments', {}).get('kinds', []))} (max {comp.get('ornaments', {}).get('max', 4)})",
        f"rules/lines  max {comp.get('lines', {}).get('max', 8)}; tokens {', '.join(comp.get('lines', {}).get('tokens', []))}",
        f"faces        keep {comp.get('faces', {}).get('min_crop_keep', 0.65):.0%} of every face; print at least {comp.get('faces', {}).get('min_width_in', 0.16)} in wide",
        f"type roles   {roles}   (fractions of the short side)",
    ])


def brief(spec: CardSpec) -> str:
    w, h = spec.card_inches
    dpi = int(spec.export.get("dpi", 300) or 300)
    style = spec.style
    lines = [
        f"# Design brief: {spec.name}",
        "",
        f"Canvas       {w:g} x {h:g} in ({w * dpi:.0f} x {h * dpi:.0f} px at {dpi} dpi)",
        f"Direction    {style.label} - {style.blurb}",
        f"             {style.guidance}",
        f"Palette      {spec.palette.label}  bg {spec.palette.bg}  ink {spec.palette.ink}  accent {spec.palette.accent}  panel {spec.palette.panel}",
        f"Type         {style.heading} / {style.body} / {style.script}; align {style.align}; margin {style.margin:g}; caps {style.caps}",
        "",
        "## The rulebook",
        rule_digest(),
        "",
        "## Photographs",
    ]
    stats = load_photo_stats(spec)
    for i, path in enumerate(spec.photo_paths):
        photo = stats[i] if i < len(stats) else None
        if photo is None:
            lines.append(f"  [{i}] {path.name}  (unreadable)")
            continue
        face = faces_mod.describe(photo.faces)
        lines.append(f"  [{i}] {path.name}  {photo.width}x{photo.height}  {photo.orientation}  "
                     f"interest {photo.interest:.2f}  {face}")
    det = faces_mod.status()
    if not det["opencv"]:
        lines.append("  faces: OpenCV is not installed, so crops are centred rather than face-aware")
    elif not det["model"]:
        lines.append("  faces: run ./ccb faces to install the YuNet model (Haar is the fallback)")
    lines += [
        "",
        "## Words",
    ]
    for role in config.TEXT_ROLES:
        lines.append(f"  {role:<10} {spec.text.get(role) or '(empty)'}")
    lines += [
        "",
        "## Directions you may borrow from",
    ]
    for key, st in config.STYLES.items():
        lines.append(f"  {key:<12} {st.label}: {st.guidance}")
    lines += [
        "",
        "## What to write",
        "Write 2-3 fronts and one back as compositions. Each slot is {photo, x, y, w, h}",
        "as fractions of the trim page; each zone is {roles, x, y, w, h} with optional",
        "align, valign, font, scale, caps, panel and text. Ornaments are 0-4 groups",
        "{kind, density}; rules are {x1, y1, x2, y2, token, weight}. Coordinates are",
        "from the top-left. Photographs never stretch: the engine crops around the",
        "faces unless a slot sets focus [x, y].",
        "",
        "Everything is checked by ./ccb layout; errors stop the save, warnings are",
        "notes. Then ./ccb check, ./ccb see, ./ccb render, ./ccb qa.",
        "",
        "## Shape of the file",
        json.dumps({
            "front": {"name": "your name", "side": "front", "slots": [], "zones": [],
                      "ornaments": [], "lines": []},
            "back": {"name": "back", "side": "back", "slots": [], "zones": [],
                     "ornaments": [], "lines": []},
        }, indent=2),
    ]
    return "\n".join(lines)
