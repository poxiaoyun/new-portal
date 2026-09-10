"""Normalise customer logos into transparent, monochrome-friendly PNGs."""
from PIL import Image
import numpy as np, os, sys
names = ['china-mobile','nvidia','anton','cenc','swufe','swjtu','yunkong','cloudminds']
os.makedirs('logos3', exist_ok=True)
for name in names:
    im = Image.open(f'px/partner/{name}.webp')
    rgba = im.convert('RGBA')
    a = np.asarray(rgba).astype(np.float32)
    if im.mode in ('RGBA', 'LA', 'P'):
        alpha = a[..., 3]
        # if the alpha channel is essentially empty/flat, fall back to bg-diff
        if alpha.min() > 250:
            rgb = a[..., :3]
            frame = np.concatenate([rgb[0:4].reshape(-1,3), rgb[-4:].reshape(-1,3),
                                    rgb[:,0:4].reshape(-1,3), rgb[:,-4:].reshape(-1,3)])
            bg = np.median(frame, axis=0)
            alpha = np.clip((np.abs(rgb - bg).max(axis=2) - 8) * 1.7, 0, 255)
    else:
        rgb = a[..., :3]
        frame = np.concatenate([rgb[0:4].reshape(-1,3), rgb[-4:].reshape(-1,3),
                                rgb[:,0:4].reshape(-1,3), rgb[:,-4:].reshape(-1,3)])
        bg = np.median(frame, axis=0)
        alpha = np.clip((np.abs(rgb - bg).max(axis=2) - 8) * 1.7, 0, 255)
    out = np.dstack([a[..., :3], alpha]).astype(np.uint8)
    img = Image.fromarray(out, 'RGBA')
    bbox = img.getchannel('A').point(lambda v: 255 if v > 22 else 0).getbbox()
    if bbox:
        img = img.crop(bbox)
    h = 120
    img = img.resize((max(1, int(img.width * h / img.height)), h), Image.LANCZOS)
    img.save(f'logos3/{name}.png')
    print(name, img.size)
