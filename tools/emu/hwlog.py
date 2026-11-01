"""Reader of the mz800emu HW log (trace-suite hwlog, 24-byte records with a pixel-clock timestamp).

Record: pxclk_total u64, screens_total u32, pxclk_in_screen u32, chip_id u8, sub_event u8, payload 6 B.
One pxclk (GDG tick) = 1/17 721 600 s in the emulator (MZ-800 PAL timing); 1 T = 5 ticks; CTC0 clock = 16
ticks; one TV line = 1136 ticks.

    python tools/emu/hwlog.py work/hw/probe.json     # summary of the CTC0 writes against the line timing
"""
import json
import os
import struct
import sys

CHIP_VIDEO, CHIP_PIO8255, CHIP_CTC8253, CHIP_RD = 0x06, 0x10, 0x11, 0x41
VIDEO_VBLN_START, VIDEO_VBLN_END, VIDEO_HBLN_START, VIDEO_HBLN_END = 1, 2, 5, 6
CTC_CONTROL, CTC_COUNTER = 1, 2

PX_PER_T = 5
PX_PER_CTC = 16
PX_PER_LINE = 1136
PX_HZ = 17_721_600            # emulated (the real crystal is 17 734 475 Hz)


def events(meta_path):
    """Yield (pxclk, chip, sub, payload bytes) from all chunks of a recording."""
    meta = json.load(open(meta_path))
    d = os.path.dirname(meta_path)
    rec = struct.Struct('<QIIBB6s')
    for ch in meta['chunks']:
        data = open(os.path.join(d, ch['file']), 'rb').read()
        for off in range(0, len(data) - 23, 24):
            px, _scr, _pis, chip, sub, pl = rec.unpack_from(data, off)
            yield px, chip, sub, pl


def ctc0_writes(evs):
    """[(pxclk, kind, value)] of writes to counter 0: kind 'cw' (control word for counter 0) or 'n' (count)."""
    out = []
    for px, chip, sub, pl in evs:
        if chip != CHIP_CTC8253:
            continue
        if sub == CTC_CONTROL and pl[0] == 3 and pl[1] >> 6 == 0:
            out.append((px, 'cw', pl[1]))
        elif sub == CTC_COUNTER and pl[0] == 0:
            out.append((px, 'n', pl[1]))
    return out


def summary(meta_path):
    evs = list(events(meta_path))
    hbl = [px for px, chip, sub, _ in evs if chip == CHIP_VIDEO and sub == VIDEO_HBLN_START]
    vbl = [px for px, chip, sub, _ in evs if chip == CHIP_VIDEO and sub == VIDEO_VBLN_START]
    w = [x for x in ctc0_writes(evs) if x[1] == 'n']
    print('events %d, HBLN_START %d, VBLN_START %d, CTC0 counts %d' % (len(evs), len(hbl), len(vbl), len(w)))
    if len(w) > 1:
        gaps = {}
        for a, b in zip(w, w[1:]):
            g = b[0] - a[0]
            gaps[g] = gaps.get(g, 0) + 1
        print('gaps between CTC0 counts (ticks: count):', dict(sorted(gaps.items())[:12]))
    if hbl and w:
        import bisect
        offs = {}
        for px, _, _ in w:
            i = bisect.bisect_right(hbl, px) - 1
            if i >= 0:
                o = px - hbl[i]
                offs[o] = offs.get(o, 0) + 1
        print('CTC0 count after HBLN_START (ticks: count):', dict(sorted(offs.items())[:12]))
    return evs


if __name__ == '__main__':
    summary(sys.argv[1])
