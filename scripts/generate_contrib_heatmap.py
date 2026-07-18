#!/usr/bin/env python3
"""Generate an animated GitHub-style contribution heatmap.

Uses GitHub GraphQL when GH_PROFILE_TOKEN is present, which allows the total and
calendar to match the profile contribution graph. Falls back to a public data
source when no token is configured.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "contrib-heatmap.svg"
DATA = ROOT / "data" / "contributions.json"
USERNAME = os.environ.get("GH_PROFILE_USER", "vivaanseth")
TOKEN = os.environ.get("GH_PROFILE_TOKEN", "").strip()

CELL = 12
GAP = 3
STEP = CELL + GAP
GRID_LEFT = 74
GRID_TOP = 91
BOX_X = 14
BOX_Y = 48
FOOTER_Y = 226
SVG_HEIGHT = 266

LEVEL_NAMES = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}


def utc_today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def rolling_window() -> tuple[dt.date, dt.date]:
    end = utc_today()
    start = end - dt.timedelta(days=364)
    return start, end


def github_graphql_payload() -> dict:
    start, end = rolling_window()
    body = {
        "query": """
        query($login: String!, $from: DateTime!, $to: DateTime!) {
          user(login: $login) {
            contributionsCollection(from: $from, to: $to) {
              contributionCalendar {
                totalContributions
                weeks {
                  firstDay
                  contributionDays {
                    contributionCount
                    contributionLevel
                    date
                    weekday
                  }
                }
              }
            }
          }
        }
        """,
        "variables": {
            "login": USERNAME,
            "from": f"{start.isoformat()}T00:00:00Z",
            "to": f"{end.isoformat()}T23:59:59Z",
        },
    }

    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": "vivaan-readme-heatmap/2.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        payload = json.loads(response.read().decode("utf-8"))

    if payload.get("errors"):
        raise RuntimeError(payload["errors"])

    calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return {"source": "graphql", "calendar": calendar}


def fallback_public_payload() -> dict:
    request = urllib.request.Request(
        f"https://github-contributions-api.jogruber.de/v4/{USERNAME}?y=last",
        headers={"User-Agent": "vivaan-readme-heatmap/2.0"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = json.loads(response.read().decode("utf-8"))

    start, end = rolling_window()
    public_days = {
        item["date"]: item
        for item in raw.get("contributions", [])
        if start <= dt.date.fromisoformat(item["date"]) <= end
    }

    # Create the same Sunday-column structure GitHub uses.
    first_sunday = start - dt.timedelta(days=(start.weekday() + 1) % 7)
    last_saturday = end + dt.timedelta(days=(5 - end.weekday()) % 7 + 1)

    weeks = []
    week_start = first_sunday
    while week_start <= last_saturday:
        contribution_days = []
        for weekday in range(7):
            date = week_start + dt.timedelta(days=weekday)
            item = public_days.get(date.isoformat())
            if item is None:
                count = 0
                level = 0
            else:
                count = int(item.get("count", 0))
                raw_level = item.get("level", 0)
                level = LEVEL_NAMES.get(str(raw_level), raw_level)
                level = max(0, min(4, int(level)))

            contribution_days.append(
                {
                    "date": date.isoformat(),
                    "weekday": weekday,
                    "contributionCount": count,
                    "contributionLevel": level,
                }
            )

        weeks.append(
            {
                "firstDay": week_start.isoformat(),
                "contributionDays": contribution_days,
            }
        )
        week_start += dt.timedelta(days=7)

    return {
        "source": "fallback",
        "calendar": {
            "totalContributions": int(
                raw.get("total", {}).get(
                    "lastYear",
                    sum(
                        int(item.get("count", 0))
                        for item in public_days.values()
                    ),
                )
            ),
            "weeks": weeks,
        },
    }


def fetch_payload() -> dict:
    if TOKEN:
        try:
            return github_graphql_payload()
        except Exception as error:  # noqa: BLE001
            print(f"GraphQL fetch failed; using public fallback: {error}")

    return fallback_public_payload()


def level_index(value: object) -> int:
    if isinstance(value, int):
        return max(0, min(4, value))
    return LEVEL_NAMES.get(str(value), 0)


def month_labels(weeks: list[dict]) -> list[tuple[int, str]]:
    labels: list[tuple[int, str]] = []
    seen: set[tuple[int, int]] = set()

    for column, week in enumerate(weeks):
        days = week.get("contributionDays", [])
        for day in days:
            date = dt.date.fromisoformat(day["date"])
            key = (date.year, date.month)

            # Label the first visible month and then each month near its start.
            if not labels or (key not in seen and date.day <= 7):
                labels.append((column, date.strftime("%b")))
                seen.add(key)
                break

    return labels


def render(payload: dict) -> str:
    calendar = payload["calendar"]
    weeks = calendar["weeks"]
    total = int(calendar["totalContributions"])

    width = GRID_LEFT + len(weeks) * STEP + 28
    box_width = width - BOX_X * 2
    box_height = 201

    styles = """
:root {
  --page: #0d1117;
  --border: #30363d;
  --text: #f0f6fc;
  --muted: #8b949e;
  --l0: #161b22;
  --l1: #0e4429;
  --l2: #006d32;
  --l3: #26a641;
  --l4: #39d353;
}
@media (prefers-color-scheme: light) {
  :root {
    --page: #ffffff;
    --border: #d0d7de;
    --text: #1f2328;
    --muted: #656d76;
    --l0: #ebedf0;
    --l1: #9be9a8;
    --l2: #40c463;
    --l3: #30a14e;
    --l4: #216e39;
  }
}
@keyframes reveal {
  0% { opacity: 0; transform: scale(.35); }
  65% { opacity: 1; transform: scale(1.08); }
  100% { opacity: 1; transform: scale(1); }
}
.cell {
  opacity: 0;
  transform-box: fill-box;
  transform-origin: center;
  animation: reveal .42s cubic-bezier(.2,.8,.2,1) both;
}
.l0 { fill: var(--l0); }
.l1 { fill: var(--l1); }
.l2 { fill: var(--l2); }
.l3 { fill: var(--l3); }
.l4 { fill: var(--l4); }
@media (prefers-reduced-motion: reduce) {
  .cell { opacity: 1 !important; animation: none !important; }
}
""".strip()

    parts = [
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{SVG_HEIGHT}" viewBox="0 0 {width} {SVG_HEIGHT}" '
            'font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">'
        ),
        f"<style>{styles}</style>",
        f'<rect width="{width}" height="{SVG_HEIGHT}" fill="var(--page)"/>',
        (
            f'<text x="{BOX_X}" y="29" fill="var(--text)" '
            f'font-size="18" font-weight="600">'
            f'{total} contributions in the last year</text>'
        ),
        (
            f'<rect x="{BOX_X}" y="{BOX_Y}" width="{box_width}" '
            f'height="{box_height}" rx="6" fill="none" '
            f'stroke="var(--border)"/>'
        ),
    ]

    # Month labels sit above the first grid row.
    for column, label in month_labels(weeks):
        x = GRID_LEFT + column * STEP
        parts.append(
            f'<text x="{x}" y="77" fill="var(--text)" '
            f'font-size="9.5">{label}</text>'
        )

    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        y = GRID_TOP + row * STEP + 9.5
        parts.append(
            f'<text x="31" y="{y:.1f}" fill="var(--text)" '
            f'font-size="9.5">{label}</text>'
        )

    # GitHub GraphQL's weekday is aligned to the calendar rows: 0=Sunday,
    # 1=Monday, ... 6=Saturday. Use it directly so partial weeks stay aligned.
    for column, week in enumerate(weeks):
        for day in week.get("contributionDays", []):
            row = int(day.get("weekday", 0))
            if row < 0 or row > 6:
                row = dt.date.fromisoformat(day["date"]).isoweekday() % 7

            x = GRID_LEFT + column * STEP
            y = GRID_TOP + row * STEP
            level = level_index(day.get("contributionLevel", 0))
            count = int(day.get("contributionCount", 0))
            delay = column * 0.018 + row * 0.035
            plural = "" if count == 1 else "s"

            parts.append(
                (
                    f'<rect class="cell l{level}" x="{x}" y="{y}" '
                    f'width="{CELL}" height="{CELL}" rx="2" '
                    f'style="animation-delay:{delay:.3f}s">'
                    f'<title>{day["date"]}: {count} contribution{plural}</title>'
                    '</rect>'
                )
            )

    # Footer is entirely below the seven grid rows.
    parts.append(
        f'<text x="31" y="{FOOTER_Y}" fill="var(--muted)" '
        f'font-size="9.5">Learn how we count contributions</text>'
    )

    legend_start = width - 151
    parts.append(
        f'<text x="{legend_start}" y="{FOOTER_Y}" '
        f'fill="var(--muted)" font-size="9.5">Less</text>'
    )

    square_start = legend_start + 28
    for level in range(5):
        parts.append(
            f'<rect class="l{level}" x="{square_start + level * 15}" '
            f'y="{FOOTER_Y - 10}" width="11" height="11" rx="2"/>'
        )

    parts.append(
        f'<text x="{square_start + 79}" y="{FOOTER_Y}" '
        f'fill="var(--muted)" font-size="9.5">More</text>'
    )
    parts.append("</svg>")
    return "".join(parts)


def main() -> None:
    payload = fetch_payload()

    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    OUT.write_text(render(payload), encoding="utf-8")

    print(
        f"Wrote {OUT.name}: "
        f"{payload['calendar']['totalContributions']} contributions "
        f"(source={payload.get('source', 'unknown')})"
    )


if __name__ == "__main__":
    main()
