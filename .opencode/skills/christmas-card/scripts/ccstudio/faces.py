"""Faces: detection, face-aware crop focus and crop safety.

The primary detector is YuNet (a small CNN that returns a box, five landmarks
and a score). If its model is missing the module falls back to OpenCV's Haar
cascade, and if OpenCV is not installed at all it degrades to "no faces" rather
than breaking a card. ``./ccb faces`` installs the model.

Nothing here invents faces: every box is a detection with a score. The gate uses
the boxes to keep faces inside a crop, and ``see`` draws them so the agent can
look at the same evidence a person would.
"""
from __future__ import annotations

import math
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

from . import config

MODEL_NAME = "face_detection_yunet_2023mar.onnx"
MODEL_URLS = (
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/"
    "models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
    "https://raw.githubusercontent.com/opencv/opencv_zoo/main/"
    "models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
)
SCORE = 0.62


class FaceUnavailable(RuntimeError):
    pass


@dataclass
class Face:
    x: float               # fraction of the photograph
    y: float
    w: float
    h: float
    score: float
    eyes: tuple[tuple[float, float], tuple[float, float]] | None = None
    source: str = "yunet"

    @property
    def cx(self) -> float:
        return self.x + self.w / 2

    @property
    def cy(self) -> float:
        return self.y + self.h / 2


_QUIET = False


def _cv2():
    global _QUIET
    try:
        import cv2  # type: ignore
    except Exception:
        return None
    if not _QUIET:
        # OpenCV 5's graph engine prints a warning per inference; silence it.
        try:
            cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
        except Exception:
            pass
        _QUIET = True
    return cv2


def available() -> bool:
    return _cv2() is not None


def model_path() -> Path:
    return config.MODEL_DIR / MODEL_NAME


def status() -> dict:
    cv2 = _cv2()
    return {
        "opencv": bool(cv2),
        "opencv_version": getattr(cv2, "__version__", "") if cv2 else "",
        "model": model_path().exists(),
        "model_path": str(model_path()),
        "detector": "YuNet" if (cv2 and model_path().exists()) else ("Haar" if cv2 else "none"),
    }


def ensure_model(force: bool = False, log=print) -> Path:
    path = model_path()
    if path.exists() and path.stat().st_size > 100_000 and not force:
        return path
    config.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    errors = []
    for url in MODEL_URLS:
        log(f"downloading {MODEL_NAME} ...")
        try:
            with urllib.request.urlopen(url, timeout=60) as response, tmp.open("wb") as out:
                out.write(response.read())
        except Exception as exc:
            errors.append(f"{url}: {exc}")
            continue
        if tmp.stat().st_size < 100_000:
            errors.append(f"{url}: got {tmp.stat().st_size} bytes (LFS pointer or error page)")
            tmp.unlink(missing_ok=True)
            continue
        tmp.replace(path)
        log(f"face model ready: {path}")
        return path
    tmp.unlink(missing_ok=True)
    raise FaceUnavailable("could not download the YuNet model: " + "; ".join(errors))


def detect(image: Image.Image, max_side: int = 1024) -> list[Face]:
    """Detect faces and return them as fractions of the image."""
    cv2 = _cv2()
    if cv2 is None:
        return []
    rgb = image.convert("RGB")
    scale = min(1.0, max_side / max(rgb.width, rgb.height))
    small = rgb.resize((max(1, int(rgb.width * scale)), max(1, int(rgb.height * scale))),
                       Image.LANCZOS) if scale < 1 else rgb
    import numpy as np
    bgr = np.asarray(small)[:, :, ::-1].copy()

    faces: list[Face] = []
    path = model_path()
    if path.exists():
        try:
            detector = cv2.FaceDetectorYN.create(str(path), "", (small.width, small.height),
                                                 SCORE, 0.3, 5000)
            detector.setInputSize((small.width, small.height))
            _, rows = detector.detect(bgr)
            if rows is not None:
                for row in rows:
                    x, y, w, h = (float(v) for v in row[:4])
                    score = float(row[-1])
                    pts = row[4:14]
                    eyes = ((float(pts[0]) / small.width, float(pts[1]) / small.height),
                            (float(pts[2]) / small.width, float(pts[3]) / small.height))
                    faces.append(_fraction(x, y, w, h, score, small.width, small.height, eyes, "yunet"))
        except Exception:
            faces = []
    if not faces:
        try:
            cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
            gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
            rows = cascade.detectMultiScale(gray, scaleFactor=1.08, minNeighbors=6,
                                            minSize=(max(24, small.width // 18),) * 2)
            for x, y, w, h in rows:
                faces.append(_fraction(float(x), float(y), float(w), float(h), 0.5,
                                       small.width, small.height, None, "haar"))
        except Exception:
            faces = []
    return sorted(faces, key=lambda f: (f.y, f.x))


def _fraction(x, y, w, h, score, width, height, eyes, source) -> Face:
    return Face(
        max(0.0, x / width), max(0.0, y / height),
        min(1.0, w / width), min(1.0, h / height),
        float(score), eyes, source,
    )


def focus(faces: list[Face], fallback: tuple[float, float] = (0.5, 0.42)) -> tuple[float, float]:
    """A crop focus that keeps the people in the frame."""
    if not faces:
        return fallback
    weight = sum(max(0.01, f.w * f.h) for f in faces) or 1.0
    cx = sum(f.cx * max(0.01, f.w * f.h) for f in faces) / weight
    cy = sum(f.cy * max(0.01, f.w * f.h) for f in faces) / weight
    return (min(0.85, max(0.15, cx)), min(0.78, max(0.18, cy)))


def crop_box(src_w: int, src_h: int, target_w: int, target_h: int,
             focus_x: float, focus_y: float) -> tuple[int, int, int, int]:
    """The same crop ``photos.cover`` takes, so the gate can map faces into a slot."""
    target = target_w / max(1, target_h)
    src = src_w / max(1, src_h)
    if src > target:
        new_w = max(1, int(round(src_h * target)))
        left = int(round((src_w - new_w) * max(0.0, min(1.0, focus_x))))
        return left, 0, new_w, src_h
    if src < target:
        new_h = max(1, int(round(src_w / target)))
        top = int(round((src_h - new_h) * max(0.0, min(1.0, focus_y))))
        return 0, top, src_w, new_h
    return 0, 0, src_w, src_h


def keep_ratio(face: Face, box: tuple[int, int, int, int], src_w: int, src_h: int) -> float:
    """How much of a face survives a crop box, 0..1 by area."""
    bx, by, bw, bh = box
    fx, fy, fw, fh = face.x * src_w, face.y * src_h, face.w * src_w, face.h * src_h
    dx = min(fx + fw, bx + bw) - max(fx, bx)
    dy = min(fy + fh, by + bh) - max(fy, by)
    if dx <= 0 or dy <= 0:
        return 0.0
    return max(0.0, min(1.0, (dx * dy) / max(1.0, fw * fh)))


def min_width_in(faces: list[Face], card_w_in: float, slot_w_fraction: float, crop_fraction: float) -> float:
    """Approximate printed width of the widest face in a slot, in inches."""
    if not faces:
        return 0.0
    widest = max(f.w for f in faces)
    return widest * card_w_in * slot_w_fraction * crop_fraction


def describe(faces: list[Face]) -> str:
    if not faces:
        return "no faces detected"
    return f"{len(faces)} face{'s' if len(faces) != 1 else ''}"


def angle(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
