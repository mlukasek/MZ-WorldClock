"""Screenshots for the README: the program in the emulator, the screen rebuilt from its VRAM at 2x with square
pixels (640x400), as an emulator window or today's monitor shows it. Standard library only (tools/cgrom.py:
the CG-ROMs from the emulator sources for the text screens).

    python tools/screenshots.py [--utc 2026-11-01T15:04:30] [--out docs/img]

historic-eu.png      MZ-700 (EU), the period view
historic-jp.png      MZ-700 (JP), the period view with the hiragana title
historic-atl.png     MZ-700 (EU) after SPACE, Europe in the middle
map.png              MZ-800 with the VRAM extension, the map (16 colours)
digital.png          MZ-800, the digital clock
analog.png           MZ-800, the analog clock
"""
import argparse
import os
import struct
import sys
from datetime import datetime, timezone

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'emu'))
import cgrom  # noqa: E402
import mkhistoric  # noqa: E402
import mkmodern  # noqa: E402
import modref  # noqa: E402
from mzemu import Emu, load_map  # noqa: E402

EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)
MZF = os.path.join(ROOT, 'build', 'worldclock.mzf')


def start(emu, syms, utc, frames):
    emu.run_mzf(MZF)
    emu.poke(syms['_test_hook'] + 4, bytes([1]) + struct.pack('<I', int((utc - EPOCH).total_seconds())))
    emu.run(frames)


def save_text(emu, rom, path, view='pacific'):
    """The text screen, once the colons of the clocks are on (they blink)"""
    data = mkhistoric.parse(os.path.join(ROOT, 'data', 'historic.txt'))
    row, col = mkhistoric.clock_positions(data, view)[0]
    colon = mkhistoric.to_display(':')[0]
    for _ in range(60):
        if emu.text_dump()[0][row * 40 + col + 2] == colon:
            break
        emu.run(1)
    chars, attrs = emu.text_dump()
    w, h, rows = cgrom.render_screen(rom, chars, attrs, 2)
    cgrom.write_png(path, w, h, rows)
    print(path)


def save_gfx(emu, palette, path):
    """The four planes; colours 0-3 through `palette` (IGRB), 4-15 IGRB as they are"""
    planes = [emu.region('vram_phys_plane', 0, 8000, sub_id=k) for k in range(4)]
    rgb = [modref.MZ800_RGB[palette[c] if c < 4 else c] for c in range(16)]
    rows = []
    for y in range(200):
        line = bytearray()
        for x in range(320):
            i, b = y * 40 + x // 8, x % 8
            c = rgb[sum(((planes[k][i] >> b) & 1) << k for k in range(4))]
            line += bytes([c >> 16, (c >> 8) & 255, c & 255]) * 2
        rows += [bytes(line)] * 2
    cgrom.write_png(path, 640, 400, rows)
    print(path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--utc', default='2026-11-01T15:04:30')
    ap.add_argument('--out', default=os.path.join(ROOT, 'docs', 'img'))
    a = ap.parse_args()
    utc = datetime.fromisoformat(a.utc).replace(tzinfo=timezone.utc)
    os.makedirs(a.out, exist_ok=True)
    syms = load_map(os.path.join(ROOT, 'build', 'worldclock.map'))
    out = lambda name: os.path.join(a.out, name)  # noqa: E731
    with Emu('mz700emu-pal.exe', rom='EU') as emu:
        start(emu, syms, utc, 650)                 # the keys under the ruler gone
        save_text(emu, cgrom.load('EU'), out('historic-eu.png'))
        emu.key('SPACE', 3, 50)
        save_text(emu, cgrom.load('EU'), out('historic-atl.png'), 'atlantic')
    with Emu('mz700emu-ntsc.exe', rom='JP') as emu:
        start(emu, syms, utc, 780)
        save_text(emu, cgrom.load('JP'), out('historic-jp.png'))
    with Emu('mz800emu.exe') as emu:
        start(emu, syms, utc, 100)
        emu.key('RIGHT', 3, 150)
        save_gfx(emu, mkmodern.PALETTE, out('map.png'))
        emu.key('RIGHT', 3, 50)
        save_gfx(emu, [0, 1, 2, 3], out('digital.png'))
        emu.key('RIGHT', 3, 50)
        save_gfx(emu, [0, 1, 2, 3], out('analog.png'))


if __name__ == '__main__':
    main()
