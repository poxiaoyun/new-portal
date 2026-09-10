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
mark = '''<svg width="60" height="60" viewBox="0 0 60 60" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="10" y="6" width="15" height="48" rx="7.5" fill="url(#mk-teal)"/>
<rect x="31" y="14" width="15" height="30" rx="7.5" fill="url(#mk-violet)"/>
<defs>
<linearGradient id="mk-teal" x1="10" y1="6" x2="25" y2="54" gradientUnits="userSpaceOnUse">
<stop stop-color="#7DF3F0"/><stop offset="1" stop-color="#2CC7D8"/>
</linearGradient>
<linearGradient id="mk-violet" x1="31" y1="14" x2="46" y2="44" gradientUnits="userSpaceOnUse">
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
logo = '''<svg width="150" height="28" viewBox="0 0 150 28" fill="none" xmlns="http://www.w3.org/2000/svg">
<rect x="1" y="2" width="7.6" height="24" rx="3.8" fill="url(#lg-teal)"/>
<rect x="11.4" y="6" width="7.6" height="15" rx="3.8" fill="url(#lg-violet)"/>
<text x="27" y="20.4" font-family="Geist, Inter, 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif"
 font-size="17" font-weight="600" letter-spacing="0.4" fill="#ffffff">晓石云</text>
<defs>
<linearGradient id="lg-teal" x1="1" y1="2" x2="8.6" y2="26" gradientUnits="userSpaceOnUse">
<stop stop-color="#7DF3F0"/><stop offset="1" stop-color="#2CC7D8"/></linearGradient>
<linearGradient id="lg-violet" x1="11.4" y1="6" x2="19" y2="21" gradientUnits="userSpaceOnUse">
<stop stop-color="#8E7BFF"/><stop offset="1" stop-color="#5A46E0"/></linearGradient>
</defs></svg>'''
save('logo.svg', logo)
print('done')
