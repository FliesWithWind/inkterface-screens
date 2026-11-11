#!/usr/bin/env python3
"""Scaffold a new screen directory under screens/ from a template.

    python tools/new_screen.py my-screen                 # declarative starter
    python tools/new_screen.py my-code-screen --code     # code (screen.py) starter

Creates screens/<id>/ with a minimal screen.json, sample-data.json and README.md (and screen.py
for a code screen). Render and validate it next:

    python tools/render_preview.py <id>
    python tools/validate.py <id>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog_lib as C  # noqa: E402

ID_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")

DECL_JSON = {
    "schema": 1,
    "id": "",
    "name": "",
    "version": "1.0.0",
    "author": "inkterface contributors",
    "active": {
        "refresh_s": 1,
        "widgets": [
            {"type": "text", "x": 0, "y": 0, "w": 648, "h": 30,
             "text": " {settings.title}", "font": "bold-20", "valign": "middle", "invert": True},
            {"type": "number", "x": 8, "y": 44, "w": 200, "h": 64,
             "bind": "system.cpu.load", "unit": "%", "font": "bold-40"},
        ],
    },
    "settings": [
        {"key": "title", "type": "string", "label": "Title", "default": "MY SCREEN"},
    ],
}

CODE_JSON = {
    "schema": 1,
    "id": "",
    "name": "",
    "version": "1.0.0",
    "author": "inkterface contributors",
    "active": {"refresh_s": 5, "code": "screen.py", "widgets": []},
    "settings": [
        {"key": "title", "type": "string", "label": "Title", "default": "My Screen"},
    ],
}

CODE_PY = '''"""Code-tier screen. Runs in the plugin's guarded child process: standard library + Pillow only,
finish well under 2 seconds, return a 648x480 1-bit PNG.

render(canvas_size, data, settings) -> PNG bytes (or a PIL image), exactly canvas_size, 1-bit.
`data` is the host snapshot as a plain dict; `settings` are the resolved screen settings.
"""
import io

from PIL import Image, ImageDraw, ImageFont


def render(canvas_size, data, settings):
    img = Image.new("1", canvas_size, 1)  # 1 = white
    d = ImageDraw.Draw(img)
    d.rectangle((0, 0, canvas_size[0] - 1, canvas_size[1] - 1), outline=0, width=4)
    font = ImageFont.load_default(size=40)
    d.text((32, 32), str(settings["title"]), font=font, fill=0)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()
'''

SAMPLE = {"system.cpu.load": 37, "system.cpu.load.history": [12, 20, 35, 60, 44, 37]}

README = """# {name}

<!-- What the screen shows, in a sentence or two. -->

## Settings

- `title` -- {title_hint}

## Data it needs

<!-- List the data sources this screen binds to. -->
{code_section}
This screen is contributed under the MIT License.
"""

CODE_SECTION = """
## What the code does

<!-- Plain-words description of what screen.py draws and how. The owner reads every line. -->
"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Scaffold a new screen.")
    ap.add_argument("id", help="screen id (lowercase a-z, 0-9, '-')")
    ap.add_argument("--code", action="store_true", help="scaffold a code-tier screen (screen.py)")
    ap.add_argument("--name", help="display name (default: derived from the id)")
    args = ap.parse_args(argv)

    sid = args.id
    if not ID_RE.fullmatch(sid):
        print(f"invalid id {sid!r}: use lowercase a-z, 0-9 and single '-'", file=sys.stderr)
        return 1
    name = args.name or sid.replace("-", " ").title()

    dest = C.screen_dir_for(sid)
    if dest.exists():
        print(f"screens/{sid} already exists", file=sys.stderr)
        return 1
    dest.mkdir(parents=True)

    doc = dict(CODE_JSON if args.code else DECL_JSON)
    doc["id"] = sid
    doc["name"] = name
    (dest / "screen.json").write_text(json.dumps(doc, indent=2) + "\n", "utf-8")
    (dest / "sample-data.json").write_text(json.dumps(SAMPLE, indent=2) + "\n", "utf-8")
    if args.code:
        (dest / "screen.py").write_text(CODE_PY, "utf-8")
    (dest / "README.md").write_text(
        README.format(name=name, title_hint="the header text",
                      code_section=CODE_SECTION if args.code else ""), "utf-8")

    print(f"created screens/{sid}/")
    print(f"  next: python tools/render_preview.py {sid} && python tools/validate.py {sid}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
