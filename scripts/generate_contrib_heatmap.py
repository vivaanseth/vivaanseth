#!/usr/bin/env python3
"""Generate an animated GitHub-style contribution heatmap.

Preferred data source: GitHub GraphQL contributionCalendar (exact week structure,
rolling last-year window, total count, and color levels).
Fallback: existing public endpoint when a token is not configured.

To match GitHub exactly, set GH_PROFILE_TOKEN in the workflow secrets. Without
that token, the fallback may omit private/internal contributions.
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

# GitHub contribution calendar dark-theme colors.
EMPTY = "#161b22"
LEVEL_COLORS = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
BG = "#0d1117"
BORDER = "#30363d"
TEXT = "#e6edf3"
MUTED = "#8b949e"
LINK = "#58a6ff"

CELL = 15
GAP = 4
STEP = CELL + GAP
LEFT = 96
TOP = 84
HEADER_H = 28
ROW_LABEL_X = 28


def utc_today() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


def window() -> tuple[dt.date, dt.date]:
    end = utc_today()
    start = end - dt.timedelta(days=364)
    return start, end


def _github_graphql_payload() -> dict:
    start, end = window()
    query = {
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
                    color
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
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps(query).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "User-Agent": "vivaan-readme-heatmap/1.0",
            "Content-Type": "application/json",
            "Accept": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    calendar = payload["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    return {"source": "graphql", "calendar": calendar}


def _fallback_public_payload() -> dict:
    # Public-only fallback. Good for availability, but may not exactly match
    # GitHub if private contributions are enabled on the profile.
    req = urllib.request.Request(
        f"https://github-contributions-api.jogruber.de/v4/{USERNAME}?y=last",
        headers={"User-Agent": "vivaan-readme-heatmap/1.0"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        raw = json.loads(resp.read().decode("utf-8"))

    contributions = raw.get("contributions", [])
    start, end = window()
    wanted = []
    for item in contributions:
        d = dt.date.fromisoformat(item["date"])
        if start <= d <= end:
            wanted.append(item)
    wanted.sort(key=lambda x: x["date"])

    # Pad the exact rolling window.
    by_date = {item["date"]: item for item in wanted}
    days = []
    cur = start
    while cur <= end:
        item = by_date.get(cur.isoformat(), {"date": cur.isoformat(), "count": 0, "level": 0})
        level = item.get("level", 0)
        if isinstance(level, str):
            level = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}.get(level, 0)
        days.append({
            "date": item["date"],
            "weekday": dt.date.fromisoformat(item["date"]).weekday(),
            "count": int(item.get("count", 0)),
            "level": max(0, min(4, int(level))),
        })
        cur += dt.timedelta(days=1)

    # Sunday-based weeks to mirror GitHub.
    start_sunday = start - dt.timedelta(days=(start.weekday() + 1) % 7)
    end_saturday = end + dt.timedelta(days=(5 - end.weekday()) % 7 + 1)
    date_map = {d["date"]: d for d in days}
    weeks = []
    cur = start_sunday
    while cur <= end_saturday:
        week_days = []
        for i in range(7):
            day = cur + dt.timedelta(days=i)
            item = date_map.get(day.isoformat())
            if item is None:
                week_days.append({
                    "date": day.isoformat(),
                    "weekday": (day.weekday() + 1) % 7,
                    "contributionCount": 0,
                    "contributionLevel": "NONE",
                    "color": EMPTY,
                    "_placeholder": True,
                })
            else:
                week_days.append({
                    "date": item["date"],
                    "weekday": (day.weekday() + 1) % 7,
                    "contributionCount": item["count"],
                    "contributionLevel": item["level"],
                    "color": LEVEL_COLORS[item["level"]],
                })
        weeks.append({"firstDay": cur.isoformat(), "contributionDays": week_days})
        cur += dt.timedelta(days=7)

    return {
        "source": "fallback",
        "calendar": {
            "totalContributions": int(raw.get("total", {}).get("lastYear", sum(x["count"] for x in days))),
            "weeks": weeks,
        },
    }


def fetch_payload() -> dict:
    if TOKEN:
        try:
            return _github_graphql_payload()
        except Exception as exc:  # noqa: BLE001
            print(f"GraphQL fetch failed, falling back to public endpoint: {exc}")
    return _fallback_public_payload()


def level_to_index(value) -> int:
    if isinstance(value, int):
        return max(0, min(4, value))
    mapping = {
        "NONE": 0,
        "FIRST_QUARTILE": 1,
        "SECOND_QUARTILE": 2,
        "THIRD_QUARTILE": 3,
        "FOURTH_QUARTILE": 4,
    }
    return mapping.get(str(value), 0)


def month_labels(weeks: list[dict]) -> list[tuple[int, str]]:
    labels = []
    seen = set()
    # Always label the first visible month at column 0.
    first_date = dt.date.fromisoformat(weeks[0]["firstDay"])
    labels.append((0, first_date.strftime("%b")))
    seen.add((first_date.year, first_date.month))

    for idx, week in enumerate(weeks):
        for day in week["contributionDays"]:
            d = dt.date.fromisoformat(day["date"])
            key = (d.year, d.month)
            if key not in seen and d.day <= 7:
                labels.append((idx, d.strftime("%b")))
                seen.add(key)
                break
    return labels


def render(payload: dict) -> str:
    calendar = payload["calendar"]
    weeks = calendar["weeks"]
    total = int(calendar["totalContributions"])

    width = LEFT + len(weeks) * STEP + 44
    height = 286
    chart_x = 16
    chart_y = 52
    chart_w = width - 32
    chart_h = 190

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="-apple-system,BlinkMacSystemFont,Segoe UI,Helvetica,Arial,sans-serif">',
        '<style>'
        '@keyframes pop{0%{opacity:0;transform:scale(.35)}65%{opacity:1;transform:scale(1.08)}100%{opacity:1;transform:scale(1)}}'
        '.cell{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .42s cubic-bezier(.2,.8,.2,1) both}'
        '@media(prefers-reduced-motion:reduce){.cell{opacity:1!important;animation:none!important}}'
        '</style>',
        f'<rect width="{width}" height="{height}" fill="{BG}"/>',
        f'<text x="16" y="28" fill="{TEXT}" font-size="18" font-weight="600">{total} contributions in the last year</text>',
        f'<rect x="{chart_x}" y="{chart_y}" width="{chart_w}" height="{chart_h}" rx="6" fill="none" stroke="{BORDER}"/>',
    ]

    for col, label in month_labels(weeks):
        x = LEFT + col * STEP
        parts.append(f'<text x="{x}" y="88" fill="{TEXT}" font-size="9.5">{label}</text>')

    for label, row in (("Mon", 1), ("Wed", 3), ("Fri", 5)):
        y = TOP + row * STEP + 11
        parts.append(f'<text x="{ROW_LABEL_X}" y="{y}" fill="{TEXT}" font-size="9.5">{label}</text>')

    for col, week in enumerate(weeks):
        for row, day in enumerate(week["contributionDays"]):
            x = LEFT + col * STEP
            y = TOP + row * STEP
            idx = level_to_index(day.get("contributionLevel", day.get("level", 0)))
            color = day.get("color") or LEVEL_COLORS[idx]
            count = int(day.get("contributionCount", day.get("count", 0)))
            delay = col * 0.02 + row * 0.04
            parts.append(
                f'<rect class="cell" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2" fill="{color}" style="animation-delay:{delay:.3f}s"><title>{day["date"]}: {count} contribution{"" if count == 1 else "s"}</title></rect>'
            )

    bottom_y = chart_y + chart_h - 26
    parts.append(f'<text x="28" y="{bottom_y}" fill="{MUTED}" font-size="9.5">Learn how we count contributions</text>')

    legend_right = chart_x + chart_w - 28
    more_x = legend_right - 4
    less_x = more_x - 150
    parts.append(f'<text x="{less_x}" y="{bottom_y}" fill="{MUTED}" font-size="9.5">Less</text>')
    square_start = less_x + 26
    for i, color in enumerate(LEVEL_COLORS):
        parts.append(f'<rect x="{square_start + i*15}" y="{bottom_y-10}" width="11" height="11" rx="2" fill="{color}"/>')
    parts.append(f'<text x="{square_start + 5*15 + 4}" y="{bottom_y}" fill="{MUTED}" font-size="9.5">More</text>')
    parts.append('</svg>')
    return ''.join(parts)


def save_debug(payload: dict) -> None:
    DATA.parent.mkdir(parents=True, exist_ok=True)
    DATA.write_text(json.dumps(payload, indent=2), encoding='utf-8')


def main() -> None:
    payload = fetch_payload()
    save_debug(payload)
    OUT.write_text(render(payload), encoding='utf-8')
    source = payload.get('source', 'unknown')
    total = payload['calendar']['totalContributions']
    print(f'Wrote {OUT.name}: {total} contributions (source={source})')


if __name__ == '__main__':
    main()
