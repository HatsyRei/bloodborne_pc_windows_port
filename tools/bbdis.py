"""Disassembly helper for the game's eboot.elf (image offsets, as used by src/probe.c hooks).

Needs: pip install capstone pyelftools
ELF: --elf, else $BB_EBOOT_ELF, else out/eboot.elf (written by scripts/prepare.py).

  python tools/bbdis.py dis 143ac60 [len=0x200] [--all]   disassemble (stops at first ret unless --all)
  python tools/bbdis.py calls 143ac60                     direct call sites of a function
  python tools/bbdis.py grep e85b400000                   byte pattern in executable segments
  python tools/bbdis.py read 1436d2f [len=16]             hex bytes (e.g. for hook signatures)
"""
import argparse
import os
import struct
from pathlib import Path

from capstone import CS_ARCH_X86, CS_MODE_64, Cs
from elftools.elf.elffile import ELFFile


class Image:
    def __init__(self, path):
        self.data = Path(path).read_bytes()
        with open(path, 'rb') as f:
            self.segs = [(s['p_vaddr'], s['p_offset'], s['p_filesz'], s['p_flags'])
                         for s in ELFFile(f).iter_segments() if s['p_type'] == 'PT_LOAD']
        self.base = min(s[0] for s in self.segs)
        self.md = Cs(CS_ARCH_X86, CS_MODE_64)

    def read(self, off, n):
        va = self.base + off
        for vaddr, foff, size, _ in self.segs:
            if vaddr <= va < vaddr + size:
                start = foff + va - vaddr
                return self.data[start:start + min(n, vaddr + size - va)]
        return b''

    def text(self):
        for vaddr, foff, size, flags in self.segs:
            if flags & 1:
                yield vaddr - self.base, self.data[foff:foff + size]

    def dis(self, off, n, stop_at_ret):
        for insn in self.md.disasm(self.read(off, n), self.base + off):
            print('%08x: %-8s %s' % (insn.address - self.base, insn.mnemonic, insn.op_str))
            if stop_at_ret and insn.mnemonic == 'ret':
                break

    def calls(self, target):
        for seg_off, buf in self.text():
            i = buf.find(b'\xe8')
            while 0 <= i <= len(buf) - 5:
                if seg_off + i + 5 + struct.unpack_from('<i', buf, i + 1)[0] == target:
                    print('call from %08x' % (seg_off + i))
                i = buf.find(b'\xe8', i + 1)

    def grep(self, pattern):
        for seg_off, buf in self.text():
            i = buf.find(pattern)
            while i >= 0:
                print('%08x' % (seg_off + i))
                i = buf.find(pattern, i + 1)


def main():
    hexint = lambda s: int(s, 16)
    default_elf = os.environ.get('BB_EBOOT_ELF') or Path(__file__).resolve().parent.parent / 'out' / 'eboot.elf'
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--elf', default=default_elf)
    sub = parser.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('dis')
    p.add_argument('offset', type=hexint)
    p.add_argument('length', type=hexint, nargs='?', default=0x200)
    p.add_argument('--all', action='store_true', help='do not stop at the first ret')
    sub.add_parser('calls').add_argument('target', type=hexint)
    sub.add_parser('grep').add_argument('pattern', type=bytes.fromhex)
    p = sub.add_parser('read')
    p.add_argument('offset', type=hexint)
    p.add_argument('length', type=hexint, nargs='?', default=16)
    args = parser.parse_args()

    img = Image(args.elf)
    if args.cmd == 'dis':
        img.dis(args.offset, args.length, not args.all)
    elif args.cmd == 'calls':
        img.calls(args.target)
    elif args.cmd == 'grep':
        img.grep(args.pattern)
    elif args.cmd == 'read':
        print(img.read(args.offset, args.length).hex())


if __name__ == '__main__':
    main()
