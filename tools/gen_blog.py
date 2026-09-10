"""Procedurally generated dark editorial covers for the news cards (self-authored).

The cards render their cover through
  `.tf-blog-image-frame img { opacity:.38; filter:grayscale() contrast(.9) brightness(1.1); object-fit:cover; transform:scale(1.3) }`
so a mid-tone gradient turns into a featureless grey smear. These covers are
therefore built as *near-black plates with bright line art* — an eroded edge
band at full ink, plus a sparse dithered fill inside the shapes — which keeps
its structure after the opacity/filter/zoom treatment.
"""
from PIL import Image, ImageDraw, ImageFilter
import numpy as np, os, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else 'blog'
os.makedirs(OUT, exist_ok=True)
W, H = 1200, 600
BG = (5, 5, 6)


def mask_from_draw(fn, blur=6.0):
    m = Image.new('L', (W, H), 0)
    fn(ImageDraw.Draw(m))
    return m.filter(ImageFilter.GaussianBlur(blur))


def lattice(spacing=9.0):
    """Distance to the nearest dot centre."""
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    gx = ((xx / spacing) % 1.0 - 0.5) ** 2
    gy = ((yy / spacing) % 1.0 - 0.5) ** 2
    return np.sqrt((gx + gy) * spacing * spacing * 4.0)


def plate(mask, color, edge_ink=1.0, fill_ink=0.30, spacing=9.0,
          edge_width=26, glow=0.16):
    a = np.asarray(mask).astype(np.float32) / 255.0
    # PIL caps MinFilter at size 9, so erode in several passes
    er = mask
    for _ in range(max(1, round(edge_width / 8))):
        er = er.filter(ImageFilter.MinFilter(9))
    inner = np.asarray(er).astype(np.float32) / 255.0
    edge = np.clip(a - inner, 0, 1)                  # band just inside the outline
    dot = np.clip(1.0 - lattice(spacing) / (spacing * 0.34), 0, 1.0)  # dot stencil
    fill = inner * dot * fill_ink

    col = np.array(color, dtype=np.float32)
    img = np.zeros((H, W, 3), np.float32) + np.array(BG, np.float32)
    if glow:
        soft = np.asarray(mask.filter(ImageFilter.GaussianBlur(60))).astype(np.float32) / 255.0
        img = img + soft[..., None] * col * glow
    ink = np.clip(edge * edge_ink + fill, 0, 1)[..., None]
    img = img * (1 - ink * 0.97) + col * (ink * 0.97)
    return img


def save(arr, name):
    Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), 'RGB').save(
        os.path.join(OUT, name), quality=94)
    print('wrote', name)


# --- 1. accelerator board --------------------------------------------------
TEAL = (188, 246, 252)


def s1(d):
    d.rounded_rectangle([250, 105, 950, 495], radius=56, fill=200)
    d.rounded_rectangle([345, 190, 855, 410], radius=40, fill=255)
    d.rounded_rectangle([470, 250, 730, 350], radius=26, fill=90)
    for x in range(275, 930, 60):                       # pins
        d.rectangle([x, 66, x + 30, 105], fill=235)
        d.rectangle([x, 495, x + 30, 534], fill=235)
    for y in range(150, 460, 60):
        d.rectangle([210, y, 249, y + 30], fill=235)
        d.rectangle([951, y, 990, y + 30], fill=235)
    for i in range(4):                                  # die traces
        d.line([(400 + i * 110, 210), (400 + i * 110, 390)], fill=150, width=8)


save(plate(mask_from_draw(s1, 5), TEAL, spacing=7.6, fill_ink=0.85), 'cover-ppu.png')

# --- 2. interoperability: two interlocking systems -------------------------
VIOLET = (206, 198, 255)


def s2(d):
    d.ellipse([-150, 90, 640, 880], outline=235, width=14)
    d.ellipse([560, -290, 1350, 500], outline=235, width=14)
    d.ellipse([150, 380, 700, 930], outline=140, width=8)
    for r in range(110, 330, 44):
        d.ellipse([520 - r, 300 - r, 520 + r, 300 + r], outline=190, width=6)
    for i, y in enumerate(range(30, 590, 46)):
        d.line([(60 + i * 20, y), (1140 - i * 20, y)], fill=120, width=4)


save(plate(mask_from_draw(s2, 4), VIOLET, spacing=7.4, fill_ink=0.62), 'cover-hygon.png')

# --- 3. energy field -------------------------------------------------------
AMBER = (255, 220, 172)


def s3(d):
    d.polygon([(-40, 520), (250, 200), (560, 470), (860, 150), (1240, 470),
               (1240, 470), (-40, 520)], outline=250, width=12)
    d.polygon([(-40, 570), (300, 405), (640, 570), (980, 385), (1240, 545),
               (1240, 545), (-40, 570)], outline=170, width=8)
    for x in range(20, W, 52):
        h = 34 + int(130 * abs(np.sin(x / 210.0)))
        d.rectangle([x, 560 - h, x + 22, 560], outline=205, width=7)
    for i in range(3):                                  # rig mast
        d.line([(600, 120 + i * 26), (600, 300)], fill=220, width=7)
    d.line([(540, 170), (660, 170)], fill=220, width=7)


save(plate(mask_from_draw(s3, 4), AMBER, spacing=7.6, fill_ink=0.58), 'cover-oilfield.png')

# --- 4. spare: platform / control-plane ambience ---------------------------
BLUE = (214, 230, 255)


def s4(d):
    for i in range(24):
        x = -100 + i * 56
        d.line([(x, 600), (600, 300), (1300 - i * 30, 600)], fill=125, width=5)
    for r in range(90, 430, 50):
        d.ellipse([600 - r, 330 - r, 600 + r, 330 + r], outline=185, width=6)


save(plate(mask_from_draw(s4, 5), BLUE, spacing=8.0, fill_ink=0.55), 'cover-platform.png')
print('done')
