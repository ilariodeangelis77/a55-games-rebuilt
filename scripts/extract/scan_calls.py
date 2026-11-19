"""Scan a C166 fullflash for far CALLS/JMPS (DA/FA seg addrLo addrHi) at even offsets and write
candidate function entry points (CPU addresses) for Ghidra seeding.
Usage: python -I scan_calls.py <dump> <out.txt> [base_hex]"""
import sys, collections
d = open(sys.argv[1], 'rb').read()
base = int(sys.argv[3], 16) if len(sys.argv) > 3 else 0x800000
CODE = [(0x800000, 0x880000), (0xA00000, 0xDA0000)]
def in_code(a): return any(lo <= a < hi for lo, hi in CODE)
calls = collections.Counter(); srcs = collections.Counter()
for i in range(0, len(d) - 4, 2):
    if d[i] == 0xDA:
        seg, off = d[i + 1], d[i + 2] | d[i + 3] << 8
        tgt = seg << 16 | off
        if off & 1 or not in_code(tgt) or not in_code(base + i): continue
        b = d[tgt - base]
        if b == 0xFF: continue
        calls[tgt] += 1
print('distinct CALLS targets', len(calls), 'total refs', sum(calls.values()))
# keep targets called at least twice, or once if target looks like a typical prologue
keep = sorted(t for t, n in calls.items() if n >= 2)
print('kept (>=2 refs)', len(keep))
open(sys.argv[2], 'w').write('\n'.join('%06x' % t for t in keep))
