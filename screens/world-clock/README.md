# World Clock

Three time zones side by side, each with its own label and IANA zone name. One large zone on top,
two smaller ones below, and the local time along the bottom. It also ships an idle section so the
panel shows a big clock and date while the machine is off.

## What it shows

- Active: three configurable zones (a big top zone and two below), each with time and date, plus a
  running local clock
- Idle: a large clock and the full date, rendered by the panel firmware (mono partial refresh)

## Settings

- `label1` / `tz1` -- label and IANA zone for the top clock (default `Berlin` / `Europe/Berlin`)
- `label2` / `tz2` -- second clock (default `New York` / `America/New_York`)
- `label3` / `tz3` -- third clock (default `Tokyo` / `Asia/Tokyo`)

Zone names are IANA identifiers such as `Europe/Berlin` or `Asia/Tokyo`.

## Data it needs

- `time.now` -- the current time, converted to each configured zone
- `time.tz` -- the host's local zone, used for the bottom local clock

Missing values render as `--`.

This screen is contributed under the MIT License.
