"""The MZ-800's own looks in the emulator against the reference renderers, byte for byte.

    python tests/emu/run_modern.py [--utc 2026-11-01T15:00:05]

On the emulated MZ-800: the time into the test hook, G (the map, 16 colours), compare VRAM planes I-IV with
tools/modref.py at the program's time; M (the Atlantic view), compare; run over a minute change (the moved
day and night and the new clocks are drawn a few rows per frame), compare; M back, compare. G (the digital
clock, 16 colours), compare planes I-IV with tools/clockref.py, again a second later; G (the analog clock),
compare, again over a minute change; G back to the historic look (the text screen and the own glyphs in the
CG-RAM); BREAK (the CG-RAM restored). Then once more acting as without the VRAM extension (test hook flag):
the map and both clocks in 4 colours, planes III and IV empty. Screenshots go to work/emu/.
"""
import argparse
import os
import struct
import sys
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'emu'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from mzemu import Emu, load_map  # noqa: E402
import mkmodern  # noqa: E402
import modref  # noqa: E402
import clockref  # noqa: E402
import mkhistoric  # noqa: E402
import mkglyphs  # noqa: E402
import run_wc  # noqa: E402

EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)
HOME = 'PRAGUE'          # the default home zone on a European machine


def compare(emu, syms, d, view, label, errs, hicolor=True):
    utc = EPOCH + timedelta(seconds=struct.unpack('<I', emu.mem(syms['_tb_last_utc'], 4))[0])
    want = modref.render(d, utc, [z[0] for z in d['zones']].index(HOME), view, hicolor)
    for k in range(4):
        got = emu.region('vram_phys_plane', 0, 8000, sub_id=k)
        bad = [i for i in range(8000) if got[i] != want[k][i]]
        if bad:
            i = bad[0]
            errs.append('%s (%s, %s): plane %s, %d bytes differ, first row %d byte %d: %02X want %02X'
                        % (label, view, utc.time(), 'I II III IV'.split()[k], len(bad), i // 40, i % 40,
                           got[i], want[k][i]))
    emu.screenshot(os.path.join(ROOT, 'work', 'emu', 'modern-%s.png' % label))
    modref.write_png(want, os.path.join(ROOT, 'work', 'emu', 'modern-%s-ref.png' % label))
    return utc


def compare_clock(emu, syms, d, analog, hicolor, label, errs):
    utc = EPOCH + timedelta(seconds=struct.unpack('<I', emu.mem(syms['_tb_last_utc'], 4))[0])
    want = clockref.render(d, utc, [z[0] for z in d['zones']].index(HOME), analog, hicolor)
    for k in range(4):
        got = emu.region('vram_phys_plane', 0, 8000, sub_id=k)
        bad = [i for i in range(8000) if got[i] != want[k][i]]
        if bad:
            i = bad[0]
            errs.append('%s (%s): plane %s, %d bytes differ, first row %d byte %d: %02X want %02X'
                        % (label, utc.time(), 'I II III IV'.split()[k], len(bad), i // 40, i % 40, got[i],
                           want[k][i]))
    emu.screenshot(os.path.join(ROOT, 'work', 'emu', 'clock-%s.png' % label))
    clockref.write_png(want, os.path.join(ROOT, 'work', 'emu', 'clock-%s-ref.png' % label), hicolor)
    return utc


def back_to_historic(emu, syms, data, errs, label):
    check = []
    run_wc.check_screen(emu, data, run_wc.program_time(emu, syms), True, check, 'pacific', True)
    errs += ['historic after %s: %s' % (label, e) for e in check]
    cgram = emu.region('cgram_700', 0, 4096)
    for g in mkglyphs.parse(os.path.join(ROOT, 'data', 'glyphs.txt')):
        o = (g['set'] * 256 + g['code']) * 8
        if list(cgram[o:o + 8]) != g['rows']:
            errs.append('CG-RAM glyph %s missing after %s' % (g['name'], label))
    emu.key('BREAK', 5, 30)
    if emu.region('cgram_700', 0, 4096) != emu.region('cgrom', 0, 4096):
        errs.append('CG-RAM not restored after BREAK (%s)' % label)
    pc = emu.regs()['PC']
    if pc >= 0x1000:
        errs.append('after BREAK PC %04X is not in the monitor (%s)' % (pc, label))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--utc', default='2026-11-01T15:00:05')
    a = ap.parse_args()
    utc0 = datetime.fromisoformat(a.utc).replace(tzinfo=timezone.utc)
    d = mkmodern.build(os.path.join(ROOT, 'build', 'test', 'gen'))
    syms = load_map(os.path.join(ROOT, 'build', 'worldclock.map'))
    data = mkhistoric.parse(os.path.join(ROOT, 'data', 'historic.txt'))
    errs = []
    with Emu('mz800emu.exe') as emu:
        emu.run_mzf(os.path.join(ROOT, 'build', 'worldclock.mzf'))
        emu.poke(syms['_test_hook'] + 4, bytes([1]) + struct.pack('<I', int((utc0 - EPOCH).total_seconds())))
        emu.run(50)
        emu.key('G', 3, 150)
        compare(emu, syms, d, 'pacific', 'enter', errs)
        emu.key('M', 3, 150)
        t = compare(emu, syms, d, 'atlantic', 'atlantic', errs)
        # over the next minute change, then far enough for the spread redraw
        emu.run(int((60 - t.second + 10) * 50))
        compare(emu, syms, d, 'atlantic', 'next-minute', errs)
        emu.key('M', 3, 150)
        compare(emu, syms, d, 'pacific', 'back-pacific', errs)
        emu.key('G', 3, 50)
        compare_clock(emu, syms, d, False, True, 'digital-16', errs)
        emu.run(75)
        compare_clock(emu, syms, d, False, True, 'digital-16-next', errs)
        emu.key('G', 3, 50)
        t = compare_clock(emu, syms, d, True, True, 'analog-16', errs)
        emu.run(int((60 - t.second + 3) * 50))                  # over the next minute change
        compare_clock(emu, syms, d, True, True, 'analog-16-minute', errs)
        emu.key('G', 3, 50)
        emu.screenshot(os.path.join(ROOT, 'work', 'emu', 'modern-back-historic.png'))
        back_to_historic(emu, syms, data, errs, 'G')
    # without the VRAM extension: the map and the clocks in 4 colours
    with Emu('mz800emu.exe') as emu:
        emu.run_mzf(os.path.join(ROOT, 'build', 'worldclock.mzf'))
        emu.poke(syms['_test_hook'] + 4, bytes([3]) + struct.pack('<I', int((utc0 - EPOCH).total_seconds())))
        emu.run(50)
        emu.key('G', 3, 150)
        compare(emu, syms, d, 'pacific', 'enter-4', errs, False)
        emu.key('G', 3, 50)
        compare_clock(emu, syms, d, False, False, 'digital-4', errs)
        emu.key('G', 3, 50)
        compare_clock(emu, syms, d, True, False, 'analog-4', errs)
        emu.key('G', 3, 50)
        back_to_historic(emu, syms, data, errs, 'G (4 colours)')
    print('mz800 modern', 'OK' if not errs else 'FAIL\n  ' + '\n  '.join(errs))
    sys.exit(1 if errs else 0)


if __name__ == '__main__':
    main()
