"""Generate pixel-style SVG icons in the reference design language (self-authored)."""
import os, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out'
os.makedirs(OUT, exist_ok=True)
U = 4.0
N = 16
GRAY = '#585858'
ON = '#ffffff'


class Grid:
    def __init__(self, n=N):
        self.n = n
        self.cells = {}

    def set(self, x, y, c):
        if 0 <= x < self.n and 0 <= y < self.n:
            self.cells[(x, y)] = c

    def rect(self, x, y, w, h, c):
        for j in range(y, y + h):
            for i in range(x, x + w):
                self.set(i, j, c)

    def border(self, x, y, w, h, c):
        for i in range(x, x + w):
            self.set(i, y, c)
            self.set(i, y + h - 1, c)
        for j in range(y, y + h):
            self.set(x, j, c)
            self.set(x + w - 1, j, c)

    def clear(self, x, y, w, h):
        for j in range(y, y + h):
            for i in range(x, x + w):
                self.cells.pop((i, j), None)

    def hollow(self, x, y, w, h, c):
        self.rect(x, y, w, h, c)
        self.clear(x + 1, y + 1, w - 2, h - 2)

    def rows(self, spec, c):
        """spec: {row: (start, end_inclusive)}"""
        for y, (a, b) in spec.items():
            for x in range(a, b + 1):
                self.set(x, y, c)

    def svg(self, size=64, bg='none'):
        out = [f'<svg width="{size}" height="{size}" viewBox="0 0 {self.n} {self.n}" '
               f'fill="none" xmlns="http://www.w3.org/2000/svg">']
        # merge horizontal runs for compact output
        for (x, y), c in sorted(self.cells.items(), key=lambda kv: (kv[0][1], kv[0][0])):
            out.append(f'<path d="M{x} {y}h1v1h-1z" fill="{c}"/>')
        out.append('</svg>')
        return '\n'.join(out)


def save(name, svg):
    p = os.path.join(OUT, name)
    open(p, 'w', encoding='utf-8').write(svg)
    print('wrote', p)


# --- 1. cloud (multi-cloud management) -------------------------------------
g = Grid()
CLOUD = {5: (6, 9), 6: (4, 11), 7: (2, 13), 8: (1, 14),
         9: (1, 14), 10: (1, 14), 11: (2, 13), 12: (4, 11)}
for y, (a, b) in CLOUD.items():
    for x in range(a, b + 1):
        g.set(x, y, GRAY)
for y in range(6, 12):
    if y not in CLOUD:
        continue
    a, b = CLOUD[y]
    for x in range(a + 1, b):
        g.cells.pop((x, y), None)
for p in [(4, 9), (7, 9), (10, 9), (6, 7), (9, 11), (12, 10)]:
    g.set(*p, ON)
save('icon-cloud.svg', g.svg())

# --- 2. chip (AI compute) --------------------------------------------------
g = Grid()
g.hollow(3, 3, 10, 10, GRAY)
g.rect(6, 6, 4, 4, ON)
for i in (5, 8, 11):
    g.rect(i, 1, 1, 2, GRAY)
    g.rect(i, 13, 1, 2, GRAY)
    g.rect(1, i, 2, 1, GRAY)
    g.rect(13, i, 2, 1, GRAY)
save('icon-chip.svg', g.svg())

# --- 3. database / asset vault --------------------------------------------
g = Grid()
for top in (2, 6, 10):
    g.rect(3, top, 10, 1, GRAY)
    g.rect(3, top + 1, 10, 1, GRAY)
    g.rect(4, top + 2, 8, 1, GRAY)
    g.rect(5, top + 2, 1, 1, ON)
save('icon-db.svg', g.svg())

# --- 4. hexagon (container cloud) -----------------------------------------
HEX = {2: (6, 9), 3: (4, 11), 4: (3, 12), 5: (2, 13), 6: (1, 14),
       7: (1, 14), 8: (1, 14), 9: (1, 14), 10: (2, 13), 11: (3, 12),
       12: (4, 11), 13: (6, 9)}
g = Grid()
for y, (a, b) in HEX.items():
    for x in range(a, b + 1):
        g.set(x, y, GRAY)
for y in range(3, 12):
    a, b = HEX[y]
    for x in range(a + 1, b):
        g.cells.pop((x, y), None)
g.rect(7, 5, 2, 2, ON)
g.rect(5, 8, 6, 1, ON)
g.rect(7, 10, 2, 1, ON)
save('icon-hex.svg', g.svg())

# --- 5. gateway (AI router) -----------------------------------------------
g = Grid()
g.rect(2, 3, 1, 11, GRAY)
g.rect(13, 3, 1, 11, GRAY)
for y in (5, 8, 11):
    g.rect(4, y, 8, 1, ON)
    g.rect(12, y - 1, 1, 1, GRAY)
    g.rect(12, y + 1, 1, 1, GRAY)
    g.rect(11, y - 1, 1, 1, GRAY)
    g.rect(11, y + 1, 1, 1, GRAY)
g.rect(3, 7, 1, 1, GRAY)
g.rect(3, 9, 1, 1, GRAY)
save('icon-gate.svg', g.svg())

# --- 6. brand mark (hub) ---------------------------------------------------
# 2026-09-11: the two bars are **top-aligned**, same convention as the nav
# lockup in §10. The short bar used to sit y 14..44 -- 8 units below the tall
# bar's top (y 6), which read as "floating in the middle" of the tall one. Its
# height (30) is unchanged; only its top moved 14 -> 6.
#
# With both marks aligned, the nav lockup is back to being an exact 0.5x scale
# of this file in bar geometry (48/30 -> 24/15, offset 0 -> 0, top 6 -> 2).
# Keep it that way: if you move a bar here, move the matching one in §10.
#
# The mark is used in three places -- favicon, the hero hub
# (`.tf-icon-hero.center img`) and the Harness band (`.tf-control-harness-mark
# img`) -- all as a square <img> with `object-fit: contain` on a square 60x60
# canvas. Nothing crops, and the tall bar still spans y 6..54, so moving the
# short bar cannot shift any layout.
mark = '''<svg width="60" height="60" viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="10" y="6" width="15" height="48" rx="7.5" fill="url(#mk-teal)"/>
<rect x="31" y="6" width="15" height="30" rx="7.5" fill="url(#mk-violet)"/>
<defs>
<linearGradient id="mk-teal" x1="10" y1="6" x2="25" y2="54" gradientUnits="userSpaceOnUse">
<stop stop-color="#7DF3F0"/><stop offset="1" stop-color="#2CC7D8"/>
</linearGradient>
<linearGradient id="mk-violet" x1="31" y1="6" x2="46" y2="36" gradientUnits="userSpaceOnUse">
<stop stop-color="#8E7BFF"/><stop offset="1" stop-color="#5A46E0"/>
</linearGradient>
</defs></svg>'''
save('icon-mark.svg', mark)

# --- 7. faq toggle (drawn as a cross; CSS rotates it 45deg into a plus) ----
g = Grid()
for i in range(11):
    g.set(3 + i, 3 + i, ON)
    g.set(3 + i, 13 - i, ON)
save('icon-plus.svg', g.svg())

# --- 8. faq bubble ---------------------------------------------------------
g = Grid()
g.hollow(2, 3, 12, 9, GRAY)
g.rect(5, 12, 2, 2, GRAY)
g.rect(3, 6, 10, 1, ON)
g.rect(3, 8, 7, 1, ON)
save('icon-faq.svg', g.svg())

# --- 9. information --------------------------------------------------------
g = Grid()
g.hollow(2, 2, 12, 12, GRAY)
g.rect(7, 4, 2, 2, ON)
g.rect(7, 7, 2, 5, ON)
save('icon-info.svg', g.svg())

# --- 10. wordmark logo (nav) ----------------------------------------------
# The mark is mono on purpose: it has to read as the same light glyph as the
# hero hub, which is assets/img/icon-mark.svg run through custom.css's
#   .tf-icon-hero.center img { filter: grayscale() contrast(1.12) brightness(1.72) }
# on #111214. So the stops below are that filter's exact output for the brand
# gradient, computed in sRGB, one channel at a time:
#   #7DF3F0 / #2CC7D8 (teal)   -> both clamp to #FFFFFF
#   #8E7BFF -> #EDEDED,  #5A46E0 -> #8A8A8A  (violet, dropped to a grey ramp)
# Baked in rather than applied as a CSS filter on the <img> so the white
# wordmark keeps its crisp antihaliasing -- brightness() runs over the whole
# element, so it would thicken every glyph edge. If the hub filter changes,
# re-derive these two stops; that is the only thing linking the two files.
# The canvas stays 150x28 even though the wordmark is 5 glyphs now (~x114 at
# 17px + .4 tracking), so the nav layout does not move.
#
# 2026-09-11: the two bars are **top-aligned**. They used to sit y 2..26 (tall
# bar) and y 6..21 (short bar) -- the short one hung 4 units lower. The user
# asked for both tops to line up, so the short bar moved 6 -> 2. Do **not**
# "fix" it back: the previous version read as the short bar floating in the
# middle of the tall one rather than as a pair of bars sharing a baseline.
#
# §6 was aligned the same day, so this lockup is again an exact 0.5x scale of
# assets/img/icon-mark.svg in bar geometry (tall 48->24, short 30->15, tops
# 6->2). The two files are meant to move together -- see §6's note.
# The short bar keeps its own height (15); only its top moved.
logo = '''<svg width="150" height="28" viewBox="0 0 150 28" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="1" y="2" width="7.6" height="24" rx="3.8" fill="#ffffff"/>
<rect x="11.4" y="2" width="7.6" height="15" rx="3.8" fill="url(#lg-mono)"/>
<text x="27" y="20.4" font-family="Geist, Inter, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif"
 font-size="17" font-weight="600" letter-spacing="0.4" fill="#ffffff">破晓石科技</text>
<defs>
<linearGradient id="lg-mono" x1="11.4" y1="2" x2="19" y2="17" gradientUnits="userSpaceOnUse">
<stop stop-color="#EDEDED"/><stop offset="1" stop-color="#8A8A8A"/></linearGradient>
</defs></svg>'''
save('logo.svg', logo)
print('done')
