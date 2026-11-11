"""Builder tests: exact schema, sorting, hashes, reproducibility, derived has_code, overrides."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import build_catalog as B  # noqa: E402
import catalog_lib as C  # noqa: E402
from conftest import make_code, make_declarative  # noqa: E402


@pytest.fixture
def catalog_repo(tmp_path, monkeypatch):
    """A repo with two screens (one declarative, one code) and a catalog.json."""
    repo = tmp_path / "repo"
    screens = repo / "screens"
    screens.mkdir(parents=True)
    make_declarative(screens, sid="alpha", version="1.2.3")
    make_code(screens, sid="beta", version="2.0.0")
    (repo / "catalog.json").write_text(json.dumps(
        {"min_plugin_version": "1.0.0", "overrides": {"beta": "1.5.0"}}))
    monkeypatch.setattr(C, "REPO_ROOT", repo)
    monkeypatch.setattr(C, "SCREENS_DIR", screens)
    return repo


def test_index_schema_exact(catalog_repo, tmp_path):
    import time

    serial = 1731000000
    index = B.build(tmp_path / "site", serial=serial)
    assert set(index) == {"schema", "serial", "generated", "screens"}
    assert index["schema"] == 1
    assert index["serial"] == serial
    assert index["generated"] == time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(serial))
    allowed = {"id", "name", "version", "author", "description", "has_code", "has_active",
               "has_idle", "zip", "sha256", "size", "preview", "preview_sha256", "min_plugin_version"}
    for e in index["screens"]:
        assert set(e) == allowed


def test_sorted_and_unique(catalog_repo, tmp_path):
    index = B.build(tmp_path / "site", serial=1)
    ids = [e["id"] for e in index["screens"]]
    assert ids == sorted(ids)
    assert len(ids) == len(set(ids))


def test_sha256_and_size_match_files(catalog_repo, tmp_path):
    site = tmp_path / "site"
    index = B.build(site, serial=1)
    for e in index["screens"]:
        zb = (site / e["zip"]).read_bytes()
        assert e["sha256"] == C.sha256_hex(zb)
        assert e["size"] == len(zb)
        pb = (site / e["preview"]).read_bytes()
        assert e["preview_sha256"] == C.sha256_hex(pb)


def test_zips_byte_identical_across_builds(catalog_repo, tmp_path):
    i1 = B.build(tmp_path / "s1", serial=1)
    i2 = B.build(tmp_path / "s2", serial=1)
    z1 = (tmp_path / "s1" / i1["screens"][0]["zip"]).read_bytes()
    z2 = (tmp_path / "s2" / i2["screens"][0]["zip"]).read_bytes()
    assert z1 == z2


def test_has_code_derived(catalog_repo, tmp_path):
    index = B.build(tmp_path / "site", serial=1)
    by_id = {e["id"]: e for e in index["screens"]}
    assert by_id["alpha"]["has_code"] is False
    assert by_id["beta"]["has_code"] is True


def test_min_plugin_version_override(catalog_repo, tmp_path):
    index = B.build(tmp_path / "site", serial=1)
    by_id = {e["id"]: e for e in index["screens"]}
    assert by_id["alpha"]["min_plugin_version"] == "1.0.0"   # default
    assert by_id["beta"]["min_plugin_version"] == "1.5.0"    # override


def test_canonical_json_form(catalog_repo, tmp_path):
    site = tmp_path / "site"
    B.build(site, serial=1)
    raw = (site / "index.json").read_bytes()
    obj = json.loads(raw)
    expected = (json.dumps(obj, indent=1, sort_keys=True, ensure_ascii=False) + "\n").encode("utf-8")
    assert raw == expected
    assert (site / ".nojekyll").is_file()


def test_build_fails_on_invalid_screen(catalog_repo, tmp_path):
    # Corrupt one screen's preview so validation fails.
    from PIL import Image

    Image.new("1", (640, 480), 1).save(catalog_repo / "screens" / "alpha" / "preview.png", "PNG")
    with pytest.raises(C.CatalogError):
        B.build(tmp_path / "site", serial=1)
