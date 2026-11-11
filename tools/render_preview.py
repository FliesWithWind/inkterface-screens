#!/usr/bin/env python3
"""Render a screen's preview.png with the plugin's own renderer.

    python tools/render_preview.py gpu-focus      # writes screens/gpu-focus/preview.png
    python tools/render_preview.py --all          # every screen with an active section

Declarative screens render through the plugin engine + sample-data.json; code screens render
through the plugin's guarded run_code, exactly as the plugin draws them. The output is a 1-bit
648x480 optimized PNG -- the same encoding validate.py and build_catalog.py compare against.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog_lib as C  # noqa: E402


def render_one(screen_dir: Path) -> Path:
    img = C.render_preview_image(screen_dir)
    out = screen_dir / "preview.png"
    out.write_bytes(C.image_to_preview_bytes(img))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Render screen previews with the plugin renderer.")
    ap.add_argument("ids", nargs="*", help="screen ids to render")
    ap.add_argument("--all", action="store_true", help="render every screen that has an active section")
    args = ap.parse_args(argv)

    try:
        C.ensure_core_on_path()
    except C.CatalogError as e:
        print(e, file=sys.stderr)
        return 1

    if args.all:
        dirs = C.all_screen_dirs()
    elif args.ids:
        dirs = [C.screen_dir_for(i) for i in args.ids]
    else:
        ap.error("give one or more screen ids, or --all")

    failed = 0
    for d in dirs:
        if not (d / "screen.json").is_file():
            print(f"screens/{d.name}: not a screen directory", file=sys.stderr)
            failed += 1
            continue
        try:
            out = render_one(d)
            print(f"ok    {d.name} -> {out}")
        except C.CatalogError as e:
            # idle-only screens have no active preview: skip under --all, fail if named
            if args.all and "no active section" in str(e):
                print(f"skip  {d.name} (idle-only, no host preview)")
                continue
            failed += 1
            print(f"FAIL  {d.name}: {e}", file=sys.stderr)
        except Exception as e:  # noqa: BLE001
            failed += 1
            for m in getattr(e, "errors", [str(e)]):
                print(f"FAIL  {d.name}: {m}", file=sys.stderr)
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
