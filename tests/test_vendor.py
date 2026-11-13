"""Tests for the vendored inkterface_core copy and its check/sync tools.

These do not need the plugin repo (except the sync round-trip, which uses the sibling inkterface-rc
worktree when present and otherwise skips; CI has no plugin checkout, so it always skips there). They work on a throwaway copy of the real
vendor/ tree so the repo's own files are never mutated.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import check_vendor  # noqa: E402
import sync_vendor  # noqa: E402

REAL_VENDOR = Path(__file__).resolve().parents[1] / "vendor"
PKG = "inkterface_core"


@pytest.fixture
def vendor_copy(tmp_path, monkeypatch):
    """A writable copy of the real vendor/ tree, with check_vendor pointed at it."""
    dst = tmp_path / "vendor"
    shutil.copytree(REAL_VENDOR, dst)
    monkeypatch.setattr(check_vendor, "VENDOR", dst)
    return dst


def test_real_vendor_is_sound():
    """The committed vendor/ passes check_vendor with no plugin repo."""
    assert check_vendor.check() == []


def test_copy_is_sound(vendor_copy):
    assert check_vendor.check() == []


def test_tampered_file_detected(vendor_copy):
    target = vendor_copy / PKG / "screens" / "renderer.py"
    target.write_bytes(target.read_bytes() + b"\n# tampered\n")
    problems = check_vendor.check()
    assert any("renderer.py" in p and "tampered" in p for p in problems)


def test_extra_file_detected(vendor_copy):
    (vendor_copy / PKG / "screens" / "sneaky.py").write_text("x = 1\n", "utf-8")
    problems = check_vendor.check()
    assert any("sneaky.py" in p and "extra" in p for p in problems)


def test_missing_file_detected(vendor_copy):
    (vendor_copy / PKG / "screens" / "icons.py").unlink()
    problems = check_vendor.check()
    assert any("icons.py" in p and "missing on disk" in p for p in problems)


def test_bad_commit_file_detected(vendor_copy):
    (vendor_copy / "PLUGIN_COMMIT").write_text("not-a-sha\n", "utf-8")
    problems = check_vendor.check()
    assert any("PLUGIN_COMMIT" in p and "40-hex" in p for p in problems)


def test_commit_file_must_be_full_40_hex(vendor_copy):
    # a short (abbreviated) sha is rejected: PLUGIN_COMMIT must be the full 40-hex sha
    (vendor_copy / "PLUGIN_COMMIT").write_text("be01bd2\n", "utf-8")
    problems = check_vendor.check()
    assert any("PLUGIN_COMMIT" in p and "40-hex" in p for p in problems)


def _rc_plugin_checkout() -> Path | None:
    """The sibling inkterface-rc worktree used for the sync round-trip, if it is a git checkout holding
    the pinned commit."""
    # REAL_VENDOR = <engineer>/inkterface-screens-catalog/vendor; the rc worktree is a sibling of the catalog.
    rc = REAL_VENDOR.parents[1] / "inkterface-rc"
    if not (rc / ".git").exists():
        return None
    return rc


def test_check_against_plugin(vendor_copy):
    """With --plugin, the vendored files must equal `git show <PLUGIN_COMMIT>:<path>`."""
    rc = _rc_plugin_checkout()
    if rc is None:
        pytest.skip("no inkterface-rc plugin worktree beside the catalog; skipping plugin cross-check")
    assert check_vendor.check(plugin=rc) == []


def test_sync_round_trip(tmp_path, monkeypatch):
    """sync_vendor --plugin <rc> reproduces a tree that check_vendor accepts (and matches the committed one)."""
    rc = _rc_plugin_checkout()
    if rc is None:
        pytest.skip("no inkterface-rc plugin worktree beside the catalog; skipping sync round-trip")

    fresh = tmp_path / "vendor"
    fresh.mkdir()
    monkeypatch.setattr(sync_vendor, "VENDOR", fresh)
    commit = (REAL_VENDOR / "PLUGIN_COMMIT").read_text("utf-8").strip()
    assert sync_vendor.main(["--plugin", str(rc), "--commit", commit]) == 0

    # The freshly synced tree is self-consistent...
    monkeypatch.setattr(check_vendor, "VENDOR", fresh)
    assert check_vendor.check() == []
    # ...and identical to what is committed (SHA256SUMS, MANIFEST, PLUGIN_COMMIT, and every file).
    for meta in ("PLUGIN_COMMIT", "MANIFEST", "SHA256SUMS", "BUILTIN_SCREEN_IDS"):
        assert (fresh / meta).read_bytes() == (REAL_VENDOR / meta).read_bytes(), meta
    def _src_files(base: Path) -> set[Path]:
        return {
            p.relative_to(base) for p in (base / PKG).rglob("*")
            if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"
        }

    fresh_files = _src_files(fresh)
    real_files = _src_files(REAL_VENDOR)
    assert fresh_files == real_files
    for rel in fresh_files:
        assert (fresh / rel).read_bytes() == (REAL_VENDOR / rel).read_bytes(), rel
