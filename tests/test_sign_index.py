"""Signing tests: verify ok, tampered fails, wrong key fails, --pubkey mismatch fails, bad seed rejected."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import catalog_lib as C  # noqa: E402
import sign_index as S  # noqa: E402

SEED_A = "00" * 31 + "01"
SEED_B = "00" * 31 + "02"


def _ed():
    C.ensure_core_on_path()
    from inkterface_core.ota import ed25519
    return ed25519


def _index(tmp_path):
    p = tmp_path / "index.json"
    p.write_bytes(b'{"schema": 1, "serial": 1, "generated": "x", "screens": []}\n')
    return p


def test_sign_and_verify_ok(tmp_path):
    ed = _ed()
    idx = _index(tmp_path)
    seed = bytes.fromhex(SEED_A)
    sig_path = S.sign_index(idx, seed, None)
    sig = sig_path.read_bytes()
    assert len(sig) == 64
    assert ed.verify(ed.publickey(seed), idx.read_bytes(), sig)


def test_tampered_index_fails_verification(tmp_path):
    ed = _ed()
    idx = _index(tmp_path)
    seed = bytes.fromhex(SEED_A)
    sig = S.sign_index(idx, seed, None).read_bytes()
    idx.write_bytes(idx.read_bytes() + b" ")  # tamper after signing
    assert not ed.verify(ed.publickey(seed), idx.read_bytes(), sig)


def test_wrong_key_fails_verification(tmp_path):
    ed = _ed()
    idx = _index(tmp_path)
    sig = S.sign_index(idx, bytes.fromhex(SEED_A), None).read_bytes()
    wrong_pub = ed.publickey(bytes.fromhex(SEED_B))
    assert not ed.verify(wrong_pub, idx.read_bytes(), sig)


def test_pubkey_mismatch_fails_loudly(tmp_path):
    ed = _ed()
    idx = _index(tmp_path)
    expected = ed.publickey(bytes.fromhex(SEED_B))  # not the signing key's public
    with pytest.raises(C.CatalogError):
        S.sign_index(idx, bytes.fromhex(SEED_A), expected)


def test_pubkey_match_ok(tmp_path):
    ed = _ed()
    idx = _index(tmp_path)
    seed = bytes.fromhex(SEED_A)
    expected = ed.publickey(seed)
    assert S.sign_index(idx, seed, expected).is_file()


@pytest.mark.parametrize("bad", ["short", "zz" * 32, "00" * 31])
def test_bad_seed_rejected(bad):
    with pytest.raises(C.CatalogError):
        S.load_seed(bad)


def test_missing_key_env_exit_1(tmp_path, monkeypatch):
    monkeypatch.delenv("INKTERFACE_CATALOG_KEY", raising=False)
    idx = _index(tmp_path)
    assert S.main([str(idx)]) == 1
    assert not idx.with_name("index.json.sig").exists()
