# Month Calendar

A code-tier screen that draws a calendar grid for the current month, with today's date boxed. It
is a quiet, glanceable screen for an idle machine or a second-monitor panel.

## What it shows

- The month name and year in a header bar
- A weekday row and a grid of the month's days
- A box around today's cell

## Settings

- `week_starts` -- whether the week starts on `monday` (default) or `sunday`

## Data it needs

- `time.now` -- the current time. In the guarded process this arrives as an ISO 8601 string (or
  epoch seconds); if it is missing the screen falls back to the host's local date.

## What the code does

`screen.py` reads `time.now` and parses it into a date (falling back to the local clock if it is
missing or unparseable). It uses the standard-library `calendar` module to lay the month out into
weeks, then draws, with Pillow: a filled header bar with the month and year, a weekday label row,
and one cell per day. Today's cell gets a drawn outline. The result is a 648x480 1-bit PNG. It
reads nothing else, writes no files, opens no network connections, and starts no processes -- just
`time.now`, `calendar`, and Pillow drawing. The owner reads every line before approving it.

This screen is contributed under the MIT License.
