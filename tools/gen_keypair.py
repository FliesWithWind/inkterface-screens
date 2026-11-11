#!/usr/bin/env python3
"""Generate the catalog's Ed25519 signing keypair.

    python tools/gen_keypair.py --private catalog.key --public catalog-pubkey.txt

Writes the 32-byte seed as 64 hex chars (mode 0600, refuses to overwrite) and the public key as
64 hex chars (0644). Store the PRIVATE file's contents as the GitHub Actions secret
INKTERFACE_CATALOG_KEY; never commit it. Paste the PUBLIC hex into the plugin's
inkterface_core/catalog/trust.py as PRODUCTION_PUBLIC_KEY_HEX so the plugin trusts this catalog.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import catalog_lib as C  # noqa: E402


def _write_new(path: str, text: str, mode: int) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)  # O_EXCL: never clobber a key
    with os.fdopen(fd, "w") as f:
        f.write(text)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Generate the catalog signing keypair.")
    ap.add_argument("--private", required=True, help="where to write the private seed (hex)")
    ap.add_argument("--public", required=True, help="where to write the public key (hex)")
    args = ap.parse_args(argv)

    try:
        C.ensure_core_on_path()
    except C.CatalogError as e:
        print(e, file=sys.stderr)
        return 1
    from inkterface_core.ota import ed25519  # noqa: E402

    seed = os.urandom(32)
    pub = ed25519.publickey(seed)
    try:
        _write_new(args.private, seed.hex() + "\n", 0o600)
        try:
            _write_new(args.public, pub.hex() + "\n", 0o644)
        except FileExistsError:
            os.unlink(args.private)  # do not leave an orphan private key behind
            raise
    except FileExistsError as e:
        print(f"refusing to overwrite {e.filename}", file=sys.stderr)
        return 1
    print(f"private key: {args.private}  (keep secret; 0600)")
    print(f"public key : {args.public}")
    print(f"PUBLIC KEY (paste into inkterface_core/catalog/trust.py as PRODUCTION_PUBLIC_KEY_HEX): {pub.hex()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
