"""Reference renderer of the MZ-800 clock screens (src/mz/clockview.c, src/mz/gfx.asm): the four VRAM planes
(8000 bytes each, 40 bytes per line, bit 0 = the leftmost pixel) the program must produce, drawn in the same
order with the same integer arithmetic and the GDG's REPLACE / PSET write formats. Standard library only (plus
tools/cgrom.py for the MZ-800 CG-ROM font, read from the emulator sources). Used by tests/emu/run_modern.py.

    python tools/clockref.py [--utc 2026-11-01T15:04:37] [--home PRAGUE] [--png work/clock]
"""
import argparse
import os
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cgrom  # noqa: E402
import mkmodern as mm  # noqa: E402
import modref  # noqa: E402
from mkhistoric import to_display  # noqa: E402

(C_TITLE, C_DIGITS, C_NAME, C_DAY, C_NIGHT, C_BAR, C_RULER, C_FACE_DAY, C_FACE_NIGHT, C_RIM, C_TICK, C_HAND,
 C_SECOND) = range(13)
COL16 = [13, 14, 10, 14, 9, 11, 12, 9, 1, 2, 15, 14, 10]
COL4 = [3, 3, 2, 3, 1, 2, 1, 1, 0, 2, 3, 3, 2]
PAL16 = [0, 1, 2, 3]                   # IGRB of the palette entries 0-3
PAL4 = [0, 1, 10, 14]
NUMERALS = ['12', '3', '6', '9']


class Vram:
    """Planes I-IV; the 4-colour mode writes only I and II (REPLACE, PSET: the colour's bits)."""

    def __init__(self, hicolor, font):
        self.p = [bytearray(8000) for _ in range(4)]
        self.n = 4 if hicolor else 2
        self.font = font

    def replace(self, i, v, c):
        for k in range(self.n):
            self.p[k][i] = v if (c >> k) & 1 else 0

    def pset(self, i, v, c):
        for k in range(self.n):
            if (c >> k) & 1:
                self.p[k][i] |= v
            else:
                self.p[k][i] &= ~v & 0xFF

    def glyph(self, ch):
        code = to_display(ch)[0]
        return self.font[code * 8:code * 8 + 8]

    def ctext(self, bx, y, s, c, sx=1, sy=1):
        for ch in s:
            g = self.glyph(ch)
            row = y
            for r in range(8):
                bits = []
                for b in range(8):
                    bits += [(g[r] >> b) & 1] * sx
                e = [sum(bits[j * 8 + i] << i for i in range(8)) for j in range(sx)]
                for _ in range(sy):
                    for j in range(sx):
                        self.replace(row * 40 + bx + j, e[j], c)
                    row += 1
            bx += sx

    def ptext(self, x, y, s, c):
        for ch in s:
            g = self.glyph(ch)
            sh = x & 7
            for r in range(8):
                v = g[r] << sh
                i = (y + r) * 40 + (x >> 3)
                self.pset(i, v & 0xFF, c)
                if sh:
                    self.pset(i + 1, v >> 8, c)
            x += 8

    def hspan(self, x0, x1, y, c):
        b0, b1 = x0 >> 3, x1 >> 3
        m0, m1 = (0xFF << (x0 & 7)) & 0xFF, 0xFF >> (7 - (x1 & 7))
        if b0 == b1:
            self.pset(y * 40 + b0, m0 & m1, c)
            return
        self.pset(y * 40 + b0, m0, c)
        for b in range(b0 + 1, b1):
            self.pset(y * 40 + b, 0xFF, c)
        self.pset(y * 40 + b1, m1, c)

    def line(self, x0, y0, x1, y1, c, width):
        adx, ady = abs(x1 - x0), abs(y1 - y0)
        sx, sy = (-1 if x1 < x0 else 1), (-1 if y1 < y0 else 1)
        steep = ady > adx
        o = -((width - 1) >> 1)
        for _ in range(width):
            x, y = (x0 + o, y0) if steep else (x0, y0 + o)
            major, minor = (ady, adx) if steep else (adx, ady)
            err = major >> 1
            for _ in range(major + 1):
                self.pset(y * 40 + (x >> 3), 1 << (x & 7), c)
                if steep:
                    y += sy
                else:
                    x += sx
                err -= minor
                if err < 0:
                    err += major
                    if steep:
                        x += sx
                    else:
                        y += sy
            o += 1

    def bar(self, sec, c):
        """modview.c mod_bar"""
        end = mm.BAR_X + 4 * (sec + 1)
        for r in range(4):
            for b in range(mm.BAR_X >> 3, (mm.BAR_X + 240) >> 3):
                if b * 8 + 8 <= end:
                    v = 0xFF
                elif b * 8 >= end:
                    v = 0
                else:
                    v = (1 << (end & 7)) - 1
                self.replace((mm.BAR_Y + r) * 40 + b, v, c)

    def ruler(self, c):
        """modview.c mod_ruler"""
        line = bytearray(40)
        for x in range(mm.BAR_X - 1, mm.BAR_X + 240):
            line[x >> 3] |= 1 << (x & 7)
        for b in range(40):
            self.replace(199 * 40 + b, line[b], c)
        posts = bytearray(40)
        for k in range(7):
            x = mm.BAR_X - 1 + 40 * k
            posts[x >> 3] |= 1 << (x & 7)
        for y in range(mm.RULER_Y, 199):
            for b in range(40):
                self.replace(y * 40 + b, posts[b], c)


def offset_text(local):
    off = int(local.utcoffset().total_seconds()) // 60
    return 'UTC%s%d' % ('-' if off < 0 else '+', abs(off) // 60) + (':%02d' % (abs(off) % 60) if off % 60 else '')


def render(d, utc, home, analog, hicolor):
    """The planes of the digital (analog=False) or analog clock screen at `utc` (a whole second)."""
    sin60 = mm.clock_tables()[0]
    face_in, face_out = mm.clock_tables()[1:]
    vr = Vram(hicolor, cgrom.load('800'))
    col = COL16 if hicolor else COL4
    name, std, rule = d['zones'][home]
    local = modref.wc_split_local(utc, std, rule)
    yday = utc.timetuple().tm_yday - 1
    x16 = mm.subsolar_x16(utc.hour * 3600 + utc.minute * 60, yday, d['eot'])
    tanlat, acos = mm.tanlat_table(), mm.acos_table()

    def day_at(x, y):
        start, length = mm.day_interval(y - mm.MAP_Y, yday, x16, d['tand'], tanlat, acos)
        return (x - start) % mm.W < length

    def point(length, pos):
        dx, dy = mm.clock_point(length, pos, sin60)
        return mm.CLK_CX + dx, mm.CLK_CY + dy

    vr.ctext(0, 0, '*** WORLD CLOCK ***', col[C_TITLE])
    for i, c in enumerate(mm.CITIES):
        if analog:
            vr.ctext(mm.PANEL_BX, mm.LIST_Y + i * mm.LIST_DY, c[0], col[C_NAME])
        else:
            vr.ctext(mm.GRID_BX[i % 3], mm.GRID_Y + (i // 3) * mm.GRID_DY, c[0], col[C_NAME])
    if analog:
        vr.ctext(mm.PANEL_BX, mm.PANEL_NAME_Y, name, col[C_NAME])
    else:
        vr.ruler(col[C_RULER])
    # the minute: the date, the offset, the face, the cities' times
    vr.ctext(26, 0, '%s %02d.%02d.%04d' % (modref.DAYS[(local.weekday() + 1) % 7], local.day, local.month,
                                           local.year), col[C_TITLE])
    off = offset_text(local)
    if analog:
        vr.ctext(mm.PANEL_BX, mm.PANEL_OFF_Y, '%-10s' % off, col[C_TITLE])
        hx, hy = d['home_xy'][home]
        fc = col[C_FACE_DAY if not hy or day_at(hx, hy) else C_FACE_NIGHT]
        for dy in range(mm.CLK_RO, -1, -1):
            for y in ((mm.CLK_CY - dy, mm.CLK_CY + dy) if dy else (mm.CLK_CY,)):
                vr.hspan(mm.CLK_CX - face_out[dy], mm.CLK_CX + face_out[dy], y, col[C_RIM])
                if dy <= mm.CLK_R:
                    vr.hspan(mm.CLK_CX - face_in[dy], mm.CLK_CX + face_in[dy], y, fc)
        for p in range(60):
            if p % 5:
                x, y = point(mm.TICK_DOT, p)
                vr.hspan(x, x, y, col[C_TICK])
            else:
                vr.line(*point(mm.TICK_IN, p), *point(mm.TICK_OUT, p), col[C_TICK], 2)
        for k, s in enumerate(NUMERALS):
            x, y = point(mm.NUM_R, k * 15)
            vr.ptext(x - 4 * len(s), y - 4, s, col[C_TICK])
    else:
        n, k = len(name), len(off)
        line = [' '] * 40
        bx = (40 - n - 2 - k) // 2
        line[bx:bx + n] = name
        line[bx + n + 2:bx + n + 2 + k] = off
        vr.ctext(0, mm.DIG_HOME_Y, ''.join(line), col[C_NAME])
    for i, (cname, lat, lon, cstd, crule) in enumerate(mm.CITIES):
        t = modref.wc_split_local(utc, cstd, crule)
        x, y = mm.city_xy(lat, lon, 'pacific')
        c = col[C_DAY if day_at(x, y) else C_NIGHT]
        if analog:
            vr.ctext(mm.LIST_TBX, mm.LIST_Y + i * mm.LIST_DY, '%02d:%02d' % (t.hour, t.minute), c)
        else:
            vr.ctext(mm.GRID_BX[i % 3], mm.GRID_Y + (i // 3) * mm.GRID_DY + 8, '%02d:%02d' % (t.hour, t.minute), c)
    # the second: the digits, the bar or the hands
    hms = '%02d:%02d:%02d' % (local.hour, local.minute, local.second)
    for i, ch in enumerate(hms):
        if analog:
            vr.ctext(mm.PANEL_BX + 2 * i, mm.PANEL_TIME_Y, ch, col[C_DIGITS], 2, 2)
        else:
            vr.ctext(mm.DIG_BX + 4 * i, mm.DIG_Y, ch, col[C_DIGITS], 4, 6)
    if analog:
        s, m = local.second, local.minute
        h = (local.hour % 12) * 5 + m // 12
        vr.line(mm.CLK_CX, mm.CLK_CY, *point(mm.HAND_H, h), col[C_HAND], 3)
        vr.line(mm.CLK_CX, mm.CLK_CY, *point(mm.HAND_M, m), col[C_HAND], 2)
        vr.line(*point(mm.HAND_TAIL, (s + 30) % 60), *point(mm.HAND_S, s), col[C_SECOND], 1)
        for y in range(mm.CLK_CY - 1, mm.CLK_CY + 2):
            vr.hspan(mm.CLK_CX - 2, mm.CLK_CX + 2, y, col[C_HAND])
    else:
        vr.bar(utc.second, col[C_BAR])
    return vr.p


def write_png(planes, path, hicolor, scale=2):
    """With the pixel aspect of a 4:3 screen (2x wide, 2.4x tall)."""
    pal = PAL16 if hicolor else PAL4
    lines = []
    for y in range(200):
        line = bytearray()
        for x in range(320):
            i, bit = y * 40 + x // 8, x % 8
            code = sum(((planes[k][i] >> bit) & 1) << k for k in range(4 if hicolor else 2))
            rgb = modref.MZ800_RGB[pal[code] if code < 4 else code]
            line += bytes([rgb >> 16, (rgb >> 8) & 255, rgb & 255]) * scale
        lines.append(bytes(line))
    cgrom.write_png(path, 320 * scale, 480, [lines[int(y / 2.4)] for y in range(480)])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--utc', default='2026-11-01T15:04:37')
    ap.add_argument('--home', default='PRAGUE')
    ap.add_argument('--png', default=os.path.join(os.path.dirname(HERE), 'work', 'clock'))
    a = ap.parse_args()
    d = mm.build(os.path.join(os.path.dirname(HERE), 'build', 'test', 'gen'))
    utc = datetime.fromisoformat(a.utc).replace(tzinfo=timezone.utc)
    home = [z[0] for z in d['zones']].index(a.home)
    for analog in (False, True):
        for hicolor in (True, False):
            path = '%s-%s-%d.png' % (a.png, 'analog' if analog else 'digital', 16 if hicolor else 4)
            write_png(render(d, utc, home, analog, hicolor), path, hicolor)
            print(path)


if __name__ == '__main__':
    main()
