#!/usr/bin/env python3
"""Build the published catalog: validate every screen, then write the site tree the plugin fetches.

    python tools/build_catalog.py --out site
    python tools/build_catalog.py --out site --serial 1731000000   # fixed serial (reproducible)

Writes into <out>:
  zips/<id>-<version>.zip          reproducible package (README/preview excluded, via make_zip)
  previews/<id>-<version>.png      freshly rendered, authoritative 1-bit 648x480 preview
  index.json                       the catalog index (exact schema -- see the brief)
  .nojekyll                        so GitHub Pages serves the files verbatim

index.json is canonical JSON: json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False)+"\n", UTF-8.
`has_code` is DERIVED from the validated screen, never taken from contributor input. `min_plugin_version`
comes from catalog.json overrides[id], else the catalog default. Exit 1 if any screen fails validation.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog_lib as C  # noqa: E402
import validate as V  # noqa: E402


def load_catalog_json() -> dict:
    """catalog.json: {"min_plugin_version": "...", "overrides": {"<id>": "<version>"}}."""
    f = C.REPO_ROOT / "catalog.json"
    if not f.is_file():
        return {"min_plugin_version": C.DEFAULT_MIN_PLUGIN_VERSION, "overrides": {}}
    data = json.loads(f.read_text("utf-8"))
    data.setdefault("min_plugin_version", C.DEFAULT_MIN_PLUGIN_VERSION)
    data.setdefault("overrides", {})
    return data


def canonical_json(obj) -> bytes:
    return (json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")


def build(out_dir: Path, serial: int | None) -> dict:
    C.ensure_core_on_path()
    builtins = C.builtin_ids()
    catalog = load_catalog_json()
    default_mpv = catalog["min_plugin_version"]
    overrides = catalog["overrides"]

    dirs = C.all_screen_dirs()
    all_errors: list[str] = []
    for d in dirs:
        errs, _ = V.validate_screen_dir(d, builtins, base=None)
        all_errors.extend(errs)
    if all_errors:
        raise C.CatalogError(all_errors)

    serial = int(serial) if serial is not None else int(time.time())
    generated = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(serial))

    zips_dir = out_dir / "zips"
    previews_dir = out_dir / "previews"
    zips_dir.mkdir(parents=True, exist_ok=True)
    previews_dir.mkdir(parents=True, exist_ok=True)

    from inkterface_core.screens import load_screen  # noqa: E402

    entries = []
    for d in dirs:
        screen = load_screen(d)
        sid, version = screen.id, screen.version
        zip_bytes = C.build_zip_bytes(d)
        zip_rel = f"zips/{sid}-{version}.zip"
        (out_dir / zip_rel).write_bytes(zip_bytes)

        preview_bytes = C.image_to_preview_bytes(C.render_preview_image(d))
        preview_rel = f"previews/{sid}-{version}.png"
        (out_dir / preview_rel).write_bytes(preview_bytes)

        entries.append({
            "id": sid,
            "name": screen.name,
            "version": version,
            "author": screen.author,
            "description": screen.description or "",
            "has_code": screen.code_path is not None,
            "has_active": screen.active is not None,
            "has_idle": screen.idle is not None,
            "zip": zip_rel,
            "sha256": C.sha256_hex(zip_bytes),
            "size": len(zip_bytes),
            "preview": preview_rel,
            "preview_sha256": C.sha256_hex(preview_bytes),
            "min_plugin_version": overrides.get(sid, default_mpv),
        })

    entries.sort(key=lambda e: e["id"])
    ids = [e["id"] for e in entries]
    if len(set(ids)) != len(ids):
        raise C.CatalogError("duplicate screen ids in the catalog")

    index = {"schema": 1, "serial": serial, "generated": generated, "screens": entries}
    (out_dir / "index.json").write_bytes(canonical_json(index))
    (out_dir / ".nojekyll").write_bytes(b"")
    return index


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build the published catalog site.")
    ap.add_argument("--out", required=True, type=Path, metavar="DIR", help="output site directory")
    ap.add_argument("--serial", type=int, help="fixed serial (default: int unix seconds at build)")
    args = ap.parse_args(argv)
    try:
        index = build(args.out, args.serial)
    except C.CatalogError as e:
        print("\n".join(e.errors), file=sys.stderr)
        return 1
    print(f"built {len(index['screens'])} screen(s) into {args.out} (serial {index['serial']})")
    for e in index["screens"]:
        print(f"  {e['id']} {e['version']}  zip {e['size']}B  {e['sha256'][:12]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
