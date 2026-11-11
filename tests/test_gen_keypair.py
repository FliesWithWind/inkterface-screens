"""gen_keypair tests: refuses to overwrite, private key is 0600, keys are a valid pair."""
from __future__ import annotations

import os
import stat
import sys
from pathlib import Path

TOOLS = Path(__file__).resolve().parents[1] / "tools"
sys.path.insert(0, str(TOOLS))

import catalog_lib as C  # noqa: E402
import gen_keypair as G  # noqa: E402


def test_generates_valid_pair(tmp_path):
    priv = tmp_path / "cat.key"
    pub = tmp_path / "cat.pub"
    assert G.main(["--private", str(priv), "--public", str(pub)]) == 0
    C.ensure_core_on_path()
    from inkterface_core.ota import ed25519

    seed = bytes.fromhex(priv.read_text().strip())
    assert len(seed) == 32
    assert bytes.fromhex(pub.read_text().strip()) == ed25519.publickey(seed)


def test_private_key_mode_0600(tmp_path):
    priv = tmp_path / "cat.key"
    pub = tmp_path / "cat.pub"
    G.main(["--private", str(priv), "--public", str(pub)])
    assert stat.S_IMODE(os.stat(priv).st_mode) == 0o600


def test_refuses_to_overwrite_private(tmp_path):
    priv = tmp_path / "cat.key"
    pub = tmp_path / "cat.pub"
    priv.write_text("existing\n")
    assert G.main(["--private", str(priv), "--public", str(pub)]) == 1
    assert priv.read_text() == "existing\n"   # untouched
    assert not pub.exists()


def test_refuses_to_overwrite_public_and_cleans_up(tmp_path):
    priv = tmp_path / "cat.key"
    pub = tmp_path / "cat.pub"
    pub.write_text("existing-pub\n")
    assert G.main(["--private", str(priv), "--public", str(pub)]) == 1
    assert not priv.exists()   # no orphan private key left behind
    assert pub.read_text() == "existing-pub\n"
