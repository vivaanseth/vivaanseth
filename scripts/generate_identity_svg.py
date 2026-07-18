#!/usr/bin/env python3
"""Generate Vivaan's animated terminal-style ASCII identity SVG."""
from pathlib import Path
import html

OUT = Path(__file__).resolve().parents[1] / "vivaan-ascii.svg"
W, H = 370, 376
PAD, TITLE_H = 18, 30
BG, BG2, FRAME = "#0d1117", "#111722", "#30363d"
INK, MUTED, CYAN, VIOLET = "#c9d1d9", "#7d8590", "#22d3ee", "#a78bfa"

FONT = {
    "V": ["#...#", "#...#", "#...#", "#...#", ".#.#.", ".#.#.", "..#.."],
    "I": ["#####", "..#..", "..#..", "..#..", "..#..", "..#..", "#####"],
    "A": [".###.", "#...#", "#...#", "#####", "#...#", "#...#", "#...#"],
    "N": ["#...#", "##..#", "##..#", "#.#.#", "#..##", "#..##", "#...#"],
}
word = "VIVAAN"
rows = []
for r in range(7):
    line = "  ".join(FONT[ch][r] for ch in word)
    # Double-height for a denser terminal-print feel.
    rows.extend([line, line])

# Deterministic terminal texture around the wordmark.
texture_top = [
    ":: initializing identity vector ................. ok",
    ":: loading projects [bloom|jarvis|upright] ....... ok",
    ":: syncing robotics + ai education ............... ok",
]
texture_bottom = [
    "local-first // privacy-aware // product-minded",
]
all_lines = texture_top + [""] + rows + [""] + texture_bottom

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">',
    '<defs>',
    f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient>',
    f'<linearGradient id="ink" x1="0" y1="0" x2="1" y2="0"><stop stop-color="{CYAN}"/><stop offset=".55" stop-color="{INK}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>',
    '</defs>',
    f'<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>',
    f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="{FRAME}"/>',
    f'<line x1="0" y1="{TITLE_H}" x2="{W}" y2="{TITLE_H}" stroke="{FRAME}"/>',
]
for i, color in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD+i*16}" cy="15" r="5" fill="{color}"/>')
parts.append(f'<text x="{W/2}" y="19" text-anchor="middle" fill="{MUTED}" font-size="11">vivaan@github: ~$ ./identity.sh</text>')

y = 49
for i, line in enumerate(all_lines):
    is_art = 4 <= i < 18
    fs = 8.2 if is_art else 9.3
    fill = 'url(#ink)' if is_art else MUTED
    weight = '700' if is_art else '500'
    safe = html.escape(line)
    text_len = 326 if is_art else None
    attrs = f' textLength="{text_len}" lengthAdjust="spacing"' if text_len else ''
    delay = i * 0.085
    width = 326
    parts.append(f'<clipPath id="r{i}"><rect x="{PAD}" y="{y-10}" height="14" width="0"><animate attributeName="width" from="0" to="{width}" begin="{delay:.3f}s" dur=".24s" fill="freeze"/></rect></clipPath>')
    parts.append(f'<text xml:space="preserve" x="{PAD}" y="{y}" fill="{fill}" font-size="{fs}" font-weight="{weight}" clip-path="url(#r{i})"{attrs}>{safe}</text>')
    if line == "":
        y += 8
    else:
        y += 13 if is_art else 14

parts.extend([
    f'<line x1="0" y1="344" x2="{W}" y2="344" stroke="{FRAME}"/>',
    f'<text x="{PAD}" y="365" fill="{MUTED}" font-size="11">vivaan@github:~$ whoami <tspan fill="{INK}">Vivaan</tspan></text>',
    f'<rect x="238" y="353" width="7" height="13" fill="{CYAN}"><animate attributeName="opacity" values="1;1;0;0" keyTimes="0;.5;.51;1" dur="1s" repeatCount="indefinite"/></rect>',
    '</svg>'
])
OUT.write_text(''.join(parts), encoding='utf-8')
print(f'wrote {OUT}')
