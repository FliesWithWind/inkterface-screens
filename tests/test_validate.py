"""Validator tests: each distinct failure the validator must catch, plus the good path."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import catalog_lib as C  # noqa: E402
import validate as V  # noqa: E402
from conftest import make_code, make_declarative, render_preview_into  # noqa: E402


def errs(screen_dir, builtins=frozenset(), base=None):
    return V.validate_screen_dir(screen_dir, set(builtins), base)[0]


def test_good_declarative_passes(declarative):
    assert errs(declarative) == []


def test_good_code_passes(code_screen):
    e, info = V.validate_screen_dir(code_screen, set(), None)
    assert e == []
    assert info["has_code"] is True
    assert len(info["code_sha256"]) == 64


def test_id_folder_mismatch(tmp_path):
    d = make_declarative(tmp_path, sid="demo")
    doc = json.loads((d / "screen.json").read_text())
    doc["id"] = "other"
    (d / "screen.json").write_text(json.dumps(doc))
    # load_screen itself flags the mismatch (folder name check).
    assert any("match the folder name" in m for m in errs(d))


def test_builtin_id_collision(tmp_path):
    d = make_declarative(tmp_path, sid="telemetry")
    assert any("built-in screen id" in m for m in errs(d, builtins={"telemetry"}))


def test_stray_screen_py_fails(declarative):
    (declarative / "screen.py").write_text("x = 1\n")
    assert any("does not declare active.code" in m for m in errs(declarative))


def test_declared_but_missing_screen_py_fails(tmp_path):
    d = make_code(tmp_path)
    (d / "screen.py").unlink()
    # The plugin validator rejects a declared-but-missing active.code before packaging.
    assert any("active.code" in m and "not found" in m for m in errs(d))


def test_oversize_readme_fails(declarative):
    (declarative / "README.md").write_text("#\n" + "x" * (C.MAX_README_BYTES + 10))
    assert any("README.md: too large" in m for m in errs(declarative))


def test_wrong_preview_size_fails(declarative):
    from PIL import Image

    bad = declarative / "preview.png"
    Image.new("1", (640, 480), 1).save(bad, "PNG")
    assert any("must be exactly 648x480" in m for m in errs(declarative))


def test_preview_mismatch_fails(declarative):
    from PIL import Image, ImageDraw

    img = Image.new("1", (648, 480), 1)
    ImageDraw.Draw(img).rectangle((0, 0, 647, 479), fill=0)  # all black: >1% different
    img.save(declarative / "preview.png", "PNG")
    assert any("differs from a fresh render" in m for m in errs(declarative))


def test_missing_preview_fails(declarative):
    (declarative / "preview.png").unlink()
    assert any("preview.png: required" in m for m in errs(declarative))


def test_code_readme_missing_section_fails(tmp_path):
    d = make_code(tmp_path)
    (d / "README.md").write_text("# Code Demo\n\nNo required heading here.\n")
    assert any(C.CODE_README_SECTION in m for m in errs(d))


def test_oversize_code_fails(tmp_path):
    d = make_code(tmp_path)
    # Pad screen.py past the 64 KiB limit with a comment; keep render() working.
    src = (d / "screen.py").read_text()
    (d / "screen.py").write_text(src + "\n# " + "p" * (C.MAX_CODE_BYTES + 10))
    render_preview_into(d)
    assert any("screen.py: too large" in m for m in errs(d))


def test_too_many_files_fails(declarative):
    assets = declarative / "assets"
    assets.mkdir()
    for i in range(C.MAX_FILES + 1):
        (assets / f"f{i}.txt").write_text("x")
    assert any("too many files" in m for m in errs(declarative))


# ---- version bump enforcement against a temporary git repo base ---------------------------


def _git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def git_catalog(tmp_path, monkeypatch):
    """A tiny git repo laid out like the catalog (screens/<id>/...), committed as 'base'."""
    repo = tmp_path / "repo"
    (repo / "screens").mkdir(parents=True)
    _git(repo, "init", "-b", "main")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    make_declarative(repo / "screens", sid="demo", version="1.0.0")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-m", "base")
    # Point catalog_lib / validate at this repo.
    monkeypatch.setattr(C, "REPO_ROOT", repo)
    monkeypatch.setattr(C, "SCREENS_DIR", repo / "screens")
    return repo


def test_changed_screen_needs_bump(git_catalog):
    d = git_catalog / "screens" / "demo"
    doc = json.loads((d / "screen.json").read_text())
    doc["description"] = "changed, packaged file edited"  # lands in the zip
    (d / "screen.json").write_text(json.dumps(doc))
    render_preview_into(d)
    # same version 1.0.0 -> must fail
    assert any("version: must be greater" in m for m in errs(d, base="HEAD"))


def test_bumped_version_passes(git_catalog):
    d = git_catalog / "screens" / "demo"
    doc = json.loads((d / "screen.json").read_text())
    doc["description"] = "changed, packaged file edited"
    doc["version"] = "1.0.1"
    (d / "screen.json").write_text(json.dumps(doc))
    render_preview_into(d)
    assert errs(d, base="HEAD") == []


def test_new_screen_needs_no_bump(git_catalog):
    d = make_declarative(git_catalog / "screens", sid="fresh", version="1.0.0")
    assert errs(d, base="HEAD") == []  # did not exist at base


def test_readme_only_change_no_bump(git_catalog):
    d = git_catalog / "screens" / "demo"
    (d / "README.md").write_text("# Demo\n\nJust docs, nothing packaged changed. MIT.\n")
    # README is excluded from the zip, so no bump required even at the same version.
    assert errs(d, base="HEAD") == []
