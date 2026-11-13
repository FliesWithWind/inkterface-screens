#!/usr/bin/env python3
"""Draw the original artwork of the haunted-telemetry screen (bats, cobwebs, jack-o'-lantern).

    python tools/make_haunted_art.py            # rewrites screens/haunted-telemetry/assets/*.png

Everything is drawn here with Pillow primitives at 4x and scaled down, then cut to pure black/white so
the screen's `image` widgets use `dither: threshold` and the panel shows crisp shapes. The shapes are
the contributor's own work, released under the repo's MIT licence like the rest of the screen.
"""
from __future__ import annotations

import math
from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "screens" / "haunted-telemetry" / "assets"
S = 4  # supersampling factor


def _canvas(w: int, h: int):
    img = Image.new("L", (w * S, h * S), 255)
    return img, ImageDraw.Draw(img)


def _save(img: Image.Image, w: int, h: int, name: str) -> None:
    small = img.resize((w, h), Image.LANCZOS).point(lambda v: 0 if v < 140 else 255)
    OUT.mkdir(parents=True, exist_ok=True)
    small.save(OUT / name, "PNG", optimize=True)


def _pts(points, dx=0, dy=0):
    return [((x + dx) * S, (y + dy) * S) for x, y in points]


def web(corner: str, size: int = 108) -> None:
    """A cobweb hanging in one corner: radial threads plus sagging arcs between them."""
    img, d = _canvas(size, size)
    n = 6
    radii = [20, 38, 56, 74, 92]
    angles = [math.radians(90 * i / (n - 1)) for i in range(n)]
    far = size - 2
    for a in angles:  # radial threads from the corner (0, 0)
        d.line([(0, 0), (far * math.cos(a) * S, far * math.sin(a) * S)], fill=0, width=S)
    for r in radii:  # each arc is a quadratic curve pulled toward the corner
        for a0, a1 in zip(angles, angles[1:]):
            p0 = (r * math.cos(a0), r * math.sin(a0))
            p1 = (r * math.cos(a1), r * math.sin(a1))
            mid = ((p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2)
            c = (mid[0] * 0.78, mid[1] * 0.78)
            curve = []
            for i in range(13):
                t = i / 12
                x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * c[0] + t ** 2 * p1[0]
                y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * c[1] + t ** 2 * p1[1]
                curve.append((x * S, y * S))
            d.line(curve, fill=0, width=S)
    if corner in ("tr", "br"):
        img = img.transpose(Image.FLIP_LEFT_RIGHT)
    if corner in ("bl", "br"):
        img = img.transpose(Image.FLIP_TOP_BOTTOM)
    _save(img, size, size, f"web-{corner}.png")


def bat(name: str, w: int, h: int, wings_up: bool) -> None:
    """A bat seen from the front: ears, round body, two scalloped wings."""
    img, d = _canvas(w, h)
    cx = w / 2
    cy = h * 0.55
    tip_y = h * 0.12 if wings_up else h * 0.62
    for sign in (-1, 1):
        sx = lambda dx: cx + sign * dx * w / 2  # noqa: E731 - dx in 0..1 of the half width
        wing = [
            (sx(0.18), cy - h * 0.10),
            (sx(0.55), tip_y + h * 0.05),
            (sx(1.0), tip_y),
            (sx(0.88), tip_y + h * 0.30),
            (sx(0.72), tip_y + h * 0.20),
            (sx(0.62), tip_y + h * 0.44),
            (sx(0.42), tip_y + h * 0.32),
            (sx(0.30), cy + h * 0.28),
            (sx(0.14), cy + h * 0.14),
        ]
        d.polygon(_pts(wing), fill=0)
        ear = [(cx + sign * w * 0.045, h * 0.30), (cx + sign * w * 0.11, h * 0.06), (cx + sign * w * 0.12, h * 0.34)]
        d.polygon(_pts(ear), fill=0)
    d.ellipse([(cx - w * 0.10) * S, (cy - h * 0.34) * S, (cx + w * 0.10) * S, (cy + h * 0.02) * S], fill=0)  # head
    d.ellipse([(cx - w * 0.12) * S, (cy - h * 0.10) * S, (cx + w * 0.12) * S, (cy + h * 0.42) * S], fill=0)  # body
    for sign in (-1, 1):  # white eyes
        ex = cx + sign * w * 0.045
        ey = cy - h * 0.20
        r = max(1.2, w * 0.018)
        d.ellipse([(ex - r) * S, (ey - r) * S, (ex + r) * S, (ey + r) * S], fill=255)
    _save(img, w, h, name)


def pumpkin(w: int = 152, h: int = 150) -> None:
    """A jack-o'-lantern: rib marks, a curled stem and a carved face."""
    img, d = _canvas(w, h)
    cx = w / 2
    top, bot = 20, h - 3
    lw = 3 * S
    d.ellipse([3 * S, top * S, (w - 3) * S, bot * S], fill=255, outline=0, width=lw)
    for off in (-36, 36):  # ribs: only their top and bottom arcs, clear of the face
        box = [(cx + off - 24) * S, (top + 9) * S, (cx + off + 24) * S, (bot - 9) * S]
        d.arc(box, 235, 305, fill=0, width=2 * S)
        d.arc(box, 55, 125, fill=0, width=2 * S)
    # stem
    d.polygon(_pts([(cx - 9, top + 6), (cx - 5, 8), (cx + 3, 2), (cx + 12, 6), (cx + 6, 12), (cx + 8, top + 6)]), fill=0)
    # curled vine
    d.arc([(cx + 8) * S, 2 * S, (cx + 30) * S, 22 * S], 200, 90, fill=0, width=2 * S)
    # eyes: two triangles; nose: small triangle
    d.polygon(_pts([(cx - 36, 64), (cx - 12, 64), (cx - 24, 42)]), fill=0)
    d.polygon(_pts([(cx + 12, 64), (cx + 36, 64), (cx + 24, 42)]), fill=0)
    d.polygon(_pts([(cx - 7, 84), (cx + 7, 84), (cx, 70)]), fill=0)
    # mouth: wide grin with three teeth left as white gaps
    mouth = [(cx - 40, 94), (cx - 28, 102), (cx - 18, 96), (cx - 9, 105), (cx, 98), (cx + 9, 105),
             (cx + 18, 96), (cx + 28, 102), (cx + 40, 94), (cx + 30, 120), (cx + 14, 126), (cx, 124),
             (cx - 14, 126), (cx - 30, 120)]
    d.polygon(_pts(mouth), fill=0)
    for tx in (-20, 0, 20):  # teeth
        d.polygon(_pts([(cx + tx - 6, 112), (cx + tx + 6, 112), (cx + tx, 124)]), fill=255)
    _save(img, w, h, "pumpkin.png")


def main() -> int:
    for corner in ("tl", "tr"):
        web(corner)
    for corner in ("bl", "br"):
        web(corner, 88)
    bat("bat-up.png", 80, 48, True)
    bat("bat-down.png", 80, 48, False)
    bat("bat-small.png", 48, 30, True)
    pumpkin()
    for p in sorted(OUT.glob("*.png")):
        print(f"wrote {p.relative_to(OUT.parents[2])} ({p.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
