"""Print the [map] section of data/historic.txt from the photo measurement (analysis tool).

    python tools/ref/align_catalog.py       (writes work/ref/blocks.npy)
    python tools/ref/extract_map.py > work/ref/map.txt

Each mosaic block (80x50) is read from the 1983 catalogue photo: lit if its blueness is >= 0.6, dark if
<= 0.15. In between the photo cannot decide (about 10 edge blocks); those take the value of the second,
independent reading of the period screen, the 2019 remake (traced from the leaflet mz-700c2.jpg; local
file input/World-Clock/WorldClock.mzt, not in the repository). Text cells of the catalogue screen stay dark
(the labels are drawn over them). Rows 0-3 (title) and 44-49 (seconds bar, ruler) have no map.
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

LIT, DARK = 0.6, 0.15
# text cells of the catalogue screen (row, first column, length): names in red, times in yellow
TEXT = [(4, 9, 6), (5, 9, 5), (7, 5, 5), (8, 5, 5), (9, 13, 5), (10, 13, 5), (7, 22, 4), (8, 24, 5),
        (11, 19, 5), (12, 19, 5), (10, 29, 10), (11, 33, 5), (15, 34, 3), (16, 33, 5), (18, 2, 8),
        (19, 4, 5), (19, 17, 6), (20, 17, 5)]


def remake_blocks(path):
    scr = open(path, 'rb').read()[128:][-2000:]
    ch, at = scr[:1000], scr[1000:]
    m = np.zeros((50, 80), bool)
    for i in range(1000):
        c = ch[i]
        cy, cx = divmod(i, 40)
        if 0xF0 <= c <= 0xFF and (at[i] >> 4) & 7 == 1:
            b = c & 15
            m[cy * 2, cx * 2], m[cy * 2, cx * 2 + 1] = b & 1, (b >> 1) & 1
            m[cy * 2 + 1, cx * 2], m[cy * 2 + 1, cx * 2 + 1] = (b >> 2) & 1, (b >> 3) & 1
    return m


def main():
    val = np.load(os.path.join(ROOT, 'work', 'ref', 'blocks.npy'))
    rem = remake_blocks(os.path.join(ROOT, 'input', 'World-Clock', 'WorldClock.mzt'))
    text = np.zeros((25, 40), bool)
    for r, c, n in TEXT:
        text[r, c:c + n] = True
    text = np.kron(text, np.ones((2, 2), bool))
    out = np.where(val >= LIT, True, np.where(val <= DARK, False, rem))
    out &= ~text
    out[:4] = False
    out[44:] = False
    amb = (val > DARK) & (val < LIT) & ~text
    amb[:4] = amb[44:] = False
    print('# %d blocks lit, %d decided by the second reading' % (out.sum(), amb.sum()), file=sys.stderr)
    for row in range(50):
        print(''.join('#' if b else '.' for b in out[row]))


if __name__ == '__main__':
    main()
