"""Shared pytest fixtures for the catalog tests.

The tests build throwaway screen directories in a tmp path and point the tools at them, so they
never depend on the repo's own screens/ layout. They need the plugin code on sys.path; the brief's
run command sets INKTERFACE_CORE, and catalog_lib picks it up.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import catalog_lib as C  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def _core_on_path():
    C.ensure_core_on_path()


def _png_1bit(size=(648, 480)):
    from PIL import Image

    img = Image.new("1", size, 1)
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


GOOD_SAMPLE = {
    "system.cpu.load": 40,
    "system.cpu.load.history": [10, 20, 30, 40],
}


def make_declarative(path: Path, sid="demo", version="1.0.0", author="inkterface contributors"):
    """A minimal valid declarative screen folder with a matching preview."""
    d = path / sid
    d.mkdir(parents=True)
    doc = {
        "schema": 1, "id": sid, "name": "Demo", "version": version, "author": author,
        "description": "A demo screen.",
        "active": {"refresh_s": 1, "widgets": [
            {"type": "number", "x": 8, "y": 8, "w": 200, "h": 56, "bind": "system.cpu.load", "unit": "%"},
        ]},
    }
    (d / "screen.json").write_text(json.dumps(doc), "utf-8")
    (d / "sample-data.json").write_text(json.dumps(GOOD_SAMPLE), "utf-8")
    (d / "README.md").write_text("# Demo\n\nContributed under the MIT License.\n", "utf-8")
    render_preview_into(d)
    return d


def make_code(path: Path, sid="codedemo", version="1.0.0"):
    """A minimal valid code screen folder with a matching preview and the required README section."""
    d = path / sid
    d.mkdir(parents=True)
    doc = {
        "schema": 1, "id": sid, "name": "Code Demo", "version": version, "author": "inkterface contributors",
        "description": "A code demo.",
        "active": {"refresh_s": 5, "code": "screen.py", "widgets": []},
    }
    (d / "screen.json").write_text(json.dumps(doc), "utf-8")
    (d / "screen.py").write_text(
        "import io\n"
        "from PIL import Image, ImageDraw\n"
        "def render(canvas_size, data, settings):\n"
        "    img = Image.new('1', canvas_size, 1)\n"
        "    d = ImageDraw.Draw(img)\n"
        "    d.rectangle((0, 0, canvas_size[0]-1, canvas_size[1]-1), outline=0, width=4)\n"
        "    buf = io.BytesIO(); img.save(buf, 'PNG'); return buf.getvalue()\n",
        "utf-8",
    )
    (d / "sample-data.json").write_text(json.dumps({}), "utf-8")
    (d / "README.md").write_text(
        "# Code Demo\n\n## What the code does\n\nDraws a box.\n\nContributed under the MIT License.\n", "utf-8")
    render_preview_into(d)
    return d


def render_preview_into(screen_dir: Path):
    img = C.render_preview_image(screen_dir)
    (screen_dir / "preview.png").write_bytes(C.image_to_preview_bytes(img))


@pytest.fixture
def declarative(tmp_path):
    return make_declarative(tmp_path)


@pytest.fixture
def code_screen(tmp_path):
    return make_code(tmp_path)
