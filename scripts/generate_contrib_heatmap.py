#!/usr/bin/env python3
"""Render an animated GitHub-style contribution heatmap for the current calendar year."""

from __future__ import annotations

from pathlib import Path
import datetime as dt
import json
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "contrib-heatmap.svg"
DATA = ROOT / "data" / "contributions.json"

USERNAME = "vivaanseth"
YEAR = dt.date.today().year
API = f"https://github-contributions-api.jogruber.de/v4/{USERNAME}?y={YEAR}"

CELL = 12
GAP = 3
STEP = CELL + GAP
LEFT = 38
TOP = 55
TITLEBAR_H = 30

COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
BG = "#0a0e14"
BG2 = "#0d1420"
FRAME = "#30363d"
MUTED = "#8b949e"
TEXT = "#e6edf3"
GREEN = "#39d353"


def fetch_payload() -> dict:
    request = urllib.request.Request(
        API,
        headers={"User-Agent": "vivaan-profile-readme/2.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if not isinstance(payload, dict):
        raise ValueError("Contribution API returned an unexpected response")

    return payload


def all_dates_for_year(year: int) -> list[dt.date]:
    start = dt.date(year, 1, 1)
    end = dt.date(year, 12, 31)
    day_count = (end - start).days + 1
    return [start + dt.timedelta(days=i) for i in range(day_count)]


def normalize(payload: dict) -> list[dict]:
    raw = payload.get("contributions", [])
    by_date: dict[str, dict] = {}

    for item in raw:
        date_text = item.get("date")
        if not date_text:
            continue

        try:
            date = dt.date.fromisoformat(date_text)
        except ValueError:
            continue

        if date.year != YEAR:
            continue

        count = max(0, int(item.get("count", 0)))
        level = max(0, min(4, int(item.get("level", 0))))
        by_date[date_text] = {
            "date": date_text,
            "count": count,
            "level": level,
        }

    normalized: list[dict] = []
    today = dt.date.today()

    for date in all_dates_for_year(YEAR):
        item = by_date.get(date.isoformat())

        # GitHub displays future dates as empty cells.
        if date > today:
            item = None

        normalized.append(
            item
            or {
                "date": date.isoformat(),
                "count": 0,
                "level": 0,
            }
        )

    return normalized


def padded_calendar(days: list[dict]) -> list[dict | None]:
    first = dt.date(YEAR, 1, 1)
    last = dt.date(YEAR, 12, 31)

    # Sunday = row 0, matching GitHub's calendar.
    leading = (first.weekday() + 1) % 7
    trailing = 6 - ((last.weekday() + 1) % 7)

    return [None] * leading + days + [None] * trailing


def render(days: list[dict]) -> str:
    padded = padded_calendar(days)
    weeks = len(padded) // 7
    width = LEFT + weeks * STEP + 27
    height = 230
    total = sum(day["count"] for day in days)

    css = """
@keyframes pop {
  0% { opacity: 0; transform: translateY(-5px) scale(.35); }
  70% { opacity: 1; transform: translateY(1px) scale(1.06); }
  100% { opacity: 1; transform: none; }
}
.c {
  opacity: 0;
  transform-box: fill-box;
  transform-origin: center;
  animation: pop .46s cubic-bezier(.2,.8,.2,1) both;
}
@media (prefers-reduced-motion: reduce) {
  .c { opacity: 1 !important; animation: none !important; }
}
""".strip()

    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" '
            'font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">'
        ),
        f"<style>{css}</style>",
        "<defs>",
        (
            f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">'
            f'<stop stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/>'
            "</linearGradient>"
        ),
        "</defs>",
        f'<rect width="{width}" height="{height}" rx="12" fill="url(#bg)"/>',
        (
            f'<rect x=".5" y=".5" width="{width - 1}" height="{height - 1}" '
            f'rx="12" fill="none" stroke="{FRAME}"/>'
        ),
        (
            f'<line x1="0" y1="{TITLEBAR_H}" x2="{width}" y2="{TITLEBAR_H}" '
            f'stroke="{FRAME}"/>'
        ),
    ]

    for i, color in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(
            f'<circle cx="{20 + i * 16}" cy="15" r="5" fill="{color}"/>'
        )

    parts.append(
        (
            f'<text x="{width / 2}" y="19" text-anchor="middle" '
            f'fill="{MUTED}" font-size="11">'
            f"vivaan@github: ~/{YEAR}/contributions --graph"
            "</text>"
        )
    )

    # Month labels use the week containing the first day of each month.
    first = dt.date(YEAR, 1, 1)
    leading = (first.weekday() + 1) % 7

    for month in range(1, 13):
        month_start = dt.date(YEAR, month, 1)
        offset = leading + (month_start - first).days
        week = offset // 7
        x = LEFT + week * STEP
        parts.append(
            f'<text x="{x}" y="47" fill="{MUTED}" font-size="9">'
            f"{month_start.strftime('%b')}</text>"
        )

    for label, row in [("Mon", 1), ("Wed", 3), ("Fri", 5)]:
        y = TOP + row * STEP + 10
        parts.append(
            f'<text x="8" y="{y}" fill="{MUTED}" font-size="9">{label}</text>'
        )

    for index, day in enumerate(padded):
        if day is None:
            continue

        week, row = divmod(index, 7)
        x = LEFT + week * STEP
        y = TOP + row * STEP
        level = day["level"]
        count = day["count"]
        delay = week * 0.019 + row * 0.042
        plural = "" if count == 1 else "s"

        parts.append(
            (
                f'<rect class="c" x="{x}" y="{y}" width="{CELL}" '
                f'height="{CELL}" rx="2.4" fill="{COLORS[level]}" '
                f'style="animation-delay:{delay:.3f}s">'
                f'<title>{day["date"]}: {count} contribution{plural}</title>'
                "</rect>"
            )
        )

    grid_bottom = TOP + 7 * STEP
    legend_y = grid_bottom + 7
    legend_x = width - 132

    parts.append(
        f'<text x="{legend_x - 8}" y="{legend_y + 10}" '
        f'fill="{MUTED}" font-size="9" text-anchor="end">Less</text>'
    )

    for level, color in enumerate(COLORS):
        x = legend_x + level * 15
        parts.append(
            f'<rect x="{x}" y="{legend_y}" width="11" height="11" '
            f'rx="2.2" fill="{color}"/>'
        )

    parts.append(
        f'<text x="{legend_x + 79}" y="{legend_y + 10}" '
        f'fill="{MUTED}" font-size="9">More</text>'
    )

    separator_y = legend_y + 24
    parts.append(
        f'<line x1="0" y1="{separator_y}" x2="{width}" y2="{separator_y}" '
        f'stroke="{FRAME}"/>'
    )
    parts.append(
        (
            f'<text x="22" y="{separator_y + 27}" fill="{TEXT}" font-size="13">'
            f'<tspan fill="{GREEN}" font-weight="700">{total}</tspan>'
            f"<tspan> contributions in {YEAR}</tspan></text>"
        )
    )
    parts.append(
        (
            f'<text x="{width - 22}" y="{separator_y + 27}" '
            f'fill="{MUTED}" text-anchor="end" font-size="11">'
            "January 1 → December 31"
            "</text>"
        )
    )

    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    payload = fetch_payload()
    days = normalize(payload)

    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(
        json.dumps(
            {
                "username": USERNAME,
                "year": YEAR,
                "total": sum(day["count"] for day in days),
                "contributions": days,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    OUT.write_text(render(days), encoding="utf-8")
    print(
        f"Wrote {OUT.name}: "
        f"{sum(day['count'] for day in days)} contributions in {YEAR}"
    )


if __name__ == "__main__":
    main()
