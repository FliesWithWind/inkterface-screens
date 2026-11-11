#!/usr/bin/env python3
"""Validate community screen packages against the plugin's own rules plus the catalog's limits.

    python tools/validate.py                 # every screen under screens/
    python tools/validate.py gpu-focus       # named screens only
    python tools/validate.py --base origin/main   # only screens changed vs a git ref

For each screen directory it checks (see catalog-brief section 1):
  (a) the plugin's own validator (inkterface_core.screens.load_screen)
  (b) folder name == screen.json id, and the id is not a built-in id
  (c) it packages cleanly into a staging copy (README/preview excluded) with the plugin's make_zip
  (d) the catalog size/shape limits (catalog_lib constants)
  (e) screen.py present  <=>  active.code == "screen.py"
  (f) a committed preview.png matches a freshly rendered one (<=1% differing pixels)
  (g) with --base: a changed existing screen must bump its version (strict semver)
  (h) a summary; for code screens, the sha256 of screen.py; markdown to $GITHUB_STEP_SUMMARY

Exit 1 if any screen fails. Error lines read `screens/<id>/<file>: <field>: <message>`.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog_lib as C  # noqa: E402


def _git(base: str, *args: str) -> list[str]:
    out = subprocess.run(["git", "-C", str(C.REPO_ROOT), *args], capture_output=True, text=True)
    if out.returncode != 0:
        raise C.CatalogError(f"git {' '.join(args)} failed: {out.stderr.strip()}")
    return [ln for ln in out.stdout.splitlines() if ln]


def changed_screen_ids(base: str) -> set[str]:
    """Screen ids with any file changed vs `base` (added, modified or deleted)."""
    ids: set[str] = set()
    for line in _git(base, "diff", "--name-only", base, "--", "screens/"):
        parts = Path(line).parts
        if len(parts) >= 2 and parts[0] == "screens":
            ids.add(parts[1])
    return ids


def base_screen_json(base: str, screen_id: str) -> dict | None:
    """Parse screens/<id>/screen.json as it was at `base`, or None if it did not exist there."""
    out = subprocess.run(["git", "-C", str(C.REPO_ROOT), "show", f"{base}:screens/{screen_id}/screen.json"],
                         capture_output=True, text=True)
    if out.returncode != 0:
        return None
    try:
        return json.loads(out.stdout)
    except ValueError:
        return None


def zip_relevant_files_changed(base: str, screen_id: str) -> bool:
    """True if any file that lands in the shared zip (i.e. not README.md/preview.png) changed vs base."""
    for line in _git(base, "diff", "--name-only", base, "--", f"screens/{screen_id}/"):
        rel = Path(line).relative_to(Path("screens") / screen_id)
        if rel.parts and rel.parts[0] not in C.EXCLUDE_FROM_ZIP:
            return True
    return False


def _folder_size(screen_dir: Path) -> int:
    return sum(p.stat().st_size for p in screen_dir.rglob("*") if p.is_file())


def _file_count(screen_dir: Path) -> int:
    return sum(1 for p in screen_dir.rglob("*") if p.is_file())


def validate_screen_dir(screen_dir: Path, builtins: set[str], base: str | None) -> tuple[list[str], dict]:
    """Validate one screen. Returns (errors, info). `info` carries summary fields when it passed."""
    C.ensure_core_on_path()
    from inkterface_core.ota.manifest import semver  # noqa: E402
    from inkterface_core.screens import ScreenError, load_screen  # noqa: E402

    sid = screen_dir.name
    prefix = f"screens/{sid}"
    errs: list[str] = []
    info: dict = {"id": sid}

    # (a) plugin validator. Its messages already start with "screen.json: ...", so prepend only
    # the screen dir to reach `screens/<id>/screen.json: field: message`.
    try:
        screen = load_screen(screen_dir)
    except ScreenError as e:
        return [f"{prefix}/{m}" for m in e.errors], info
    info["version"] = screen.version
    info["name"] = screen.name
    info["author"] = screen.author
    info["description"] = screen.description
    info["has_active"] = screen.active is not None
    info["has_idle"] = screen.idle is not None

    # (b) folder name == id (load_screen already enforces this; keep an explicit message) + not a built-in
    if screen.id != sid:
        errs.append(f"{prefix}/screen.json: id: '{screen.id}' must match the folder name '{sid}'")
    if sid in builtins:
        errs.append(f"{prefix}: id '{sid}' is a built-in screen id and cannot be reused")

    # (e) screen.py present <=> active.code == "screen.py"
    code_file = screen_dir / "screen.py"
    declared = (screen.active or {}).get("code")
    has_code = declared == "screen.py"
    info["has_code"] = has_code
    if declared is not None and declared != "screen.py":
        errs.append(f"{prefix}/screen.json: active.code: must be 'screen.py' (got {declared!r})")
    if has_code and not code_file.is_file():
        errs.append(f"{prefix}/screen.json: active.code: declares screen.py but screens/{sid}/screen.py is missing")
    if code_file.is_file() and not has_code:
        errs.append(f"{prefix}/screen.py: present but screen.json does not declare active.code == 'screen.py'")

    # (d) limits
    n_files = _file_count(screen_dir)
    if n_files > C.MAX_FILES:
        errs.append(f"{prefix}: too many files ({n_files} > {C.MAX_FILES})")
    folder_bytes = _folder_size(screen_dir)
    if folder_bytes > C.MAX_FOLDER_BYTES:
        errs.append(f"{prefix}: folder too large ({folder_bytes} bytes > {C.MAX_FOLDER_BYTES})")
    if code_file.is_file():
        cb = code_file.stat().st_size
        if cb > C.MAX_CODE_BYTES:
            errs.append(f"{prefix}/screen.py: too large ({cb} bytes > {C.MAX_CODE_BYTES})")
        info["code_sha256"] = C.sha256_hex(code_file.read_bytes())
    readme = screen_dir / "README.md"
    if not readme.is_file():
        errs.append(f"{prefix}/README.md: required (describe the screen; MIT contribution)")
    else:
        rb = readme.stat().st_size
        if rb > C.MAX_README_BYTES:
            errs.append(f"{prefix}/README.md: too large ({rb} bytes > {C.MAX_README_BYTES})")
        if has_code and C.CODE_README_SECTION not in readme.read_text("utf-8"):
            errs.append(f"{prefix}/README.md: a code screen's README must contain the line '{C.CODE_README_SECTION}'")

    # (c) packages cleanly
    zip_bytes = None
    try:
        zip_bytes = C.build_zip_bytes(screen_dir)
    except Exception as e:  # noqa: BLE001 - PackageError and friends
        for m in getattr(e, "errors", [str(e)]):
            errs.append(f"{prefix}: packaging failed: {m}")
    if zip_bytes is not None and len(zip_bytes) > C.MAX_ZIP_BYTES:
        errs.append(f"{prefix}: packaged zip too large ({len(zip_bytes)} bytes > {C.MAX_ZIP_BYTES})")

    # (d/f) preview.png: must exist, be exactly 648x480 PNG and <=200 KiB, and match a fresh render
    preview = screen_dir / "preview.png"
    if not preview.is_file():
        errs.append(f"{prefix}/preview.png: required -- run `python tools/render_preview.py {sid}`")
    elif screen.active is None:
        # idle-only screen: nothing to render; still require the size/shape of the committed file
        pb = preview.read_bytes()
        if len(pb) > C.MAX_PREVIEW_BYTES:
            errs.append(f"{prefix}/preview.png: too large ({len(pb)} bytes > {C.MAX_PREVIEW_BYTES})")
        try:
            w, h, _ = C.png_dimensions(pb)
            if (w, h) != C.PREVIEW_SIZE:
                errs.append(f"{prefix}/preview.png: must be exactly {C.PREVIEW_SIZE[0]}x{C.PREVIEW_SIZE[1]} (got {w}x{h})")
        except C.CatalogError as e:
            errs.append(f"{prefix}/preview.png: {e}")
    else:
        pb = preview.read_bytes()
        if len(pb) > C.MAX_PREVIEW_BYTES:
            errs.append(f"{prefix}/preview.png: too large ({len(pb)} bytes > {C.MAX_PREVIEW_BYTES})")
        try:
            w, h, _ = C.png_dimensions(pb)
            if (w, h) != C.PREVIEW_SIZE:
                errs.append(f"{prefix}/preview.png: must be exactly {C.PREVIEW_SIZE[0]}x{C.PREVIEW_SIZE[1]} (got {w}x{h})")
            else:
                fresh = C.image_to_preview_bytes(C.render_preview_image(screen_dir))
                diff, total = C.count_diff_pixels(pb, fresh)
                if diff > total * 0.01:
                    errs.append(f"{prefix}/preview.png: differs from a fresh render by {diff}/{total} pixels "
                                f"(> 1%); run `python tools/render_preview.py {sid}`")
        except C.CatalogError as e:
            errs.append(f"{prefix}/preview.png: {e}")

    # (g) version bump enforcement vs base
    if base is not None and not errs:
        prev = base_screen_json(base, sid)
        if prev is not None and zip_relevant_files_changed(base, sid):
            try:
                if semver(screen.version) <= semver(prev.get("version", "0.0.0")):
                    errs.append(f"{prefix}/screen.json: version: must be greater than the base version "
                                f"{prev.get('version')!r} because packaged files changed (got {screen.version!r})")
            except ValueError as e:
                errs.append(f"{prefix}/screen.json: version: {e}")

    return errs, info


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Validate community screen packages.")
    ap.add_argument("ids", nargs="*", help="screen ids to validate (default: all)")
    ap.add_argument("--base", metavar="REF", help="only validate screens changed vs this git ref; enforce version bumps")
    args = ap.parse_args(argv)

    try:
        C.ensure_core_on_path()
        builtins = C.builtin_ids()
    except C.CatalogError as e:
        print(e, file=sys.stderr)
        return 1

    if args.ids:
        dirs = [C.screen_dir_for(i) for i in args.ids]
        missing = [d for d in dirs if not (d / "screen.json").is_file()]
        if missing:
            for d in missing:
                print(f"screens/{d.name}: not a screen directory (no screen.json)", file=sys.stderr)
            return 1
    elif args.base:
        try:
            changed = changed_screen_ids(args.base)
        except C.CatalogError as e:
            print(e, file=sys.stderr)
            return 1
        dirs = [C.screen_dir_for(i) for i in sorted(changed) if (C.screen_dir_for(i) / "screen.json").is_file()]
    else:
        dirs = C.all_screen_dirs()

    if not dirs:
        print("no screens to validate")

    all_errors: list[str] = []
    summaries: list[dict] = []
    for d in dirs:
        errs, info = validate_screen_dir(d, builtins, args.base)
        if errs:
            all_errors.extend(errs)
        else:
            summaries.append(info)

    for e in all_errors:
        print(e, file=sys.stderr)

    # (h) summary
    lines = ["", f"Validated {len(dirs)} screen(s): {len(summaries)} ok, {len(all_errors)} error(s)."]
    for s in summaries:
        tier = "code" if s.get("has_code") else "declarative"
        sections = "+".join(x for x, on in (("active", s["has_active"]), ("idle", s["has_idle"])) if on)
        line = f"  ok  {s['id']} {s.get('version','?')} [{tier}, {sections}]"
        if s.get("code_sha256"):
            line += f"  screen.py sha256={s['code_sha256']}"
        lines.append(line)
    print("\n".join(lines))

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        md = [f"## Catalog validation\n\n{len(summaries)} ok, {len(all_errors)} error(s).\n"]
        if summaries:
            md.append("| id | version | tier | sections | screen.py sha256 |")
            md.append("|----|---------|------|----------|------------------|")
            for s in summaries:
                tier = "code" if s.get("has_code") else "declarative"
                sections = "+".join(x for x, on in (("active", s["has_active"]), ("idle", s["has_idle"])) if on)
                md.append(f"| {s['id']} | {s.get('version','?')} | {tier} | {sections} | "
                          f"{s.get('code_sha256', '-')} |")
        if all_errors:
            md.append("\n### Errors\n")
            md.extend(f"- `{e}`" for e in all_errors)
        try:
            with open(step_summary, "a", encoding="utf-8") as f:
                f.write("\n".join(md) + "\n")
        except OSError:
            pass

    return 1 if all_errors else 0


if __name__ == "__main__":
    sys.exit(main())
