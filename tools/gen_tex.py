"""Generate dithered halftone textures (self-authored, no third-party assets)."""
import numpy as np
from PIL import Image
import sys, os

OUT = sys.argv[1] if len(sys.argv) > 1 else 'out'


def field(w, h, seed, waves, zoom=1.0):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    xx = xx / w * zoom
    yy = yy / h * zoom
    f = np.zeros((h, w))
    for _ in range(waves):
        ang = rng.uniform(0, np.pi)
        k = rng.uniform(1.2, 4.0)
        ph = rng.uniform(0, 6.283)
        amp = rng.uniform(0.5, 1.0)
        f += amp * np.sin(k * (np.cos(ang) * xx + np.sin(ang) * yy) * 2 * np.pi + ph)
        # slight cross term for organic curvature
        f += 0.35 * amp * np.cos(k * 0.6 * (np.cos(ang + 1.2) * xx - np.sin(ang + 0.6) * yy) * 2 * np.pi + ph)
    f -= f.min()
    f /= max(f.max(), 1e-6)
    return f


def ribbons(w, h, seed, bands=7, spacing=4.0, waves=5, mask_fn=None,
            ink=(214, 220, 228), zoom=1.0, thickness=0.42, bg=None, alpha_scale=1.0,
            hard=0.0, gamma=1.0, dotmax=0.72):
    f = field(w, h, seed, waves, zoom)
    # sawtooth ribbons: hard edge on one side, dissolving on the other
    p = (f * bands) % 1.0
    t = np.clip(p / thickness, 0.0, 1.0) ** gamma
    w_ = (1.0 - t) ** 1.0
    if hard:
        w_ = np.where(p < 1e-9, 0.0, w_)
        w_ = np.clip(w_ - hard, 0.0, 1.0) / max(1.0 - hard, 1e-6)

    if mask_fn is not None:
        w_ = w_ * mask_fn(w, h)

    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    gx = ((xx / spacing) % 1.0 - 0.5) ** 2
    gy = ((yy / spacing) % 1.0 - 0.5) ** 2
    r2 = (gx + gy) * spacing * spacing * 4.0         # dist^2 to nearest lattice pt
    R = w_ * spacing * dotmax                         # dot radius
    dot = np.clip(1.0 - np.sqrt(r2) / np.maximum(R, 1e-6), 0.0, 1.0)
    a = np.clip(dot * 1.15, 0.0, 1.0) * alpha_scale

    if bg is None:
        img = np.zeros((h, w, 4), dtype=np.uint8)
        img[..., 0], img[..., 1], img[..., 2] = ink
        img[..., 3] = (a * 255).astype(np.uint8)
        return Image.fromarray(img, 'RGBA')
    img = np.zeros((h, w, 4), dtype=np.uint8)
    img[..., 0], img[..., 1], img[..., 2] = ink
    img[..., 3] = (a * 255).astype(np.uint8)
    base = Image.new('RGBA', (w, h), bg + (255,))
    return Image.alpha_composite(base, Image.fromarray(img, 'RGBA'))


def vfade(top=0.0, bottom=1.0):
    def m(w, h):
        y = np.linspace(0, 1, h)[:, None]
        v = np.ones((h, 1))
        v = np.clip((bottom - y) / max(bottom - top, 1e-6), 0, 1)
        return np.repeat(v, w, axis=1)
    return m


def topfade(power=1.0):
    def m(w, h):
        y = np.linspace(0, 1, h)[:, None]
        v = np.exp(-((y / 0.72) ** 2) * 1.15) * (1 - np.clip((y - 0.62) / 0.38, 0, 1) * 0.9)
        return np.repeat(v ** power, w, axis=1)
    return m


def weave(w, h, seed, spacing=4.0, ink=(214, 220, 228), alpha_scale=1.0, bg=None):
    """dissolving noise-dot field"""
    rng = np.random.default_rng(seed)
    f = field(w, h, seed + 11, 6)
    d = rng.random((h, w))
    keep = (f > 0.52).astype(np.float64)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
    gx = ((xx / spacing) % 1.0 - 0.5) ** 2
    gy = ((yy / spacing) % 1.0 - 0.5) ** 2
    R = np.sqrt(keep) * spacing * 0.8
    dot = np.clip(1.0 - np.sqrt((gx + gy) * spacing * spacing * 4.0) / np.maximum(R, 1e-6), 0, 1)
    a = np.clip(dot * 1.3, 0, 1) * alpha_scale
    img = np.zeros((h, w, 4), dtype=np.uint8)
    img[..., 0], img[..., 1], img[..., 2] = ink
    img[..., 3] = (a * 255).astype(np.uint8)
    im = Image.fromarray(img, 'RGBA')
    if bg:
        im = Image.alpha_composite(Image.new('RGBA', (w, h), bg + (255,)), im)
    return im


def save(im, name, fmt):
    p = os.path.join(OUT, name)
    im.save(p, fmt, quality=92, method=6)
    print('wrote', p, im.size)


os.makedirs(OUT, exist_ok=True)

# hero primary: broad flowing ribbons fading downward
save(ribbons(1440, 759, 7, bands=4, spacing=5, waves=4, zoom=0.5,
             mask_fn=topfade(0.85), alpha_scale=0.95, thickness=0.40, gamma=1.25,
             dotmax=0.8), 'dither-hero-01.webp', 'WEBP')
# hero secondary: finer, shifted flow
save(ribbons(1440, 630, 23, bands=6, spacing=4.5, waves=5, zoom=0.38,
             mask_fn=topfade(0.75), alpha_scale=0.8, thickness=0.34, gamma=1.2,
             dotmax=0.78), 'dither-hero-02.webp', 'WEBP')
# footer wordmark texture
save(ribbons(1440, 463, 41, bands=5, spacing=5, waves=5, zoom=0.42,
             mask_fn=topfade(0.6), alpha_scale=0.9, thickness=0.36, gamma=1.2,
             dotmax=0.8), 'dither-footer.webp', 'WEBP')
# pricing intro wash
save(ribbons(1440, 620, 59, bands=5, spacing=5.5, waves=4, zoom=0.35,
             mask_fn=topfade(0.7), alpha_scale=0.72, thickness=0.34, gamma=1.2,
             dotmax=0.78), 'dither-wash.webp', 'WEBP')
# CTA card texture (dark dots on transparent -> subtle on white card)
save(weave(566, 140, 3, spacing=4, ink=(24, 24, 27), alpha_scale=0.5), 'cta-dither.webp', 'WEBP')
# perspective grid band
band = ribbons(2350, 126, 91, bands=2, spacing=8, waves=3, zoom=0.3,
               mask_fn=lambda w, h: np.repeat(
                   (1 - np.abs(np.linspace(-1, 1, h))[:, None] ** 2.2), w, axis=1),
               alpha_scale=0.6, thickness=0.5, dotmax=0.7)
save(band, 'perspective-grid.webp', 'WEBP')
# overview atmosphere image (used as faded bg behind section)
save(ribbons(1440, 958, 113, bands=7, spacing=5, waves=6, zoom=1.0,
             mask_fn=topfade(0.55), alpha_scale=0.85, thickness=0.3, gamma=1.2,
             dotmax=0.8), 'grid-ambient.webp', 'WEBP')
print('done')
