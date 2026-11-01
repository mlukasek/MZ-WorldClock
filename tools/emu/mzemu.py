"""Minimal client of mz800emu over its MCP pipe (JSON lines on stdin/stdout), standard library only.

Taken over from MZ-700-Bad-Apple (tools/emu/mzemu.py) and adapted: the ini overrides are per key, the ROM
set (EU / JP) and the Unicard can be chosen, and there are helpers for the text screen and the keyboard.

The emulator runs headless with our own configuration build/emu/<exe>.ini (a copy of the emulator's ini with
our overrides), so nothing in the emulator folder is changed. Machines (fixed per executable):
    mz700emu-pal.exe   MZ-700, PAL 50 Hz, 312 lines
    mz700emu-ntsc.exe  MZ-700, NTSC 60 Hz, 262 lines
    mz800emu.exe       MZ-800 (PAL), starts in MZ-700 mode after reset
ROM for the MZ-700 builds: 'EU' (1Z-013A + EU CG-ROM) or 'JP' (1Z-009B + JP CG-ROM).

Environment: MZ800EMU_DIR (default ..\\mz800emu-2.0.5-preview next to this repo).

    from mzemu import Emu
    with Emu('mz700emu-ntsc.exe', rom='JP') as emu:
        emu.run_mzf('build/worldclock.mzf')
        emu.run(50)
        print('\\n'.join(emu.text_lines()))
"""
import base64
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
EMU_DIR = os.environ.get('MZ800EMU_DIR', os.path.join(os.path.dirname(ROOT), 'mz800emu-2.0.5-preview'))

ROM_TYPES = {'EU': 'STANDARD-EU', 'JP': 'STANDARD-JP'}


def make_ini(path, base, overrides):
    """Copy of the ini `base` with the keys from `overrides` ({section: {key: value}}) replaced or added."""
    src = []
    if base and os.path.exists(base):
        src = open(base, encoding='utf-8', errors='replace').read().splitlines()
    todo = {s: dict(kv) for s, kv in overrides.items()}
    out, section = [], None

    def flush(sec):
        # keys of the section that were not in the base ini go at its end
        for k, v in todo.pop(sec, {}).items():
            out.append('%s = %s' % (k, v))

    for line in src:
        s = line.strip()
        if s.startswith('[') and s.endswith(']'):
            if section is not None:
                flush(section)
            section = s[1:-1]
            out.append(line)
            continue
        if section in todo and '=' in s:
            key = s.split('=', 1)[0].strip()
            if key in todo[section]:
                out.append('%s = %s' % (key, todo[section].pop(key)))
                continue
        out.append(line)
    if section is not None:
        flush(section)
    for sec in list(todo):
        out.append('[%s]' % sec)
        flush(sec)
        out.append('')
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='') as f:
        f.write('\n'.join(out) + '\n')


class EmuError(RuntimeError):
    pass


class Emu:
    def __init__(self, exe='mz800emu.exe', rom=None, unicard=False, hwlog=None, hs_decimation=0):
        """rom: 'EU' / 'JP' for the MZ-700 builds (None keeps the emulator's setting).
        unicard: plug the Unicard in (its RTC returns the host's local time).
        hwlog: 'dir/name' of the HW log (CTC writes etc.), recorded between hwlog_start and hwlog_stop.
        hs_decimation: 1 logs every HS/HBLN edge too. (The pipe mode takes no trace options on the command
        line, they go through the ini.)"""
        self.exe = exe
        arch = os.path.splitext(exe)[0].replace('-ntsc', '').replace('-pal', '')
        ov = {'RAMDISK': {'mr1r18_pluged': '0', 'mr1r18_type': 'ROM', 'mr1r18_filepath': 'none.dat',
                          'pezik_e8_pluged': '0', 'pezik_68_pluged': '0'},
              'UNICARD': {'connected': '1' if unicard else '0'}}
        if rom:
            ov['ROM'] = {'rom_type': ROM_TYPES[rom]}
        if hwlog:
            d, n = os.path.split(os.path.abspath(hwlog))
            os.makedirs(d, exist_ok=True)
            # one big chunk: 2.0.5 loses what follows a full chunk
            ov['TRACE_HWLOG'] = {'mode': 'OFF', 'dir': d, 'name': n, 'chunk_mb': '0x200',
                                 'max_total_mb': '0x800', 'save_on_exit': '1',
                                 'hs_decimation': '0x%02X' % hs_decimation}
        ini = os.path.join(ROOT, 'build', 'emu', os.path.splitext(exe)[0] + '.ini')
        make_ini(ini, os.path.join(EMU_DIR, arch + '.ini'), ov)
        cmd = [os.path.join(EMU_DIR, exe), '--mcp-pipe', '--headless', '--no-first-run-windows', '--no-save-ini',
               '--config', ini]
        self.proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                     stderr=subprocess.DEVNULL, text=True, bufsize=1, cwd=EMU_DIR,
                                     encoding='utf-8', errors='replace')
        self.req_id = 0
        while True:                   # the emulator is ready after its hello message
            line = self.proc.stdout.readline()
            if not line:
                raise EmuError('emulator did not start: %s' % ' '.join(cmd))
            if line.startswith('{') and json.loads(line).get('type') == 'hello':
                break
        for _ in range(200):          # and then the emulation thread still has to come up
            try:
                self.call('get_state')
                break
            except EmuError:
                time.sleep(0.05)
        self.call('pause')
        self.call('set_speed', {'mode': 'max', 'percent': 100, 'step': 0})   # headless pipe runs ~1 fps otherwise

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def call(self, cmd, data=None):
        self.req_id += 1
        req = {'req_id': self.req_id, 'cmd': cmd}
        if data is not None:
            req['data'] = data
        self.proc.stdin.write(json.dumps(req) + '\n')
        self.proc.stdin.flush()
        while True:
            line = self.proc.stdout.readline()
            if not line:
                raise EmuError('emulator closed the pipe (cmd %s)' % cmd)
            if not line.startswith('{'):
                continue
            resp = json.loads(line)
            if resp.get('req_id') != self.req_id:
                continue              # broadcasts and stale responses
            if not resp.get('success', False):
                raise EmuError('%s: %s' % (cmd, resp.get('error', resp)))
            return resp.get('data')

    def close(self):
        if self.proc is None:
            return
        try:
            self.call('shutdown')
        except Exception:
            pass
        try:
            self.proc.wait(timeout=20)
        except subprocess.TimeoutExpired:
            self.proc.kill()
            self.proc.wait()
        self.proc = None

    # helpers -----------------------------------------------------------------------------------------
    def run(self, frames):
        """Run whole frames (at most 1000 per call); returns the emulator's state after the run."""
        res = None
        while frames > 0:
            n = min(frames, 1000)
            res = self.call('run', {'frames': n})
            if res.get('stopped_by') not in ('frames', 'timeout'):
                break             # a breakpoint or the program stopped it
            frames -= res.get('actual_frames', n)   # a slow run (HW log) ends on the wall clock limit
        return res

    def pause(self):
        return self.call('pause')

    def mem(self, addr, length):
        out = bytearray()
        while length > 0:
            n = min(length, 256)
            d = self.call('mem_read', {'addr': addr, 'len': n})
            out += base64.b64decode(d['data_b64'])
            addr += n
            length -= n
        return bytes(out)

    def word(self, addr):
        b = self.mem(addr, 2)
        return b[0] | b[1] << 8

    def poke(self, addr, data):
        """Write bytes to RAM (CPU view)."""
        for i in range(0, len(data), 256):
            self.call('mem_write', {'addr': addr + i, 'data_hex': bytes(data[i:i + 256]).hex()})

    def raster(self):
        return self.call('get_raster_pos')

    def regs(self):
        return self.call('get_registers')

    def set_pc(self, addr):
        self.call('set_register', {'reg': 'PC', 'value': addr})

    def run_mzf(self, path, boot_frames=50):
        """Reset, let the IPL ROM boot, load the MZF and start it at its exec address (memory map untouched:
        ROM 0000h, VRAM D000h, E000h I/O as after the boot in MZ-700 mode). Note: the program starts on the
        monitor's stack with interrupts enabled."""
        self.call('reset')
        self.run(boot_frames)
        hdr = open(path, 'rb').read(128)
        exec_addr = hdr[0x16] | hdr[0x17] << 8
        self.call('media_load_mzf', {'path': os.path.abspath(path)})
        self.set_pc(exec_addr)
        return exec_addr

    def text_dump(self):
        """40x25 text screen in MZ-700 mode: (1000 display codes, 1000 attributes), read through the CPU
        view of D000h / D800h. (get_video_text_dump returns wrong data on mz800emu 2.0.5-preview.)"""
        return self.mem(0xD000, 1000), self.mem(0xD800, 1000)

    def text_lines(self):
        """The text screen as 25 strings (display code -> ASCII where it is a letter, digit or common sign)."""
        chars, _ = self.text_dump()
        return [''.join(display_to_ascii(c) for c in chars[r * 40:r * 40 + 40]) for r in range(25)]

    def key(self, name, frames=3, gap=3):
        """Hold a key (emulator key name, e.g. 'BREAK', 'T', 'RETURN') for `frames` frames, then release it."""
        self.call('input_press_key', {'key': name})
        self.run(frames)
        self.call('input_release_key', {'key': name})
        self.run(gap)

    def hwlog_start(self):
        return self.call('trace_start', {'channel': 'hwlog'})

    def hwlog_stop(self):
        return self.call('trace_stop', {'channel': 'hwlog'})

    def screenshot(self, path):
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        return self.call('screenshot_save_to_file', {'path': os.path.abspath(path)})


# ASCII 20h-5Fh -> display code, as in the monitor's table at 0A92h (the same in 1Z-013A and 1Z-009B)
ASCII_TO_DISPLAY = dict(zip(
    ' !"#$%&\'()*+,-./0123456789:;<=>?@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_',
    [0x00, 0x61, 0x62, 0x63, 0x64, 0x65, 0x66, 0x67, 0x68, 0x69, 0x6B, 0x6A, 0x2F, 0x2A, 0x2E, 0x2D,
     0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27, 0x28, 0x29, 0x4F, 0x2C, 0x51, 0x2B, 0x57, 0x49,
     0x55] + list(range(0x01, 0x1B)) + [0x52, 0x59, 0x54, 0x50, 0x45]))
DISPLAY_TO_ASCII = {v: k for k, v in ASCII_TO_DISPLAY.items()}


def display_to_ascii(c):
    """Display code -> ASCII for tests (the printable ASCII subset; anything else is '#')."""
    return DISPLAY_TO_ASCII.get(c, '#')


def load_map(path):
    """z88dk map file (zcc -m) -> {name: value}."""
    out = {}
    pat = re.compile(r'^(\S+)\s*=\s*\$([0-9A-Fa-f]+)')
    for line in open(path, encoding='latin-1'):
        m = pat.match(line)
        if m:
            out[m.group(1)] = int(m.group(2), 16)
    return out


if __name__ == '__main__':
    # python mzemu.py EXE CMD '{"arg": value}'
    with Emu(sys.argv[1]) as emu:
        print(json.dumps(emu.call(sys.argv[2], json.loads(sys.argv[3]) if len(sys.argv) > 3 else None),
                         indent=1)[:5000])
