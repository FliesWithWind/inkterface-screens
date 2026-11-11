"""Month calendar code screen.

Draws a calendar grid for the month of `data["time.now"]`, with today's cell boxed. Runs in the
plugin's guarded child process: standard library + Pillow only, finishes well under 2 seconds, and
returns a 648x480 1-bit PNG.

render(canvas_size, data, settings) -> PNG bytes, exactly canvas_size, 1-bit.
`data["time.now"]` arrives as an ISO 8601 string (the host serialises its aware datetime) or as
epoch seconds; if it is missing or unparseable the screen falls back to the host's local date.
"""
import calendar
import io
from datetime import datetime, timezone

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 648, 480


def _now(data):
    v = data.get("time.now")
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        try:
            return datetime.fromtimestamp(v, timezone.utc)
        except (ValueError, OSError, OverflowError):
            pass
    if isinstance(v, str):
        try:
            return datetime.fromisoformat(v)
        except ValueError:
            pass
    return datetime.now()


def render(canvas_size, data, settings):
    w, h = canvas_size
    now = _now(data)
    year, month, today = now.year, now.month, now.day

    first_weekday = 0 if settings.get("week_starts") == "monday" else 6  # Mon or Sun
    cal = calendar.Calendar(firstweekday=first_weekday)
    weeks = cal.monthdayscalendar(year, month)  # rows of 7, 0 == padding

    img = Image.new("1", (w, h), 1)  # 1 = white
    d = ImageDraw.Draw(img)

    title_font = ImageFont.load_default(size=40)
    dow_font = ImageFont.load_default(size=18)
    day_font = ImageFont.load_default(size=30)

    # Header bar with month and year.
    d.rectangle((0, 0, w - 1, 56), fill=0)
    title = now.strftime("%B %Y")
    tb = d.textbbox((0, 0), title, font=title_font)
    d.text(((w - (tb[2] - tb[0])) // 2, (56 - (tb[3] - tb[1])) // 2 - tb[1]), title, font=title_font, fill=1)

    # Grid geometry.
    top = 64
    cols = 7
    col_w = w // cols
    left = (w - col_w * cols) // 2
    dow_h = 28
    rows = len(weeks)
    grid_top = top + dow_h
    row_h = (h - grid_top - 8) // rows

    # Day-of-week labels.
    names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    order = names[first_weekday:] + names[:first_weekday]
    for c, label in enumerate(order):
        lb = d.textbbox((0, 0), label, font=dow_font)
        x = left + c * col_w + (col_w - (lb[2] - lb[0])) // 2
        d.text((x, top), label, font=dow_font, fill=0)
    d.line((left, grid_top - 2, left + col_w * cols, grid_top - 2), fill=0, width=2)

    # Day cells.
    for r, week in enumerate(weeks):
        for c, day in enumerate(week):
            if day == 0:
                continue
            cx = left + c * col_w
            cy = grid_top + r * row_h
            if day == today:
                d.rectangle((cx + 3, cy + 3, cx + col_w - 4, cy + row_h - 4), outline=0, width=3)
            s = str(day)
            sb = d.textbbox((0, 0), s, font=day_font)
            tx = cx + (col_w - (sb[2] - sb[0])) // 2 - sb[0]
            ty = cy + (row_h - (sb[3] - sb[1])) // 2 - sb[1]
            d.text((tx, ty), s, font=day_font, fill=0)

    buf = io.BytesIO()
    img.save(buf, "PNG")
    return buf.getvalue()
