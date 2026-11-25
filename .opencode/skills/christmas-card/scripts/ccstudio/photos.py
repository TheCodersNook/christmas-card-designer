"""Reading photographs: EXIF rotation, colour, and a deterministic 'interest' score.

Nothing here writes to a photograph. The original files are opened read-only and
every crop happens on an in-memory copy.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter, ImageOps

from . import faces as faces_mod

SUPPORTED = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp", ".heic"}


class PhotoError(RuntimeError):
    pass


@dataclass
class Photo:
    path: Path
    image: Image.Image          # full-resolution RGB copy
    width: int
    height: int
    interest: float             # 0..1, detail + contrast
    brightness: float           # 0..1
    saturation: float           # 0..1
    faces: list = field(default_factory=list)   # faces_mod.Face, fractions of the image

    @property
    def aspect(self) -> float:
        return self.width / self.height if self.height else 1.0

    @property
    def megapixels(self) -> float:
        return self.width * self.height / 1_000_000

    @property
    def face_count(self) -> int:
        return len(self.faces)

    @property
    def face_focus(self) -> tuple[float, float]:
        """A crop focus that keeps the people in frame (or the usual upper centre)."""
        return faces_mod.focus(self.faces, (0.5, 0.42))

    @property
    def orientation(self) -> str:
        if self.aspect > 1.06:
            return "landscape"
        if self.aspect < 0.94:
            return "portrait"
        return "square"

    def thumb(self, box: int = 480) -> Image.Image:
        t = self.image.copy()
        t.thumbnail((box, box), Image.LANCZOS)
        return t


def load(path: str | Path) -> Photo:
    p = Path(path).expanduser()
    if not p.exists():
        raise PhotoError(f"photograph not found: {p}")
    if p.suffix.lower() not in SUPPORTED:
        raise PhotoError(f"unsupported photograph type: {p.suffix or 'no extension'}")
    try:
        with Image.open(p) as raw:
            img = ImageOps.exif_transpose(raw)
            img = img.convert("RGB")
    except (OSError, ValueError) as exc:
        raise PhotoError(f"cannot read {p.name}: {exc}") from exc
    interest, brightness, saturation = _analyse(img)
    key = (str(p.resolve()), p.stat().st_mtime_ns, p.stat().st_size)
    if key not in _FACE_CACHE:
        _FACE_CACHE[key] = faces_mod.detect(img)
    return Photo(p, img, img.width, img.height, interest, brightness, saturation, _FACE_CACHE[key])


_FACE_CACHE: dict[tuple, list] = {}


def _analyse(img: Image.Image) -> tuple[float, float, float]:
    """Cheap, deterministic statistics on a small copy (no model, no network)."""
    small = img.copy()
    small.thumbnail((420, 420), Image.BILINEAR)
    arr = np.asarray(small, dtype=np.float32) / 255.0
    lum = 0.2126 * arr[:, :, 0] + 0.7152 * arr[:, :, 1] + 0.0722 * arr[:, :, 2]
    brightness = float(lum.mean())
    mx, mn = arr.max(axis=2), arr.min(axis=2)
    saturation = float(np.mean(np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)))

    edges = np.asarray(small.convert("L").filter(ImageFilter.FIND_EDGES), dtype=np.float32) / 255.0
    detail = float(np.clip(edges.std() * 6.0, 0.0, 1.0))
    contrast = float(np.clip(lum.std() * 4.0, 0.0, 1.0))
    interest = float(np.clip(0.55 * detail + 0.30 * contrast + 0.15 * saturation, 0.0, 1.0))
    return interest, brightness, saturation


def cover(img: Image.Image, width: int, height: int, focus_x: float = 0.5, focus_y: float = 0.48) -> Image.Image:
    """Centre crop to the slot's aspect, then resize. Never stretches."""
    width, height = max(1, int(width)), max(1, int(height))
    target = width / height
    src = img.width / img.height
    if src > target:                       # too wide: crop the sides
        new_w = max(1, int(round(img.height * target)))
        left = int(round((img.width - new_w) * _clamp(focus_x)))
        box = (left, 0, left + new_w, img.height)
    elif src < target:                     # too tall: crop top and bottom
        new_h = max(1, int(round(img.width / target)))
        top = int(round((img.height - new_h) * _clamp(focus_y)))
        box = (0, top, img.width, top + new_h)
    else:
        box = (0, 0, img.width, img.height)
    crop = img.crop(box)
    if crop.size != (width, height):
        crop = crop.resize((width, height), Image.LANCZOS)
    return crop


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


def rounded(img: Image.Image, radius_px: float) -> Image.Image:
    """Rounded corners with real transparency, drawn once."""
    r = max(0, int(round(radius_px)))
    if r <= 1:
        return img
    mask = Image.new("L", img.size, 0)
    from PIL import ImageDraw
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, img.width - 1, img.height - 1), radius=r, fill=255)
    out = img.convert("RGBA")
    out.putalpha(mask)
    return out


def frame(img: Image.Image, color: str, width_px: int) -> Image.Image:
    """A printed keyline around a photograph, inside its slot."""
    from PIL import ImageDraw
    out = img.copy()
    if width_px > 0:
        ImageDraw.Draw(out).rectangle(
            (0, 0, out.width - 1, out.height - 1), outline=color, width=max(1, width_px)
        )
    return out


def shadowed(img: Image.Image, spread: int = 10, opacity: int = 60) -> Image.Image:
    """A soft printed shadow, sized to keep the photograph in place."""
    from PIL import ImageDraw
    spread = max(2, int(spread))
    canvas = Image.new("RGBA", (img.width + spread * 2, img.height + spread * 2), (0, 0, 0, 0))
    shadow = Image.new("RGBA", canvas.size, (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rectangle((spread, spread + spread // 2, spread + img.width, spread + img.height),
                                     fill=(0, 0, 0, opacity))
    shadow = shadow.filter(ImageFilter.GaussianBlur(spread / 1.6))
    canvas = Image.alpha_composite(canvas, shadow)
    canvas.paste(img.convert("RGBA"), (spread, spread))
    return canvas


def tilt(img: Image.Image, degrees: float) -> Image.Image:
    """A postcard-style tilt with an expanded canvas so nothing is clipped."""
    return img.convert("RGBA").rotate(degrees, expand=True, resample=Image.BICUBIC)
