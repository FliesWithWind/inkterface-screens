"""haunted-telemetry: golden renders for two data states, and the partial-refresh layout rules.

Update the goldens after an intended visual change with INKTERFACE_UPDATE_GOLDENS=1 and review the PNGs.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path

import pytest
from PIL import Image, ImageChops

import catalog_lib as C

SCREEN = C.SCREENS_DIR / "haunted-telemetry"
GOLDEN = Path(__file__).resolve().parent / "golden"

# game running, high load: the committed sample data
GAME = json.loads((SCREEN / "sample-data.json").read_text("utf-8"))
# machine idle: low load, no game
IDLE = {"time.now": "2026-10-30T09:05:00+01:00", "time.tz": "Europe/Berlin",
        "system.cpu.load": 4, "system.cpu.temp": 41, "system.gpu.load": 1, "system.gpu.temp": 38,
        "steam.now_playing": None}
STATES = {"game": GAME, "idle": IDLE}


def _render(data: dict) -> Image.Image:
    from inkterface_core.screens import load_screen
    from inkterface_core.screens.data import DataSnapshot
    from inkterface_core.screens.renderer import render

    return render(load_screen(SCREEN), DataSnapshot(data, SCREEN)).convert("1")


def _widgets() -> list[dict]:
    return json.loads((SCREEN / "screen.json").read_text("utf-8"))["active"]["widgets"]


def _is_dynamic(w: dict) -> bool:
    return "bind" in w or w["type"] == "clock" or bool(re.search(r"(?<!\{)\{[a-z]", w.get("text", "")))


def _box(w: dict):
    return (w["x"], w["y"], w["x"] + w["w"], w["y"] + w["h"])


def _overlap(a, b) -> bool:
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


@pytest.mark.parametrize("state", STATES)
def test_matches_golden(state):
    img = _render(STATES[state])
    assert img.size == (648, 480)
    path = GOLDEN / f"haunted-telemetry-{state}.png"
    if os.environ.get("INKTERFACE_UPDATE_GOLDENS"):
        img.save(path, "PNG", optimize=True)
    assert path.is_file(), f"missing golden {path.name}; run with INKTERFACE_UPDATE_GOLDENS=1"
    diff = sum(ImageChops.difference(img, Image.open(path).convert("1")).histogram()[1:])
    assert diff <= 480 * 648 * 0.002, f"{diff} pixels differ from {path.name}"


def test_states_actually_differ():
    assert sum(ImageChops.difference(_render(GAME), _render(IDLE)).histogram()[1:]) > 1000


def test_changes_stay_inside_the_dynamic_boxes():
    """Between the two states only the declared dynamic boxes may change pixels."""
    diff = ImageChops.difference(_render(GAME), _render(IDLE))
    boxes = [_box(w) for w in _widgets() if _is_dynamic(w)]
    assert boxes
    px = diff.load()
    stray = [(x, y) for y in range(480) for x in range(648)
             if px[x, y] and not any(b[0] <= x < b[2] and b[1] <= y < b[3] for b in boxes)]
    assert stray == [], f"{len(stray)} changed pixels outside dynamic boxes, first {stray[:3]}"


def test_dynamic_boxes_are_small_and_isolated():
    widgets = _widgets()
    dyn = [w for w in widgets if _is_dynamic(w)]
    for w in dyn:
        assert w["w"] * w["h"] <= 224 * 52, f"dynamic widget too large: {w}"
        assert not w.get("invert"), f"dynamic widget on a black fill: {w}"
    for i, w in enumerate(widgets):
        for v in widgets[i + 1:]:
            if _is_dynamic(w) or _is_dynamic(v):
                assert not _overlap(_box(w), _box(v)), f"overlap: {w} / {v}"


def test_screen_is_declarative_with_original_assets():
    doc = json.loads((SCREEN / "screen.json").read_text("utf-8"))
    assert "code" not in doc["active"] and not (SCREEN / "screen.py").exists()
    srcs = {w["src"] for w in doc["active"]["widgets"] if w["type"] == "image"}
    assert srcs and srcs == {p.name for p in (SCREEN / "assets").glob("*.png")}
