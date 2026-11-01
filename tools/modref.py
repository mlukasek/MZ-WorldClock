"""Reference renderer of the modern MZ-800 look: the VRAM planes (8000 bytes each, 40 bytes per line, bit 0
= the leftmost pixel; two in the 4-colour mode, four in the 16-colour one with the VRAM extension) that
src/mz/modview.c must produce. Standard library only (plus tools/cgrom.py for the
MZ-800 CG-ROM font, read from the emulator sources). Used by tools/mkmodern.py --png and the emulator test.
"""
import os
import sys
from datetime import timedelta, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cgrom  # noqa: E402
import mkmodern as mm  # noqa: E402
from mkhistoric import to_display  # noqa: E402

MZ800_RGB = [0x000000, 0x4040ac, 0xd03400, 0xb40c8c, 0x406c00, 0x24ccff, 0xe8d430, 0xd0d0d0,
             0x848484, 0x008ce8, 0xff0000, 0xf054cc, 0x54ff54, 0x80ffff, 0xffff28, 0xffffff]
DAYS = ['SUN', 'MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT']
# modview.c: the colours of the title (and date, offset), the names, the times, the bar, the ruler
M_TITLE, M_NAME, M_TIME, M_BAR, M_RULER = range(5)
MCOL16 = [13, 10, 14, 11, 12]
MCOL4 = [3, 3, 3, 3, 2]


class Planes:
    def __init__(self):
        self.p = [bytearray(8000) for _ in range(4)]

    def pixel(self, x, y, c):
        if 0 <= x < 320 and 0 <= y < 200:
            i, bit = y * 40 + x // 8, 1 << (x % 8)
            for k in range(4):
                if (c >> k) & 1:
                    self.p[k][i] |= bit
                else:
                    self.p[k][i] &= ~bit & 0xFF

    def byte(self, bx, y, c0, c1):
        """a map byte: planes I, II; III, IV cleared"""
        i = y * 40 + bx
        self.p[0][i], self.p[1][i], self.p[2][i], self.p[3][i] = c0, c1, 0, 0

    def text(self, bx, y, s, font, shadow, colour=3):
        """8x8 glyphs at byte column bx, pixel row y in a colour; with a black shadow 1 px right and down, or
        opaque (black background) when shadow is False."""
        for k, ch in enumerate(s):
            g = font[to_display(ch)[0] * 8:to_display(ch)[0] * 8 + 8]
            for r in range(8):
                if shadow:
                    for x in range(8):
                        if (g[r] >> x) & 1:
                            self.pixel((bx + k) * 8 + x + 1, y + r + 1, 0)
                else:
                    for p in range(4):
                        self.p[p][(y + r) * 40 + bx + k] = g[r] if (colour >> p) & 1 else 0
        if shadow:
            for k, ch in enumerate(s):
                g = font[to_display(ch)[0] * 8:to_display(ch)[0] * 8 + 8]
                for r in range(8):
                    for x in range(8):
                        if (g[r] >> x) & 1:
                            self.pixel((bx + k) * 8 + x, y + r, colour)


def wc_split_local(utc, std, rule):
    """Local time by the same rules as src/core/wctime.c (checked against zoneinfo by tests/core)."""
    from zoneinfo import ZoneInfo
    zone = {(60, 'EU'): 'Europe/Paris', (0, 'EU'): 'Europe/London', (120, 'EU'): 'Europe/Helsinki',
            (-480, 'US'): 'America/Los_Angeles', (-420, 'US'): 'America/Denver', (-360, 'US'): 'America/Chicago',
            (-300, 'US'): 'America/New_York', (600, 'AU'): 'Australia/Sydney'}.get((std, rule))
    if zone:
        return utc.astimezone(ZoneInfo(zone))
    return utc.astimezone(timezone(timedelta(minutes=std)))


def map_row(d, y, yday, x16):
    """Plane I and II bytes of map row y in the Pacific view."""
    land = d['land'][y]
    start, length = mm.day_interval(y, yday, x16, d['tand'], mm.tanlat_table(), mm.acos_table())
    day = bytearray(320)
    for k in range(length):
        day[(start + k) % 320] = 1
    p0, p1 = bytearray(40), bytearray(40)
    dither = 0x55 if (mm.MAP_Y + y) & 1 else 0xAA
    for bx in range(40):
        lb = sum(land[bx * 8 + i] << i for i in range(8))
        db = sum(day[bx * 8 + i] << i for i in range(8))
        p0[bx] = ~lb & db & 0xFF
        p1[bx] = lb & (db | dither) & 0xFF
    return p0, p1


def render(d, utc, home, view, hicolor=False):
    """The planes (four; in the 4-colour mode III and IV stay empty)"""
    pl = Planes()
    col = MCOL16 if hicolor else MCOL4
    font = cgrom.load('800')
    zones = d['zones']
    name, std, rule = zones[home]
    local = wc_split_local(utc, std, rule)
    yday = utc.timetuple().tm_yday - 1
    secs = utc.hour * 3600 + utc.minute * 60           # the program computes the sun at the start of the minute
    x16 = mm.subsolar_x16(secs, yday, d['eot'])
    shift = mm.ATL_SHIFT // 8 if view == 'atlantic' else 0
    # title, date
    pl.text(0, 0, '*** WORLD CLOCK ***', font, False, col[M_TITLE])
    pl.text(26, 0, '%s %02d.%02d.%04d' % (DAYS[(local.weekday() + 1) % 7], local.day, local.month, local.year),
            font, False, col[M_TITLE])
    # map
    for y in range(mm.MAP_H):
        p0, p1 = map_row(d, y, yday, x16)
        for bx in range(40):
            pl.byte((bx + shift) % 40, mm.MAP_Y + y, p0[bx], p1[bx])
    # home zone border: dots on the top-left pixel of the border cells
    z = d['home_zone'][home]
    zid = d['zid']
    zw, zh = len(zid[0]), len(zid)
    for cy in range(zh):
        for cx in range(zw):
            if zid[cy][cx] != z:
                continue
            if any(not (0 <= cx + dx < zw and 0 <= cy + dy < zh) or zid[cy + dy][cx + dx] != z
                   for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                pl.pixel((cx * 2 + shift * 8) % 320, mm.MAP_Y + cy * 2, 3)
    # markers
    for k, c in enumerate(mm.CITIES):
        x, y = mm.city_xy(c[1], c[2], view)
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            pl.pixel(x + dx, y + dy, 3)
    hx, hy = d['home_xy'][home]
    if hy:
        hx = (hx + shift * 8) % 320
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1), (2, 0), (-2, 0), (0, 2), (0, -2)):
            pl.pixel(hx + dx, hy + dy, 3)
    # labels
    lab = d['labels'][1 if view == 'atlantic' else 0]
    for (cname, lat, lon, cstd, crule), (bx, by) in zip(mm.CITIES, lab):
        t = wc_split_local(utc, cstd, crule)
        pl.text(bx, by, cname, font, True, col[M_NAME])
        pl.text(bx, by + 8, '%02d:%02d' % (t.hour, t.minute), font, True, col[M_TIME])
    # home line: name and time, the offset at the right
    pl.text(0, mm.HOME_Y, '%-10s' % name, font, False, col[M_NAME])
    pl.text(10, mm.HOME_Y, ' %02d:%02d:%02d' % (local.hour, local.minute, local.second), font, False, col[M_TIME])
    off = int(local.utcoffset().total_seconds()) // 60
    s = 'UTC%s%d' % ('-' if off < 0 else '+', abs(off) // 60) + (':%02d' % (abs(off) % 60) if off % 60 else '')
    pl.text(40 - 8, mm.HOME_Y, '%8s' % s, font, False, col[M_TITLE])
    # seconds bar (4 px per second, full in the last second) and its ruler
    for x in range(mm.BAR_X, mm.BAR_X + 4 * (utc.second + 1)):
        for y in range(mm.BAR_Y, mm.BAR_Y + 4):
            pl.pixel(x, y, col[M_BAR])
    for x in range(mm.BAR_X - 1, mm.BAR_X + 240):
        pl.pixel(x, 199, col[M_RULER])
    for k in range(7):
        for y in range(mm.RULER_Y, 199):
            pl.pixel(mm.BAR_X - 1 + 40 * k, y, col[M_RULER])
    return pl.p


def write_png(planes, path, scale=2):
    """Colours 0-3 through the map's palette, 4-15 IGRB (the 16-colour mode)"""
    pal = [MZ800_RGB[c] for c in mm.PALETTE] + MZ800_RGB[4:]
    rows = []
    for y in range(200):
        line = bytearray()
        for x in range(320):
            i, bit = y * 40 + x // 8, x % 8
            c = pal[sum(((planes[k][i] >> bit) & 1) << k for k in range(len(planes)))]
            line += bytes([c >> 16, (c >> 8) & 255, c & 255]) * scale
        rows += [bytes(line)] * scale
    cgrom.write_png(path, 320 * scale, 200 * scale, rows)
