"""catalog-pubkey.txt is what publish.yml checks the INKTERFACE_CATALOG_KEY secret against."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_pubkey_file_is_one_public_key_in_hex():
    text = (ROOT / "catalog-pubkey.txt").read_text()
    assert re.fullmatch(r"[0-9a-f]{64}\n?", text)


def test_pubkey_file_is_tracked_not_ignored():
    assert "catalog-pubkey.txt" not in (ROOT / ".gitignore").read_text()
