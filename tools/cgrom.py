"""Sharp MZ character generator ROMs and a small PNG writer (standard library only).

The CG-ROM images are read at run time from the mz800emu sources next to this repository (they are (c) Sharp
and never stored in this repository):
    ..\\mz800emu\\src\\emulator\\mzarch\\mz700\\memory\\ROM\\ROM_MZ700_EU_CGROM.c   ('EU')
    ..\\mz800emu\\src\\emulator\\mzarch\\mz700\\memory\\ROM\\ROM_MZ700_JP_CGROM.c   ('JP')
    ..\\mz800emu\\src\\emulator\\mzarch\\mz800\\memory\\ROM\\ROM_MZ800_CGROM.c      ('800')
Environment: MZ800EMU_SRC (default ..\\mz800emu next to this repo).

A CG-ROM has 512 glyphs of 8 bytes (one byte per row, top row first): set 0 = codes 00h-FFh, set 1
(attribute bit 7) = the next 256. In a row byte, bit 0 is the leftmost pixel.

    python tools/cgrom.py sheet EU work/cg/eu.png      all 512 glyphs, 16 per row, scaled
"""
import os
import re
import struct
import sys
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
EMU_SRC = os.environ.get('MZ800EMU_SRC', os.path.join(os.path.dirname(ROOT), 'mz800emu'))
ROM_DIR = os.path.join(EMU_SRC, 'src', 'emulator', 'mzarch')
FILES = {'EU': os.path.join(ROM_DIR, 'mz700', 'memory', 'ROM', 'ROM_MZ700_EU_CGROM.c'),
         'JP': os.path.join(ROM_DIR, 'mz700', 'memory', 'ROM', 'ROM_MZ700_JP_CGROM.c'),
         '800': os.path.join(ROM_DIR, 'mz800', 'memory', 'ROM', 'ROM_MZ800_CGROM.c')}

# MZ-700 colours (attribute bits 6-4 foreground, 2-0 background): GRB order 0 black ... 7 white
COLOURS = [(0, 0, 0), (0, 0, 255), (255, 0, 0), (255, 0, 255), (0, 255, 0), (0, 255, 255), (255, 255, 0),
           (255, 255, 255)]


def load(kind):
    """CG-ROM `kind` ('EU', 'JP', '800') as bytes (4096)."""
    text = open(FILES[kind], encoding='latin-1').read()
    body = text[text.index('{') + 1:text.rindex('}')]
    data = bytes(int(x, 16) for x in re.findall(r'0x([0-9a-fA-F]{2})', body))
    if len(data) < 4096:
        raise ValueError('%s: %d bytes' % (FILES[kind], len(data)))
    return data[:4096]


def glyph(rom, code, set1=False):
    """8 rows of 8 pixels (lists of 0/1, left to right) of `code` in set 0 or 1."""
    base = ((256 if set1 else 0) + code) * 8
    return [[(rom[base + y] >> x) & 1 for x in range(8)] for y in range(8)]


def write_png(path, width, height, rows):
    """rows: list of `height` bytes objects, each width*3 bytes RGB."""
    def chunk(tag, data):
        return struct.pack('>I', len(data)) + tag + data + struct.pack('>I', zlib.crc32(tag + data) & 0xFFFFFFFF)
    raw = b''.join(b'\x00' + bytes(r) for r in rows)
    png = (b'\x89PNG\r\n\x1a\n' + chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 2, 0, 0, 0))
           + chunk(b'IDAT', zlib.compress(raw, 9)) + chunk(b'IEND', b''))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(png)


def render_screen(rom, chars, attrs, scale=2):
    """40x25 MZ-700 text screen -> (width, height, RGB rows)."""
    w, h = 320 * scale, 200 * scale
    rows = []
    for py in range(200):
        line = bytearray()
        cy, gy = divmod(py, 8)
        for cx in range(40):
            i = cy * 40 + cx
            a = attrs[i]
            fg, bg = COLOURS[(a >> 4) & 7], COLOURS[a & 7]
            g = glyph(rom, chars[i], bool(a & 0x80))[gy]
            for px in g:
                line += bytes(fg if px else bg) * scale
        rows += [bytes(line)] * scale
    return w, h, rows


def sheet(rom, path, scale=3):
    """All 512 glyphs, 16 per row with a 2-pixel grid (grey), set 1 below set 0; cell (row r, col c) = code
    r*16+c (set 1: rows 16-31)."""
    cell = 8 * scale + 2
    w, h = 16 * cell + 2, 32 * cell + 2
    img = [bytearray(b'\x60\x60\x60' * w) for _ in range(h)]
    for n in range(512):
        r, c = divmod(n, 16)
        g = glyph(rom, n & 255, n >= 256)
        for y in range(8):
            for x in range(8):
                col = b'\xff\xff\xff' if g[y][x] else b'\x00\x00\x00'
                for sy in range(scale):
                    row = img[2 + r * cell + y * scale + sy]
                    o = (2 + c * cell + x * scale) * 3
                    row[o:o + 3 * scale] = col * scale
    write_png(path, w, h, img)


if __name__ == '__main__':
    if len(sys.argv) == 4 and sys.argv[1] == 'sheet':
        sheet(load(sys.argv[2]), sys.argv[3])
    else:
        print(__doc__)
        sys.exit(1)
