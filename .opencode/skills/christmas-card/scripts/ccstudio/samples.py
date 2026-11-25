"""Demo photographs, drawn from scratch so the project ships without binaries.

They are flat illustrations, not stock photography - enough to try the studio
before anyone adds real photographs.
"""
from __future__ import annotations

import math
import random
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

from . import config

SCENES = [
    ("tree_lights.jpg", 1100, 1500, "tree"),
    ("couple_snow.jpg", 1500, 1050, "couple"),
    ("cabin.jpg", 1500, 1050, "cabin"),
    ("gifts.jpg", 1100, 1500, "gifts"),
    ("snowman.jpg", 1400, 1000, "snowman"),
    ("table.jpg", 1200, 1200, "table"),
]


def _gradient(w: int, h: int, top: tuple[int, int, int], bottom: tuple[int, int, int]) -> Image.Image:
    ramp = np.linspace(0, 1, h, dtype=np.float32)[:, None]
    arr = np.zeros((h, w, 3), dtype=np.float32)
    for i in range(3):
        arr[:, :, i] = top[i] + (bottom[i] - top[i]) * ramp
    return Image.fromarray(arr.astype(np.uint8), "RGB")


def _snow(draw: ImageDraw.ImageDraw, w: int, h: int, count: int, rng: random.Random,
          colour: str = "#FFFFFF", alpha_max: int = 230) -> None:
    for _ in range(count):
        r = rng.uniform(0.002, 0.008) * min(w, h)
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        shade = rng.randint(200, alpha_max)
        draw.ellipse((x - r, y - r, x + r, y + r), fill=colour if shade > 215 else "#E7EEF4")


def _pines(draw: ImageDraw.ImageDraw, w: int, h: int, base_y: float, rng: random.Random) -> None:
    for i in range(7):
        x = (i + 0.5) * w / 7 + rng.uniform(-20, 20)
        size = rng.uniform(0.09, 0.16) * h
        colour = "#22402F" if i % 2 else "#1A3326"
        for layer in range(4):
            top = base_y - size + layer * size * 0.22
            half = size * (0.20 + layer * 0.10)
            draw.polygon([(x, top), (x - half, top + size * 0.42), (x + half, top + size * 0.42)], fill=colour)
        draw.rectangle((x - size * 0.03, base_y, x + size * 0.03, base_y + size * 0.10), fill="#3A2A20")


def _tree(draw: ImageDraw.ImageDraw, w: int, h: int, cx: float, base_y: float, size: float,
          rng: random.Random, lights: int = 60) -> None:
    draw.rectangle((cx - size * 0.04, base_y, cx + size * 0.04, base_y + size * 0.09), fill="#3A2A20")
    for layer in range(5):
        top = base_y - size + layer * size * 0.17
        half = size * (0.18 + layer * 0.075)
        draw.polygon([(cx, top), (cx - half, top + size * 0.34), (cx + half, top + size * 0.34)], fill="#1E4030")
    for _ in range(lights):
        layer = rng.randint(0, 4)
        top = base_y - size + layer * size * 0.17 + size * 0.10
        half = size * (0.18 + layer * 0.075) * 0.8
        x = cx + rng.uniform(-half, half)
        y = top + rng.uniform(0, size * 0.18)
        r = size * 0.013
        colour = rng.choice(["#F6C453", "#E4572E", "#F2E9C9", "#7FB7A6"])
        draw.ellipse((x - r, y - r, x + r, y + r), fill=colour)
    star = size * 0.055
    draw.polygon([(cx, base_y - size - star), (cx + star * 0.35, base_y - size - star * 0.2),
                  (cx + star, base_y - size), (cx + star * 0.3, base_y - size + star * 0.2),
                  (cx, base_y - size + star), (cx - star * 0.3, base_y - size + star * 0.2),
                  (cx - star, base_y - size), (cx - star * 0.35, base_y - size - star * 0.2)], fill="#F6C453")


def _figure(draw: ImageDraw.ImageDraw, x: float, y: float, h: float, coat: str, hat: str) -> None:
    head = h * 0.13
    draw.ellipse((x - head, y - h * 0.98, x + head, y - h * 0.98 + head * 2), fill="#E8C4A8")
    draw.pieslice((x - head * 1.1, y - h * 0.99, x + head * 1.1, y - h * 0.84), 180, 360, fill=hat)
    body_w = h * 0.20
    draw.rounded_rectangle((x - body_w, y - h * 0.74, x + body_w, y - h * 0.12), radius=h * 0.05, fill=coat)
    draw.rectangle((x - body_w * 0.7, y - h * 0.16, x - body_w * 0.1, y), fill="#2B3646")
    draw.rectangle((x + body_w * 0.1, y - h * 0.16, x + body_w * 0.7, y), fill="#2B3646")


def _scene(kind: str, w: int, h: int, rng: random.Random) -> Image.Image:
    if kind == "tree":
        img = _gradient(w, h, (18, 42, 44), (8, 18, 22))
        draw = ImageDraw.Draw(img)
        for _ in range(90):
            x, y, r = rng.uniform(0, w), rng.uniform(0, h * 0.7), rng.uniform(0.001, 0.0035) * w
            draw.ellipse((x - r, y - r, x + r, y + r), fill="#F3E8C8")
        draw.rectangle((0, h * 0.84, w, h), fill="#101F22")
        _tree(draw, w, h, w * 0.5, h * 0.86, h * 0.62, rng, lights=90)
        for i, x in enumerate((w * 0.2, w * 0.47, w * 0.76)):
            _figure(draw, x, h * 0.95, h * (0.30 - i * 0.02), "#7A2230" if i == 1 else "#2E4A63", "#E7D8B8")
        return img
    if kind == "couple":
        img = _gradient(w, h, (196, 212, 224), (238, 240, 238))
        draw = ImageDraw.Draw(img)
        draw.ellipse((-w * 0.3, h * 0.55, w * 1.3, h * 1.9), fill="#F3F5F4")
        _pines(draw, w, h, h * 0.62, rng)
        _figure(draw, w * 0.40, h * 0.80, h * 0.52, "#8C2B33", "#22303E")
        _figure(draw, w * 0.53, h * 0.82, h * 0.55, "#2E4A63", "#7A2230")
        _snow(draw, w, h, 260, rng)
        return img
    if kind == "cabin":
        img = _gradient(w, h, (34, 54, 78), (206, 170, 130))
        draw = ImageDraw.Draw(img)
        draw.ellipse((w * 0.1, h * 0.1, w * 0.2, h * 0.22), fill="#F2E6CC")
        for _ in range(80):
            x, y = rng.uniform(0, w), rng.uniform(0, h * 0.55)
            r = rng.uniform(0.0008, 0.002) * w
            draw.ellipse((x - r, y - r, x + r, y + r), fill="#F7F1E3")
        draw.polygon([(0, h * 0.72), (w * 0.3, h * 0.60), (w * 0.65, h * 0.72), (w, h * 0.64), (w, h), (0, h)],
                     fill="#E8EDF0")
        _pines(draw, w, h, h * 0.74, rng)
        cx, cy, bw, bh = w * 0.56, h * 0.66, w * 0.22, h * 0.18
        draw.rectangle((cx, cy, cx + bw, cy + bh), fill="#5A3B2B")
        draw.polygon([(cx - bw * 0.08, cy), (cx + bw * 0.5, cy - bh * 0.55), (cx + bw * 1.08, cy)], fill="#39251C")
        for wx in (0.2, 0.55):
            draw.rectangle((cx + bw * wx, cy + bh * 0.35, cx + bw * (wx + 0.2), cy + bh * 0.75), fill="#F6C453")
        draw.rectangle((cx + bw * 0.42, cy + bh * 0.55, cx + bw * 0.58, cy + bh), fill="#2C1C15")
        return img
    if kind == "gifts":
        img = _gradient(w, h, (58, 74, 62), (26, 34, 30))
        draw = ImageDraw.Draw(img)
        draw.rectangle((0, h * 0.78, w, h), fill="#20261F")
        for i, (x, size, colour) in enumerate(((0.30, 0.30, "#A62B33"), (0.55, 0.24, "#E8DCC0"), (0.72, 0.18, "#3C6E63"))):
            bx = w * x
            bw = w * size
            bh = h * size * 0.9
            by = h * 0.80 - bh
            draw.rectangle((bx, by, bx + bw, by + bh), fill=colour)
            draw.rectangle((bx + bw * 0.42, by, bx + bw * 0.58, by + bh), fill="#C9A227")
            draw.rectangle((bx, by + bh * 0.40, bx + bw, by + bh * 0.52), fill="#C9A227")
            draw.ellipse((bx + bw * 0.42, by + bh * 0.52, bx + bw * 0.58, by + bh * 0.72), fill="#C9A227")
        _tree(draw, w, h, w * 0.16, h * 0.80, h * 0.55, rng, lights=50)
        return img
    if kind == "snowman":
        img = _gradient(w, h, (204, 220, 231), (240, 241, 236))
        draw = ImageDraw.Draw(img)
        draw.ellipse((-w * 0.2, h * 0.62, w * 1.2, h * 1.8), fill="#FBFBF8")
        cx, base = w * 0.52, h * 0.82
        for scale, cy in ((0.26, 0.30), (0.19, 0.52), (0.14, 0.68)):
            r = h * scale / 2
            draw.ellipse((cx - r, h * cy - r, cx + r, h * cy + r), fill="#FFFFFF", outline="#DCE3E6", width=3)
        draw.ellipse((cx - h * 0.03, h * 0.235, cx - h * 0.015, h * 0.25), fill="#2B2B2B")
        draw.ellipse((cx + h * 0.015, h * 0.235, cx + h * 0.03, h * 0.25), fill="#2B2B2B")
        draw.polygon([(cx, h * 0.26), (cx + h * 0.06, h * 0.275), (cx, h * 0.29)], fill="#E4572E")
        draw.rectangle((cx - h * 0.10, h * 0.185, cx + h * 0.10, h * 0.20), fill="#2B2B2B")
        draw.rectangle((cx - h * 0.055, h * 0.12, cx + h * 0.055, h * 0.19), fill="#2B2B2B")
        draw.rectangle((cx - h * 0.09, h * 0.145, cx + h * 0.09, h * 0.165), fill="#2B2B2B")
        draw.rectangle((cx - h * 0.10, h * 0.335, cx + h * 0.10, h * 0.365), fill="#A62B33")
        draw.polygon([(cx + h * 0.10, h * 0.36), (cx + h * 0.16, h * 0.42), (cx + h * 0.11, h * 0.40)], fill="#A62B33")
        draw.line((cx - h * 0.13, h * 0.47, cx - h * 0.33, h * 0.40), fill="#5A3B2B", width=6)
        draw.line((cx + h * 0.13, h * 0.47, cx + h * 0.33, h * 0.40), fill="#5A3B2B", width=6)
        _snow(draw, w, h, 150, rng)
        return img
    # table
    img = _gradient(w, h, (86, 62, 48), (48, 34, 27))
    draw = ImageDraw.Draw(img)
    draw.rectangle((0, h * 0.42, w, h), fill="#EFE9DA")
    draw.rectangle((0, h * 0.42, w, h * 0.455), fill="#D9CFB8")
    for i, x in enumerate((0.22, 0.5, 0.78)):
        cx = w * x
        draw.ellipse((cx - w * 0.12, h * 0.52, cx + w * 0.12, h * 0.72), fill="#FBF9F2", outline="#CDBF9F", width=4)
        draw.ellipse((cx - w * 0.075, h * 0.555, cx + w * 0.075, h * 0.685), fill="#E7DFC9")
        draw.ellipse((cx - w * 0.012, h * 0.57, cx + w * 0.012, h * 0.60), fill="#C0392B")
    for x in (0.1, 0.9):
        cx = w * x
        draw.rectangle((cx - w * 0.012, h * 0.20, cx + w * 0.012, h * 0.50), fill="#F2E3C0")
        draw.ellipse((cx - w * 0.03, h * 0.47, cx + w * 0.03, h * 0.56), fill="#EBCB7E")
        draw.ellipse((cx - w * 0.008, h * 0.145, cx + w * 0.008, h * 0.165), fill="#F6C453")
    for i in range(9):
        x = w * (0.30 + i * 0.05)
        draw.ellipse((x - w * 0.02, h * 0.48, x + w * 0.02, h * 0.515), fill="#2E4A3A")
    return img


def write_demo_photos(folder: Path | None = None) -> list[Path]:
    folder = Path(folder or (config.ROOT / "inputs")).resolve()
    folder.mkdir(parents=True, exist_ok=True)
    written = []
    for i, (name, w, h, kind) in enumerate(SCENES):
        rng = random.Random(1000 + i)
        img = _scene(kind, w, h, rng)
        img = img.filter(ImageFilter.GaussianBlur(0.4))
        target = folder / name
        img.save(target, format="JPEG", quality=92, subsampling=0)
        written.append(target)
    return written
