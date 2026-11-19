"""Print a coarse layout map of a fullflash: per-64KB block, how much is erased (0xFF), entropy,
and any EELITE/EEFULL headers. Usage: python -I flash_layout.py <dump> [base_hex]"""
import sys, math, collections, re
d = open(sys.argv[1], 'rb').read()
base = int(sys.argv[2], 16) if len(sys.argv) > 2 else 0x800000
BLK = 0x10000
rows = []
for o in range(0, len(d), BLK):
    b = d[o:o + BLK]
    ff = b.count(0xFF) / len(b)
    c = collections.Counter(b); n = len(b)
    ent = -sum(v / n * math.log2(v / n) for v in c.values())
    kind = 'erased' if ff > 0.999 else ('mostly-empty' if ff > 0.9 else ('high-entropy' if ent > 7.5 else 'data/code'))
    rows.append((o, kind, ff, ent))
# merge runs of same kind
start = 0
for i in range(1, len(rows) + 1):
    if i == len(rows) or rows[i][1] != rows[start][1]:
        o0 = rows[start][0]; o1 = rows[i - 1][0] + BLK
        ents = [r[3] for r in rows[start:i]]
        print('0x%06x-0x%06x  CPU 0x%06x-0x%06x  %-13s ent %.1f-%.1f' % (o0, o1 - 1, base + o0, base + o1 - 1, rows[start][1], min(ents), max(ents)))
        start = i
for m in re.finditer(rb'\xfe\xfe(EELITE|EEFULL)', d):
    print('header %s at 0x%06x (CPU 0x%06x)' % (m.group(1).decode(), m.start(), base + m.start()))
