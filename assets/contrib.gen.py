"""Isometric 3D contribution graph, in the same visual language as hero.svg.

Each day is an extruded column whose height tracks that day's contribution count.
Data comes from the GitHub GraphQL contributions calendar, so re-running this
refreshes the graph; .github/workflows/contrib.yml does that daily.

Usage:  GITHUB_TOKEN=... python3 contrib.gen.py <out-dir> [username]
"""
import json, math, os, subprocess, sys, pathlib, urllib.request

HERE = pathlib.Path(__file__).parent
USER = sys.argv[2] if len(sys.argv) > 2 else "MansurPro"

_FONTS = {
    "sg-bold.ttf": "https://fonts.gstatic.com/s/spacegrotesk/v22/V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj4PVksj.ttf",
    "sg-med.ttf": "https://fonts.gstatic.com/s/spacegrotesk/v22/V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj7aUUsj.ttf",
}
for _n, _u in _FONTS.items():
    if not (HERE / _n).exists():
        req = urllib.request.Request(_u, headers={"User-Agent": "Mozilla/5.0"})
        (HERE / _n).write_bytes(urllib.request.urlopen(req).read())

from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

BOLD, MED = str(HERE / "sg-bold.ttf"), str(HERE / "sg-med.ttf")
BG, INK, DIM, FAINT = "#080b13", "#eef3fb", "#93a3ba", "#4a5a72"
# empty → busiest; brightness ascends with activity
RAMP = ["#121a2b", "#2e4a8f", "#4c6fd8", "#7d93fb", "#b39dff"]

_fc = {}


def _f(p):
    if p not in _fc:
        t = TTFont(p)
        _fc[p] = (t.getGlyphSet(), t.getBestCmap(), t["hmtx"], t["head"].unitsPerEm)
    return _fc[p]


def tw(font, text, size, tracking=0.0):
    _, cmap, hmtx, upem = _f(font)
    s = size / upem
    return sum((hmtx[cmap[ord(c)]][0] * s if ord(c) in cmap else size * 0.32) + tracking * size for c in text)


def tp(font, text, size, x=0.0, y=0.0, tracking=0.0):
    gs, cmap, hmtx, upem = _f(font)
    s, out, pen = size / upem, [], 0.0
    for ch in text:
        gn = cmap.get(ord(ch))
        if gn is None:
            pen += size * 0.32 + tracking * size
            continue
        sink = SVGPathPen(gs)
        gs[gn].draw(TransformPen(sink, Transform(s, 0, 0, -s, x + pen, y)))
        if sink.getCommands():
            out.append(sink.getCommands())
        pen += hmtx[gn][0] * s + tracking * size
    return " ".join(out)


# ── contribution data ──────────────────────────────────────────────────────────
Q = ('{user(login:"%s"){contributionsCollection{contributionCalendar{'
     'totalContributions weeks{firstDay contributionDays{date contributionCount weekday}}}}}}') % USER
raw = subprocess.run(["gh", "api", "graphql", "-f", f"query={Q}"], capture_output=True, text=True, check=True).stdout
cal = json.loads(raw)["data"]["user"]["contributionsCollection"]["contributionCalendar"]
weeks, total = cal["weeks"], cal["totalContributions"]

counts = sorted(d["contributionCount"] for w in weeks for d in w["contributionDays"] if d["contributionCount"] > 0)
peak = counts[-1] if counts else 1
# quartile thresholds over active days only, so a few huge days don't flatten the rest
q = [counts[int(len(counts) * f)] for f in (0.25, 0.5, 0.75)] if counts else [1, 2, 3]


def level(c):
    if c == 0:
        return 0
    return 1 + sum(c > t for t in q)


# ── geometry ───────────────────────────────────────────────────────────────────
# Dimetric rather than true 30° isometric: a 53×7 field in full isometric is a long
# thin diagonal that leaves most of the canvas empty. Shallowing the week axis turns
# it into a wide banner while keeping real 3D volume.
UX, UY = 1.00, 0.16              # week axis: right, slight descent
VX, VY = -0.70, 0.60             # day axis: down and left
CELL, PAD = 18.0, 2.6            # footprint and gap between columns
MAXH = 88.0                      # tallest column
NW = len(weeks)


def iso(x, y, z, ox, oy):
    return (ox + x * UX + z * VX, oy + x * UY + z * VY - y)


def column(wx, dz, h, color, ox, oy):
    s = CELL - PAD
    x, z = wx * CELL, dz * CELL
    P = lambda a, b, c: "%.1f,%.1f" % iso(a, b, c, ox, oy)
    top = f"{P(x,h,z)} {P(x+s,h,z)} {P(x+s,h,z+s)} {P(x,h,z+s)}"
    right = f"{P(x+s,0,z)} {P(x+s,h,z)} {P(x+s,h,z+s)} {P(x+s,0,z+s)}"
    front = f"{P(x,0,z+s)} {P(x,h,z+s)} {P(x+s,h,z+s)} {P(x+s,0,z+s)}"

    def sh(c, f):
        r, g, b = (int(c[i:i + 2], 16) for i in (1, 3, 5))
        return "#%02x%02x%02x" % tuple(min(255, int(v * f)) for v in (r, g, b))

    return (f'<polygon points="{front}" fill="{sh(color,0.44)}"/>'
            f'<polygon points="{right}" fill="{sh(color,0.66)}"/>'
            f'<polygon points="{top}" fill="{color}"/>')


# Field extent, derived from the projection rather than guessed, so retuning the
# axes above cannot silently push the graph off-canvas.
span_x, span_z = NW * CELL, 7 * CELL
MARGIN, HEADER = 64, 142
field_w = span_x * UX + span_z * abs(VX)
field_h = span_x * UY + span_z * VY
OX = MARGIN + span_z * abs(VX)                 # leave room for the left-leaning day axis
OY = HEADER + MAXH
W, H = int(field_w + MARGIN * 2), int(OY + field_h + 46)

p = [f'<rect width="{W}" height="{H}" fill="{BG}"/>']

# header
p.append(f'<path d="{tp(BOLD, f"{total:,} contributions", 30, 64, 66, tracking=-0.002)}" fill="{INK}"/>')
p.append(f'<path d="{tp(MED, "in the last year", 30, 64 + tw(BOLD, f"{total:,} contributions", 30, -0.002) + 12, 66)}" fill="{FAINT}"/>')
p.append(f'<path d="{tp(MED, f"{len(counts)} active days   ·   busiest day {peak}   ·   github.com/{USER}", 14, 66, 94, tracking=0.01)}" fill="{DIM}"/>')

# legend
lx = 64
p.append(f'<path d="{tp(MED, "less", 12, lx, 128, tracking=0.02)}" fill="{FAINT}"/>')
lx += tw(MED, "less", 12, 0.02) + 8
for c in RAMP:
    p.append(f'<rect x="{lx:.0f}" y="119" width="11" height="11" rx="2" fill="{c}"/>')
    lx += 15
p.append(f'<path d="{tp(MED, "more", 12, lx + 2, 128, tracking=0.02)}" fill="{FAINT}"/>')

# Month axis along the FRONT edge. Columns only ever rise, so anything below the
# front edge is guaranteed clear of the terrain — labels sat inside it otherwise.
month_marks = []
seen = set()
for wi, w in enumerate(weeks):
    m = w["firstDay"][:7]
    if m in seen or wi == 0 or wi > NW - 3:
        seen.add(m)
        continue
    seen.add(m)
    mx, my = iso(wi * CELL, 0, 7 * CELL, OX, OY)
    label = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][int(m[5:7]) - 1]
    month_marks.append(f'<path d="{tp(MED, label, 11.5, mx - 6, my + 20, tracking=0.03)}" fill="{FAINT}"/>')

# columns, painted far-to-near so nearer ones occlude correctly
cells = []
for wi, w in enumerate(weeks):
    for d in w["contributionDays"]:
        c = d["contributionCount"]
        h = 2.5 if c == 0 else 2.5 + (c / peak) ** 0.55 * MAXH
        cells.append((wi * UY + d["weekday"] * VY, wi, d["weekday"], h, RAMP[level(c)]))
for _, wi, dz, h, col in sorted(cells, key=lambda t: t[0]):
    p.append(column(wi, dz, h, col, OX, OY))
p.extend(month_marks)

svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Isometric contribution graph: {total} contributions in the last year across {len(counts)} active days, busiest day {peak}.">
  <title>{total:,} contributions in the last year</title>
{chr(10).join(p)}
</svg>
'''
out = pathlib.Path(sys.argv[1])
out.mkdir(parents=True, exist_ok=True)
(out / "contrib-3d.svg").write_text(svg)
print(f"contrib-3d.svg  {len(svg)/1024:.1f} kB  {W}x{H}  total={total} peak={peak} thresholds={q}")
