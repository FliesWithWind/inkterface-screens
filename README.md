# inkterface-screens

Community screen catalog for the inkterface Decky plugin. Each screen here is a package the plugin
can download and show on the e-ink panel. The
plugin fetches a signed index from GitHub Pages and lets users browse and install screens from its
Screen Store page.

**Users:** you do not clone this repo. Install screens from the plugin's Screen Store page inside the
inkterface plugin. This repo is where screens are contributed and reviewed.

## What a screen is

A screen is a folder with a `screen.json` that describes what to draw on the 648x480 1-bit panel.
The authoritative schema is the vendored validator (`vendor/inkterface_core/screens/schema.py`): it
lists every widget type, field and limit, and `tools/validate.py` enforces it. The panel emulator
(`python -m inkterface_core.screens.emulate`, see below) renders a screen exactly as the plugin does.

- **Declarative** screens are a `screen.json` (plus optional `assets/`). No code runs.
- **Code** screens add one `screen.py` that draws the frame. These run on the user's machine in a
  guarded process, so they get extra review (see below).

Seed screens in this repo: `gpu-focus` (declarative active), `month-calendar` (code), `world-clock`
(declarative, with an idle section).

## Make a screen

You need Python 3.14 and Pillow. The tools import the plugin's own validator and renderer, which are
**vendored** in this repo at `vendor/inkterface_core` (a pinned, byte-identical copy; see
[vendor/README.md](vendor/README.md)). Nothing else is required: no sibling plugin clone, no
`.inkterface` symlink, no network. The tests run out of the box.

Run the tests (uv pulls the dependencies; no sibling checkout needed):

```sh
uv run --python 3.14 --no-project --with pytest --with pillow==13.0.0 --with cryptography \
  pytest tests -q -p no:cacheprovider -rf
```

Developing against a live plugin checkout instead of the vendored copy? Point `INKTERFACE_CORE` at
its `decky/py_modules`; it overrides `vendor/`:

```sh
export INKTERFACE_CORE=/path/to/inkterface/decky/py_modules
```

```sh
# 1. scaffold
python tools/new_screen.py my-screen            # add --code for a code screen

# 2. edit screens/my-screen/, then preview it with the panel emulator (no hardware)
python -m inkterface_core.screens.emulate screens/my-screen --out out.png

# 3. render the committed preview with the plugin's own renderer
python tools/render_preview.py my-screen

# 4. validate against the plugin validator and the catalog's rules
python tools/validate.py my-screen

# 5. open a PR
```

Every screen needs a `README.md` and a committed `preview.png`. Code screens must also have a
`## What the code does` section in their README. Bump `version` (semver) whenever you change a
screen's packaged files.

## Review policy

- **Declarative screens** get a normal review: layout, data bindings, sensible defaults.
- **Code screens** get an extra line-by-line review by the owner. A code screen runs as the user's
  own account; the plugin runs it in a guarded child process (an empty environment, a wall-clock
  timeout and resource limits) but that is a guardrail against bugs, **not a sandbox** -- the code
  can read the user's files and use the network. The plugin shows users the `sha256` of `screen.py`
  and makes them approve exactly that hash before it ever runs. The guarded runner and its limits
  are the vendored `vendor/inkterface_core/packages/sandbox.py`.

## Licensing

Every screen is contributed under the **MIT License** (see [LICENSE](LICENSE)). By opening a PR you
agree your screen is released under it.

## Repository layout

```
screens/<id>/        one folder per screen (screen.json, screen.py?, assets/?, sample-data.json?, README.md, preview.png)
tools/               validate.py, render_preview.py, build_catalog.py, sign_index.py, gen_keypair.py, new_screen.py,
                     catalog_lib.py, sync_vendor.py, check_vendor.py
tests/               pytest suite (offline)
vendor/              pinned, byte-identical copy of the plugin's inkterface_core (validator/renderer); see vendor/README.md
catalog.json         { "min_plugin_version", "overrides": { "<id>": "<version>" } }
```

### Refreshing the vendored plugin copy

`vendor/inkterface_core` is pinned to the plugin commit in `vendor/PLUGIN_COMMIT`. To update it to a
newer plugin commit, run from a plugin checkout:

```sh
python tools/sync_vendor.py --plugin /path/to/inkterface [--commit <sha>]
python tools/check_vendor.py --plugin /path/to/inkterface   # verify it matches the pinned commit
```

Then commit `vendor/`. `tools/check_vendor.py` (no plugin repo needed) verifies the copy against
`vendor/SHA256SUMS` and runs in CI before validation, and as `tests/test_vendor.py`.

## Maintainer note

The GitHub Actions secret holding the catalog signing key is `INKTERFACE_CATALOG_KEY`. The published
base URL the plugin reads is `https://flieswithwind.github.io/inkterface-screens/` (index at
`<base>index.json`, signature at `<base>index.json.sig`).
