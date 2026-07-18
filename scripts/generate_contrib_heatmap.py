#!/usr/bin/env python3
"""Fetch Vivaan's public contribution calendar and render an animated SVG."""
from pathlib import Path
import datetime as dt
import json
import sys
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "contrib-heatmap.svg"
DATA = ROOT / "data" / "contributions.json"
USERNAME = "vivaanseth"
API = f"https://github-contributions-api.jogruber.de/v4/{USERNAME}?y=last"

CELL, GAP, LEFT, TOP = 12, 3, 38, 49
STEP = CELL + GAP
COLORS = ["#161b22", "#103448", "#075985", "#0891b2", "#22d3ee"]
BG, BG2, FRAME = "#0a0e14", "#0d1420", "#30363d"
MUTED, TEXT, CYAN, VIOLET = "#7d8590", "#e6edf3", "#22d3ee", "#a78bfa"


def fetch():
    req = urllib.request.Request(API, headers={"User-Agent": "vivaan-profile-readme/1.0"})
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def render(payload):
    contributions = payload.get("contributions", [])
    total = payload.get("total", {}).get("lastYear", sum(x.get("count", 0) for x in contributions))
    if not contributions:
        raise ValueError("Contribution API returned no days")

    start = dt.date.fromisoformat(contributions[0]["date"])
    # Align to Sunday. The API normally returns a Sunday-aligned year, but this
    # keeps the renderer correct if that changes.
    lead = (start.weekday() + 1) % 7
    padded = [None] * lead + contributions
    while len(padded) % 7:
        padded.append(None)
    weeks = len(padded) // 7

    width = LEFT + weeks * STEP + 22
    height = 208
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">',
        '<style>@keyframes pop{0%{opacity:0;transform:translateY(-5px) scale(.35)}70%{opacity:1;transform:translateY(1px) scale(1.06)}100%{opacity:1;transform:none}}.c{opacity:0;transform-box:fill-box;transform-origin:center;animation:pop .46s cubic-bezier(.2,.8,.2,1) both}@media(prefers-reduced-motion:reduce){.c{opacity:1!important;animation:none!important}}</style>',
        '<defs>',
        f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient>',
        f'<linearGradient id="accent" x1="0" y1="0" x2="1" y2="0"><stop stop-color="{CYAN}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>',
        '</defs>',
        f'<rect width="{width}" height="{height}" rx="12" fill="url(#bg)"/>',
        f'<rect x=".5" y=".5" width="{width-1}" height="{height-1}" rx="12" fill="none" stroke="{FRAME}"/>',
        f'<line x1="0" y1="30" x2="{width}" y2="30" stroke="{FRAME}"/>',
    ]
    for i, color in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
        parts.append(f'<circle cx="{20+i*16}" cy="15" r="5" fill="{color}"/>')
    parts.append(f'<text x="{width/2}" y="19" text-anchor="middle" fill="{MUTED}" font-size="11">vivaan@github: ~/contributions --graph</text>')

    # Month labels at the first week containing days 1-7 of a month.
    seen = set()
    for i, day in enumerate(padded):
        if not day:
            continue
        date = dt.date.fromisoformat(day["date"])
        key = (date.year, date.month)
        week = i // 7
        if key not in seen and date.day <= 7:
            seen.add(key)
            parts.append(f'<text x="{LEFT+week*STEP}" y="43" fill="{MUTED}" font-size="9">{date.strftime("%b")}</text>')
    for name, row in [("Mon",1),("Wed",3),("Fri",5)]:
        parts.append(f'<text x="8" y="{TOP+row*STEP+10}" fill="{MUTED}" font-size="9">{name}</text>')

    for i, day in enumerate(padded):
        if not day:
            continue
        week, row = i // 7, i % 7
        x, y = LEFT + week * STEP, TOP + row * STEP
        level = max(0, min(4, int(day.get("level", 0))))
        count = int(day.get("count", 0))
        delay = week * 0.019 + row * 0.042
        plural = "s" if count != 1 else ""
        parts.append(f'<rect class="c" x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.4" fill="{COLORS[level]}" style="animation-delay:{delay:.3f}s"><title>{day["date"]}: {count} contribution{plural}</title></rect>')

    sep = 164
    parts.append(f'<line x1="0" y1="{sep}" x2="{width}" y2="{sep}" stroke="{FRAME}"/>')
    parts.append(f'<text x="20" y="188" fill="{TEXT}" font-size="12"><tspan fill="url(#accent)" font-weight="700">{int(total):,}</tspan><tspan fill="{MUTED}"> contributions in the last year</tspan></text>')
    parts.append(f'<text x="{width-20}" y="188" text-anchor="end" fill="{MUTED}" font-size="10">updated daily · public GitHub data</text>')
    parts.append('</svg>')
    return ''.join(parts)


if __name__ == '__main__':
    try:
        payload = fetch()
        DATA.parent.mkdir(parents=True, exist_ok=True)
        DATA.write_text(json.dumps(payload, indent=2), encoding='utf-8')
        OUT.write_text(render(payload), encoding='utf-8')
        print(f'wrote {OUT}')
    except Exception as exc:
        print(f'Could not refresh contribution graph: {exc}', file=sys.stderr)
        if OUT.exists():
            print('Keeping the existing SVG instead of overwriting it.', file=sys.stderr)
            sys.exit(0)
        raise
