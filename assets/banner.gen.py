"""Author the Flight Operations nameplate banner as pure-vector SVG.

Text is converted to outlines from the project's real faces (Saira Condensed Bold,
Martian Mono) so the banner renders identically everywhere with no font loading —
GitHub serves README images through camo, where @font-face is not reliable.
"""
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

SAIRA = ".next/static/media/bcc6c7b97aa3243e-s.p.0-bot13eqj7bq.woff2"   # Saira Condensed Bold
MONO = ".next/static/media/ee9d8ff0751135e3-s.p.12ukhzf-lem3a.woff2"    # Martian Mono

# Flight Operations palette (DESIGN.md)
ROOM, ROOM2 = "#10140f", "#191f19"
INK, INK_DIM = "#e7e9df", "#a3ac9b"
EDGE, PANEL_LO = "#444d42", "#6b7568"
AMBER, GO, PHOSPHOR = "#e8a21c", "#3fbe73", "#7ce0a8"
ENGRAVE = "#080a07"


def text_path(font_file, text, size, tracking=0.0, x=0.0, y=0.0):
    """Return (svg_path_d, advance_width). tracking is in em units."""
    f = TTFont(font_file)
    upem = f["head"].unitsPerEm
    gs, cmap, hmtx = f.getGlyphSet(), f.getBestCmap(), f["hmtx"]
    scale = size / upem
    track = tracking * size
    d, pen_x = [], 0.0
    for ch in text:
        gname = cmap.get(ord(ch))
        if gname is None:
            pen_x += size * 0.33 + track
            continue
        sink = SVGPathPen(gs)
        # flip Y (font space is y-up, SVG is y-down) and place at the baseline
        t = Transform(scale, 0, 0, -scale, x + pen_x, y)
        gs[gname].draw(TransformPen(sink, t))
        cmds = sink.getCommands()
        if cmds:
            d.append(cmds)
        pen_x += hmtx[gname][0] * scale + track
    return " ".join(d), pen_x


def lamp(x, y, w, label, lit):
    """An annunciator lamp: recessed housing, engraved legend, jewel when lit."""
    h = 30
    face = AMBER if lit else "#1c221b"
    legend = ENGRAVE if lit else "#6e7568"
    d, adv = text_path(MONO, label, 10.5, tracking=0.06, x=0, y=0)
    tx = x + (w - adv) / 2
    return f"""
  <g>
    <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{face}" stroke="{EDGE}" stroke-width="1"/>
    <rect x="{x}" y="{y}" width="{w}" height="1.5" fill="{'#f6c455' if lit else '#2a322a'}"/>
    <g transform="translate({tx - x}, {y + h / 2 + 3.6})"><path d="{d}" fill="{legend}" transform="translate({x},0)"/></g>
  </g>"""


W, H = 1200, 300
parts = []

# ── room ground, panel bevel, hairlines ────────────────────────────────────────
parts.append(f'<rect width="{W}" height="{H}" fill="{ROOM}"/>')
parts.append(f'<rect x="28" y="26" width="{W-56}" height="{H-52}" fill="{ROOM2}" stroke="{EDGE}" stroke-width="1"/>')
parts.append(f'<rect x="28" y="26" width="{W-56}" height="2" fill="#2e3529"/>')

# ── mission designation ────────────────────────────────────────────────────────
NAME_SIZE = 86
name_d, name_w = text_path(SAIRA, "MANSURBEK SATAROV", NAME_SIZE, tracking=0.005, x=72, y=128)
parts.append(f'<path d="{name_d}" fill="{ENGRAVE}" transform="translate(0,3)"/>')  # recess
parts.append(f'<path d="{name_d}" fill="{INK}"/>')

# duty line
duty = "TRUSTWORTHY AI RESEARCH   ·   ML SYSTEMS   ·   FULL-STACK ENGINEERING"
duty_d, duty_w = text_path(MONO, duty, 12.5, tracking=0.11, x=74, y=164)
parts.append(f'<path d="{duty_d}" fill="{INK_DIM}"/>')

# hairline under the duty line, stopping where the text stops
parts.append(f'<rect x="74" y="182" width="{duty_w:.0f}" height="1" fill="{EDGE}"/>')

# graduated scale — engraved metal, carries no color meaning
for i in range(0, 41):
    gx = 74 + i * (duty_w / 40)
    tall = (i % 5 == 0)
    parts.append(f'<rect x="{gx:.1f}" y="{183 if tall else 183}" width="1" height="{7 if tall else 4}" fill="#2e3529"/>')

# ── readout block, right column ────────────────────────────────────────────────
RX, RY, ROW = 884, 96, 27
readout = [("STATION", "CINCINNATI, OH"),
           ("PROGRAM", "PH.D. COMPUTER SCIENCE"),
           ("FOCUS", "TRUSTWORTHY AI")]
for i, (k, v) in enumerate(readout):
    y = RY + i * ROW
    kd, _ = text_path(MONO, k, 9.5, tracking=0.10, x=RX, y=y)
    vw = text_path(MONO, v, 9.5, tracking=0.04)[1]
    vd, _ = text_path(MONO, v, 9.5, tracking=0.04, x=1128 - vw, y=y)
    parts.append(f'<path d="{kd}" fill="{PANEL_LO}"/>')
    parts.append(f'<path d="{vd}" fill="{INK_DIM}"/>')
    parts.append(f'<rect x="{RX}" y="{y + 8}" width="{1128 - RX}" height="1" fill="#252c24"/>')

# ── annunciator lamp bank ──────────────────────────────────────────────────────
lamps = [("ALIGNMENT", True), ("RLHF", True), ("LLM SECURITY", True),
         ("AGENTIC AI", True), ("COMPUTER VISION", False), ("SYSTEMS", False)]
lx = 74
for label, lit in lamps:
    _, lw = text_path(MONO, label, 10.5, tracking=0.06)
    bw = lw + 26
    parts.append(lamp(lx, 226, bw, label, lit))
    lx += bw + 9

# GO lamp, right-aligned on the same row
_, gw = text_path(MONO, "GO", 10.5, tracking=0.06)
gbw = gw + 26
parts.append(f"""
  <g>
    <rect x="{W-74-gbw}" y="226" width="{gbw}" height="30" fill="{GO}" stroke="{EDGE}" stroke-width="1"/>
    <rect x="{W-74-gbw}" y="226" width="{gbw}" height="1.5" fill="#7fe0a5"/>
    <path d="{text_path(MONO, 'GO', 10.5, tracking=0.06, x=W-74-gbw+13, y=245.6)[0]}" fill="{ENGRAVE}"/>
  </g>""")

# rivets
for rx, ry in [(46, 44), (W - 46, 44), (46, H - 44), (W - 46, H - 44)]:
    parts.append(f'<circle cx="{rx}" cy="{ry}" r="3.5" fill="#20261f" stroke="#0a0d09" stroke-width="1"/>')
    parts.append(f'<circle cx="{rx}" cy="{ry-0.8}" r="1.4" fill="#3b4239"/>')

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Mansurbek Satarov — trustworthy AI research, ML systems, full-stack engineering">
  <title>Mansurbek Satarov — Trustworthy AI Research · ML Systems · Full-Stack Engineering</title>
{chr(10).join(parts)}
</svg>
'''

import sys, pathlib
out = pathlib.Path(sys.argv[1])
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(svg)
print(f"wrote {out}  {len(svg)/1024:.1f} kB   name_w={name_w:.0f}px  duty_w={duty_w:.0f}px  lamps_end={lx:.0f}px")
