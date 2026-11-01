"""Wrap a binary into an MZF file (Sharp tape format): 128-byte header + body.

    python tools/mkmzf.py IN.bin OUT.mzf --name NAME [--load 2000] [--exec 2000]

Taken over from MZ-700-Bad-Apple; here the program must end below 8000h (the MZ-800 VRAM window).

Header: 0 type (01h = machine code), 1-17 name (Sharp ASCII, 0Dh terminated), 12h size, 14h load address,
16h exec address, the rest zeros.
"""
import argparse


def mzf(body, name, load, exec_addr, ftype=1):
    hdr = bytearray(128)
    hdr[0] = ftype
    n = name.upper().encode('ascii')[:16]
    hdr[1:1 + len(n)] = n
    hdr[1 + len(n)] = 0x0D
    hdr[0x12:0x14] = len(body).to_bytes(2, 'little')
    hdr[0x14:0x16] = load.to_bytes(2, 'little')
    hdr[0x16:0x18] = exec_addr.to_bytes(2, 'little')
    return bytes(hdr) + bytes(body)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('inp')
    ap.add_argument('out')
    ap.add_argument('--name', default='WORLD CLOCK')
    ap.add_argument('--load', default='2000')
    ap.add_argument('--exec', dest='exec_addr', default=None)
    a = ap.parse_args()
    load = int(a.load, 16)
    exec_addr = int(a.exec_addr, 16) if a.exec_addr else load
    body = open(a.inp, 'rb').read()
    if load + len(body) > 0x8000:
        raise SystemExit('program 0x%04X-0x%04X runs into the MZ-800 VRAM window (8000h)'
                         % (load, load + len(body) - 1))
    with open(a.out, 'wb') as f:
        f.write(mzf(body, a.name, load, exec_addr))


if __name__ == '__main__':
    main()
