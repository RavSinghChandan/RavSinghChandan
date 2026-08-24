"""Regenerate assets/buckyball.svg.

A C60 truncated icosahedron: 60 vertices, 90 bonds, 12 pentagons, 20 hexagons.
The merged PRs ride on a farthest-point spread of those vertices. Rotation is
precomputed into discrete frames toggled by CSS, because GitHub strips scripts
from README markup.

Usage:  python3 tools/gen_buckyball.py
"""
import math
import os

FRAMES = 30
DURATION = 12          # seconds for a full turn
MERGE_COUNT = 25       # bump this when a PR merges
ATOM_COLOR = "#34d399"

OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "assets", "buckyball.svg")


def build_c60():
    """Return (vertices on the unit sphere, bonds) of a truncated icosahedron."""
    phi = (1 + 5 ** 0.5) / 2
    raw = []
    seeds = [[0, 1, 3 * phi], [1, 2 + phi, 2 * phi], [2, 1 + 2 * phi, phi]]
    cyc = lambda t: [[t[0], t[1], t[2]], [t[1], t[2], t[0]], [t[2], t[0], t[1]]]
    for seed in seeds:
        for p in cyc(seed):
            for sx in (1, -1):
                for sy in (1, -1):
                    for sz in (1, -1):
                        v = (p[0] * sx, p[1] * sy, p[2] * sz)
                        if not any(abs(o[0] - v[0]) < 1e-9 and abs(o[1] - v[1]) < 1e-9
                                   and abs(o[2] - v[2]) < 1e-9 for o in raw):
                            raw.append(v)
    norm = math.dist((0, 0, 0), raw[0])
    verts = [(x / norm, y / norm, z / norm) for x, y, z in raw]
    shortest = min(math.dist(verts[i], verts[j])
                   for i in range(60) for j in range(i + 1, 60))
    bonds = [(i, j) for i in range(60) for j in range(i + 1, 60)
             if math.dist(verts[i], verts[j]) < shortest * 1.12]
    assert len(verts) == 60 and len(bonds) == 90, (len(verts), len(bonds))
    return verts, bonds


def carriers(verts, k):
    """Spread k atoms over the sphere, farthest-point first."""
    chosen = [max(range(60), key=lambda i: verts[i][1])]
    while len(chosen) < k:
        best, best_d = -1, -1.0
        for i in range(60):
            if i in chosen:
                continue
            d = min(math.dist(verts[i], verts[c]) for c in chosen)
            if d > best_d:
                best_d, best = d, i
        chosen.append(best)
    return chosen


def project(verts, rot_x, rot_y, radius=250, cx=340, cy=300):
    sx, cxr = math.sin(rot_x), math.cos(rot_x)
    sy, cyr = math.sin(rot_y), math.cos(rot_y)
    out = []
    for x, y, z in verts:
        x1 = x * cyr + z * sy
        z1 = -x * sy + z * cyr
        y2 = y * cxr - z1 * sx
        z2 = y * sx + z1 * cxr
        persp = 1 / (1 - z2 * 0.28)
        out.append((cx + x1 * radius * persp, cy + y2 * radius * persp, z2))
    return out


def frame_markup(verts, bonds, carried, rot_y):
    pr = project(verts, -0.35, rot_y)
    parts = []
    # bonds, batched into depth bands so the file stays small
    bands = {}
    for i, j in sorted(bonds, key=lambda e: (pr[e[0]][2] + pr[e[1]][2]) / 2):
        depth = ((pr[i][2] + pr[j][2]) / 2 + 1) / 2
        bands.setdefault(min(4, int(depth * 5)), []).append(
            f"M{pr[i][0]:.0f} {pr[i][1]:.0f}L{pr[j][0]:.0f} {pr[j][1]:.0f}")
    for b in sorted(bands):
        alpha = round(0.10 + (b / 4) * 0.55, 2)
        width = round(0.6 + (b / 4) * 1.7, 1)
        parts.append(f'<path d="{"".join(bands[b])}" stroke="url(#bond)" '
                     f'stroke-opacity="{alpha}" stroke-width="{width}" fill="none"/>')
    # bare lattice carbons
    lattice = {}
    for idx, (x, y, z) in enumerate(pr):
        if idx in carried:
            continue
        lattice.setdefault(min(3, int(((z + 1) / 2) * 4)), []).append((x, y))
    for b in sorted(lattice):
        r = 1.6 + (b / 3) * 2.0
        op = round(0.20 + (b / 3) * 0.55, 2)
        pts = "".join(
            f"M{x:.0f} {y:.0f}m-{r:.1f} 0a{r:.1f} {r:.1f} 0 1 0 {2*r:.1f} 0"
            f"a{r:.1f} {r:.1f} 0 1 0 -{2*r:.1f} 0" for x, y in lattice[b])
        parts.append(f'<path d="{pts}" fill="#94a3b8" fill-opacity="{op}"/>')
    # the merged PRs, back to front
    for idx in sorted(carried, key=lambda i: pr[i][2]):
        x, y, z = pr[idx]
        depth = (z + 1) / 2
        r = 6.5 * (0.62 + depth * 0.55)
        op = round(0.40 + depth * 0.60, 2)
        parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r*2.6:.1f}" '
                     f'fill="{ATOM_COLOR}" fill-opacity="{op*0.16:.2f}"/>')
        parts.append(f'<circle cx="{x:.0f}" cy="{y:.0f}" r="{r:.1f}" '
                     f'fill="{ATOM_COLOR}" fill-opacity="{op}"/>')
    return "".join(parts)


def main():
    verts, bonds = build_c60()
    carried = set(carriers(verts, MERGE_COUNT))
    frames = [frame_markup(verts, bonds, carried, (f / FRAMES) * 2 * math.pi)
              for f in range(FRAMES)]

    step = 100.0 / FRAMES
    def keyframes(f):
        a, b = f * step, (f + 1) * step
        lead = "" if f == 0 else f"0%{{opacity:0}}{max(a-0.001,0):.4f}%{{opacity:0}}"
        return (f"@keyframes k{f}{{{lead}{a:.4f}%{{opacity:1}}"
                f"{b-0.001:.4f}%{{opacity:1}}{b:.4f}%{{opacity:0}}100%{{opacity:0}}}}")

    css = "".join(f"#f{f}{{opacity:0;animation:k{f} {DURATION}s infinite steps(1,end)}}"
                  for f in range(FRAMES))
    css += "".join(keyframes(f) for f in range(FRAMES))
    body = "".join(f'<g id="f{f}">{frames[f]}</g>' for f in range(FRAMES))

    label = (f"A rotating buckminsterfullerene: 60 vertices, 90 bonds, "
             f"carrying {MERGE_COUNT} merged open-source pull requests")
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="680" height="600" viewBox="0 0 680 600" role="img" aria-label="{label}">
<title>How It All Connects - {MERGE_COUNT} merged PRs on a C60 buckyball</title>
<defs>
<linearGradient id="bond" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="#818cf8"/><stop offset="0.5" stop-color="#38e8f9"/><stop offset="1" stop-color="#c084fc"/>
</linearGradient>
<style>{css}</style>
</defs>
<rect width="680" height="600" rx="18" fill="#0b1220"/>
{body}
<text x="340" y="574" text-anchor="middle" font-family="ui-sans-serif,system-ui,sans-serif" font-size="14" fill="#94a3b8">C&#8320;&#8320; &#183; {MERGE_COUNT} merged PRs &#183; 60 vertices &#183; 90 bonds &#183; 12 pentagons &#183; 20 hexagons</text>
</svg>'''
    with open(OUT, "w") as fh:
        fh.write(svg)
    print(f"wrote {OUT} ({len(svg)} bytes, {MERGE_COUNT} atoms, {FRAMES} frames)")


if __name__ == "__main__":
    main()
