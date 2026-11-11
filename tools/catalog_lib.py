"""Shared helpers for the inkterface-screens catalog tools.

Everything the validator, preview renderer, catalog builder and signer have in common:
where the plugin code is, the per-screen limits, how a screen is packaged into a staging
copy, and how its preview is rendered with the plugin's own renderer.

The plugin code (the `inkterface_core` package) is VENDORED in this repo at `vendor/inkterface_core`
(a pinned, byte-identical copy; see vendor/README.md), so the tools and CI are self-contained and never
need the plugin repo. For development against a live plugin checkout, set the INKTERFACE_CORE
environment variable to the directory that CONTAINS `inkterface_core` (the plugin's decky/py_modules);
it takes precedence over the vendored copy.
"""
from __future__ import annotations

import hashlib
import io
import os
import shutil
import sys
import tempfile
from pathlib import Path

# ---- where things live --------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[1]
SCREENS_DIR = REPO_ROOT / "screens"
VENDOR_CORE = REPO_ROOT / "vendor"   # contains the vendored inkterface_core package

# ---- per-screen limits (the brief's section (d)) ------------------------------------------

MAX_FILES = 40                      # files in a screen dir
MAX_FOLDER_BYTES = 1 * 1024 * 1024  # whole screen dir on disk (1 MiB)
MAX_ZIP_BYTES = 512 * 1024          # packaged zip (512 KiB)
MAX_CODE_BYTES = 64 * 1024          # screen.py (64 KiB)
MAX_PREVIEW_BYTES = 200 * 1024      # preview.png (200 KiB)
MAX_README_BYTES = 20 * 1024        # README.md (20 KiB)
PREVIEW_SIZE = (648, 480)           # exact PNG dimensions

# Files that live in a screen dir but never go into the shared zip.
EXCLUDE_FROM_ZIP = {"README.md", "preview.png"}

CODE_README_SECTION = "## What the code does"

# catalog.json default when a screen has no override.
DEFAULT_MIN_PLUGIN_VERSION = "1.0.0-beta.1"   # 1.0.0 would exclude the beta plugin: prereleases sort below


class CatalogError(Exception):
    """A tool failure. `.errors` holds one `screens/<id>/file: field: message` line per problem."""

    def __init__(self, errors):
        self.errors = [errors] if isinstance(errors, str) else list(errors)
        super().__init__("\n".join(self.errors))


# ---- plugin code import ---------------------------------------------------------------------

def core_dir() -> Path:
    """Directory that contains the `inkterface_core` package. The vendored copy (vendor/) wins; a live
    plugin checkout can override it with the INKTERFACE_CORE env var (the dir containing inkterface_core)."""
    if os.environ.get("INKTERFACE_CORE"):
        return Path(os.environ["INKTERFACE_CORE"])
    return VENDOR_CORE


def ensure_core_on_path() -> Path:
    """Put the plugin code on sys.path and return the inkterface_core package dir. Raises CatalogError if missing."""
    d = core_dir()
    pkg = d / "inkterface_core"
    if not pkg.is_dir():
        raise CatalogError(
            f"inkterface_core not found at {pkg} -- the vendored copy at {VENDOR_CORE / 'inkterface_core'} "
            f"is missing (run tools/sync_vendor.py), or set INKTERFACE_CORE to a plugin checkout's "
            f"decky/py_modules to override it"
        )
    s = str(d)
    if s not in sys.path:
        sys.path.insert(0, s)
    return pkg


BUILTIN_IDS_FILE = VENDOR_CORE / "BUILTIN_SCREEN_IDS"   # one built-in screen id per line, synced from the plugin


def builtin_ids() -> set[str]:
    """Ids a community screen may not use: the plugin's built-in screen folder names.

    When INKTERFACE_CORE points at a live plugin checkout, read them from its decky/screens; otherwise use
    the vendored list in vendor/BUILTIN_SCREEN_IDS (refreshed by tools/sync_vendor.py)."""
    if os.environ.get("INKTERFACE_CORE"):
        # INKTERFACE_CORE is .../decky/py_modules; built-ins live at .../decky/screens.
        screens = core_dir().parent / "screens"
        if screens.is_dir():
            return {p.name for p in screens.iterdir() if (p / "screen.json").is_file()}
        return set()
    if BUILTIN_IDS_FILE.is_file():
        return {ln.strip() for ln in BUILTIN_IDS_FILE.read_text("utf-8").splitlines() if ln.strip()}
    return set()


# ---- staging + packaging -------------------------------------------------------------------

def stage_copy(screen_dir: Path, dest: Path) -> Path:
    """Copy a screen dir into `dest/<id>` EXCLUDING README.md and preview.png, so the zip holds only
    what users receive. Returns the staged folder."""
    staged = dest / screen_dir.name
    staged.mkdir(parents=True)
    for p in sorted(screen_dir.rglob("*")):
        rel = p.relative_to(screen_dir)
        if rel.parts[0] in EXCLUDE_FROM_ZIP:
            continue
        target = staged / rel
        if p.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(p, target)
    return staged


def build_zip_bytes(screen_dir: Path) -> bytes:
    """Package a screen into reproducible zip bytes via the plugin's own make_zip (which re-imports
    through load_zip as a check). The README and preview are excluded via a staging copy."""
    ensure_core_on_path()
    from inkterface_core.packages.build import make_zip  # noqa: E402

    with tempfile.TemporaryDirectory(prefix="inkcat-stage-") as td:
        staged = stage_copy(screen_dir, Path(td))
        out = Path(td) / f"{screen_dir.name}.zip"
        make_zip(staged, out)
        return out.read_bytes()


# ---- rendering ------------------------------------------------------------------------------

def render_preview_image(screen_dir: Path):
    """Render a screen's active section to a 648x480 1-bit PIL image using the plugin's renderer.

    Declarative: the plugin renderer + sample-data.json. Code: the plugin's guarded run_code on the
    screen's own screen.py bytes, exactly as the plugin runs it. Idle-only screens have no active
    section to render and raise CatalogError.
    """
    ensure_core_on_path()
    import json

    from inkterface_core.packages.sandbox import run_code  # noqa: E402
    from inkterface_core.screens import load_screen  # noqa: E402
    from inkterface_core.screens.data import DataSnapshot  # noqa: E402
    from inkterface_core.screens.renderer import render  # noqa: E402

    screen = load_screen(screen_dir)
    if screen.active is None:
        raise CatalogError(f"screens/{screen_dir.name}: no active section to render a preview from "
                           f"(idle-only screens have no host preview)")
    data_file = screen_dir / "sample-data.json"
    data = json.loads(data_file.read_text("utf-8")) if data_file.is_file() else {}
    if not isinstance(data, dict):
        raise CatalogError(f"screens/{screen_dir.name}/sample-data.json: top level must be an object")
    if screen.code_path is None:
        return render(screen, DataSnapshot(data, data_file.parent))
    return run_code(screen.code_path.read_bytes(), screen.root, data, screen.resolve_settings())


def image_to_preview_bytes(img) -> bytes:
    """1-bit 648x480 PNG bytes, optimized. The authoritative preview encoding used everywhere."""
    if img.mode != "1":
        img = img.convert("1")
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def png_dimensions(data: bytes):
    """(width, height, mode) of PNG bytes, via Pillow. Raises CatalogError on non-PNG."""
    ensure_core_on_path()
    from PIL import Image  # noqa: E402

    try:
        with Image.open(io.BytesIO(data)) as im:
            return im.width, im.height, im.mode
    except Exception as e:  # noqa: BLE001
        raise CatalogError(f"not a readable PNG: {e}") from None


def count_diff_pixels(a: bytes, b: bytes) -> tuple[int, int]:
    """(differing pixel count, total pixels) between two PNGs, compared as 1-bit. Raises on size mismatch."""
    ensure_core_on_path()
    from PIL import Image, ImageChops  # noqa: E402

    ia = Image.open(io.BytesIO(a)).convert("1")
    ib = Image.open(io.BytesIO(b)).convert("1")
    if ia.size != ib.size:
        raise CatalogError(f"preview size {ia.size} does not match the freshly rendered {ib.size}")
    diff = ImageChops.difference(ia, ib)
    # histogram of the 1-bit diff: index 0 counts identical pixels, index 255 the differing ones.
    hist = diff.histogram()
    nonzero = sum(hist[1:])
    return nonzero, ia.size[0] * ia.size[1]


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


# ---- screen discovery ----------------------------------------------------------------------

def all_screen_dirs() -> list[Path]:
    """Every screen directory (a dir under screens/ holding screen.json), sorted by id."""
    if not SCREENS_DIR.is_dir():
        return []
    return sorted((p for p in SCREENS_DIR.iterdir() if (p / "screen.json").is_file()), key=lambda p: p.name)


def screen_dir_for(screen_id: str) -> Path:
    return SCREENS_DIR / screen_id
