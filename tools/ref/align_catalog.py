"""Align the screen in the 1983 MZ-700 catalogue photo with the 320x200 MZ-700 screen (analysis tool).

    python tools/ref/align_catalog.py [--photo input/catalog/smz72.JPG]

Needs Pillow, numpy and scipy (analysis only; the build does not use this). Writes to work/ref/:
    align.json          the fitted transform (screen x, y -> photo u, v): cubic polynomials
    rectified_x4.png    the photo resampled into screen coordinates (1280x800) with the 8x8 cell grid
    blocks.npy / .txt   photo blueness at the dot centre of each of the 80x50 mosaic blocks

Model: u = P(x, y), v = Q(x, y), full cubic polynomials (the camera and the curved CRT glass). Fitted only to
features whose screen position is certain (docs/original.md):
  - title row 0: the six '*' (columns 2-4 and 34-36; glyph 6Bh, centre x = 8*col+4, y = 3), photo u
    measured from the cyan profile above the title line;
  - the cyan line of row 1 (character 36h, screen y 8.5), photo v detected per photo column;
  - the ruler of row 23: posts and ticks at screen x 31, 71, 111, 151, 191, 231, 272 (y 187.5), photo u
    measured from the green profile; the ruler line at screen y 191, photo v detected per column;
then refined by the phase of the mosaic dot lattice (a lit dot is 3x3 pixels at 1..3 inside each 4x4 block)
and of the text cells (red / yellow glyphs leave the cell's column 7 and row 7 dark), without using any map
or label content.
"""
import argparse
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage, optimize

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

# screen x -> photo u (measured on smz72.JPG, see docs/original.md)
STARS = [(20, 1100.0), (28, 1104.0), (36, 1109.0), (276, 1253.0), (284, 1258.0), (292, 1263.0)]   # y = 3
RULER = [(31, 1110.6), (71, 1133.3), (111, 1154.8), (151, 1176.4), (191, 1199.7), (231, 1222.7),
         (272, 1248.4)]                                                                         # y = 187.5
TITLE_LINE_X = (16, 296, 8.5)
RULER_LINE_X = (31, 272, 191.0)


def photo_classes(rgb):
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    return {'blue': np.clip((b - np.maximum(r, 0.6 * g) - 40) / 100.0, 0, 1),
            'cyan': np.clip(np.minimum(g, b) - r - 30, 0, None),
            'green': np.clip(g - np.maximum(r, b) - 10, 0, None),
            'text': np.clip((r - b - 40) / 100.0, 0, 1)}          # red names and yellow times


def lowest_peak_curve(m, u0, u1, prior, halfwidth, min_peak):
    """For each photo column u in [u0, u1): the centroid of the lowest strong run of `m` within
    +-halfwidth of the straight prior line ((ua, va), (ub, vb)), so that nearby features (the map under the
    title line, the bar above the ruler) are not taken."""
    (ua, va), (ub, vb) = prior
    us, vs = [], []
    for u in range(u0, u1):
        vp = va + (vb - va) * (u - ua) / (ub - ua)
        v0, v1 = int(vp - halfwidth), int(vp + halfwidth) + 1
        col = m[v0:v1, u]
        if col.max() < min_peak:
            continue
        idx = np.nonzero(col > 0.4 * col.max())[0]
        runs = np.split(idx, np.nonzero(np.diff(idx) > 1)[0] + 1)
        run = runs[-1]
        us.append(u)
        vs.append(v0 + (run * col[run]).sum() / col[run].sum())
    return np.array(us, float), np.array(vs)


def terms(x, y):
    """Cubic monomials of normalised screen coordinates."""
    a, b = (np.asarray(x, float) - 160.0) / 160.0, (np.asarray(y, float) - 100.0) / 100.0
    return [np.ones_like(a), a, b, a * a, a * b, b * b, a ** 3, a * a * b, a * b * b, b ** 3]


def transform(p, x, y):
    t = terms(x, y)
    return sum(c * m for c, m in zip(p[:10], t)), sum(c * m for c, m in zip(p[10:], t))


def sample(img, u, v):
    return ndimage.map_coordinates(img, [v, u], order=1, mode='constant')


def hypothesis_mask(path):
    """Blue foreground pixels (320x200) of a 40x25 screen stored as the last 2000 bytes of an MZF/MZT."""
    import cgrom
    scr = open(path, 'rb').read()[128:][-2000:]
    chars, attrs = scr[:1000], scr[1000:]
    rom = cgrom.load('JP')
    m = np.zeros((200, 320))
    for i in range(1000):
        if (attrs[i] >> 4) & 7 == 1:
            cy, cx = divmod(i, 40)
            m[cy * 8:cy * 8 + 8, cx * 8:cx * 8 + 8] = np.array(cgrom.glyph(rom, chars[i], bool(attrs[i] & 0x80)))
    return m


def fit(rgb, hyp, hyp_weight=4.0, ridge=0.05, verbose=True):
    """Cubic screen->photo mapping: the certain features at the top and bottom (geometric residuals in photo
    px) plus, inside, the correlation of the photo's blue with the hypothesis screen `hyp` (320x200)."""
    cls = photo_classes(rgb)
    tu, tv = lowest_peak_curve(cls['cyan'], 1099, 1265, ((1099, 155.5), (1265, 172.5)), 4, 25)
    ru, rv = lowest_peak_curve(cls['green'], 1112, 1248, ((1112, 271.0), (1248, 288.5)), 3, 12)

    def geo_res(p):
        res = []
        x = np.array([s for s, _ in STARS], float)
        pu, _ = transform(p, x, np.full_like(x, 3.0))
        res += list(pu - np.array([u for _, u in STARS]))
        x = np.array([s for s, _ in RULER], float)
        pu, _ = transform(p, x, np.full_like(x, 187.5))
        res += list(pu - np.array([u for _, u in RULER]))
        for (x0, x1, y), cu, cv in ((TITLE_LINE_X, tu, tv), (RULER_LINE_X, ru, rv)):
            xs = np.arange(x0, x1 + 1, 4.0)
            pu, pv = transform(p, xs, np.full_like(xs, y))
            ok = (pu > cu[0]) & (pu < cu[-1])
            res += list(np.where(ok, pv - np.interp(pu, cu, cv), 0.0))
        return np.array(res)

    blue = ndimage.gaussian_filter(cls['blue'], 0.7)
    hs = ndimage.gaussian_filter(hyp, 1.0)[16:176:2, ::2]
    hs = hs - hs.mean()
    ys, xs = np.mgrid[16:176:2, 0:320:2].astype(float)

    def corr(p):
        u, v = transform(p, xs, ys)
        sv = sample(blue, u, v)
        sv = sv - sv.mean()
        return (sv * hs).sum() / np.sqrt((sv * sv).sum() * (hs * hs).sum() + 1e-9)

    nonlin = [3, 4, 5, 6, 7, 8, 9, 13, 14, 15, 16, 17, 18, 19]

    def cost(p):
        g = geo_res(p)
        return (g ** 2).mean() - hyp_weight * corr(p) + ridge * (p[nonlin] ** 2).sum()

    # start: affine least squares on the geometric features, then everything
    p0 = np.zeros(20)
    p0[0], p0[1], p0[10], p0[11], p0[12] = 1180.0, 80.0, 220.0, 9.0, 60.0
    p1 = optimize.least_squares(geo_res, p0, loss='soft_l1', f_scale=1.0).x
    for k in nonlin:
        p1[k] = 0.0
    p1 = optimize.least_squares(lambda q: np.concatenate([geo_res(q), np.sqrt(ridge) * q[nonlin]]), p1,
                                loss='soft_l1', f_scale=1.0).x
    if verbose:
        g = geo_res(p1)
        print('geometric fit: rms %.2f max %.2f photo px; hypothesis corr %.3f' % (np.sqrt((g ** 2).mean()),
                                                                                np.abs(g).max(), corr(p1)))
    best = None
    for du in (-1.0, 0.0, 1.0):
        for dv in (-1.0, 0.0, 1.0):
            q = p1.copy()
            q[0] += du
            q[10] += dv
            r = optimize.minimize(cost, q, method='Powell', options={'xtol': 1e-4, 'ftol': 1e-8, 'maxiter': 60000})
            if best is None or r.fun < best.fun:
                best = r
    p = best.x
    if verbose:
        g = geo_res(p)
        print('combined fit:  rms %.2f max %.2f photo px; hypothesis corr %.3f' % (np.sqrt((g ** 2).mean()),
                                                                                np.abs(g).max(), corr(p)))
        print('worst residuals (index, photo px):', sorted(enumerate(np.round(g, 1)), key=lambda t: -abs(t[1]))[:5])
    return p, cls


def rectify(rgb, p, x0, y0, x1, y1, s, grid=8, label=False):
    yy, xx = np.mgrid[0:(y1 - y0) * s, 0:(x1 - x0) * s].astype(float)
    u, v = transform(p, x0 + (xx + 0.5) / s - 0.5, y0 + (yy + 0.5) / s - 0.5)
    out = np.stack([sample(rgb[..., c], u, v) for c in range(3)], -1)
    img = Image.fromarray(np.clip(out, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(img)
    for cx in range(x0 - x0 % grid, x1 + 1, grid):
        d.line([((cx - x0) * s, 0), ((cx - x0) * s, img.height)], fill=(60, 60, 60) if cx % 40 else (120, 120, 0))
        if label and cx % 8 == 0:
            d.text(((cx - x0) * s + 2, img.height - 11), str(cx // 8), fill=(255, 255, 255))
    for cy in range(y0 - y0 % grid, y1 + 1, grid):
        d.line([(0, (cy - y0) * s), (img.width, (cy - y0) * s)], fill=(60, 60, 60) if cy % 40 else (120, 120, 0))
        if label and cy % 8 == 0:
            d.text((2, (cy - y0) * s + 1), str(cy // 8), fill=(255, 255, 255))
    return img


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--photo', default=os.path.join(ROOT, 'input', 'catalog', 'smz72.JPG'))
    ap.add_argument('--out', default=os.path.join(ROOT, 'work', 'ref'))
    ap.add_argument('--hyp-weight', type=float, default=40.0)
    ap.add_argument('--hyp', default=os.path.join(ROOT, 'input', 'World-Clock', 'WorldClock.mzt'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    rgb = np.asarray(Image.open(a.photo).convert('RGB')).astype(float)
    p, cls = fit(rgb, hypothesis_mask(a.hyp), hyp_weight=a.hyp_weight)
    json.dump({'model': 'cubic', 'params': p.tolist(), 'photo': os.path.relpath(a.photo, ROOT)},
              open(os.path.join(a.out, 'align.json'), 'w'), indent=1)
    rectify(rgb, p, 0, 0, 320, 200, 4).save(os.path.join(a.out, 'rectified_x4.png'))
    gx, gy = np.meshgrid(np.arange(80) * 4 + 2.0, np.arange(50) * 4 + 2.0)
    u, v = transform(p, gx, gy)
    val = sample(ndimage.gaussian_filter(cls['blue'], 0.5), u, v)
    np.save(os.path.join(a.out, 'blocks.npy'), val)
    with open(os.path.join(a.out, 'blocks.txt'), 'w') as f:
        f.write('# photo blueness 0-9 at the dot centre of each mosaic block, 80x50\n')
        for row in range(50):
            f.write(''.join(str(min(9, int(x * 10))) for x in val[row]) + '\n')
    print('written', a.out)


if __name__ == '__main__':
    main()
