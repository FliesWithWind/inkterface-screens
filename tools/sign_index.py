#!/usr/bin/env python3
"""Sign the catalog index with the catalog's Ed25519 key.

    INKTERFACE_CATALOG_KEY=<64 hex> python tools/sign_index.py site/index.json
    python tools/sign_index.py site/index.json --key-file catalog.key
    python tools/sign_index.py site/index.json --key-env INKTERFACE_CATALOG_KEY --pubkey-file site/catalog-pubkey.txt

Signs the EXACT bytes of INDEX with the plugin's pure-python ed25519 and writes INDEX+".sig"
(raw 64 bytes). Verifies the signature afterwards. The seed must be 64 hex chars. The key is
never printed. If a public key is given (--pubkey HEX / --pubkey-file F) and the seed derives a
different public key, the tool fails loudly -- so CI passing catalog-pubkey.txt turns a wrong
secret into a failed job instead of an index the plugin would reject.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog_lib as C  # noqa: E402


def load_seed(text: str) -> bytes:
    text = text.strip()
    try:
        seed = bytes.fromhex(text)
    except ValueError:
        seed = b""
    if len(seed) != 32 or len(text) != 64:
        raise C.CatalogError("catalog signing key must be exactly 64 hex characters (a 32-byte seed)")
    return seed


def load_pubkey(hex_value: str | None, file: Path | None) -> bytes | None:
    if hex_value is None and file is None:
        return None
    text = hex_value if hex_value is not None else file.read_text("utf-8")
    text = text.strip()
    try:
        pub = bytes.fromhex(text)
    except ValueError:
        pub = b""
    if len(pub) != 32:
        raise C.CatalogError("expected public key as 64 hex characters (a 32-byte Ed25519 public key)")
    return pub


def sign_index(index_path: Path, seed: bytes, expected_pub: bytes | None) -> Path:
    C.ensure_core_on_path()
    from inkterface_core.ota import ed25519  # noqa: E402

    derived_pub = ed25519.publickey(seed)
    if expected_pub is not None and derived_pub != expected_pub:
        raise C.CatalogError("the signing key does not match the expected public key "
                             "(refusing to publish an index the plugin would reject)")
    raw = index_path.read_bytes()
    sig = ed25519.sign(seed, raw)
    if not ed25519.verify(derived_pub, raw, sig):
        raise C.CatalogError("self-check of the fresh signature failed")
    sig_path = index_path.with_name(index_path.name + ".sig")
    sig_path.write_bytes(sig)
    return sig_path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Sign the catalog index.")
    ap.add_argument("index", type=Path, help="path to index.json")
    ap.add_argument("--key-env", default="INKTERFACE_CATALOG_KEY", help="env var holding the seed (default INKTERFACE_CATALOG_KEY)")
    ap.add_argument("--key-file", type=Path, help="file holding the seed (64 hex chars); overrides --key-env")
    p = ap.add_mutually_exclusive_group()
    p.add_argument("--pubkey", help="expected public key as 64 hex chars")
    p.add_argument("--pubkey-file", type=Path, help="file with the expected public key (64 hex chars)")
    args = ap.parse_args(argv)

    try:
        if args.key_file:
            seed = load_seed(args.key_file.read_text("utf-8"))
        else:
            raw = os.environ.get(args.key_env)
            if not raw:
                raise C.CatalogError(f"no signing key: set {args.key_env} or pass --key-file "
                                     f"(never publish an unsigned index)")
            seed = load_seed(raw)
        expected_pub = load_pubkey(args.pubkey, args.pubkey_file)
        sig_path = sign_index(args.index, seed, expected_pub)
    except C.CatalogError as e:
        print("\n".join(e.errors), file=sys.stderr)
        return 1
    except OSError as e:
        print(f"{args.index}: {e}", file=sys.stderr)
        return 1
    print(f"wrote {sig_path} ({sig_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
