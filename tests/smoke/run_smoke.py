"""Run the toolchain smoke test (build\\smoke-<cc>.mzf) on the emulated machines and check the screen.

    python tests/smoke/run_smoke.py [--cc sccz80|sdcc]

For each machine: load the MZF, run it, check the title and the detected machine on the text screen and
the stack, press BREAK and check that the program said BYE and returned to the monitor.
"""
import argparse
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools', 'emu'))
from mzemu import Emu  # noqa: E402

MACHINES = [  # (label, executable, ROM, expected detection)
    ('MZ-700 EU PAL', 'mz700emu-pal.exe', 'EU', 'MZ-700 EU'),
    ('MZ-700 JP NTSC', 'mz700emu-ntsc.exe', 'JP', 'MZ-700 JP'),
    ('MZ-700 EU NTSC', 'mz700emu-ntsc.exe', 'EU', 'MZ-700 EU'),
    ('MZ-800', 'mz800emu.exe', None, 'MZ-800'),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--cc', default='sccz80')
    a = ap.parse_args()
    mzf = os.path.join(ROOT, 'build', 'smoke-%s.mzf' % a.cc)
    fails = 0
    for label, exe, rom, expect in MACHINES:
        errs = []
        with Emu(exe, rom=rom) as emu:
            emu.run_mzf(mzf)
            emu.run(10)
            lines = emu.text_lines()
            regs = emu.regs()
            if lines[0].rstrip() != '*** WORLD CLOCK SMOKE TEST ***':
                errs.append('title: %r' % lines[0])
            if lines[2].rstrip() != 'MACHINE: ' + expect:
                errs.append('machine: %r' % lines[2])
            sp = regs.get('SP', regs.get('sp'))
            if sp is not None and not (0x7000 <= sp <= 0x8000):
                errs.append('SP %04X' % sp)
            shot = os.path.join(ROOT, 'work', 'smoke', '%s-%s.png' % (label.replace(' ', '_'), a.cc))
            emu.screenshot(shot)
            emu.key('BREAK', 5, 10)
            lines = emu.text_lines()
            pc = emu.regs().get('PC', emu.regs().get('pc'))
            if not lines[6].startswith('BYE'):
                errs.append('no BYE: %r' % lines[6])
            if pc is not None and pc >= 0x1000:
                errs.append('PC %04X not in the monitor' % pc)
        print('%-16s %s' % (label, 'OK' if not errs else 'FAIL ' + '; '.join(errs)))
        fails += bool(errs)
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
