"""Isometric hero + 3D keycap buttons for a GitHub profile README.

Concept: the work rendered as a physical stack — five slabs from interfaces down to
infrastructure. Real isometric projection with per-face shading; labels stay upright
and off the geometry so they read at a glance.

Type is outlined from Space Grotesk so it renders identically through GitHub's camo.
All animation is additive (float + specular sweep) — every element is fully visible
at rest, so nothing disappears if CSS animation does not run in the img context.
"""
import math, sys, pathlib
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.misc.transform import Transform

HERE = pathlib.Path(__file__).parent

# Space Grotesk (SIL OFL 1.1) is fetched on demand rather than vendored, so this repo
# does not redistribute the font binaries.
_FONTS = {
    "sg-bold.ttf": "https://fonts.gstatic.com/s/spacegrotesk/v22/V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj4PVksj.ttf",
    "sg-med.ttf": "https://fonts.gstatic.com/s/spacegrotesk/v22/V8mQoQDjQSkFtoMM3T6r8E7mF71Q-gOoraIAEj7aUUsj.ttf",
}
for _name, _url in _FONTS.items():
    if not (HERE / _name).exists():
        import urllib.request
        print(f"fetching {_name} ...")
        req = urllib.request.Request(_url, headers={"User-Agent": "Mozilla/5.0"})
        (HERE / _name).write_bytes(urllib.request.urlopen(req).read())

BOLD, MED = str(HERE / "sg-bold.ttf"), str(HERE / "sg-med.ttf")

BG = "#080b13"
INK, DIM, FAINT = "#eef3fb", "#93a3ba", "#5c6b81"
GREEN = "#34d399"

_cache = {}


def _font(p):
    if p not in _cache:
        f = TTFont(p)
        _cache[p] = (f, f.getGlyphSet(), f.getBestCmap(), f["hmtx"], f["head"].unitsPerEm)
    return _cache[p]


def tw(font, text, size, tracking=0.0):
    _, _, cmap, hmtx, upem = _font(font)
    s = size / upem
    return sum((hmtx[cmap[ord(c)]][0] * s if ord(c) in cmap else size * 0.32) + tracking * size
               for c in text)


def tp(font, text, size, x=0.0, y=0.0, tracking=0.0):
    """Outline `text` at baseline (x, y). Returns SVG path data."""
    _, gs, cmap, hmtx, upem = _font(font)
    s = size / upem
    out, pen = [], 0.0
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


# ── isometric projection ───────────────────────────────────────────────────────
COS30, SIN30 = math.cos(math.radians(30)), 0.5


def iso(x, y, z, ox, oy):
    return (ox + (x - z) * COS30, oy + (x + z) * SIN30 - y)


def shade(hex_color, factor):
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % tuple(min(255, max(0, int(c * factor))) for c in (r, g, b))


def slab(px, py, pz, w, h, d, color, ox, oy, cls):
    """Three visible faces of a box: top lit, right mid, front dark."""
    P = lambda x, y, z: "%.2f,%.2f" % iso(x, y, z, ox, oy)
    top = f"{P(px,py+h,pz)} {P(px+w,py+h,pz)} {P(px+w,py+h,pz+d)} {P(px,py+h,pz+d)}"
    right = f"{P(px+w,py,pz)} {P(px+w,py+h,pz)} {P(px+w,py+h,pz+d)} {P(px+w,py,pz+d)}"
    front = f"{P(px,py,pz+d)} {P(px,py+h,pz+d)} {P(px+w,py+h,pz+d)} {P(px+w,py,pz+d)}"
    return f"""  <g class="{cls}">
    <polygon points="{front}" fill="{shade(color,0.42)}"/>
    <polygon points="{right}" fill="{shade(color,0.62)}"/>
    <polygon points="{top}" fill="{color}"/>
    <polyline points="{P(px,py+h,pz+d)} {P(px,py+h,pz)} {P(px+w,py+h,pz)}" fill="none" stroke="{shade(color,1.35)}" stroke-width="1.1" opacity="0.9"/>
  </g>"""


# ── hero ───────────────────────────────────────────────────────────────────────
W, H = 1200, 575
LAYERS = [
    ("INTERFACES",       "React · Next.js · Three.js · Tailwind",        "#7dd3fc"),
    ("SERVICES & APIs",  "FastAPI · Django · GraphQL · Postgres",        "#60a5fa"),
    ("AGENTS & RAG",     "LangGraph · ChromaDB · tool use · retrieval",  "#818cf8"),
    ("MODELS & TRAINING","PyTorch · RLHF · influence analysis",          "#a78bfa"),
    ("SYSTEMS & INFRA",  "Docker · Kubernetes · Linux · CI/CD",          "#c084fc"),
]
SW, SD, SH = 260, 86, 18          # slab width, depth, thickness
GAP = 46                           # vertical rise between slabs
OX, OY = 152, 378                  # projection origin (y=0 ground plane)
LABEL_X = 700
TOP = (len(LAYERS) - 1) * GAP      # 3D height of the topmost slab

p = []
p.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')
p.append(f'<ellipse cx="300" cy="320" rx="520" ry="340" fill="url(#glow)"/>')

# ground grid on the y=0 plane, sized to sit just under the stack
for i in range(-2, 8):
    a, b = iso(i * 58, -7, -120, OX, OY), iso(i * 58, -7, 280, OX, OY)
    p.append(f'<line x1="{a[0]:.1f}" y1="{a[1]:.1f}" x2="{b[0]:.1f}" y2="{b[1]:.1f}" stroke="#141d33" stroke-width="1"/>')
    c, e = iso(-120, -7, i * 58, OX, OY), iso(400, -7, i * 58, OX, OY)
    p.append(f'<line x1="{c[0]:.1f}" y1="{c[1]:.1f}" x2="{e[0]:.1f}" y2="{e[1]:.1f}" stroke="#141d33" stroke-width="1"/>')

# stack: LAYERS[0] is the top layer, so height descends with index.
# Draw the lowest slab first so upper slabs paint over it.
for idx in range(len(LAYERS) - 1, -1, -1):
    name, sub, col = LAYERS[idx]
    p.append(slab(0, (len(LAYERS) - 1 - idx) * GAP, 0, SW, SH, SD, col, OX, OY, f"s{idx}"))

# leader lines + upright labels, aligned to each slab's right corner
extents = []
for idx, (name, sub, col) in enumerate(LAYERS):
    y3 = (len(LAYERS) - 1 - idx) * GAP
    bx, by = iso(SW, y3 + SH, 0, OX, OY)
    extents.append(by)
    p.append(f'<line x1="{bx+9:.1f}" y1="{by:.1f}" x2="{LABEL_X-14:.1f}" y2="{by:.1f}" stroke="{col}" stroke-width="1.2" opacity="0.6"/>')
    p.append(f'<circle cx="{bx+9:.1f}" cy="{by:.1f}" r="3" fill="{col}"/>')
    p.append(f'<path d="{tp(BOLD, name, 20, LABEL_X, by - 5, tracking=0.012)}" fill="{INK}"/>')
    p.append(f'<path d="{tp(MED, sub, 14, LABEL_X, by + 16, tracking=0.006)}" fill="{DIM}"/>')

# name block
p.append(f'<path d="{tp(BOLD, "MANSURBEK SATAROV", 54, 78, 80, tracking=-0.004)}" fill="{INK}"/>')
role = "Trustworthy AI Researcher   ·   ML Systems Engineer   ·   Full-Stack Developer"
p.append(f'<path d="{tp(MED, role, 16, 80, 110, tracking=0.014)}" fill="{DIM}"/>')

# availability pill
pill_t = "Ph.D. @ University of Cincinnati — open to research + industry"
pw = tw(MED, pill_t, 13, 0.01) + 46
PILL_Y = 126
p.append(f'<rect x="78" y="{PILL_Y}" width="{pw:.0f}" height="30" rx="15" fill="#0e1626" stroke="#1d2b45"/>')
p.append(f'<circle cx="98" cy="{PILL_Y+15}" r="4" fill="{GREEN}"><animate attributeName="opacity" values="1;0.35;1" dur="2.6s" repeatCount="indefinite"/></circle>')
p.append(f'<path d="{tp(MED, pill_t, 13, 110, PILL_Y+20, tracking=0.01)}" fill="{DIM}"/>')

# geometry guards — collisions here are invisible in code but obvious on screen
_stack_top = OY - (TOP + SH)
_stack_bot = OY + (SW + SD) * 0.5
assert _stack_top > PILL_Y + 30, f"stack overlaps the pill ({_stack_top:.0f} vs {PILL_Y+30})"
assert _stack_bot < H, f"stack runs past the canvas ({_stack_bot:.0f} vs {H})"
assert max(extents) + 22 < H, f"lowest label clipped ({max(extents)+22:.0f} vs {H})"
print(f"  stack y {_stack_top:.0f}..{_stack_bot:.0f} | pill ends {PILL_Y+30} | labels {min(extents):.0f}..{max(extents)+22:.0f}")

style = """
  <style>
    .s0,.s1,.s2,.s3,.s4 { animation: float 6s ease-in-out infinite; }
    .s1 { animation-delay: -.5s } .s2 { animation-delay: -1s }
    .s3 { animation-delay: -1.5s } .s4 { animation-delay: -2s }
    @keyframes float { 0%,100% { transform: translateY(0) } 50% { transform: translateY(-5px) } }
    @media (prefers-reduced-motion: reduce) { .s0,.s1,.s2,.s3,.s4 { animation: none } }
  </style>"""

hero = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="Mansurbek Satarov — Trustworthy AI Researcher, ML Systems Engineer, Full-Stack Developer. The stack he works across: interfaces, services and APIs, agents and RAG, models and training, systems and infrastructure.">
  <title>Mansurbek Satarov — the stack I work across</title>
  <defs>
    <radialGradient id="glow" cx="50%" cy="50%">
      <stop offset="0%" stop-color="#1b2a4a" stop-opacity="0.55"/>
      <stop offset="100%" stop-color="#080b13" stop-opacity="0"/>
    </radialGradient>
  </defs>{style}
{chr(10).join(p)}
</svg>
'''

out_dir = pathlib.Path(sys.argv[1])
out_dir.mkdir(parents=True, exist_ok=True)
(out_dir / "hero.svg").write_text(hero)
print(f"hero.svg  {len(hero)/1024:.1f} kB")


# ── 3D keycap buttons ──────────────────────────────────────────────────────────
def keycap(label, accent, fname):
    fs, pad, h, depth = 15.5, 26, 44, 5
    w = int(tw(BOLD, label, fs, 0.02) + pad * 2 + 20)
    tot_h = h + depth + 2
    body = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {tot_h}" width="{w}" height="{tot_h}" role="img" aria-label="{label}">
  <title>{label}</title>
  <defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{shade(accent,1.18)}"/><stop offset="100%" stop-color="{accent}"/>
  </linearGradient></defs>
  <rect x="0.5" y="{depth+0.5}" width="{w-1}" height="{h}" rx="9" fill="{shade(accent,0.45)}"/>
  <rect x="0.5" y="0.5" width="{w-1}" height="{h}" rx="9" fill="url(#g)"/>
  <rect x="4" y="3" width="{w-8}" height="{h/2}" rx="7" fill="#ffffff" opacity="0.13"/>
  <path d="{tp(BOLD, label, fs, pad, h/2 + fs/2 - 2.5, tracking=0.02)}" fill="{shade(accent,0.24)}"/>
  <path d="M {w-pad+2} {h/2-4.5} l 5 4.5 l -5 4.5" fill="none" stroke="{shade(accent,0.24)}" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"/>
</svg>
'''
    (out_dir / fname).write_text(body)
    return fname, w


for lbl, acc, fn in [("Website", "#7dd3fc", "btn-website.svg"),
                     ("Projects", "#818cf8", "btn-projects.svg"),
                     ("Research", "#a78bfa", "btn-research.svg"),
                     ("Contact", "#34d399", "btn-contact.svg")]:
    n, wd = keycap(lbl, acc, fn)
    print(f"  {n}  {wd}px")


# ── terminal tagline ───────────────────────────────────────────────────────────
# The text is painted statically and the cursor blink is the only animated part,
# so this still reads perfectly if SVG animation is frozen (which is exactly what
# happens to SMIL-driven "typing" SVGs inside an <img>).
def tagline(text, fname):
    fs, ph = 18.0, 46
    prompt = "~ $"
    px = 14
    pw = tw(MED, prompt, fs, 0.02)
    tx = px + pw + 14
    twid = tw(MED, text, fs, 0.005)
    w = int(tx + twid + 20 + 14)
    body = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {ph}" width="{w}" height="{ph}" role="img" aria-label="{text}">
  <title>{text}</title>
  <style>
    .cur {{ animation: blink 1.15s steps(1,end) infinite }}
    @keyframes blink {{ 0%,55% {{ opacity: 1 }} 56%,100% {{ opacity: 0.15 }} }}
    @media (prefers-reduced-motion: reduce) {{ .cur {{ animation: none }} }}
  </style>
  <rect width="{w}" height="{ph}" rx="9" fill="#0d1424" stroke="#1d2b45"/>
  <path d="{tp(MED, prompt, fs, px, ph/2 + fs*0.34, tracking=0.02)}" fill="#34d399"/>
  <path d="{tp(MED, text, fs, tx, ph/2 + fs*0.34, tracking=0.005)}" fill="{INK}"/>
  <rect class="cur" x="{tx + twid + 5:.0f}" y="{ph/2 - fs*0.44:.0f}" width="9" height="{fs*0.92:.0f}" fill="#7dd3fc"/>
</svg>
'''
    (out_dir / fname).write_text(body)
    print(f"  {fname}  {w}x{ph}")


tagline("studying how model behavior forms during training", "tagline.svg")
