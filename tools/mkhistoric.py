"""The historic screen: data/historic.txt -> C tables (and PNG previews). Standard library only.

    python tools/mkhistoric.py data/historic.txt build/gen          historic.c, historic.h
    python tools/mkhistoric.py data/historic.txt --png work/historic --time 00:00 --bar 17
                    work/historic-eu.png, -jp.png and -eu-atl.png (the continents swapped, key M), the clocks
                    showing Tokyo time --time in standard time (as in the photos)

Two views: 'pacific' (the period screen) and 'atlantic' (section [atlantic]: the map rotated, the names and
clocks moved with it). The PNG needs the CG-ROMs from the mz800emu sources (tools/cgrom.py); the C tables
do not.
"""
import argparse
import os
import re
import sys

COLOURS = ['black', 'blue', 'red', 'magenta', 'green', 'cyan', 'yellow', 'white']
DST_RULES = ['none', 'EU', 'US', 'AU']
MAP_ROWS = range(2, 22)            # text rows of the map area: their names and clocks move with the map

# ASCII 20h-5Fh -> display code (the monitor's table at 0A92h, the same in 1Z-013A and 1Z-009B)
ASCII_DISPLAY = [0x00, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6B, 0x6A, 0x2F, 0x2A, 0x2E, 0x2D,
                 0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x4F, 0x2C, 0x51, 0x2B, 0x57, 0x49,
                 0x55, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07, 0x08, 0x09, 0x0A, 0x0B, 0x0C, 0x0D, 0x0E, 0x0F,
                 0x10, 0x11, 0x12, 0x13, 0x14, 0x15, 0x16, 0x17, 0x18, 0x19, 0x1A, 0x52, 0x59, 0x54, 0x50, 0x45]


def to_display(text):
    out = []
    for ch in text:
        c = ord(ch)
        if not 0x20 <= c < 0x60:
            raise ValueError('no display code for %r' % ch)
        out.append(ASCII_DISPLAY[c - 0x20])
    return out


class Screen:
    def __init__(self):
        self.chars = [0] * 1000
        self.attrs = [0] * 1000

    def put(self, row, col, code, colour, set1=False):
        if not (0 <= row < 25 and 0 <= col < 40):
            raise ValueError('cell %d,%d outside the screen' % (row, col))
        i = row * 40 + col
        self.chars[i] = code
        self.attrs[i] = (0x80 if set1 else 0) | COLOURS.index(colour) << 4


def parse(path):
    data = {'map': [], 'screen': [], 'title EU': [], 'title JP': [], 'bar': None, 'clocks': [],
            'atlantic': {'shift': 0, 'places': {}}}
    section = None
    for n, raw in enumerate(open(path, encoding='utf-8'), 1):
        line = raw.rstrip('\n')
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        m = re.match(r'^\[(.+)\]$', line.strip())
        if m:
            section = m.group(1)
            if section not in data:
                raise SystemExit('%s:%d: unknown section [%s]' % (path, n, section))
            continue
        try:
            if section == 'map':
                if len(line) != 80 or set(line) - set('#.'):
                    raise ValueError('map rows are 80 characters of # and .')
                data['map'].append([c == '#' for c in line])
            elif section in ('screen', 'title EU', 'title JP'):
                row, col, colour, kind, rest = line.split(None, 4)
                if colour not in COLOURS:
                    raise ValueError('colour %s' % colour)
                cells = []
                if kind == 'text':
                    cells = [(c, False) for c in to_display(rest)]
                elif kind == 'codes':
                    for tok in rest.split():
                        tok, _, rep = tok.partition('*')
                        set1 = len(tok) == 3 and tok[0] == '1'
                        code = int(tok[1:] if set1 else tok, 16)
                        cells += [(code, set1)] * (int(rep) if rep else 1)
                else:
                    raise ValueError('kind %s (text or codes)' % kind)
                data[section].append((int(row), int(col), colour, cells, rest if kind == 'text' else None))
            elif section == 'bar':
                row, col, cells, colour, code = line.split()
                data['bar'] = (int(row), int(col), int(cells), colour, int(code, 16))
            elif section == 'clocks':
                row, col, name, offset, rule = line.split()
                if rule not in DST_RULES:
                    raise ValueError('DST rule %s' % rule)
                data['clocks'].append((int(row), int(col), name, int(offset), rule))
            elif section == 'atlantic':
                f = line.split()
                if f[0] == 'shift':
                    data['atlantic']['shift'] = int(f[1])
                    if data['atlantic']['shift'] % 2:
                        raise ValueError('the shift must be even (whole characters)')
                else:
                    data['atlantic']['places'][f[0]] = tuple(int(x) for x in f[1:5])
            else:
                raise ValueError('line outside a section')
        except ValueError as e:
            raise SystemExit('%s:%d: %s' % (path, n, e))
    if len(data['map']) != 50:
        raise SystemExit('%s: the map has %d rows, not 50' % (path, len(data['map'])))
    return data


def view_layout(data, view):
    """(map rows, [screen items], [clock positions (row, col)]) of a view; checks that nothing crosses the
    screen edge and that no two names or clocks overlap."""
    items = list(data['screen'])
    clocks = [(row, col) for row, col, _, _, _ in data['clocks']]
    mp = data['map']
    if view == 'atlantic':
        a = data['atlantic']
        sh = a['shift']
        mp = [[r[(c + sh) % 80] for c in range(80)] for r in mp]
        places = a['places']
        moved = []
        for row, col, colour, cells, text in items:
            if row in MAP_ROWS:
                if text in places:
                    row, col = places[text][0], places[text][1]
                else:
                    col = (col - sh // 2) % 40
            moved.append((row, col, colour, cells, text))
        items = moved
        clocks = []
        for row, col, name, _, _ in data['clocks']:
            if name in places:
                clocks.append((places[name][2], places[name][3]))
            else:
                clocks.append((row, (col - sh // 2) % 40))
    used = {}
    for row, col, colour, cells, text in items:
        if col + len(cells) > 40:
            raise SystemExit('%s view: %r at %d,%d crosses the screen edge' % (view, text or cells, row, col))
        if row in MAP_ROWS:
            for k in range(len(cells)):
                if (row, col + k) in used:
                    raise SystemExit('%s view: %r overlaps %r' % (view, text, used[(row, col + k)]))
                used[(row, col + k)] = text
    for (row, col), (_, _, name, _, _) in zip(clocks, data['clocks']):
        if col + 5 > 40:
            raise SystemExit('%s view: the clock of %s crosses the screen edge' % (view, name))
        for k in range(5):
            if (row, col + k) in used:
                raise SystemExit('%s view: the clock of %s overlaps %r' % (view, name, used[(row, col + k)]))
            used[(row, col + k)] = name + ' clock'
    return mp, items, clocks


def compose(data, title=None, view='pacific'):
    """The static screen of a view: map, then [screen], then the title `title` ('EU' / 'JP' / None)."""
    mp, items, _ = view_layout(data, view)
    s = Screen()
    for cy in range(25):
        for cx in range(40):
            b = (mp[cy * 2][cx * 2] | mp[cy * 2][cx * 2 + 1] << 1 | mp[cy * 2 + 1][cx * 2] << 2
                 | mp[cy * 2 + 1][cx * 2 + 1] << 3)
            if b:
                s.put(cy, cx, 0xF0 | b, 'blue')
    for row, col, colour, cells, _ in items + (data['title ' + title] if title else []):
        for k, (code, set1) in enumerate(cells):
            s.put(row, col + k, code, colour, set1)
    return s


def clock_positions(data, view='pacific'):
    return view_layout(data, view)[2]


def c_array(name, values, ctype='uint8_t'):
    lines = []
    for i in range(0, len(values), 20):
        lines.append('    ' + ', '.join('0x%02X' % v for v in values[i:i + 20]) + ',')
    return 'const %s %s[%d] = {\n%s\n};\n' % (ctype, name, len(values), '\n'.join(lines))


def write_c(data, outdir, src):
    os.makedirs(outdir, exist_ok=True)
    pac = compose(data)
    atl = compose(data, view='atlantic')
    titles = {}
    for t in ('EU', 'JP'):
        s = Screen()
        for row, col, colour, cells, _ in data['title ' + t]:
            if row != 0:
                raise SystemExit('titles must be in row 0')
            for k, (code, set1) in enumerate(cells):
                s.put(row, col + k, code, colour, set1)
        titles[t] = (s.chars[:40], s.attrs[:40])
    bar = data['bar']
    gen = '/* Generated by tools/mkhistoric.py from %s - do not edit. */\n' % src.replace('\\', '/')
    h = [gen, '#ifndef WC_HISTORIC_H', '#define WC_HISTORIC_H', '', '#include <stdint.h>', '',
         '/* The static screens (map, title line, ruler, city names) without the title text and the clocks:',
         '   the period screen (Pacific in the middle) and the continents swapped (Atlantic in the middle) */',
         'extern const uint8_t hist_chars[1000];', 'extern const uint8_t hist_attrs[1000];',
         'extern const uint8_t hist_atl_chars[1000];', 'extern const uint8_t hist_atl_attrs[1000];', '',
         '/* Row 0: the title for the European (WORLD CLOCK) and the Japanese CG-ROM (hiragana, set 1) */',
         'extern const uint8_t hist_title_eu_chars[40];', 'extern const uint8_t hist_title_eu_attrs[40];',
         'extern const uint8_t hist_title_jp_chars[40];', 'extern const uint8_t hist_title_jp_attrs[40];', '',
         '/* The seconds bar: full after 60 s */',
         '#define HIST_BAR_ROW %d' % bar[0], '#define HIST_BAR_COL %d' % bar[1], '#define HIST_BAR_CELLS %d' % bar[2],
         '#define HIST_BAR_ATTR 0x%02X' % (COLOURS.index(bar[3]) << 4), '#define HIST_BAR_CHAR 0x%02X' % bar[4], '',
         '/* DST rules of the clocks */']
    h += ['#define DST_%s %d' % (r.upper(), i) for i, r in enumerate(DST_RULES)]
    h += ['', 'struct hist_clock {', '    uint8_t row, col;      /* HH:MM in yellow, period view */',
          '    uint8_t row_atl, col_atl;  /* continents swapped */',
          '    int16_t utc_minutes;   /* standard time offset */', '    uint8_t dst;           /* DST_... */', '};', '',
          '#define HIST_CLOCKS %d' % len(data['clocks']), 'extern const struct hist_clock hist_clocks[HIST_CLOCKS];',
          '#define HIST_CLOCK_ATTR 0x%02X' % (COLOURS.index('yellow') << 4), '', '#endif', '']
    c = [gen, '#include "historic.h"', '',
         c_array('hist_chars', pac.chars), c_array('hist_attrs', pac.attrs),
         c_array('hist_atl_chars', atl.chars), c_array('hist_atl_attrs', atl.attrs),
         c_array('hist_title_eu_chars', titles['EU'][0]), c_array('hist_title_eu_attrs', titles['EU'][1]),
         c_array('hist_title_jp_chars', titles['JP'][0]), c_array('hist_title_jp_attrs', titles['JP'][1]),
         'const struct hist_clock hist_clocks[HIST_CLOCKS] = {']
    for (row, col, name, off, rule), (ra, ca) in zip(data['clocks'], clock_positions(data, 'atlantic')):
        c.append('    {%d, %d, %d, %d, %d, DST_%s},   /* %s */' % (row, col, ra, ca, off, rule.upper(), name))
    c += ['};', '']
    with open(os.path.join(outdir, 'historic.h'), 'w', newline='\n') as f:
        f.write('\n'.join(h))
    with open(os.path.join(outdir, 'historic.c'), 'w', newline='\n') as f:
        f.write('\n'.join(c))


def write_png(data, prefix, tokyo, bar_cells):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import cgrom
    hh, mm = map(int, tokyo.split(':'))
    for t, view, suffix in (('EU', 'pacific', 'eu'), ('JP', 'pacific', 'jp'), ('EU', 'atlantic', 'eu-atl')):
        s = compose(data, t, view)
        for (row, col), (_, _, name, off, rule) in zip(clock_positions(data, view), data['clocks']):
            # the photos show standard time; Tokyo is UTC+9
            m = (hh * 60 + mm - 540 + off) % 1440
            for k, code in enumerate(to_display('%02d:%02d' % (m // 60, m % 60))):
                s.put(row, col + k, code, 'yellow')
        row, col, cells, colour, code = data['bar']
        for k in range(min(bar_cells, cells)):
            s.put(row, col + k, code, colour)
        w, h, rows = cgrom.render_screen(cgrom.load(t), s.chars, s.attrs, 2)
        cgrom.write_png('%s-%s.png' % (prefix, suffix), w, h, rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('outdir', nargs='?')
    ap.add_argument('--png', help='prefix of the preview PNGs')
    ap.add_argument('--time', default='00:00', help='Tokyo time shown in the preview')
    ap.add_argument('--bar', type=int, default=17, help='cells of the seconds bar in the preview')
    a = ap.parse_args()
    data = parse(a.src)
    if a.outdir:
        write_c(data, a.outdir, a.src)
    if a.png:
        write_png(data, a.png, a.time, a.bar)


if __name__ == '__main__':
    main()
