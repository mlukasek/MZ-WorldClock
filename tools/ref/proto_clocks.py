"""Prototype of the MZ-800 clock screens of phase 5 (320x200, 4 colours) as PNG, for approval before any Z80 code.

    python tools/ref/proto_clocks.py [--utc 2026-11-01T15:04:37] [--home PRAGUE] [--out work/proto-clock]

Writes <out>-digital-a.png (HH:MM from the CG-ROM font 8x enlarged, the seconds as the bar), -digital-b.png
(HH:MM:SS 4x6 enlarged) and -analog.png (a clock face, the home time and the cities beside it), 640x480 with the
pixel aspect of a 4:3 screen. The
same palette as the modern map (variant A: black, blue, green, light yellow). Needs the MZ-800 CG-ROM from the
emulator sources (tools/cgrom.py); standard library only.

The MZ-800's pixels in 320x200 are about 1.2 times as tall as wide on a 4:3 screen (PAL: 8.87 MHz dots, 52 us
of 64 us visible, 288 lines), so the clock face is an ellipse 1.2 times as wide as tall in pixels.
"""
import argparse
import math
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'ref'))
import cgrom  # noqa: E402
import worldmap  # noqa: E402
from proto_modern import MZ800, PALETTES, cgrom_code  # noqa: E402

ASPECT = 1.2
CITIES = [  # name, lat, lon, tz: as on the map
    ('TOKYO', 35.68, 139.69, 'Asia/Tokyo'),
    ('PEKIN', 39.90, 116.40, 'Asia/Shanghai'),
    ('MOSCOW', 55.75, 37.62, 'Europe/Moscow'),
    ('PARIS', 48.86, 2.35, 'Europe/Paris'),
    ('WASHINGTON', 38.90, -77.04, 'America/New_York'),
    ('L.ANGELES', 34.05, -118.24, 'America/Los_Angeles'),
    ('RIO', -22.90, -43.20, 'America/Sao_Paulo'),
    ('S.AFRICA', -26.20, 28.05, 'Africa/Johannesburg'),
    ('SYDNEY', -33.87, 151.21, 'Australia/Sydney'),
]
HOMES = {'PRAGUE': (50.08, 14.42, 'Europe/Prague'), 'TOKYO': (35.68, 139.69, 'Asia/Tokyo')}


class Canvas:
    def __init__(self, font):
        self.px = [bytearray(320) for _ in range(200)]
        self.font = font

    def set(self, x, y, c):
        x, y = int(round(x)), int(round(y))
        if 0 <= x < 320 and 0 <= y < 200:
            self.px[y][x] = c

    def fill(self, x0, y0, x1, y1, c):
        for y in range(y0, y1):
            for x in range(x0, x1):
                self.set(x, y, c)

    def text(self, x, y, s, c=3, sx=1, sy=1):
        """CG-ROM text, each glyph pixel enlarged to sx x sy (byte-aligned on the MZ-800 when x is a multiple
        of 8 and sx is 1, 2, 4 or 8)."""
        for k, ch in enumerate(s):
            code = cgrom_code(ch)
            for gy in range(8):
                bits = self.font[code * 8 + gy]
                for gx in range(8):
                    if (bits >> gx) & 1:
                        self.fill(x + (k * 8 + gx) * sx, y + gy * sy, x + (k * 8 + gx + 1) * sx,
                                  y + (gy + 1) * sy, c)

    def line(self, x0, y0, x1, y1, c, width=1):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            t = i / n
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            for d in range(width):
                o = d - (width - 1) / 2
                # thicken across the line: horizontally for steep lines, vertically for flat ones
                if abs(y1 - y0) > abs(x1 - x0):
                    self.set(x + o, y, c)
                else:
                    self.set(x, y + o, c)


def is_day(utc, lat, lon):
    slat, slon = worldmap.sun(utc)
    return not worldmap.is_night(lat, lon, slat, slon)


def header(cv, home_t):
    cv.text(0, 0, '*** WORLD CLOCK ***')
    cv.text(320 - 8 * 14, 0, home_t.strftime('%a %d.%m.%Y').upper())


def home_line(cv, name, home_t, y=174):
    cv.text(0, y, '%-10s %s' % (name, home_t.strftime('%H:%M:%S')))
    off = home_t.utcoffset().total_seconds() / 60
    s = 'UTC%+d' % (off // 60) + (':%02d' % (off % 60) if off % 60 else '')
    cv.text(320 - 8 * len(s), y, s)


def seconds_bar(cv, sec):
    for x in range(32, 32 + 4 * (sec + 1)):
        for y in range(186, 190):
            cv.set(x, y, 3)
    for x in range(31, 272):
        cv.set(x, 199, 2)
    for x in range(31, 272, 40):
        for y in range(192, 199):
            cv.set(x, y, 2)


def city_grid(cv, utc, y0):
    """The 9 cities in 3 columns: the name (green) over the time (light yellow by day, blue by night)."""
    for i, (name, lat, lon, tz) in enumerate(CITIES):
        x, y = (i % 3) * 112 + 4, y0 + (i // 3) * 20
        t = utc.astimezone(ZoneInfo(tz))
        cv.text(x, y, name, 2)
        cv.text(x, y + 8, t.strftime('%H:%M'), 3 if is_day(utc, lat, lon) else 1)


def digital_a(font, utc, home):
    lat, lon, tz = HOMES[home]
    t = utc.astimezone(ZoneInfo(tz))
    cv = Canvas(font)
    header(cv, t)
    cv.text(0, 20, t.strftime('%H:%M'), 3, 8, 8)            # 320 x 64
    city_grid(cv, utc, 100)
    home_line(cv, home, t)
    seconds_bar(cv, t.second)
    return cv


def digital_b(font, utc, home):
    lat, lon, tz = HOMES[home]
    t = utc.astimezone(ZoneInfo(tz))
    cv = Canvas(font)
    header(cv, t)
    cv.text(32, 28, t.strftime('%H:%M:%S'), 3, 4, 6)         # 256 x 48
    cv.text(160 - 4 * len(home), 84, home, 2)
    city_grid(cv, utc, 104)
    home_line(cv, home, t)
    seconds_bar(cv, t.second)
    return cv


def analog(font, utc, home):
    lat, lon, tz = HOMES[home]
    t = utc.astimezone(ZoneInfo(tz))
    cv = Canvas(font)
    header(cv, t)
    cx, cy, r = 90, 102, 74                                     # r: vertical radius in pixels
    day = is_day(utc, lat, lon)
    # the face: blue by day, black by night, a green rim
    for y in range(200):
        for x in range(320):
            d = ((x - cx) / (r * ASPECT)) ** 2 + ((y - cy) / r) ** 2
            if d <= 1.0:
                cv.px[y][x] = 1 if day else 0
            elif d <= 1.13:
                cv.px[y][x] = 2

    def at(angle, rr):
        return cx + rr * math.sin(angle) * ASPECT, cy - rr * math.cos(angle)

    for m in range(60):
        a = m * math.pi / 30
        if m % 5:
            cv.set(*at(a, r - 3), 3)
        else:
            cv.line(*at(a, r - 9), *at(a, r - 2), 3, 2)
    for h, s in ((12, '12'), (3, '3'), (6, '6'), (9, '9')):
        x, y = at(h * math.pi / 6, r - 18)
        cv.text(int(x - 4 * len(s)), int(y - 4), s, 3)
    sec = t.second
    mnt = t.minute + sec / 60
    hr = t.hour % 12 + mnt / 60
    cv.line(cx, cy, *at(hr * math.pi / 6, r * 0.5), 3, 3)
    cv.line(cx, cy, *at(mnt * math.pi / 30, r * 0.8), 3, 2)
    cv.line(*at(sec * math.pi / 30 + math.pi, r * 0.15), *at(sec * math.pi / 30, r * 0.88), 2, 1)
    cv.fill(cx - 2, cy - 1, cx + 3, cy + 2, 3)
    # beside it: the home, its time and offset, then the cities, one line each
    x0 = 192
    cv.text(x0, 20, home, 2)
    cv.text(x0, 30, t.strftime('%H:%M:%S'), 3, 2, 2)
    off = t.utcoffset().total_seconds() / 60
    cv.text(x0, 50, 'UTC%+d' % (off // 60) + (':%02d' % (off % 60) if off % 60 else ''), 2)
    for i, (name, clat, clon, ctz) in enumerate(CITIES):
        y = 72 + i * 12
        ct = utc.astimezone(ZoneInfo(ctz))
        cv.text(x0, y, name, 2)
        cv.text(320 - 40, y, ct.strftime('%H:%M'), 3 if is_day(utc, clat, clon) else 1)
    return cv


def write(cv, path, palette):
    """640x480: 2x wide, 2.4x tall, i.e. the shape on a 4:3 screen."""
    pal = [MZ800[i] for i in palette]
    lines = []
    for y in range(200):
        line = bytearray()
        for x in range(320):
            c = pal[cv.px[y][x]]
            line += bytes([c >> 16, (c >> 8) & 255, c & 255]) * 2
        lines.append(bytes(line))
    rows = [lines[int(y / 2.4)] for y in range(480)]
    cgrom.write_png(path, 640, 480, rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--utc', default='2026-11-01T15:04:37')
    ap.add_argument('--home', default='PRAGUE', choices=sorted(HOMES))
    ap.add_argument('--out', default=os.path.join(ROOT, 'work', 'proto-clock'))
    a = ap.parse_args()
    utc = datetime.fromisoformat(a.utc).replace(tzinfo=timezone.utc)
    font = cgrom.load('800')
    for name, fn in (('digital-a', digital_a), ('digital-b', digital_b), ('analog', analog)):
        path = '%s-%s.png' % (a.out, name)
        write(fn(font, utc, a.home), path, PALETTES['a'])
        print(path)


if __name__ == '__main__':
    main()
