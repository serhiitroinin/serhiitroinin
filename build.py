#!/usr/bin/env python3
"""Build the profile visuals from the project data below.

    python3 build.py          # writes assets/*.svg and the block between the grid markers in README.md
    python3 build.py --mock   # also writes /tmp/profile-mock-{light,dark}.png (needs rsvg-convert)

The grid is a set of rounded cards on a 12 column grid. Each card is its own SVG with a transparent margin, so each one
carries its own link in the README and the same files work on light and dark pages.
"""
import os, re, subprocess, sys
from xml.sax.saxutils import escape

GH = "https://github.com/serhiitroinin/"
SANS = "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Helvetica Neue', Helvetica, Arial, sans-serif"
MONO = "'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Consolas, monospace"
INK, CREAM = "#1F1D1A", "#F4EFE4"
SAND, CLAY, SAGE, SLATE, COAL, STRAW, ROSE = "#EADFCB", "#E0957A", "#A9C0B0", "#A7B8CE", "#2A2926", "#E6CF8B", "#DDB0B0"
GAP, RADIUS = 12, 18

# Featured cards sit on a 12 column grid of square cells. The grid is a stack of bands; every card in a band has
# the height of the band, so each band is one line of images. Bands: (rows, [(slug, columns, fill, title, [lines], tag, art)]).
# The columns of a band must sum to COLS. Two bands of 3 rows give a 12 x 6 grid.
COLS, CELL = 12, 70
BANDS = [
    (3, [("dictate", 7, SAND, "dictate", ["Hold a key, speak, release.", "On-device dictation for macOS."], "Swift · macOS", "wave"),
         ("mondrian-studio", 5, CLAY, "mondrian-studio", ["Algorithmic atelier for", "Mondrian-style grids."], "TypeScript · web", "grid")]),
    (3, [("glu", 5, SAGE, "glu", ["FreeStyle Libre 3 glucose", "in your shell."], "TypeScript · CLI", "curve"),
         ("gpx-forge", 7, SLATE, "gpx-forge", ["Running routes from place", "names. Built for agents."], "TypeScript · CLI", "route")]),
]

# The list under the grid: (slug, fill, description). Glyphs are drawn on a 24 unit grid.
LIST = [
    ("strap", CLAY, "WHOOP recovery, strain and sleep."),
    ("cadence", SLATE, "Garmin readiness, HRV and activities."),
    ("rescuetime", STRAW, "Productivity pulse and focus time."),
    ("tick", SAGE, "Todoist tasks, projects and labels."),
    ("pigeon", SAND, "Gmail and Fastmail, multi-account."),
    ("almanac", ROSE, "Google Calendar agenda and scheduling."),
    ("dnsimple-cli", SLATE, "Domains, DNS records and certificates."),
    ("hostler", SAND, "Local dev domains with nginx."),
]
GLYPHS = {
    "strap": '<path d="M3 12h4l2-5 4 10 3-7 1 2h4"/>',
    "cadence": '<path d="M6 19v-5M12 19v-9M18 19V6"/>',
    "rescuetime": '<circle cx="12" cy="12" r="8"/><path d="M12 7v5l3 2"/>',
    "tick": '<path d="M5 12.5l4.5 4.5L19 7"/>',
    "pigeon": '<rect x="3.5" y="6" width="17" height="12" rx="2"/><path d="M4 7.5l8 6 8-6"/>',
    "almanac": '<rect x="4" y="5.5" width="16" height="14" rx="2"/><path d="M4 10h16M8.5 3.5v4M15.5 3.5v4"/>',
    "dnsimple-cli": '<circle cx="12" cy="12" r="8"/><path d="M4 12h16M12 4c-4.500 4.500-4.500 11.500 0 16M12 4c4.500 4.500 4.500 11.500 0 16"/>',
    "hostler": '<path d="M4 11.5L12 4.5l8 7V20H4z"/><path d="M10 20v-5h4v5"/>',
}


def art(kind, x, y, w, h, c, quiet):
    o = []
    if kind == "wave":
        hs = [4, 6, 11, 18, 13, 24, 35, 20, 29, 42, 26, 16, 31, 22, 12, 17, 8, 5, 7, 4]
        for i, bh in enumerate(hs):
            o.append(f'<rect x="{x + w - 28 - (len(hs) - i) * 10}" y="{y + h - 44 - bh / 2}" width="5" height="{bh}" rx="2.5" fill="{c if 5 < i < 13 else quiet}"/>')
    elif kind == "grid":
        bx, by, s = x + w - 94, y + h - 94, 70
        o.append(f'<rect x="{bx}" y="{by}" width="{s}" height="{s}" rx="3" fill="none" stroke="{c}" stroke-width="2.5"/>')
        o.append(f'<path d="M{bx + 44} {by}v{s}M{bx} {by + 26}h{s}M{bx + 44} {by + 48}h26M{bx + 19} {by + 26}v44" stroke="{c}" stroke-width="2.5"/>')
        o.append(f'<rect x="{bx + 45.5}" y="{by + 1.5}" width="23" height="23" fill="{c}"/><rect x="{bx + 1.5}" y="{by + 27.5}" width="16" height="41" fill="{quiet}"/>')
    elif kind == "curve":
        bx, by = x + 24, y + h - 56
        o.append(f'<rect x="{bx}" y="{by - 14}" width="{w - 48}" height="22" rx="4" fill="{quiet}" opacity="0.6"/>')
        seg = (w - 48) / 5
        o.append(f'<path d="M{bx} {by - 3}q{seg / 2:g} -18 {seg:g} 0' + f"t{seg:g} 0" * 4 + f'" fill="none" stroke="{c}" stroke-width="2.5" stroke-linecap="round"/>')
    elif kind == "route":
        bx, by = x + w - 190, y + h - 26
        o.append(f'<path d="M{bx} {by}c20 -40 45 5 70 -25s30 -45 60 -38 15 -28 30 -42" fill="none" stroke="{c}" stroke-width="2.5" stroke-dasharray="1 7" stroke-linecap="round"/>')
        o.append(f'<circle cx="{bx}" cy="{by}" r="5" fill="{c}"/><circle cx="{bx + 160}" cy="{by - 105}" r="5" fill="none" stroke="{c}" stroke-width="2.5"/>')
    return "".join(o)


def card_svg(w, h, fill, title, lines, tag, kind):
    """One card on a transparent canvas. The margin of GAP/2 on each side makes the gaps of the grid."""
    m = GAP / 2
    tw, th = w + GAP, h + GAP
    fg = INK
    o = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{tw:g}" height="{th:g}" viewBox="0 0 {tw:g} {th:g}" role="img" aria-label="{escape(title)}">',
         f'<rect x="{m}" y="{m}" width="{w:g}" height="{h}" rx="{RADIUS}" fill="{fill}"/>']
    o.append(art(kind, m, m, w, h, INK, INK + "55"))
    o.append(f'<text x="{m + 24}" y="{m + 52}" font-family="{SANS}" font-size="{40 if w > 400 else 32}" font-weight="700" fill="{fg}">{escape(title)}</text>')
    for i, l in enumerate(lines):
        o.append(f'<text x="{m + 24}" y="{m + 86 + i * 27}" font-family="{SANS}" font-size="20" fill="{fg}" opacity="0.8">{escape(l)}</text>')
    if tag:
        o.append(f'<text x="{m + 24}" y="{m + h - 22}" font-family="{MONO}" font-size="15" letter-spacing="0.8" fill="{fg}" opacity="0.55">{escape(tag.upper())}</text>')
    o.append("</svg>")
    return "".join(o), tw, th


def icon_svg(fill, glyph):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="40" height="40" viewBox="0 0 40 40"><rect width="40" height="40" rx="11" fill="{fill}"/>'
            f'<g transform="translate(8 8)" fill="none" stroke="{INK}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">{glyph}</g></svg>')


def build():
    os.makedirs("assets", exist_ok=True)
    placed, html, cards_html, y = [], [], [], 0
    total = COLS * CELL
    for rows, cards in BANDS:
        assert sum(c[1] for c in cards) == COLS, "the columns of a band must sum to COLS"
        x = 0
        for slug, cols, fill, title, lines, tag, kind in cards:
            svg, tw, th = card_svg(cols * CELL - GAP, rows * CELL - GAP, fill, title, lines, tag, kind)
            name = f"assets/card-{slug}.svg"
            open(name, "w").write(svg)
            placed.append((name, x * 860 / total, y, 860 / total))
            pct = int(cols / COLS * 100000) / 1000 - 0.005          # round down so a band never wraps
            cards_html.append(f'<a href="{GH}{slug}"><img src="{name}" width="{pct:.3f}%" alt="{escape(title)}: {escape(" ".join(lines))}"></a>')
            x += tw
        y += rows * CELL * 860 / total
    html += ["<p>" + "".join(cards_html) + "</p>", "", "### More tools", "", "<table>"]
    for i in range(0, len(LIST), 2):
        html.append("<tr>")
        for slug, fill, desc in LIST[i:i + 2]:
            open(f"assets/icon-{slug}.svg", "w").write(icon_svg(fill, GLYPHS[slug]))
            html.append(f'<td><a href="{GH}{slug}"><img src="assets/icon-{slug}.svg" width="26" height="26" align="absmiddle" alt=""></a>&nbsp; '
                        f'<a href="{GH}{slug}"><b>{slug}</b></a><br><sub>{escape(desc)}</sub></td>')
        html.append("</tr>")
    html.append("</table>")
    readme = open("README.md").read()
    start, end = "<!-- grid:start -->", "<!-- grid:end -->"
    assert start in readme and end in readme, "README.md needs the grid markers"
    open("README.md", "w").write(re.sub(f"{start}.*{end}", lambda _: start + "\n" + "\n".join(html) + "\n" + end, readme, flags=re.S))
    return placed, y


def mock(placed, grid_h):
    """A picture of the whole page, to judge the design without a push."""
    for mode, bg, fg, sub, border, link in (("light", "#FFFFFF", "#1F2328", "#59636E", "#D1D9E0", "#0969DA"), ("dark", "#0D1117", "#F0F6FC", "#9198A1", "#3D444D", "#4493F8")):
        pad, y, parts = 40, 40, []
        parts.append(f'<text x="{pad}" y="{y + 30}" font-family="{MONO}" font-size="28" font-weight="500" fill="{"#4A5A66" if mode == "light" else CREAM}">Hi, I\'m Serhii</text>')
        y += 66
        parts.append(f'<text x="{pad}" y="{y}" font-family="{SANS}" font-style="italic" font-size="16" fill="{fg}">I make the things I wished existed, with as much care as I can give them.</text>')
        y += 28
        for name, tx, ty, s in placed:
            inner = re.sub(r"^<svg[^>]*>|</svg>$", "", open(name).read())
            parts.append(f'<g transform="translate({pad + tx} {y + ty}) scale({s})">{inner}</g>')
        y += grid_h + 44
        parts.append(f'<text x="{pad}" y="{y}" font-family="{SANS}" font-size="20" font-weight="600" fill="{fg}">More tools</text>')
        y += 22
        colw, rowh, rows = 430, 62, (len(LIST) + 1) // 2
        parts.append(f'<rect x="{pad}" y="{y}" width="{colw * 2}" height="{rows * rowh}" fill="none" stroke="{border}"/><path d="M{pad + colw} {y}v{rows * rowh}" stroke="{border}"/>')
        for i, (slug, fill, desc) in enumerate(LIST):
            cx, cy = pad + (i % 2) * colw + 14, y + (i // 2) * rowh + 11
            if i % 2 == 0 and i:
                parts.append(f'<path d="M{pad} {cy - 11}h{colw * 2}" stroke="{border}"/>')
            parts.append(f'<g transform="translate({cx} {cy})">{re.sub(r"^<svg[^>]*>|</svg>$", "", icon_svg(fill, GLYPHS[slug]))}</g>')
            parts.append(f'<text x="{cx + 54}" y="{cy + 16}" font-family="{SANS}" font-size="16" font-weight="600" fill="{link}">{slug}</text>')
            parts.append(f'<text x="{cx + 54}" y="{cy + 35}" font-family="{SANS}" font-size="12" fill="{sub}">{escape(desc)}</text>')
        y += rows * rowh + 44
        parts.append(f'<text x="{pad}" y="{y}" font-family="{SANS}" font-size="16" fill="{link}">X  ·  email  ·  LinkedIn</text>')
        y += 40
        svg = f'<svg xmlns="http://www.w3.org/2000/svg" width="940" height="{y:g}" viewBox="0 0 940 {y:g}"><rect width="940" height="{y:g}" fill="{bg}"/>{"".join(parts)}</svg>'
        open(f"/tmp/profile-mock-{mode}.svg", "w").write(svg)
        subprocess.run(["rsvg-convert", "-z", "1.6", f"/tmp/profile-mock-{mode}.svg", "-o", f"/tmp/profile-mock-{mode}.png"], check=True)


if __name__ == "__main__":
    placed, grid_h = build()
    if "--mock" in sys.argv:
        mock(placed, grid_h)
    print(f"{len(placed)} cards, {len(LIST)} icons")
