"""The modern look of the MZ-800 (320x200, 4 colours): data -> C tables, and the reference renderer.

    python tools/mkmodern.py build/gen                 modern.c, modern.h
    python tools/mkmodern.py --png work/modern --utc 2026-11-01T15:00:00 [--home PRAGUE]
                                                       work/modern-pacific.png, -atlantic.png (reference render)

Sources: Natural Earth land and time zones (public domain, input/naturalearth/, see tools/worldmap.py), the
cities below, the home zones of src/core/zones.c. Standard library only.

The reference renderer here and src/mz/modview.c use the same integer arithmetic and the same tables, so the
emulator test can compare the VRAM planes byte for byte (tests/emu/run_modern.py).

Screen (pixels): row 0 the title and the date; rows MAP_Y..MAP_Y+159 the map (latitude 80N..64S, the Pacific
view's left edge at 25W; the Atlantic view is the same map rotated by 128 pixels = 16 bytes); the home city
line at HOME_Y; the seconds bar and its ruler at the bottom. Colours: 0 night sea (black), 1 day sea (blue),
2 land (green; at night dithered with black), 3 text, markers, the home zone border (light yellow).
"""
import argparse
import math
import os
import re
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import worldmap  # noqa: E402

W, MAP_H = 320, 160
MAP_Y = 10
HOME_Y = 174
BAR_Y, BAR_X = 186, 32               # seconds bar: 4 rows, 4 pixels per second
RULER_Y = 192                        # ruler: ticks rows RULER_Y..198, line row 199
LAT_TOP, LAT_BOTTOM = 80.0, -64.0
LON_LEFT = -25.0                     # Pacific view
ATL_SHIFT = 128                      # Atlantic view: x + 128 (mod 320), i.e. its left edge at 169W
PALETTE = [0x0, 0x1, 0x4, 0xE]       # IGRB: black, blue, green, light yellow (approved variant A)
ZONE_SCALE = 2                       # the zone map has 2x2-pixel cells

# The clock screens (src/mz/clockview.c, tools/clockref.py). Digital: HH:MM:SS from the CG-ROM font 4x6
# enlarged at byte column DIG_BX, the home zone and its offset centred on DIG_HOME_Y, the cities in 3 columns
# (byte columns GRID_BX) and 3 rows from GRID_Y, the seconds bar as on the map. Analog: a face centred at
# CLK_CX, CLK_CY, vertical radius CLK_R inside a rim up to CLK_RO, ASPECT_Q8 / 256 as wide as tall: round on
# square pixels, as an emulator and today's monitors show the MZ-800 (the author; on a 4:3 CRT the pixels are
# about 1.2x as tall as wide and the face looks that much taller); beside it from byte column PANEL_BX the
# home zone, its time 2x2, its offset and the cities one per line.
DIG_BX, DIG_Y, DIG_HOME_Y = 4, 24, 80
GRID_BX, GRID_Y, GRID_DY = (1, 15, 29), 104, 22
CLK_CX, CLK_CY, CLK_R, CLK_RO, ASPECT_Q8 = 79, 106, 72, 77, 256     # the left edge at x 2
HAND_H, HAND_M, HAND_S, HAND_TAIL = 36, 57, 60, 11       # lengths; the second hand also runs back by the tail
TICK_DOT, TICK_IN, TICK_OUT, NUM_R = 69, 63, 70, 54      # minute dots, 5-minute marks, numerals 12 3 6 9
PANEL_BX, PANEL_NAME_Y, PANEL_TIME_Y, PANEL_OFF_Y = 24, 24, 34, 54
LIST_Y, LIST_DY, LIST_TBX = 72, 12, 35


def clock_tables():
    """sin of 0, 6, .. 90 degrees in Q8; the half-widths of the face (inner) and of the rim (outer) per row
    offset from the centre."""
    sin60 = [round(256 * math.sin(math.radians(6 * i))) for i in range(16)]
    face_in = [round(CLK_R * ASPECT_Q8 / 256 * math.sqrt(1 - (dy / CLK_R) ** 2)) for dy in range(CLK_R + 1)]
    face_out = [round(CLK_RO * ASPECT_Q8 / 256 * math.sqrt(1 - (dy / CLK_RO) ** 2)) for dy in range(CLK_RO + 1)]
    return sin60, face_in, face_out


def clock_point(length, pos, sin60):
    """Offset (dx, dy) of the point `length` pixels (vertically) from the centre towards minute `pos` (0-59,
    clockwise from 12), the same integer arithmetic as clockview.c."""
    q, i = divmod(pos, 15)
    s, c = sin60[i], sin60[15 - i]
    vx, vy = ((s, -c), (c, s), (-s, c), (-c, -s))[q]
    dx = ((((length * abs(vx) + 128) >> 8) * ASPECT_Q8 + 128) >> 8)
    dy = (length * abs(vy) + 128) >> 8
    return (-dx if vx < 0 else dx), (-dy if vy < 0 else dy)

# Cities of the modern map: name, lat, lon, standard offset (min), DST rule (wctime.h)
CITIES = [
    ('TOKYO', 35.68, 139.69, 540, 'NONE'),
    ('PEKING', 39.90, 116.40, 480, 'NONE'),
    ('MOSCOW', 55.75, 37.62, 180, 'NONE'),
    ('PARIS', 48.86, 2.35, 60, 'EU'),
    ('WASHINGTON', 38.90, -77.04, -300, 'US'),
    ('L.ANGELES', 34.05, -118.24, -480, 'US'),
    ('RIO', -22.90, -43.20, -180, 'NONE'),
    ('S.AFRICA', -26.20, 28.05, 120, 'NONE'),
    ('SYDNEY', -33.87, 151.21, 600, 'AU'),
]
# Places of the home zones (src/core/zones.c, by name); UTC has none
HOME_PLACES = {'LONDON': (51.51, -0.13), 'PRAGUE': (50.08, 14.42), 'HELSINKI': (60.17, 24.94),
               'S.AFRICA': (-26.20, 28.05), 'MOSCOW': (55.75, 37.62), 'DUBAI': (25.20, 55.27),
               'DELHI': (28.61, 77.21), 'PEKING': (39.90, 116.40), 'TOKYO': (35.68, 139.69),
               'SYDNEY': (-33.87, 151.21), 'HONOLULU': (21.31, -157.86), 'L.ANGELES': (34.05, -118.24),
               'DENVER': (39.74, -104.99), 'CHICAGO': (41.88, -87.63), 'NEW YORK': (40.71, -74.01),
               'RIO': (-22.90, -43.20)}
DST_RULES = ['NONE', 'EU', 'US', 'AU']


def home_zones():
    """[(name, std_minutes, rule)] in the order of src/core/zones.c."""
    text = open(os.path.join(ROOT, 'src', 'core', 'zones.c'), encoding='utf-8').read()
    return [(m.group(1), int(m.group(2)), m.group(3)) for m in
            re.finditer(r'\{"([^"]+)",\s*(-?\d+),\s*DST_(\w+)\}', text)]


# ---- data ------------------------------------------------------------------------------------------------
def projection():
    return worldmap.Projection(W, MAP_H, LON_LEFT, LAT_TOP, LAT_BOTTOM)


LAND_FILE = os.path.join(ROOT, 'data', 'world_land.txt')
ZONES_FILE = os.path.join(ROOT, 'data', 'world_zones.txt')


def land_from_naturalearth():
    ne = os.path.join(ROOT, 'input', 'naturalearth')
    polys = [(p, r) for p, r in worldmap.load_polygons(os.path.join(ne, 'ne_50m_land.geojson'))
             if max(pt[1] for pt in r[0]) > -60]                              # no Antarctica
    return worldmap.rasterise(polys, projection())


def zones_from_naturalearth(offsets):
    """Zone id (1-based index into `offsets`, 0 = other) of each 2x2 cell, 160x80."""
    ne = os.path.join(ROOT, 'input', 'naturalearth')
    zones = worldmap.load_polygons(os.path.join(ne, 'ne_10m_time_zones.geojson'))
    proj = worldmap.Projection(W // ZONE_SCALE, MAP_H // ZONE_SCALE, LON_LEFT, LAT_TOP, LAT_BOTTOM)
    zid = [bytearray(W // ZONE_SCALE) for _ in range(MAP_H // ZONE_SCALE)]
    for i, off in enumerate(offsets, 1):
        m = worldmap.rasterise([(p, r) for p, r in zones if p.get('zone') is not None
                                and round(p['zone'] * 60) == off], proj)
        for y, row in enumerate(m):
            for x, v in enumerate(row):
                if v:
                    zid[y][x] = i
    return zid


def write_world_files(offsets):
    """data/world_land.txt and data/world_zones.txt from Natural Earth (input/naturalearth/)."""
    land = land_from_naturalearth()
    lines = ['# Land of the modern map, 320x160 pixels, # = land. Generated by tools/mkmodern.py',
             '# --from-naturalearth from Natural Earth ne_50m_land (public domain). Latitude 80N (first row)',
             '# to 64S, the left edge at 25W, 1.125 degree per column, 0.9 degree per row.']
    lines += [''.join('#' if b else '.' for b in row) for row in land]
    with open(LAND_FILE, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')
    zid = zones_from_naturalearth(offsets)
    lines = ['# Time zones of the modern map, 160x80 cells of 2x2 pixels (the same projection as',
             '# world_land.txt). Generated by tools/mkmodern.py --from-naturalearth from Natural Earth',
             '# ne_10m_time_zones (public domain). A cell is the zone id in hex; 0 = a zone not used as home.',
             '# ids: %s' % ' '.join('%X=%+d' % (i, off) for i, off in enumerate(offsets, 1))]
    lines += [''.join('%X' % b for b in row) for row in zid]
    with open(ZONES_FILE, 'w', encoding='utf-8', newline='\n') as f:
        f.write('\n'.join(lines) + '\n')


def land_mask():
    rows = [l.rstrip() for l in open(LAND_FILE, encoding='utf-8') if not l.startswith('# ')]   # rows may start with #
    assert len(rows) == MAP_H and all(len(r) == W for r in rows), LAND_FILE
    return [bytearray(c == '#' for c in r) for r in rows]


def zone_map(offsets):
    lines = open(ZONES_FILE, encoding='utf-8').read().splitlines()
    ids = [l for l in lines if l.startswith('# ids:')][0].split(':', 1)[1].split()
    if [int(t.split('=')[1]) for t in ids] != offsets:
        raise SystemExit('%s: zone ids %s do not match the home zones %s (regenerate with --from-naturalearth)'
                         % (ZONES_FILE, ids, offsets))
    rows = [l for l in lines if not l.startswith('#')]
    assert len(rows) == MAP_H // ZONE_SCALE and all(len(r) == W // ZONE_SCALE for r in rows), ZONES_FILE
    return [bytearray(int(c, 16) for c in r) for r in rows]


def rle_bits(row):
    """Runs of a 0/1 row, starting with 0; a run of 255 continues with the next byte."""
    out, cur, n = [], 0, 0
    for b in row:
        if b == cur:
            n += 1
        else:
            out += [255] * (n // 255) + [n % 255] if n >= 255 else [n]
            cur, n = b, 1
    out += [255] * (n // 255) + [n % 255] if n >= 255 else [n]
    return out


def rle_ids(row):
    """Runs of a row of zone ids (0-15), one byte each: id << 4 | (length - 1); a run longer than 16 goes on
    in the next byte with the same id (modview.c joins them)."""
    out, cur, n = [], row[0], 0
    for b in list(row) + [None]:
        if b == cur:
            n += 1
            continue
        if not 0 <= cur < 16:
            raise SystemExit('zone id %d does not fit 4 bits' % cur)
        while n:
            k = min(n, 16)
            out.append(cur << 4 | (k - 1))
            n -= k
        cur, n = b, 1
    return out


def sun_tables():
    """tan(declination) in Q15 and the equation of time in seconds, every 4 days (day of year 0..368)."""
    tand, eot = [], []
    for d in range(0, 372, 4):
        g = 2 * math.pi / 365.0 * d
        decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
                + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
        e = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g)
                      - 0.040849 * math.sin(2 * g))
        tand.append(round(math.tan(decl) * 32768))
        eot.append(round(e * 60))
    return tand, eot


def tanlat_table():
    proj = projection()
    return [round(math.tan(math.radians(proj.lat(y))) * 256) for y in range(MAP_H)]


def acos_table():
    """Half-width of the day (pixels, 0..160) for p = -tan(lat)*tan(decl) in Q8, p = 0..256."""
    return [round(math.degrees(math.acos(p / 256.0)) * W / 360.0) for p in range(257)]


# ---- the integer algorithm (the same in modview.c) ----------------------------------------------------------
X16_NOON = round((180.0 - LON_LEFT) * W * 16 / 360.0)     # x (1/16 px) of the subsolar point at 0:00 UT


def subsolar_x16(utc_secs_of_day, yday, eot_tab):
    i, f = yday >> 2, yday & 3
    eot = eot_tab[i] + (((eot_tab[i + 1] - eot_tab[i]) * f) >> 2)
    t = utc_secs_of_day + eot
    return (X16_NOON - (t * 16) // 270) % (W * 16)


def day_interval(y, yday, x16, tand_tab, tanlat, acos_tab):
    """(start, length) of the day on map row y in pixels, start in 0..319 (Pacific view)."""
    i, f = yday >> 2, yday & 3
    td = tand_tab[i] + (((tand_tab[i + 1] - tand_tab[i]) * f) >> 2)
    p = -((tanlat[y] * td) >> 15)
    if p >= 256:
        return 0, 0
    if p <= -256:
        return 0, W
    h = acos_tab[p] if p >= 0 else W // 2 - acos_tab[-p]
    return ((x16 >> 4) - h) % W, 2 * h


# ---- labels --------------------------------------------------------------------------------------------
def place_labels(cities_xy, view):
    """Byte column and pixel row of each city's label (name over HH:MM), greedily: right, left, above, below
    of the marker, never outside the map nor over another label or marker."""
    boxes = [((x - 2) // 8, y - 2, (x + 2) // 8 + 1, y + 3) for x, y in cities_xy]   # byte-column boxes
    out = []
    for k, (x, y) in enumerate(cities_xy):
        n = max(len(CITIES[k][0]), 5)
        w = n + 1                                                       # + shadow
        cands = [((x + 4 + 7) // 8, y - 8), ((x - 4) // 8 - w, y - 8), ((x // 8) - n // 2, y - 20),
                 ((x // 8) - n // 2, y + 4), ((x + 4 + 7) // 8, y + 2), ((x - 4) // 8 - w, y + 2),
                 ((x + 4 + 7) // 8, y - 16), ((x - 4) // 8 - w, y - 16)]
        for bx, by in cands:
            box = (bx, by, bx + w, by + 18)
            if bx < 0 or bx + w > W // 8 or by < MAP_Y or by + 18 > MAP_Y + MAP_H:
                continue
            if any(not (box[2] <= b[0] or b[2] <= box[0] or box[3] <= b[1] or b[3] <= box[1]) for b in boxes):
                continue
            break
        else:
            raise SystemExit('%s view: no place for the label of %s' % (view, CITIES[k][0]))
        boxes.append(box)
        out.append((bx, by))
    return out


def city_xy(lat, lon, view):
    proj = projection()
    x = int(proj.x(lon))
    if view == 'atlantic':
        x = (x + ATL_SHIFT) % W
    return x, MAP_Y + int(proj.y(lat))


# ---- C output -----------------------------------------------------------------------------------------------
def c_bytes(name, data, ctype='uint8_t'):
    lines = ['    ' + ', '.join(str(v) for v in data[i:i + 24]) + ',' for i in range(0, len(data), 24)]
    return 'const %s %s[%d] = {\n%s\n};\n' % (ctype, name, len(data), '\n'.join(lines))


def build(outdir):
    land = land_mask()
    zones = home_zones()
    offsets = sorted(set(z[1] for z in zones))
    zid = zone_map(offsets)
    tand, eot = sun_tables()
    land_rle, land_idx = [], []
    for row in land:
        land_idx.append(len(land_rle))
        land_rle += rle_bits(row)
    zone_rle, zone_idx = [], []
    for row in zid:
        zone_idx.append(len(zone_rle))
        zone_rle += rle_ids(row)
    border_max = 0                       # the most border cells of any home zone (modview.c border_build)
    zh, zw = len(zid), len(zid[0])
    for z in set(offsets.index(std) + 1 for _, std, _ in zones):
        n = sum(1 for cy in range(zh) for cx in range(zw) if zid[cy][cx] == z and any(
            not (0 <= cx + dx < zw and 0 <= cy + dy < zh) or zid[cy + dy][cx + dx] != z
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))))
        border_max = max(border_max, n)
    gen = '/* Generated by tools/mkmodern.py - do not edit. Natural Earth data (public domain). */\n'
    h = [gen, '#ifndef WC_MODERN_H', '#define WC_MODERN_H', '', '#include <stdint.h>', '',
         '#define MOD_MAP_Y %d' % MAP_Y, '#define MOD_MAP_H %d' % MAP_H, '#define MOD_HOME_Y %d' % HOME_Y,
         '#define MOD_BAR_Y %d' % BAR_Y, '#define MOD_BAR_X %d' % BAR_X, '#define MOD_RULER_Y %d' % RULER_Y,
         '#define MOD_ATL_SHIFT %d' % ATL_SHIFT, '#define MOD_X16_NOON %dL' % X16_NOON,
         '#define MOD_ZONE_W %d' % (W // ZONE_SCALE), '#define MOD_ZONE_H %d' % (MAP_H // ZONE_SCALE),
         '#define MOD_CITIES %d' % len(CITIES), '#define MOD_HOMES %d' % len(zones),
         '#define MOD_BORDER_MAX %d' % border_max, '',
         'extern const uint8_t mod_palette[4];',
         'extern const uint8_t mod_land_rle[];   /* runs, starting with sea; 255 continues */',
         'extern const uint16_t mod_land_idx[MOD_MAP_H];',
         'extern const uint8_t mod_zone_rle[];   /* runs: zone id << 4 | (length - 1), a longer run split */',
         'extern const uint16_t mod_zone_idx[MOD_ZONE_H];',
         'extern const int16_t mod_tand[93];     /* tan(declination) Q15, every 4 days */',
         'extern const int16_t mod_eot[93];      /* equation of time, s */',
         'extern const int16_t mod_tanlat[MOD_MAP_H];   /* tan(latitude) Q8 of each map row */',
         'extern const uint8_t mod_acos[257];    /* half-width of the day in pixels for p = 0..256 (Q8) */', '',
         'struct mod_city {', '    const char *name;', '    uint16_t x;             /* Pacific view */',
         '    uint8_t y;', '    uint8_t lx[2], ly[2];   /* label: byte column, pixel row; [0] Pacific, [1] Atlantic */',
         '    int16_t std_minutes;', '    uint8_t dst;', '};',
         'extern const struct mod_city mod_cities[MOD_CITIES];', '',
         '/* Home zones (src/core/zones.c order): zone id in the zone map, marker (Pacific x, y; y 0 = none) */',
         'extern const uint8_t mod_home_zone[MOD_HOMES];', 'extern const uint16_t mod_home_x[MOD_HOMES];',
         'extern const uint8_t mod_home_y[MOD_HOMES];', '',
         '/* The clock screens (clockview.c) */',
         '#define CLK_DIG_BX %d' % DIG_BX, '#define CLK_DIG_Y %d' % DIG_Y, '#define CLK_DIG_HOME_Y %d' % DIG_HOME_Y,
         '#define CLK_GRID_BX0 %d' % GRID_BX[0], '#define CLK_GRID_BXD %d' % (GRID_BX[1] - GRID_BX[0]),
         '#define CLK_GRID_Y %d' % GRID_Y, '#define CLK_GRID_DY %d' % GRID_DY,
         '#define CLK_CX %d' % CLK_CX, '#define CLK_CY %d' % CLK_CY, '#define CLK_R %d' % CLK_R,
         '#define CLK_RO %d' % CLK_RO, '#define CLK_ASPECT_Q8 %d' % ASPECT_Q8,
         '#define CLK_HAND_H %d' % HAND_H, '#define CLK_HAND_M %d' % HAND_M, '#define CLK_HAND_S %d' % HAND_S,
         '#define CLK_HAND_TAIL %d' % HAND_TAIL, '#define CLK_TICK_DOT %d' % TICK_DOT,
         '#define CLK_TICK_IN %d' % TICK_IN, '#define CLK_TICK_OUT %d' % TICK_OUT, '#define CLK_NUM_R %d' % NUM_R,
         '#define CLK_PANEL_BX %d' % PANEL_BX, '#define CLK_PANEL_NAME_Y %d' % PANEL_NAME_Y,
         '#define CLK_PANEL_TIME_Y %d' % PANEL_TIME_Y, '#define CLK_PANEL_OFF_Y %d' % PANEL_OFF_Y,
         '#define CLK_LIST_Y %d' % LIST_Y, '#define CLK_LIST_DY %d' % LIST_DY, '#define CLK_LIST_TBX %d' % LIST_TBX,
         'extern const uint16_t clk_sin60[16];   /* sin(6 i degrees) Q8 */',
         'extern const uint8_t clk_face_in[CLK_R + 1], clk_face_out[CLK_RO + 1];   /* half-widths per row */',
         '', '#endif', '']
    pac = [city_xy(c[1], c[2], 'pacific') for c in CITIES]
    atl = [city_xy(c[1], c[2], 'atlantic') for c in CITIES]
    lp, la = place_labels(pac, 'pacific'), place_labels(atl, 'atlantic')
    c = [gen, '#include "modern.h"', '#include "wctime.h"', '',
         c_bytes('mod_palette', [0x00 | PALETTE[0], 0x10 | PALETTE[1], 0x20 | PALETTE[2], 0x30 | PALETTE[3]]),
         c_bytes('mod_land_rle', land_rle), c_bytes('mod_land_idx', land_idx, 'uint16_t'),
         c_bytes('mod_zone_rle', zone_rle), c_bytes('mod_zone_idx', zone_idx, 'uint16_t'),
         c_bytes('mod_tand', tand, 'int16_t'), c_bytes('mod_eot', eot, 'int16_t'),
         c_bytes('mod_tanlat', tanlat_table(), 'int16_t'), c_bytes('mod_acos', acos_table()),
         'const struct mod_city mod_cities[MOD_CITIES] = {']
    for (name, lat, lon, std, rule), (x, y), (bxp, byp), (bxa, bya) in zip(CITIES, pac, lp, la):
        c.append('    {"%s", %d, %d, {%d, %d}, {%d, %d}, %d, DST_%s},' % (name, x, y, bxp, bxa, byp, bya, std, rule))
    c += ['};', '']
    hz, hx, hy = [], [], []
    for name, std, rule in zones:
        hz.append(offsets.index(std) + 1)
        if name in HOME_PLACES:
            x, y = city_xy(*HOME_PLACES[name], 'pacific')
        else:
            x, y = 0, 0
        hx.append(x)
        hy.append(y)
    c += [c_bytes('mod_home_zone', hz), c_bytes('mod_home_x', hx, 'uint16_t'), c_bytes('mod_home_y', hy)]
    sin60, face_in, face_out = clock_tables()
    c += [c_bytes('clk_sin60', sin60, 'uint16_t'), c_bytes('clk_face_in', face_in), c_bytes('clk_face_out', face_out)]
    os.makedirs(outdir, exist_ok=True)
    with open(os.path.join(outdir, 'modern.h'), 'w', newline='\n') as f:
        f.write('\n'.join(h))
    with open(os.path.join(outdir, 'modern.c'), 'w', newline='\n') as f:
        f.write('\n'.join(c))
    print('modern data: land %d B, zones %d B, tables %d B' % (len(land_rle) + 2 * MAP_H, len(zone_rle) + MAP_H,
                                                                2 * 93 * 2 + 2 * MAP_H + 257))
    return {'land': land, 'zid': zid, 'tand': tand, 'eot': eot, 'labels': (lp, la), 'zones': zones,
            'home_zone': hz, 'home_xy': list(zip(hx, hy))}


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('outdir', nargs='?')
    ap.add_argument('--png')
    ap.add_argument('--utc', default='2026-11-01T15:00:00')
    ap.add_argument('--home', default='PRAGUE')
    ap.add_argument('--from-naturalearth', action='store_true',
                    help='regenerate data/world_land.txt and world_zones.txt from input/naturalearth/')
    a = ap.parse_args()
    if a.from_naturalearth:
        write_world_files(sorted(set(z[1] for z in home_zones())))
    d = build(a.outdir or os.path.join(ROOT, 'build', 'gen'))
    if a.png:
        import modref
        utc = datetime.fromisoformat(a.utc).replace(tzinfo=timezone.utc)
        for view in ('pacific', 'atlantic'):
            planes = modref.render(d, utc, [z[0] for z in d['zones']].index(a.home), view)
            modref.write_png(planes, '%s-%s.png' % (a.png, view))
            print('%s-%s.png' % (a.png, view))
