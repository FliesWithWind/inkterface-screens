"""Every seed screen shipped in this repo validates, and the whole catalog builds."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import build_catalog as B  # noqa: E402
import catalog_lib as C  # noqa: E402
import validate as V  # noqa: E402

SEED_DIRS = C.all_screen_dirs()


@pytest.mark.parametrize("screen_dir", SEED_DIRS, ids=[d.name for d in SEED_DIRS])
def test_seed_screen_validates(screen_dir):
    builtins = C.builtin_ids()
    errs, info = V.validate_screen_dir(screen_dir, builtins, base=None)
    assert errs == [], "\n".join(errs)
    assert info["id"] == screen_dir.name


def test_catalog_builds(tmp_path):
    index = B.build(tmp_path / "site", serial=1731000000)
    assert len(index["screens"]) == len(SEED_DIRS)
    for e in index["screens"]:
        assert (tmp_path / "site" / e["zip"]).is_file()
        assert (tmp_path / "site" / e["preview"]).is_file()


def test_at_least_three_seed_screens():
    assert len(SEED_DIRS) >= 3
