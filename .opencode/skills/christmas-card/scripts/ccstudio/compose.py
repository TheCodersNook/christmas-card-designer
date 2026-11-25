"""Compositions: the brief, the rule checks and the installer.

There is no template here. The agent writes a page (a background, colour fields,
photograph slots, text zones, rules) and this module answers three questions:
what does the rulebook allow, what is wrong with this composition, and what
should the agent know before writing one.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import config, faces as faces_mod, layouts, photos as photo_mod
from .layouts import Design, Slot, Zone, overlaps
from .spec import CardSpec, SpecError

PALETTE_TOKENS = ("bg", "ink", "soft", "accent", "panel", "on_panel")


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


# --------------------------------------------------------------------- helpers
def _colour_ok(value: Any) -> bool:
    text = str(value or "").strip()
    if not text:
        return False
    if text.startswith("#"):
        return len(text) in (4, 7)
    return text in PALETTE_TOKENS


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


def _shape_rect(where: str, item: dict[str, Any], issues: list[Issue]) -> None:
    """Shapes may bleed off the page (a disc cut by the trim) but not wander."""
    try:
        x, y, w, h = float(item["x"]), float(item["y"]), float(item["w"]), float(item["h"])
    except (KeyError, TypeError, ValueError):
        issues.append(Issue("error", "rect.missing", "needs x, y, w and h as fractions of the page", where))
        return
    if w < 0 or h < 0:
        issues.append(Issue("error", "rect.size", "width and height cannot be negative", where))
    if not (-0.6 <= x <= 1.6) or not (-0.6 <= y <= 1.6):
        issues.append(Issue("error", "rect.bounds", f"a shape at {x:.2f}, {y:.2f} is nowhere near the page", where))
    if x + w > 1.6 or y + h > 1.6:
        issues.append(Issue("error", "rect.bounds", "the shape is nowhere near the page", where))


def _number(item: dict[str, Any], key: str, default: float) -> float:
    try:
        return float(item.get(key, default))
    except (TypeError, ValueError):
        return float(default)


def _layer_ok(layer: int) -> bool:
    lo = int(config.COMPOSE.get("layers", {}).get("min", -5))
    hi = int(config.COMPOSE.get("layers", {}).get("max", 5))
    return lo <= layer <= hi


# ---------------------------------------------------------------------- limits
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
    shape_rules = config.COMPOSE.get("shapes", {})
    treatments = [str(v) for v in slot_rules.get("treatments", [])]
    alignments = [str(v) for v in zone_rules.get("alignments", [])]
    valigns = [str(v) for v in zone_rules.get("valigns", [])]
    clips = [str(v) for v in slot_rules.get("clips", ["rect", "rounded", "arch", "circle", "oval"])]
    shape_kinds = [str(v) for v in shape_rules.get("kinds", [])]

    if len(slots) > int(slot_rules.get("max", 12)):
        issues.append(Issue("error", "slots.count", f"{len(slots)} photographs; the maximum is {slot_rules.get('max')}", name))
    if len(zones) > int(zone_rules.get("max", 10)):
        issues.append(Issue("error", "zones.count", f"{len(zones)} text zones; the maximum is {zone_rules.get('max')}", name))

    # ------------------------------------------------------------ background
    background = comp.get("background") or {}
    if background:
        if not isinstance(background, dict):
            issues.append(Issue("error", "background.shape", "background must be an object", name))
        else:
            photo = background.get("photo")
            fill = background.get("fill")
            gradient = background.get("gradient")
            if photo is None and not fill and not gradient:
                issues.append(Issue("warn", "background.empty",
                                    "a background needs 'photo', 'fill' or 'gradient'", name))
            if photo is not None:
                try:
                    index = int(photo)
                except (TypeError, ValueError):
                    index = -1
                if not (0 <= index < count):
                    issues.append(Issue("error", "background.photo",
                                        f"background photo {photo} does not exist (there are {count})", name))
                scrim = _number(background, "scrim", 0.0)
                if not (0.0 <= scrim <= 1.0):
                    issues.append(Issue("error", "background.scrim", "scrim must be 0..1", name))
                reach = _number(background, "scrim_reach", 0.65)
                if not (0.05 <= reach <= 1.0):
                    issues.append(Issue("error", "background.scrim", "scrim_reach must be 0.05..1", name))
                where = str(background.get("scrim_from") or "bottom").lower()
                if where not in ("bottom", "top", "left", "right", "full"):
                    issues.append(Issue("error", "background.scrim",
                                        "scrim_from must be bottom, top, left, right or full", name))
                if background.get("scrim_color") and not _colour_ok(background.get("scrim_color")):
                    issues.append(Issue("error", "background.colour",
                                        "scrim_color must be a palette token or #hex", name))
            if fill and not _colour_ok(fill):
                issues.append(Issue("error", "background.colour",
                                    "fill must be a palette token or #hex", name))
            if gradient:
                if not isinstance(gradient, (list, tuple)) or len(gradient) != 2:
                    issues.append(Issue("error", "background.gradient",
                                        "gradient must be [colour, colour]", name))
                elif not all(_colour_ok(v) for v in gradient):
                    issues.append(Issue("error", "background.gradient",
                                        "gradient colours must be palette tokens or #hex", name))

    # ---------------------------------------------------------------- shapes
    shapes = comp.get("shapes") or []
    if not isinstance(shapes, list):
        issues.append(Issue("error", "shapes.shape", "shapes must be a list", name))
        shapes = []
    if len(shapes) > int(shape_rules.get("max", 16)):
        issues.append(Issue("error", "shapes.count",
                            f"{len(shapes)} shapes; the maximum is {shape_rules.get('max')}", name))
    for i, shape in enumerate(shapes):
        where = f"{name} shape {i + 1}"
        if not isinstance(shape, dict):
            issues.append(Issue("error", "shapes.shape", "a shape is an object", where))
            continue
        kind = str(shape.get("kind", "rect")).lower()
        if shape_kinds and kind not in shape_kinds:
            issues.append(Issue("error", "shapes.kind", f"unknown shape '{kind}'; use {', '.join(shape_kinds)}", where))
        _shape_rect(where, shape, issues)
        if shape.get("fill") and not _colour_ok(shape.get("fill")):
            issues.append(Issue("error", "shapes.fill", "fill must be a palette token or #hex", where))
        opacity = _number(shape, "opacity", 1.0)
        if not (0.0 <= opacity <= 1.0):
            issues.append(Issue("error", "shapes.opacity", "opacity must be 0..1", where))
        rotate = _number(shape, "rotate", 0.0)
        if not (-180.0 <= rotate <= 180.0):
            issues.append(Issue("error", "shapes.rotate", "rotate must be -180..180", where))
        if not _layer_ok(int(_number(shape, "layer", 0))):
            issues.append(Issue("error", "shapes.layer", "layer is outside the allowed range", where))

    # ----------------------------------------------------------------- slots
    seen_photos: list[int] = []
    rects: list[tuple[str, str, int, tuple[float, float, float, float]]] = []
    for i, slot in enumerate(slots):
        where = f"{name} slot {i + 1}"
        if not isinstance(slot, dict):
            issues.append(Issue("error", "slot.shape", "a slot is an object", where))
            continue
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
        clip = str(slot.get("clip", "") or "").lower()
        if clip and clip not in clips:
            issues.append(Issue("error", "photo.clip", f"unknown clip '{clip}'; use {', '.join(clips)}", where))
        rotate = _number(slot, "rotate", 0.0)
        max_rotate = float(slot_rules.get("max_rotate", 12))
        if abs(rotate) > max_rotate:
            issues.append(Issue("error", "photo.rotate", f"a photograph may turn {max_rotate:g} degrees at most", where))
        layer = int(_number(slot, "layer", 0))
        if not _layer_ok(layer):
            issues.append(Issue("error", "photo.layer", "layer is outside the allowed range", where))
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
            rects.append(("slot", where, layer, rect))

    total_photo = sum(s.w * s.h for s in design({"slots": slots}).slots)
    lo = float(config.COMPOSE.get("photos", {}).get("min_coverage", 0.2))
    hi = float(config.COMPOSE.get("photos", {}).get("max_coverage", 0.84))
    # A text-only back is legitimate; coverage only applies once something is placed.
    if slots and not background.get("photo") and total_photo < lo:
        issues.append(Issue("warn", "photos.coverage", f"photographs cover only {total_photo * 100:.0f}% (aim for {lo * 100:.0f}-{hi * 100:.0f}%)", name))
    if total_photo > hi:
        issues.append(Issue("error", "photos.coverage", f"photographs cover {total_photo * 100:.0f}% (maximum {hi * 100:.0f}%)", name))

    # ----------------------------------------------------------------- zones
    over_photo_zones: list[tuple[str, tuple[float, float, float, float]]] = []
    for i, zone in enumerate(zones):
        where = f"{name} zone {i + 1}"
        if not isinstance(zone, dict):
            issues.append(Issue("error", "zone.shape", "a zone is an object", where))
            continue
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
        color = zone.get("color")
        if color and not _colour_ok(color):
            issues.append(Issue("error", "type.color", "color must be a palette token or #hex", where))
        panel = zone.get("panel")
        if isinstance(panel, str) and panel and not _colour_ok(panel):
            issues.append(Issue("error", "type.panel", "panel must be true or a palette token", where))
        opacity = _number(zone, "panel_opacity", 1.0)
        if not (0.0 <= opacity <= 1.0):
            issues.append(Issue("error", "type.panel", "panel_opacity must be 0..1", where))
        rotate = _number(zone, "rotate", 0.0)
        max_rotate = float(zone_rules.get("max_rotate", 90))
        if abs(rotate) > max_rotate:
            issues.append(Issue("error", "type.rotate", f"type may turn {max_rotate:g} degrees at most", where))
        layer = int(_number(zone, "layer", 0))
        if not _layer_ok(layer):
            issues.append(Issue("error", "type.layer", "layer is outside the allowed range", where))
        if rect:
            if rect[2] < float(zone_rules.get("min_width", 0.16)):
                issues.append(Issue("warn", "type.narrow", "a text zone this narrow will break words", where))
            if rect[2] * rect[3] < float(zone_rules.get("min_area", 0.006)):
                issues.append(Issue("warn", "type.small", "the text zone is very small for its copy", where))
            m = style.margin / 2
            if spec is not None and not zone.get("over_photo") and not panel and (
                    rect[0] < m or rect[1] < m or
                    rect[0] + rect[2] > 1 - m or rect[1] + rect[3] > 1 - m):
                issues.append(Issue("warn", "type.margin",
                                    f"text runs inside the page's safe area ({m:.3f}); the direction prefers {style.margin:.3f}", where))
            rects.append(("zone", where, layer, rect))
            if zone.get("over_photo"):
                over_photo_zones.append((where, rect))

    # ------------------------------------------------------------- overlaps
    for i in range(len(rects)):
        for j in range(i + 1, len(rects)):
            kind_a, wa, la, ra = rects[i]
            kind_b, wb, lb, rb = rects[j]
            area = overlaps(ra, rb)
            if area <= 1e-6:
                continue
            if kind_a == kind_b == "zone":
                issues.append(Issue("error", "overlap.same", f"{wa} overlaps {wb}", name))
            elif kind_a == kind_b == "slot":
                if la == lb:
                    issues.append(Issue("error", "overlap.same",
                                        f"{wa} overlaps {wb} on layer {la}; give one a different 'layer' to layer them", name))
            else:
                zone_where = wa if kind_a == "zone" else wb
                if not any(zone_where == w and overlaps(r, ra if kind_a == "zone" else rb) > 1e-6
                           for w, r in over_photo_zones):
                    issues.append(Issue("error", "overlap.text_photo",
                                        f"{wa} overlaps {wb}; set the zone's 'over_photo' if the text is meant to sit on the picture", name))

    has_background_photo = background.get("photo") is not None if isinstance(background, dict) else False
    for where, rect in over_photo_zones:
        on_slot = any(overlaps(rect, r) > 0.02 for kind, _w, _l, r in rects if kind == "slot")
        if not on_slot and not has_background_photo:
            issues.append(Issue("warn", "type.over_photo",
                                "over_photo is set but no photograph is underneath", where))

    known_roles = {str(r) for z in zones if isinstance(z, dict) for r in z.get("roles", [])}
    if spec is not None:
        for role in known_roles:
            if not str(spec.text.get(role, "")).strip() and not any(
                    isinstance(z, dict) and z.get("text") and role in z.get("roles", []) for z in zones):
                issues.append(Issue("warn", "words.empty", f"role '{role}' is placed but has no words", name))

    # ------------------------------------------------------ ornament & rules
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

    chrome = comp.get("chrome") or {}
    if isinstance(chrome, dict):
        border = str(chrome.get("border") or "none").lower()
        borders = [str(v) for v in config.COMPOSE.get("chrome", {}).get("borders", [])]
        if border not in borders:
            issues.append(Issue("error", "chrome.border", f"unknown border '{border}'; use {', '.join(borders)}", name))
        decoration = str(chrome.get("decoration") or "none").lower()
        if decoration not in ["none", *kinds]:
            issues.append(Issue("error", "chrome.decoration", f"unknown decoration '{decoration}'", name))

    # Face safety, only when we can actually see the photographs.
    if spec is not None and photo_stats is not None:
        for i, slot in enumerate(slots):
            if not isinstance(slot, dict):
                continue
            rect = _rect(f"{name} slot {i + 1}", slot, [])
            try:
                index = int(slot.get("photo"))
            except (TypeError, ValueError):
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


# ------------------------------------------------------------------ diversity
def geometry_signature(comp: dict[str, Any], step: float = 0.05) -> tuple:
    """A rough fingerprint of a page's skeleton, used to catch repeated layouts."""
    def q(v: Any) -> int:
        try:
            return int(round(float(v) / step))
        except (TypeError, ValueError):
            return -1
    marks = []
    for s in comp.get("slots", []) or []:
        if isinstance(s, dict):
            marks.append(("s", q(s.get("x")), q(s.get("y")), q(s.get("w")), q(s.get("h"))))
    for z in comp.get("zones", []) or []:
        if isinstance(z, dict):
            marks.append(("z", q(z.get("x")), q(z.get("y")), q(z.get("w")), q(z.get("h"))))
    return tuple(sorted(marks))


def _is_plain(comp: dict[str, Any]) -> bool:
    return not (comp.get("background") or comp.get("shapes") or comp.get("ornaments")
                or comp.get("lines") or (comp.get("chrome") or {}).get("border") not in (None, "", "none"))


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
    for comp in spec.compositions:
        bg = comp.get("background") or {}
        if isinstance(bg, dict) and str(bg.get("photo", "")).lstrip("-").isdigit():
            used.add(int(bg["photo"]))
    for i, photo in enumerate(stats):
        if i not in used:
            issues.append(Issue("warn", "photos.unused", f"photograph {i} ({photo.path.name}) is not placed", ""))
    if not "".join(spec.text.values()).strip():
        issues.append(Issue("error", "words.empty", "the card has no words at all"))
    if not str(spec.text.get("greeting", "")).strip():
        issues.append(Issue("warn", "words.greeting", "no greeting set"))

    fronts = spec.front_compositions
    seen: list[tuple[str, tuple]] = []
    for comp in fronts:
        label = str(comp.get("name") or "composition")
        sig = geometry_signature(comp)
        if any(sig == other for _label, other in seen):
            match = next(other_label for other_label, other in seen if other == sig)
            issues.append(Issue("warn", "composition.repeat",
                                f"'{label}' has the same skeleton as '{match}'; a second front should argue a different idea", label))
        seen.append((label, sig))
        if len(fronts) > 1 and _is_plain(comp):
            issues.append(Issue("warn", "composition.plain",
                                f"'{label}' is only photographs and a stack of text; a colour field, a full-bleed "
                                "photograph, a shape or a rule would make it this card rather than any card", label))
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
    shapes = comp.get("shapes", {})
    chrome = comp.get("chrome", {})
    return "\n".join([
        f"paper        {sizes}",
        f"bleed        {config.BLEED_IN} in, export dpi 96-{config.MAX_DPI}",
        f"margins      {comp.get('margin', {}).get('recommended_min', 0.045)}-{comp.get('margin', {}).get('recommended_max', 0.12)} (each direction has its own; advice, not a cage)",
        f"background   photo (with scrim 0-1), fill, or gradient [a, b]; the whole page, bleed included",
        f"shapes       {', '.join(shapes.get('kinds', []))} (max {shapes.get('max', 16)}); fill from the palette or #hex, opacity 0-1, rotate ±180",
        f"photographs  {comp.get('photos', {}).get('min_coverage', 0.2)}-{comp.get('photos', {}).get('max_coverage', 0.84)} of the page, max {comp.get('slots', {}).get('max', 12)} slots; clip {', '.join(comp.get('slots', {}).get('clips', []))}; rotate ±{comp.get('slots', {}).get('max_rotate', 12)}°; 'bleed' runs into the bleed",
        f"treatments   {', '.join(comp.get('slots', {}).get('treatments', []))}",
        f"text zones   max {comp.get('zones', {}).get('max', 10)}; align {', '.join(comp.get('zones', {}).get('alignments', []))}; valign {', '.join(comp.get('zones', {}).get('valigns', []))}; rotate ±{comp.get('zones', {}).get('max_rotate', 90)}°",
        f"over photos  a zone with 'over_photo': true may sit on a picture; the engine colours it for contrast",
        f"layers       {comp.get('layers', {}).get('min', -5)}..{comp.get('layers', {}).get('max', 5)} on slots, zones, shapes and rules; overlapping photographs need different layers",
        f"ornaments    {', '.join(comp.get('ornaments', {}).get('kinds', []))} (max {comp.get('ornaments', {}).get('max', 4)}); nothing is drawn unless you ask",
        f"chrome       border {', '.join(chrome.get('borders', []))}; texture true/false; also optional decoration + density",
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
        "The direction is a starting point, not a style sheet. The engine paints",
        "only what you declare: no frame, no decoration, no texture unless asked.",
        "Every page should be composed from scratch, and two fronts should not",
        "share a skeleton.",
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
        "## The vocabulary (one page)",
        "",
        "  background  {photo, scrim, scrim_from, scrim_reach, scrim_color} | {fill} | {gradient: [a, b], angle}",
        "  shapes      {kind, x, y, w, h, fill, opacity, rotate, layer, radius}",
        "  slots       {photo, x, y, w, h, treatment, focus, clip, rotate, layer, bleed}",
        "  zones       {roles, x, y, w, h, align, valign, font, scale, caps, text,",
        "               panel, panel_opacity, panel_pad, color, rotate, layer, over_photo}",
        "  lines       {x1, y1, x2, y2, token, weight, layer}",
        "  ornaments   {kind, density}",
        "  chrome      {border, decoration, density, texture}   (all off by default)",
        "",
        "A few moves that make a page specific rather than generic:",
        "",
        "  - a full-bleed photograph as the background, with a scrim and the type",
        "    sitting on the picture (zone 'over_photo': true);",
        "  - a colour field (shape 'band' or 'rect') that the photograph sits on or",
        "    breaks out of;",
        "  - an arch-, circle- or oval-clipped portrait against flat paper;",
        "  - two or three snapshots overlapping on different layers, tilted 2-4°;",
        "  - a rotated spine of type down one edge;",
        "  - a panel of colour behind a short line, or a single heavy rule.",
        "",
        "## What to write",
        "Write 2-3 fronts and one back. Each is one page you have composed: name it",
        "after the idea. Coordinates are fractions from the top-left; photographs",
        "never stretch (the engine crops around the faces unless a slot sets focus).",
        "",
        "Everything is checked by ./ccb layout; errors stop the save, warnings are",
        "notes. Then ./ccb check, ./ccb see, ./ccb render, ./ccb qa.",
        "",
        "## Shape of the file",
        json.dumps({
            "front": {
                "name": "your name", "side": "front",
                "background": {"photo": 0, "scrim": 0.45, "scrim_from": "bottom"},
                "shapes": [{"kind": "band", "x": 0, "y": 0.72, "w": 1, "h": 0.28,
                            "fill": "panel", "opacity": 0.9}],
                "slots": [], "zones": [], "ornaments": [], "lines": [],
            },
            "back": {"name": "back", "side": "back", "slots": [], "zones": [],
                     "ornaments": [], "lines": [], "chrome": {"border": "none"}},
        }, indent=2),
    ]
    return "\n".join(lines)
