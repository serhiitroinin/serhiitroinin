#!/usr/bin/env python3
"""Build the profile visuals from the project data below, in the proof design language.

    python3 build.py          # writes assets/*.svg and the blocks between the markers in README.md
    python3 build.py --mock   # also writes /tmp/profile-mock-{light,dark}.png (needs gh and the proof screenshot kit)

Every visual exists twice, light and dark, and sits in a <picture>, so it follows the GitHub theme. Tokens come from
proof (https://serhiitroinin.github.io/proof): ink on cool grey paper, hairline cards, one accent per tool.
Each card is its own SVG with a transparent margin, so each one carries its own link in the README.
"""
import os, re, subprocess, sys
from xml.sax.saxutils import escape

GH = "https://github.com/serhiitroinin/"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', monospace"

# proof Native tokens, light and dark (src/styles/globals.css).
THEMES = {
    "light": dict(card="#ffffff", border="#e1e3e6", ink="#191b1c", muted="#595b5e", faint="#6a6b6e", fill="#edeff2", shadow=True),
    "dark": dict(card="#1a1b1d", border="#292b2d", ink="#eaebed", muted="#afb1b4", faint="#88898d", fill="#202123", shadow=False),
}
# Tool family: one hue per tool, at 3:1 on the card in each mode. The first six are proof's family-*.
FAMILY = {
    "butler": ("#5e6b4e", "#8a9879"),
    "easel": ("#e2482b", "#f2573a"),
    "sculpt": ("#c08200", "#ffb020"),
    "reins": ("#3d5a80", "#7594be"),
    "glu": ("#5f8f72", "#6f9f82"),
    "strap": ("#c8644a", "#d77157"),
    "dictate": ("#18807a", "#3fb8ad"),
    "mondrian-studio": ("#b0418a", "#e06fb6"),
    "gpx-forge": ("#2f6fb8", "#5fa0e8"),
    "proof": ("#5e6b4e", "#798668"),
}
DEFAULT_TOOL = ("#5e6b4e", "#798668")
GAP, RADIUS = 12, 12

# Featured cards sit on a 12 column grid of square cells. The grid is a stack of bands; every card in a band has
# the height of the band, so each band is one line of images. Bands: (rows, [(slug, columns, [lines])]).
COLS, CELL = 12, 60
BANDS = [
    (3, [("reins", 6, ["One runtime for Claude Code and Codex.", "Your app holds the reins."]),
         ("dictate", 6, ["Hold a key, speak, release.", "On-device dictation for macOS."])]),
    (2.5, [("proof", 12, ["A shadcn registry for small, local-first tools.", "Base UI, Tailwind v4, one theme in light and dark."])]),
]

# The list under the grid: (slug, description). Tools with a mark show it; the rest get an ink glyph on a 24 unit grid.
LIST = [
    ("butler", "A folder organised by an agent. You approve every move."),
    ("easel", "One whiteboard, two hands: yours and the agent's."),
    ("sculpt", "CAD with an agent. Real solids, exported to STEP and STL."),
    ("mondrian-studio", "Algorithmic atelier for Mondrian-style grids."),
    ("gpx-forge", "Running routes from place names. Built for agents."),
    ("glu", "FreeStyle Libre 3 glucose in your shell."),
    ("strap", "WHOOP recovery, strain and sleep."),
    ("cadence", "Garmin readiness, HRV and activities."),
    ("rescuetime", "Productivity pulse and focus time."),
    ("tick", "Todoist tasks, projects and labels."),
    ("pigeon", "Gmail and Fastmail, multi-account."),
    ("almanac", "Google Calendar agenda and scheduling."),
    ("dnsimple-cli", "Domains, DNS records and certificates."),
    ("hostler", "Local dev domains with nginx."),
]
GLYPHS = {
    "cadence": '<path d="M6 19v-5M12 19v-9M18 19V6"/>',
    "rescuetime": '<circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/>',
    "tick": '<path d="M5 12.5l4.5 4.5L19 7"/>',
    "pigeon": '<rect x="3.5" y="6" width="17" height="12" rx="2"/><path d="M4 7.5l8 6 8-6"/>',
    "almanac": '<rect x="4" y="5.5" width="16" height="14" rx="2"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>',
    "dnsimple-cli": '<circle cx="12" cy="12" r="8"/><path d="M4 12h16M12 4c-4.5 4.5-4.5 11.5 0 16M12 4c4.5 4.5 4.5 11.5 0 16"/>',
    "hostler": '<path d="M4 11.5L12 4.5l8 7V20H4z"/><path d="M10 20v-5h4v5"/>',
}

# Tool marks on a 32 unit grid: ink strokes, one accent part ({a}). The first six match proof's ToolMark.
STROKE = 'fill="none" stroke="{i}" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"'
MARKS = {
    "reins": f'<rect x="10" y="5.5" width="12" height="7" rx="1.5" fill="{{a}}"/><g {STROKE}><path d="M8.5 13 16 27.5 23.5 13"/><circle cx="8" cy="9" r="3.5"/><circle cx="24" cy="9" r="3.5"/></g>',
    "butler": f'<path {STROKE} d="M12.5 13 5 8.5v15l7.5-4.5M19.5 13 27 8.5v15L19.5 19"/><rect x="12" y="11" width="8" height="10" rx="2" fill="{{a}}"/>',
    "easel": f'<path {STROKE} d="M16 4.5v2M5.5 22.5h21M11.5 22.5l-2 5M20.5 22.5l2 5"/><rect x="7" y="7" width="18" height="12.5" rx="1.5" fill="{{a}}"/>',
    "sculpt": f'<path {STROKE} d="M16 4.5 26 10v12l-10 5.5L6 22V10zM6 10l6 3.3M26 10l-6 3.3M16 27.5V21"/><path fill="{{a}}" stroke="{{a}}" stroke-width="3" stroke-linejoin="round" d="M12.8 14.2h6.4L16 19.8z"/>',
    "glu": f'<path {STROKE} d="M4.5 19c3.5 0 4-8 7.5-8s4 10 7.5 10 4-6 7.5-6"/><circle cx="19.5" cy="21" r="3.6" fill="{{a}}"/>',
    "strap": f'<path {STROKE} d="M4.5 16h6l2.5-6 4.5 12 2.5-6h7.5"/><rect x="9" y="25" width="14" height="3" rx="1.5" fill="{{a}}"/>',
    "dictate": f'<path {STROKE} d="M5 13.5v5M10.5 9v14M21.5 9v14M27 13.5v5"/><rect x="13.5" y="4.5" width="5" height="23" rx="2.5" fill="{{a}}"/>',
    "mondrian-studio": f'<rect x="17.5" y="6" width="8.5" height="8" fill="{{a}}"/><g {STROKE}><rect x="4.5" y="4.5" width="23" height="23" rx="1.5"/><path d="M16 4.5v23M4.5 15.5h23M16 21.5h11.5"/></g>',
    "proof": f'<path {STROKE} d="M7 8v19"/><circle {STROKE} cx="14" cy="15" r="6.5"/><rect x="23" y="19.5" width="5.5" height="5.5" rx="0.5" fill="{{a}}"/>',
    "gpx-forge": f'<path {STROKE} stroke-dasharray="0.1 5" d="M8 25c3-6 7-2 10-7s2-8 7-10"/><circle cx="7.5" cy="25" r="3.6" fill="{{a}}"/><circle {STROKE} cx="25" cy="7.5" r="3"/>',
}


def accent(slug, mode):
    return FAMILY.get(slug, DEFAULT_TOOL)[mode == "dark"]


def mark(slug, mode, x, y, size):
    t = THEMES[mode]
    return f'<g transform="translate({x:g} {y:g}) scale({size / 32:g})">{MARKS[slug].format(i=t["ink"], a=accent(slug, mode))}</g>'


def svg_open(w, h, label):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:g}" height="{h:g}" viewBox="0 0 {w:g} {h:g}" role="img" aria-label="{escape(label)}">'


def card_svg(w, h, slug, lines, mode):
    """One card on a transparent canvas. The margin of GAP/2 on each side makes the gaps of the grid."""
    t, m = THEMES[mode], GAP / 2
    tw, th = w + GAP, h + GAP
    o = [svg_open(tw, th, slug)]
    if t["shadow"]:  # proof elev-2, kept inside the margin
        o.append('<defs><filter id="s" x="-5%" y="-5%" width="110%" height="115%"><feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-color="#191b1c" flood-opacity="0.07"/></filter></defs>')
    o.append(f'<rect x="{m + 0.5}" y="{m + 0.5}" width="{w - 1:g}" height="{h - 1:g}" rx="{RADIUS}" fill="{t["card"]}" stroke="{t["border"]}"{" filter=\"url(#s)\"" if t["shadow"] else ""}/>')
    # Wordmark: the name in mono bold, the full stop in the tool accent.
    o.append(f'<text x="{m + 24}" y="{m + 48}" font-family="{MONO}" font-size="26" font-weight="700" letter-spacing="-0.5" fill="{t["ink"]}">{escape(slug)}<tspan fill="{accent(slug, mode)}">.</tspan></text>')
    for i, l in enumerate(lines):
        o.append(f'<text x="{m + 24}" y="{m + 80 + i * 22}" font-family="{SANS}" font-size="15" fill="{t["muted"]}">{escape(l)}</text>')
    o.append(mark(slug, mode, m + w - 24 - 48, m + h - 24 - 48, 48))
    o.append("</svg>")
    return "".join(o), tw, th


def motif(x, y, w, mode, slug=None, dot=6):
    """The proof signature: a 1.5px ink line with the accent dot at its tip."""
    t, r = THEMES[mode], dot / 2
    return (f'<path d="M{x + 1:g} {y:g}H{x + w - r:g}" stroke="{t["ink"]}" stroke-width="1.5" stroke-linecap="round"/>'
            f'<circle cx="{x + w - r:g}" cy="{y:g}" r="{r:g}" fill="{accent(slug, mode) if slug else DEFAULT_TOOL[mode == "dark"]}"/>')


def header_svg(mode):
    t = THEMES[mode]
    w, h = 860, 96
    return (svg_open(w, h, "serhii troinin")
            + f'<text x="0" y="52" font-family="{MONO}" font-size="44" font-weight="700" letter-spacing="-1.5" fill="{t["ink"]}">serhii troinin<tspan fill="{DEFAULT_TOOL[mode == "dark"]}">.</tspan></text>'
            + motif(0, 84, 120, mode, dot=8)
            + "</svg>")


def icon_svg(slug, mode):
    t = THEMES[mode]
    o = [svg_open(40, 40, slug), f'<rect x="0.5" y="0.5" width="39" height="39" rx="8" fill="{t["fill"]}" stroke="{t["border"]}"/>']
    if slug in MARKS:
        o.append(mark(slug, mode, 8, 8, 24))
    else:
        o.append(f'<g transform="translate(8 8)" fill="none" stroke="{t["ink"]}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{GLYPHS[slug]}</g>')
    o.append("</svg>")
    return "".join(o)


def picture(base, attrs, alt):
    """A light and a dark image that follow the GitHub theme."""
    return (f'<picture><source media="(prefers-color-scheme: dark)" srcset="{base}-dark.svg">'
            f'<img src="{base}-light.svg" {attrs} alt="{escape(alt)}"></picture>')


def write(name, svg):
    with open(name, "w") as f:
        f.write(svg)


def replace_block(readme, key, lines):
    start, end = f"<!-- {key}:start -->", f"<!-- {key}:end -->"
    assert start in readme and end in readme, f"README.md needs the {key} markers"
    return re.sub(f"{start}.*{end}", lambda _: start + "\n" + "\n".join(lines) + "\n" + end, readme, flags=re.S)


def build():
    os.makedirs("assets", exist_ok=True)
    for f in os.listdir("assets"):
        if f.endswith(".svg"):
            os.remove(os.path.join("assets", f))
    for mode in THEMES:
        write(f"assets/header-{mode}.svg", header_svg(mode))
    cards = []
    for rows, band in BANDS:
        assert sum(c[1] for c in band) == COLS, "the columns of a band must sum to COLS"
        for slug, cols, lines in band:
            for mode in THEMES:
                svg, _, _ = card_svg(cols * CELL - GAP, rows * CELL - GAP, slug, lines, mode)
                write(f"assets/card-{slug}-{mode}.svg", svg)
            pct = int(cols / COLS * 100000) / 1000 - 0.005  # round down so a band never wraps
            cards.append(f'<a href="{GH}{slug}">{picture(f"assets/card-{slug}", f'width="{pct:.3f}%"', f"{slug}: {' '.join(lines)}")}</a>')
    items = []
    for slug, desc in LIST:
        for mode in THEMES:
            write(f"assets/icon-{slug}-{mode}.svg", icon_svg(slug, mode))
        items.append(f'<a href="{GH}{slug}">{picture(f"assets/icon-{slug}", 'width="20" height="20" align="absmiddle"', "")}</a>&nbsp; '
                     f'<a href="{GH}{slug}">{slug}</a> {escape(desc)}<br>')
    readme = open("README.md").read()
    readme = replace_block(readme, "header", [f'<a href="{GH}">{picture("assets/header", 'width="100%"', "serhii troinin.")}</a>'])
    readme = replace_block(readme, "grid", ["<p>" + "".join(cards) + "</p>", "", "### More tools", "", "<p>"] + items + ["</p>"])
    write("README.md", readme)
    return len(cards)


def mock():
    """Render README.md with GitHub's markdown API and screenshot it in both themes."""
    html = subprocess.run(["gh", "api", "markdown", "-f", "mode=gfm", "-f", f"text={open('README.md').read()}"],
                          check=True, capture_output=True, text=True).stdout
    here = os.path.abspath(".")
    for mode, bg, fg in (("light", "#ffffff", "#1f2328"), ("dark", "#0d1117", "#f0f6fc")):
        page = (f'<!doctype html><html><head><base href="file://{here}/"><style>body{{margin:0;background:{bg};color:{fg};'
                f'font:16px/1.5 {SANS}}}main{{width:880px;margin:32px auto;padding:24px;border:1px solid {"#d1d9e0" if mode == "light" else "#3d444d"};border-radius:6px}}'
                f'a{{color:{"#0969da" if mode == "light" else "#4493f8"};text-decoration:none}}img{{max-width:100%;box-sizing:content-box}}'
                f'table{{border-collapse:collapse;width:max-content}}td{{border:1px solid {"#d1d9e0" if mode == "light" else "#3d444d"};padding:6px 13px}}'
                f'code{{font:85% {MONO};padding:.2em .4em;border-radius:6px;background:{"#818b981f" if mode == "light" else "#656c7633"}}}'
                f'p{{margin:0 0 16px}}hr{{border:0;height:.25em;background:{"#d1d9e0" if mode == "light" else "#3d444d"}}}</style></head>'
                f'<body><main>{html}</main></body></html>')
        write(f"/tmp/profile-mock-{mode}.html", page)
        subprocess.run(["node", "/tmp/proof-shot/profile-shot.mjs", f"/tmp/profile-mock-{mode}.html", f"/tmp/profile-mock-{mode}.png", mode], check=True)


if __name__ == "__main__":
    n = build()
    if "--mock" in sys.argv:
        mock()
    print(f"{n} cards, {len(LIST)} icons")
