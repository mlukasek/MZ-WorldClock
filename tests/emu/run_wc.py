"""Run build/worldclock.mzf on the emulated machines and check what it shows.

    python tests/emu/run_wc.py [--machine eu|jp|eu-ntsc|mz800|mz1500|all] [--utc 2026-11-01T15:00:10] [--dialog]

For each machine: load the MZF, put the UTC time into the test hook (2003h, skips the dialog), run 2 s,
then check the detected machine, the title, every city's HH:MM (against Python's zoneinfo; needs the tzdata
package on Windows), the colons, the seconds bar and the keys under it; after 600 frames the keys gone; SPACE
(the continents swapped), M (back), CR (the time dialog), BREAK (out of it); press BREAK and check that the
monitor runs again.
--dialog instead types a date and time into the dialog (zone PRAGUE / TOKYO by machine) and checks the
clocks. Screenshots go to work/emu/.
"""
import argparse
import os
import struct
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'emu'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
from mzemu import Emu, load_map, ASCII_TO_DISPLAY  # noqa: E402
import mkhistoric  # noqa: E402
import mkglyphs  # noqa: E402

EPOCH = datetime(2000, 1, 1, tzinfo=timezone.utc)
# own glyphs: the MZ-800 (CG-RAM: hiragana title, 1 s bar steps), the MZ-1500 (PCG: 1 s bar steps)
FINE = {'mz800', 'mz1500'}
HIRAGANA = {'mz800'}
MACHINES = {  # name: (executable, ROM, jp, ntsc, model)
    'eu': ('mz700emu-pal.exe', 'EU', 0, 0, 0),
    'jp': ('mz700emu-ntsc.exe', 'JP', 1, 1, 0),
    'eu-ntsc': ('mz700emu-ntsc.exe', 'EU', 0, 1, 0),
    'mz800': ('mz800emu.exe', None, 0, 0, 1),
    'mz1500': ('mz1500emu.exe', None, 1, 1, 2),
}
TZ = {'MOSCOW': 'Europe/Moscow', 'PARIS': 'Europe/Paris', 'PEKIN': 'Asia/Shanghai',
      'L.ANGELS': 'America/Los_Angeles', 'TOKYO': 'Asia/Tokyo', 'WASHINGTON': 'America/New_York',
      'REO': 'America/Sao_Paulo', 'S.AFRICA': 'Africa/Johannesburg', 'SYDNEY': 'Australia/Sydney'}


def disp(text):
    return bytes(ASCII_TO_DISPLAY[c] for c in text)


def hint_row(wide):
    """Row 24 with the keys (histview.c hist_hint): <> are the cursor key glyphs C4h, C3h; <>:VIEW only on
    the MZ-800, the row centred; white."""
    text = 'SPACE:TURN  <>:VIEW  CR:TIME  BREAK:END' if wide else 'SPACE:TURN  CR:TIME  BREAK:END'
    at = (40 - len(text)) // 2
    chars = [0] * 40
    for k, ch in enumerate(text):
        chars[at + k] = {'<': 0xC4, '>': 0xC3}.get(ch) or mkhistoric.to_display(ch)[0]
    return chars, [0x70] * 40


def check_screen(emu, data, utc, jp, errs, view='pacific', fine=False, pcg=False, hint=None):
    """The whole screen against the data: the static part of `view` (map, names, title, ruler), the clocks
    at the view's places in the time `utc` (zoneinfo), the seconds bar; row 24 empty or `hint` (hint_row)."""
    chars, attrs = emu.text_dump()
    # jp: the hiragana title, but WORLD CLOCK in the Atlantic view (Europe in the middle)
    want = mkhistoric.compose(data, 'JP' if jp and view == 'pacific' else 'EU', view)
    if hint:
        want.chars[960:1000], want.attrs[960:1000] = hint
    clocks = mkhistoric.clock_positions(data, view)
    skip = set()
    for row, col in clocks:
        skip.update(range(row * 40 + col, row * 40 + col + 5))
    brow, bcol, bcells, bcolour, bcode = data['bar']
    skip.update(range(brow * 40 + bcol, brow * 40 + bcol + bcells))
    bad = [i for i in range(1000) if i not in skip and (chars[i], attrs[i]) != (want.chars[i], want.attrs[i])]
    if bad:
        errs.append('%s view: %d cells differ, first at row %d col %d' % (view, len(bad), bad[0] // 40, bad[0] % 40))
    for (row, col), (_, _, name, off, rule) in zip(clocks, data['clocks']):
        local = utc.astimezone(ZoneInfo(TZ[name]))
        p = row * 40 + col
        if (chars[p:p + 2], chars[p + 3:p + 5]) != (disp('%02d' % local.hour), disp('%02d' % local.minute)):
            errs.append('%s view, %s: %s want %02d:%02d' % (view, name, chars[p:p + 5].hex(), local.hour, local.minute))
        if attrs[p] != 0x60:
            errs.append('%s: attribute %02X' % (name, attrs[p]))
    halves, state = 0, 0
    # MZ-1500: a half cell is an empty text cell with the PCG on (PCGHI bit 3 at DC00h + position)
    pcghi = emu.mem(0xDC00 + brow * 40 + bcol, bcells) if pcg else bytes(bcells)
    for k in range(bcells):
        c, a = chars[brow * 40 + bcol + k], attrs[brow * 40 + bcol + k]
        if pcghi[k] & 0x08 and c == 0x00 and state == 0:
            halves += 1
            state = 1
        elif c == bcode and a == 0x30 and state == 0:
            halves += 2
        elif c == bcode and a == 0xB0 and state == 0:
            halves += 1
            state = 1
        elif c == 0x00:
            state = 1
        else:
            errs.append('bar cell %d: %02X/%02X' % (k, c, a))
            break
    want_h = utc.second + 1 if fine else (utc.second + 1) & ~1
    if abs(halves - want_h) > 2 or (not fine and halves % 2):
        errs.append('bar: %d halves, want about %d' % (halves, want_h))


def program_time(emu, syms):
    return EPOCH + timedelta(seconds=struct.unpack('<I', emu.mem(syms['_tb_last_utc'], 4))[0])


# The state the MZ-800 IPL leaves when it starts a program in MZ-800 mode (rear switch SW1): native mode
# (DMD 0), VRAM and CG-ROM not mapped, palette black. The emulator preview cannot boot that way, so this stub
# at B000h (free RAM between the BSS and the stack) sets it up and jumps to the program.
NATIVE_STUB = bytes([0xF3, 0x3E, 0x00, 0xD3, 0xCE, 0xDB, 0xE1,      # DI; OUT (CEh),0; IN A,(E1h)
                     0x3E, 0x00, 0xD3, 0xF0, 0x3E, 0x10, 0xD3, 0xF0,  # palette 0-3 black
                     0x3E, 0x20, 0xD3, 0xF0, 0x3E, 0x30, 0xD3, 0xF0,
                     0xC3, 0x00, 0x20])                           # JP 2000h


def run_machine(name, utc0, dialog, mzf, syms, data, native=False):
    exe, rom, jp, ntsc, model = MACHINES[name]
    errs = []
    fps = 60 if ntsc else 50
    with Emu(exe, rom=rom) as emu:
        emu.run_mzf(mzf)
        if native:
            emu.poke(0xB000, NATIVE_STUB)
            emu.set_pc(0xB000)
        hook = syms['_test_hook']
        if emu.mem(hook, 4) != b'WCTH':
            return ['no test hook at %04X' % hook]
        if not dialog:
            secs = int((utc0 - EPOCH).total_seconds())
            emu.poke(hook + 4, bytes([1]) + struct.pack('<I', secs))
            emu.run(2 * fps)
            utc = utc0 + timedelta(seconds=2)
        else:
            emu.run(fps)
            lines = emu.text_lines()
            if 'SET THE DATE' not in lines[4]:
                return ['no time dialog: %r' % lines[4]]
            zone = ZoneInfo('Asia/Tokyo' if jp else 'Europe/Prague')
            local = utc0.astimezone(zone)
            for ch in local.strftime('%Y%m%d%H%M'):
                emu.key(ch, 2, 2)
            emu.key('CR', 2, 1)
            # the seconds start at 0 when CR is read
            utc = local.replace(second=0).astimezone(timezone.utc)
            emu.run(2 * fps)
            utc += timedelta(seconds=2)
        m = emu.mem(syms['_mach'], 7)
        got = (m[0], m[1], m[2], m[3] | m[4] << 8, m[5] | m[6] << 8)
        want_lines = 262 if ntsc else 312
        if got[:3] != (model, jp, ntsc) or got[3] != want_lines or got[4] != (15700 if ntsc else 15611):
            errs.append('detection %s, want model %d jp %d ntsc %d lines %d' % (got, model, jp, ntsc, want_lines))
        hira, fine = jp or name in HIRAGANA, name in FINE
        # the keys under the ruler for 500 frames after the start
        check_screen(emu, data, utc, hira, errs, fine=fine, pcg=name == 'mz1500', hint=hint_row(model == 1))
        if name in HIRAGANA:                           # the own glyphs in the CG-RAM
            cgram = emu.region('cgram_700', 0, 4096)
            for g in mkglyphs.parse(os.path.join(ROOT, 'data', 'glyphs.txt')):
                o = (g['set'] * 256 + g['code']) * 8
                if list(cgram[o:o + 8]) != g['rows']:
                    errs.append('CG-RAM glyph %s: %s' % (g['name'], cgram[o:o + 8].hex()))
        emu.screenshot(os.path.join(ROOT, 'work', 'emu', '%s%s%s.png' % (name, '-dialog' if dialog else '',
                                                                       '-native' if native else '')))
        if not dialog:                                  # the keys gone after 500 passes of the main loop
            emu.run(600 - 2 * fps)                      # (one per frame, a few take longer)
            check_screen(emu, data, program_time(emu, syms), hira, errs, 'pacific', fine, name == 'mz1500')
        if not dialog:                                  # SPACE: the continents swapped, M again: back
            emu.key('SPACE', 3, 50)              # the redraw takes ~8 frames, the clocks 9 more
            check_screen(emu, data, program_time(emu, syms), hira, errs, 'atlantic', fine, name == 'mz1500')
            emu.screenshot(os.path.join(ROOT, 'work', 'emu', '%s-atlantic.png' % name))
            emu.key('M', 3, 50)                  # the redraw takes ~8 frames, the clocks 9 more
            check_screen(emu, data, program_time(emu, syms), hira, errs, 'pacific', fine, name == 'mz1500')
            emu.key('CR', 3, 30)                 # CR: the time dialog; BREAK leaves it unchanged
            if 'SET THE DATE' not in emu.text_lines()[4]:
                errs.append('CR: no time dialog')
            emu.key('BREAK', 3, 50)
            check_screen(emu, data, program_time(emu, syms), hira, errs, 'pacific', fine, name == 'mz1500')
        emu.key('BREAK', 5, 30)
        pc = emu.regs().get('PC', emu.regs().get('pc'))
        if pc is None or pc >= 0x1000:
            errs.append('after BREAK PC %s is not in the monitor' % pc)
        chars = emu.text_dump()[0]
        if any(c not in (0x00, 0x6B) for c in chars[40:]):   # cleared, the monitor prompt '*' at the top
            errs.append('screen not cleared after BREAK')
        if name in HIRAGANA and emu.region('cgram_700', 0, 4096) != emu.region('cgrom', 0, 4096):
            errs.append('CG-RAM not restored after BREAK')
        if name == 'mz1500':
            pcghi = emu.mem(0xDC00, 1000)
            if any(b & 0x08 for b in pcghi):
                errs.append('PCG cells still on after BREAK')
    return errs


def run_drift(name, utc0, minutes, mzf, syms):
    """Run `minutes` of emulated time and compare the program's clock with the emulated time. The emulator
    runs exactly 50 / 60 frames per second (15600 / 15720 lines/s), the program divides by 15611 / 15700
    (the real line rates): expected -2.54 s/h on PAL, +4.59 s/h on NTSC."""
    exe, rom, jp, ntsc, model = MACHINES[name]
    fps = 60 if ntsc else 50
    line_rate = 15720 if ntsc else 15600
    count = 15700 if ntsc else 15611
    with Emu(exe, rom=rom) as emu:
        emu.run_mzf(mzf)
        hook = syms['_test_hook']
        secs = int((utc0 - EPOCH).total_seconds())
        emu.poke(hook + 4, bytes([1]) + struct.pack('<I', secs))
        emu.run(fps)
        t0 = struct.unpack('<I', emu.mem(syms['_tb_last_utc'], 4))[0] +             struct.unpack('<H', emu.mem(syms['_tb_last_frac'], 2))[0] / count
        frames = int(minutes * 60 * fps)
        emu.run(frames)
        t1 = struct.unpack('<I', emu.mem(syms['_tb_last_utc'], 4))[0] +             struct.unpack('<H', emu.mem(syms['_tb_last_frac'], 2))[0] / count
    real = frames / fps
    drift = (t1 - t0) - real
    want = real * (line_rate / count - 1)
    print('  %s: %.1f emulated s, clock %+.2f s (%+.2f s/h), expected %+.2f s' %
          (name, real, drift, drift * 3600 / real, want))
    return [] if abs(drift - want) < 0.2 else ['drift %+.2f s, expected %+.2f s' % (drift, want)]


def run_rtc(name, mzf, syms, data):
    """Unicard plugged in, no test hook: the program must take the time from the card's RTC (the emulated
    card returns the host's local time; the program reads it as the local time of its home zone: Prague on
    the European machines, Tokyo on the Japanese one) and show the historic screen at once."""
    exe, rom, jp, ntsc, model = MACHINES[name]
    fps = 60 if ntsc else 50
    errs = []
    home = ZoneInfo('Asia/Tokyo' if jp else 'Europe/Prague')
    with Emu(exe, rom=rom, unicard=True) as emu:
        emu.run_mzf(mzf)
        # up to 2 s waiting for the card's second, the screen, on the MZ-800 0.3 s for the modern look's zone
        # border (mod_prepare), then the clocks one city per frame
        emu.run(4 * fps)
        host = datetime.now().replace(microsecond=0)               # the host's local time, naive
        want = host.replace(tzinfo=home).astimezone(timezone.utc)
        if not emu.mem(syms['_rtc_present'], 1)[0]:
            return ['no RTC found']
        got = EPOCH + timedelta(seconds=struct.unpack('<I', emu.mem(syms['_tb_last_utc'], 4))[0])
        if abs((got - want).total_seconds()) > 3:
            errs.append('clock %s, the card says %s' % (got.isoformat(), want.isoformat()))
        if 3 <= got.second <= 57:                               # not at a minute change
            check_screen(emu, data, got, jp or name in HIRAGANA, errs, fine=name in FINE, pcg=name == 'mz1500',
                         hint=hint_row(model == 1))
        emu.screenshot(os.path.join(ROOT, 'work', 'emu', '%s-rtc.png' % name))
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--machine', default='all')
    ap.add_argument('--utc', default='2026-11-01T15:00:10')
    ap.add_argument('--dialog', action='store_true')
    ap.add_argument('--native-boot', action='store_true', help='MZ-800: start the program in MZ-800 mode')
    ap.add_argument('--drift', type=float, default=0, help='run this many emulated minutes, report the drift')
    ap.add_argument('--rtc', action='store_true', help='Unicard plugged in, the time from its RTC')
    a = ap.parse_args()
    utc0 = datetime.fromisoformat(a.utc).replace(tzinfo=timezone.utc)
    mzf = os.path.join(ROOT, 'build', 'worldclock.mzf')
    syms = load_map(os.path.join(ROOT, 'build', 'worldclock.map'))
    data = mkhistoric.parse(os.path.join(ROOT, 'data', 'historic.txt'))
    names = list(MACHINES) if a.machine == 'all' else [a.machine]
    fails = 0
    for name in names:
        if a.drift:
            errs = run_drift(name, utc0, a.drift, mzf, syms)
        elif a.rtc:
            errs = run_rtc(name, mzf, syms, data)
        else:
            if a.native_boot and MACHINES[name][4] != 1:
                continue
            errs = run_machine(name, utc0, a.dialog, mzf, syms, data, a.native_boot)
        print('%-8s %s' % (name, 'OK' if not errs else 'FAIL\n  ' + '\n  '.join(errs)))
        fails += bool(errs)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
