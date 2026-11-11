#!/usr/bin/env python3
"""Refresh the vendored copy of inkterface_core under vendor/inkterface_core/.

The catalog tools need the plugin's validator/renderer (the `inkterface_core` package). Rather than
check the private plugin repo out in CI, we vendor a pinned, byte-identical copy of the minimum set of
modules the tools and tests actually import (plus the fonts the renderer loads and their licenses).

This script copies that set FROM A COMMIT of the plugin repo (via `git show`, never the working tree),
then writes:
    vendor/PLUGIN_COMMIT   full 40-hex sha the copy comes from
    vendor/MANIFEST        the module list (one path per line, sorted)
    vendor/SHA256SUMS      sha256 of every vendored file (checked by check_vendor.py, no plugin repo needed)

Usage:
    tools/sync_vendor.py --plugin /path/to/inkterface-checkout [--commit <sha>]

Without --commit the plugin checkout's current HEAD is used. The module list below is the single source
of truth; add a module here when a tool starts importing it, then re-run and commit the result.
"""
from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
VENDOR = REPO_ROOT / "vendor"
PKG = "inkterface_core"
# Where the package lives inside the plugin repo.
PLUGIN_PKG_PREFIX = "decky/py_modules/inkterface_core"

# The minimum set the catalog tools + tests import (transitive closure), plus the renderer's fonts and
# the license files that travel with them. Paths are relative to the inkterface_core package root.
MODULES = [
    "__init__.py",
    "frame.py",
    "serial_ports.py",
    "serialport.py",
    "tls.py",
    "tz.py",
    "proto.py",
    "ota/__init__.py",
    "ota/ed25519.py",
    "ota/errors.py",
    "ota/manifest.py",
    "packages/__init__.py",
    "packages/build.py",
    "packages/extract.py",
    "packages/fetch.py",
    "packages/sandbox.py",
    "packages/store.py",
    "packages/_runner.py",
    "screens/__init__.py",
    "screens/data.py",
    "screens/fonts.py",
    "screens/icons.py",
    "screens/renderer.py",
    "screens/schema.py",
    "screens/widgets.py",
    "screens/fonts/InkterfaceMono-Regular.ttf",
    "screens/fonts/InkterfaceMono-Bold.ttf",
    "screens/fonts/OFL.txt",
    "screens/fonts/FONTLOG.txt",
]


def git_show(plugin: Path, commit: str, path: str) -> bytes:
    """Bytes of <path> at <commit> in the plugin repo. Never reads the working tree."""
    try:
        return subprocess.run(
            ["git", "-C", str(plugin), "show", f"{commit}:{path}"],
            check=True, capture_output=True,
        ).stdout
    except subprocess.CalledProcessError as e:
        sys.exit(f"git show {commit}:{path} failed: {e.stderr.decode('utf-8', 'replace').strip()}")


def resolve_commit(plugin: Path, commit: str | None) -> str:
    rev = commit or "HEAD"
    try:
        out = subprocess.run(
            ["git", "-C", str(plugin), "rev-parse", rev],
            check=True, capture_output=True,
        ).stdout.decode().strip()
    except subprocess.CalledProcessError as e:
        sys.exit(f"cannot resolve {rev} in {plugin}: {e.stderr.decode('utf-8', 'replace').strip()}")
    if len(out) != 40 or any(c not in "0123456789abcdef" for c in out):
        sys.exit(f"resolved commit is not a full 40-hex sha: {out!r}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Refresh vendor/inkterface_core from a plugin commit.")
    ap.add_argument("--plugin", required=True, type=Path, help="path to an inkterface plugin checkout")
    ap.add_argument("--commit", help="commit to copy from (default: the checkout's HEAD)")
    args = ap.parse_args(argv)

    plugin = args.plugin.expanduser().resolve()
    if not (plugin / ".git").exists():
        sys.exit(f"--plugin {plugin} is not a git checkout")
    commit = resolve_commit(plugin, args.commit)

    dest_pkg = VENDOR / PKG
    # Rebuild from scratch so a dropped module does not linger.
    if dest_pkg.exists():
        import shutil
        shutil.rmtree(dest_pkg)

    sums: list[tuple[str, str]] = []
    for rel in MODULES:
        data = git_show(plugin, commit, f"{PLUGIN_PKG_PREFIX}/{rel}")
        target = dest_pkg / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
        vendor_rel = f"{PKG}/{rel}"
        sums.append((hashlib.sha256(data).hexdigest(), vendor_rel))

    # Reserved built-in screen ids a community screen may not reuse: the plugin's decky/screens/* folders.
    try:
        tree = subprocess.run(
            ["git", "-C", str(plugin), "ls-tree", "-r", "--name-only", commit, "--", "decky/screens"],
            check=True, capture_output=True,
        ).stdout.decode()
    except subprocess.CalledProcessError as e:
        sys.exit(f"cannot list decky/screens at {commit}: {e.stderr.decode('utf-8', 'replace').strip()}")
    builtin = sorted({
        line.split("/")[2] for line in tree.splitlines()
        if line.endswith("/screen.json") and line.startswith("decky/screens/")
    })
    (VENDOR / "BUILTIN_SCREEN_IDS").write_text("\n".join(builtin) + "\n", "utf-8")

    (VENDOR / "PLUGIN_COMMIT").write_text(commit + "\n", "utf-8")
    (VENDOR / "MANIFEST").write_text(
        "\n".join(f"{PKG}/{rel}" for rel in sorted(MODULES)) + "\n", "utf-8")
    (VENDOR / "SHA256SUMS").write_text(
        "".join(f"{h}  {p}\n" for h, p in sorted(sums, key=lambda t: t[1])), "utf-8")

    print(f"Vendored {len(MODULES)} files from {commit} into {dest_pkg}")
    print(f"Built-in screen ids: {', '.join(builtin)}")
    print(f"Wrote {VENDOR / 'PLUGIN_COMMIT'}, {VENDOR / 'MANIFEST'}, {VENDOR / 'SHA256SUMS'}, "
          f"{VENDOR / 'BUILTIN_SCREEN_IDS'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
