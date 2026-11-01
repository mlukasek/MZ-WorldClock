"""Prototype of the modern look on the MZ-800 (320x200, 4 colours) as PNG, for approval before any Z80 code.

    python tools/ref/proto_modern.py [--utc 2026-11-01T15:00:00] [--out work/proto]

Writes <out>-pacific.png and <out>-atlantic.png at 2x. Needs input/naturalearth/*.geojson (Natural Earth,
public domain) and the MZ-800 CG-ROM from the emulator sources (the font; tools/cgrom.py). Standard library
only, like the generator it will become.
"""
import argparse
import os
import sys
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import cgrom  # noqa: E402
import worldmap  # noqa: E402

# MZ-800 colours (mz800emu display.c), IGRB index
MZ800 = [0x000000, 0x4040ac, 0xd03400, 0xb40c8c, 0x406c00, 0x24ccff, 0xe8d430, 0xd0d0d0,
         0x848484, 0x008ce8, 0xff0000, 0xf054cc, 0x54ff54, 0x80ffff, 0xffff28, 0xffffff]
PALETTES = {'a': [0, 1, 4, 14], 'b': [0, 9, 12, 14]}   # 0 night sea, 1 day sea, 2 land, 3 text / markers / zone

MAP_Y, MAP_H = 10, 160            # map rows on the screen
LAT_TOP, LAT_BOTTOM = 80.0, -64.0
VIEWS = {'pacific': -25.0, 'atlantic': -168.5}   # longitude of the left edge

# name, lat, lon, tz (the order is the placement priority of the labels)
CITIES = [
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
HOME = ('PRAGUE', 50.08, 14.42, 'Europe/Prague', 1)      # zone +1 in ne_10m_time_zones


class Canvas:
    def __init__(self):
        self.px = [bytearray(320) for _ in range(200)]

    def set(self, x, y, c):
        if 0 <= x < 320 and 0 <= y < 200:
            self.px[y][x] = c

    def text(self, x, y, s, font, c=3, shadow=0):
        for k, ch in enumerate(s):
            code = cgrom_code(ch)
            for gy in range(8):
                bits = font[code * 8 + gy]
                for gx in range(8):
                    if (bits >> gx) & 1:
                        if shadow is not None:
                            self.set(x + k * 8 + gx + 1, y + gy + 1, shadow)
                        self.set(x + k * 8 + gx, y + gy, c)
        # second pass so that shadows never cover glyph pixels of the neighbours
        for k, ch in enumerate(s):
            code = cgrom_code(ch)
            for gy in range(8):
                bits = font[code * 8 + gy]
                for gx in range(8):
                    if (bits >> gx) & 1:
                        self.set(x + k * 8 + gx, y + gy, c)


def cgrom_code(ch):
    import mkhistoric
    return mkhistoric.to_display(ch)[0]


def render(view, utc, land_polys, zone_polys, font):
    proj = worldmap.Projection(320, MAP_H, VIEWS[view], LAT_TOP, LAT_BOTTOM)
    land = worldmap.rasterise(land_polys, proj)
    zone = worldmap.rasterise(zone_polys, proj)
    slat, slon = worldmap.sun(utc)
    cv = Canvas()
    for y in range(MAP_H):
        lat = proj.lat(y)
        for x in range(320):
            night = worldmap.is_night(lat, proj.lon(x), slat, slon)
            if land[y][x]:
                c = 2 if not night or (x + y) & 1 else 0          # night land: green / black dither
            else:
                c = 0 if night else 1
            cv.px[MAP_Y + y][x] = c
    # home zone border, dotted
    for y in range(MAP_H):
        for x in range(320):
            if zone[y][x] and (x + y) % 2 == 0:
                edge = any(not (0 <= x + dx < 320 and 0 <= y + dy < MAP_H) or not zone[y + dy][x + dx]
                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)))
                if edge:
                    cv.px[MAP_Y + y][x] = 3
    # cities: markers first, then labels placed greedily (right, left, above, below of the marker), never
    # crossing the map area or another label / marker
    marks = []
    for name, lat, lon, tz in CITIES + [HOME[:4]]:
        x, y = int(proj.x(lon)), MAP_Y + int(proj.y(lat))
        marks.append((name, x, y, tz))
        for dx, dy in ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1)):
            cv.set(x + dx, y + dy, 3)
        if name == HOME[0]:
            for dx, dy in ((2, 0), (-2, 0), (0, 2), (0, -2)):
                cv.set(x + dx, y + dy, 3)
    boxes = [(x - 2, y - 2, x + 3, y + 3) for _, x, y, _ in marks]
    for name, x, y, tz in marks:
        if name == HOME[0]:
            continue
        w = 8 * max(len(name), 5) + 1
        for dx, dy in ((4, -8), (-w - 3, -8), (-w // 2, -19), (-w // 2, 4), (4, 2), (-w - 3, 2), (4, -16), (-w - 3, -16)):
            bx, by = x + dx, y + dy
            box = (bx, by, bx + w, by + 17)
            if bx < 0 or bx + w > 320 or by < MAP_Y or by + 17 > MAP_Y + MAP_H:
                continue
            if any(not (box[2] <= b[0] or b[2] <= box[0] or box[3] <= b[1] or b[3] <= box[1]) for b in boxes):
                continue
            break
        else:
            print('  no place for', name)
        boxes.append(box)
        local = utc.astimezone(ZoneInfo(tz))
        cv.text(bx, by, name, font)
        cv.text(bx, by + 8, local.strftime('%H:%M'), font)
    # title and the home line
    home = utc.astimezone(ZoneInfo(HOME[3]))
    cv.text(0, 0, '*** WORLD CLOCK ***', font, shadow=None)
    cv.text(320 - 8 * 14, 0, home.strftime('%a %d.%m.%Y').upper(), font, shadow=None)
    cv.text(0, 174, '%s %s' % (HOME[0], home.strftime('%H:%M:%S')), font, shadow=None)
    cv.text(320 - 8 * 8, 174, 'UTC+%d' % (home.utcoffset().total_seconds() // 3600), font, shadow=None)
    # seconds bar and ruler as in the period screen (row 22/23 of the text screen: here pixels 184-199)
    s = utc.second
    for x in range(32, 32 + 4 * (s + 1)):
        for y in range(188, 192):
            cv.set(x, y, 3)
    for x in range(31, 273):
        cv.set(x, 199, 2)
    for x in range(31, 274, 40):
        for y in range(192, 199):
            cv.set(x, y, 2)
    return cv


def write(cv, path, palette, scale=2):
    pal = [MZ800[i] for i in palette]
    rows = []
    for y in range(200):
        line = bytearray()
        for x in range(320):
            c = pal[cv.px[y][x]]
            line += bytes([c >> 16, (c >> 8) & 255, c & 255]) * scale
        rows += [bytes(line)] * scale
    cgrom.write_png(path, 320 * scale, 200 * scale, rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--utc', default='2026-11-01T15:00:00')
    ap.add_argument('--out', default=os.path.join(ROOT, 'work', 'proto'))
    a = ap.parse_args()
    utc = datetime.fromisoformat(a.utc).replace(tzinfo=timezone.utc)
    ne = os.path.join(ROOT, 'input', 'naturalearth')
    land = worldmap.load_polygons(os.path.join(ne, 'ne_50m_land.geojson'),
                                  keep=lambda p: True)
    land = [(p, r) for p, r in land if max(pt[1] for pt in r[0]) > -60]     # no Antarctica
    zone = worldmap.load_polygons(os.path.join(ne, 'ne_10m_time_zones.geojson'),
                                  keep=lambda p: p.get('zone') == HOME[4])
    font = cgrom.load('800')
    for view in VIEWS:
        cv = render(view, utc, land, zone, font)
        for k, pal in PALETTES.items():
            write(cv, '%s-%s-%s.png' % (a.out, view, k), pal)
            print('%s-%s-%s.png' % (a.out, view, k))


if __name__ == '__main__':
    main()
