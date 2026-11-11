# GPU Focus

An active screen for GPU-bound sessions. A large arc gauge shows GPU load at a glance, with
temperature, core clock and memory clock as labelled sparklines down the right, and a VRAM /
package-power line with a usage bar along the bottom.

## What it shows

- Big GPU load gauge (0-100%)
- GPU temperature, core clock and memory clock, each as a number plus a short history sparkline
- Memory used percentage and package power, with a VRAM usage bar

## Settings

None. The screen reads system metrics directly.

## Data it needs

- `system.gpu.load`, `system.gpu.temp`, `system.gpu.clock`, `system.gpu.mem_clock`
- the matching `.history` series for temp, clock and mem_clock
- `system.mem.used_pct`, `system.power.package_w`

Missing values render as `--`, so the screen is safe on hardware that does not report every metric.

This screen is contributed under the MIT License.
