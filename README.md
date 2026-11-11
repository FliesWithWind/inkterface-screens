# inkterface-screens

Community screen catalog for the [inkterface](https://github.com/FliesWithWind/inkterface) Decky
plugin. Each screen here is a package the plugin can download and show on the e-ink panel. The
plugin fetches a signed index from GitHub Pages and lets users browse and install screens from its
Store page.

**Users:** you do not clone this repo. Install screens from the plugin's Store page inside the
inkterface plugin. This repo is where screens are contributed and reviewed.

## What a screen is

A screen is a folder with a `screen.json` that describes what to draw on the 648x480 1-bit panel.
See the plugin docs: [screen format](https://github.com/FliesWithWind/inkterface/blob/main/docs/screen-format.md)
and [screen packages](https://github.com/FliesWithWind/inkterface/blob/main/docs/screen-packages.md).

- **Declarative** screens are a `screen.json` (plus optional `assets/`). No code runs.
- **Code** screens add one `screen.py` that draws the frame. These run on the user's machine in a
  guarded process, so they get extra review (see below).

Seed screens in this repo: `gpu-focus` (declarative active), `month-calendar` (code), `world-clock`
(declarative, with an idle section).

## Make a screen

You need Python 3.14 and Pillow. Point the tools at a checkout of the plugin via the
`INKTERFACE_CORE` environment variable (the directory that contains `inkterface_core`, i.e. the
plugin's `decky/py_modules`). CI does this for you by checking out the plugin at the ref in
`INKTERFACE_REF`.

```sh
export INKTERFACE_CORE=/path/to/inkterface/decky/py_modules

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
  and makes them approve exactly that hash before it ever runs. See the plugin's
  [screen packages](https://github.com/FliesWithWind/inkterface/blob/main/docs/screen-packages.md)
  for the full security model and its limits.

## Licensing

Every screen is contributed under the **MIT License** (see [LICENSE](LICENSE)). By opening a PR you
agree your screen is released under it.

## Repository layout

```
screens/<id>/        one folder per screen (screen.json, screen.py?, assets/?, sample-data.json?, README.md, preview.png)
tools/               validate.py, render_preview.py, build_catalog.py, sign_index.py, gen_keypair.py, new_screen.py, catalog_lib.py
tests/               pytest suite (offline)
catalog.json         { "min_plugin_version", "overrides": { "<id>": "<version>" } }
INKTERFACE_REF       the plugin commit the tools validate against
```

`INKTERFACE_REF` currently pins a specific plugin commit so validation is reproducible. **The owner
should replace it with a pushed plugin tag** once one exists, so the catalog tracks a released plugin
rather than a floating commit.

## Maintainer note

Catalog key setup is documented in the plugin repo at `docs/screen-catalog.md`. The GitHub Actions
secret holding the catalog signing key is `INKTERFACE_CATALOG_KEY`. The published base URL the
plugin reads is `https://flieswithwind.github.io/inkterface-screens/` (index at `<base>index.json`,
signature at `<base>index.json.sig`).
