# Contributing a screen

Thanks for contributing. The short version: one screen per PR, it validates cleanly, the preview is
committed, and code screens explain themselves.

## Steps

1. Skim the screen schema in the vendored validator, `vendor/inkterface_core/screens/schema.py`: it
   lists every widget type, field and limit the catalog accepts.
2. No setup is needed: the plugin's validator and renderer are vendored at `vendor/inkterface_core`,
   so the tools and tests run out of the box with just Python 3.14 and Pillow. (To develop against a
   live plugin checkout instead, `export INKTERFACE_CORE=/path/to/inkterface/decky/py_modules`.)
3. Scaffold: `python tools/new_screen.py my-screen` (add `--code` for a code screen). The folder
   name must equal the `id` in `screen.json`, and must not be a built-in id.
4. Edit `screens/my-screen/`. Add a `sample-data.json` so the emulator and preview have data.
5. Emulate: `python -m inkterface_core.screens.emulate screens/my-screen --out out.png`
   (add `--allow-code` for a code screen).
6. Render the committed preview: `python tools/render_preview.py my-screen`.
7. Validate: `python tools/validate.py my-screen`.
8. Open a PR and fill in the checklist.

## Rules

- **Tests / validation must pass.** `tools/validate.py` runs the plugin's own validator plus the
  catalog limits (file count, folder/zip/code/preview/README sizes, exact 648x480 preview, preview
  matches a fresh render).
- **Commit `preview.png`.** It must be the output of `tools/render_preview.py` (the plugin's own
  renderer), within 1% of a fresh render.
- **Bump `version`** (semver) whenever you change a screen's packaged files. A README-only or
  preview-only change needs no bump. New screens need no bump.
- **Every screen ships under MIT** (see [LICENSE](LICENSE)).

## Code screens

A code screen (`screen.py`) runs on the user's machine. Keep it to what it needs:

- Standard library and Pillow only. Finish well under 2 seconds. Return a 648x480 1-bit PNG.
- The README must have a `## What the code does` section, in plain words.
- Do nothing beyond drawing the screen. The guardrail is not a sandbox; the owner reads every line,
  and users approve the `sha256` of your `screen.py` before it runs.

## Limits

These are enforced by the validator (see `tools/catalog_lib.py` for the exact constants): at most
40 files per screen, folder <= 1 MiB, packaged zip <= 512 KiB, `screen.py` <= 64 KiB, `preview.png`
<= 200 KiB and exactly 648x480, `README.md` present and <= 20 KiB.
