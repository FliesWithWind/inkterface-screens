# Vendored `inkterface_core`

`inkterface_core/` here is a pinned, byte-identical copy of the minimum set of modules from the
inkterface Decky plugin that the catalog tools and tests need (the screen validator, the renderer, the
package builder/sandbox, the OTA signature code), plus the renderer's bundled fonts and their licenses.

It is vendored so this repository's CI is **self-contained**: nothing here checks out the plugin repo.
`tools/catalog_lib.ensure_core_on_path()` puts this directory on `sys.path` first; set the
`INKTERFACE_CORE` environment variable only to override it with a live plugin checkout during
development.

## What the files are

- `PLUGIN_COMMIT` -- the full 40-hex commit sha of the plugin this copy was taken from.
- `MANIFEST` -- the vendored module list (also the single source of truth in `tools/sync_vendor.py`).
- `SHA256SUMS` -- sha256 of every vendored file; `tools/check_vendor.py` verifies the copy against it
  with no plugin repo present.

## Refreshing the copy

From a plugin checkout:

```
tools/sync_vendor.py --plugin /path/to/inkterface [--commit <sha>]
```

This copies the module list from that commit (via `git show`, never the working tree) and rewrites
`PLUGIN_COMMIT`, `MANIFEST` and `SHA256SUMS`. Verify with `tools/check_vendor.py` (and
`--plugin /path/to/inkterface` to confirm byte-identity against the commit). Commit the result.

## Licenses

- The Python modules under `inkterface_core/` are part of the inkterface plugin and are distributed
  under the **MIT License** (see `MIT-LICENSE.txt` in this directory, copied from the plugin).
- The fonts under `inkterface_core/screens/fonts/` (`InkterfaceMono-Regular.ttf`,
  `InkterfaceMono-Bold.ttf`) are licensed under the **SIL Open Font License, Version 1.1**; their
  license and font log travel with them as `OFL.txt` and `FONTLOG.txt` in that folder.
