#!/usr/bin/env python3
"""Generate Vivaan's animated neofetch-style profile card."""
from pathlib import Path
import html

OUT = Path(__file__).resolve().parents[1] / "info-card.svg"
W, H = 480, 376
PAD, TITLE_H = 20, 30
BG, BG2, FRAME = "#0d1117", "#111722", "#30363d"
MUTED, INK = "#7d8590", "#c9d1d9"
KEY, SECTION, GREEN, CYAN, VIOLET = "#ffa657", "#58a6ff", "#3fb950", "#22d3ee", "#a78bfa"

ROWS = [
    ("host",),
    ("kv", "Role", "Student Developer + Product Builder"),
    ("kv", "Focus", "Local-first desktop apps + useful AI"),
    ("kv", "Based", "Washington, USA"),
    ("kv", "Build", "Bloom · Jarvis · Upright"),
    ("gap",),
    ("sec", "Stack"),
    ("kv", "Languages", "TypeScript, JavaScript, Python, Rust"),
    ("kv", "Desktop", "Tauri, Electron, React, Node.js"),
    ("kv", "Product", "AI integrations, privacy, UI/UX"),
    ("gap",),
    ("sec", "Highlights"),
    ("bul", "VEX IQ World Championship qualifier"),
    ("bul", "Team earned 4 awards during the season"),
    ("bul", "Google AI Professional Certificate"),
    ("bul", "Google + Anthropic AI coursework"),
]

parts = [
    f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="ui-monospace,SFMono-Regular,Menlo,Consolas,monospace">',
    '<defs>',
    f'<linearGradient id="bg" x1="0" y1="0" x2="0" y2="1"><stop stop-color="{BG2}"/><stop offset="1" stop-color="{BG}"/></linearGradient>',
    f'<linearGradient id="accent" x1="0" y1="0" x2="1" y2="0"><stop stop-color="{CYAN}"/><stop offset="1" stop-color="{VIOLET}"/></linearGradient>',
    '</defs>',
    f'<rect width="{W}" height="{H}" rx="12" fill="url(#bg)"/>',
    f'<rect x=".5" y=".5" width="{W-1}" height="{H-1}" rx="12" fill="none" stroke="{FRAME}"/>',
    f'<line x1="0" y1="{TITLE_H}" x2="{W}" y2="{TITLE_H}" stroke="{FRAME}"/>',
]
for i, color in enumerate(["#ff5f56", "#ffbd2e", "#27c93f"]):
    parts.append(f'<circle cx="{PAD+i*16}" cy="15" r="5" fill="{color}"/>')
parts.append(f'<text x="{W/2}" y="19" text-anchor="middle" fill="{MUTED}" font-size="11">vivaan@github: ~$ neofetch</text>')

key_x, val_x, y = PAD, 112, 55
line_h = 18.3
idx = 0
for row in ROWS:
    kind = row[0]
    if kind == 'gap':
        y += 7
        continue
    delay = 0.12 + idx * 0.055
    if kind == 'host':
        inner = f'<text x="{key_x}" y="{y}" font-size="13" font-weight="700"><tspan fill="{GREEN}">vivaan</tspan><tspan fill="{MUTED}">@</tspan><tspan fill="{CYAN}">github</tspan></text><line x1="132" y1="{y-4}" x2="{W-PAD}" y2="{y-4}" stroke="{FRAME}"/>'
    elif kind == 'sec':
        title = html.escape(row[1])
        inner = f'<text x="{key_x}" y="{y}" fill="{SECTION}" font-size="11.5" font-weight="700">— {title}</text><line x1="{key_x+90}" y1="{y-4}" x2="{W-PAD}" y2="{y-4}" stroke="{FRAME}"/>'
    elif kind == 'kv':
        key, value = html.escape(row[1]), html.escape(row[2])
        inner = f'<text x="{key_x}" y="{y}" fill="{KEY}" font-size="11.3" font-weight="700">{key}</text><text x="{val_x}" y="{y}" fill="{INK}" font-size="11.3">{value}</text>'
    else:
        value = html.escape(row[1])
        inner = f'<circle cx="{key_x+3}" cy="{y-4}" r="2.3" fill="url(#accent)"/><text x="{key_x+14}" y="{y}" fill="{INK}" font-size="11.3">{value}</text>'
    parts.append(f'<g opacity="0" transform="translate(0,5)">{inner}<animate attributeName="opacity" from="0" to="1" begin="{delay:.3f}s" dur=".38s" fill="freeze"/><animateTransform attributeName="transform" type="translate" from="0 5" to="0 0" begin="{delay:.3f}s" dur=".38s" fill="freeze"/></g>')
    y += line_h
    idx += 1

parts.append('</svg>')
OUT.write_text(''.join(parts), encoding='utf-8')
print(f'wrote {OUT}')
