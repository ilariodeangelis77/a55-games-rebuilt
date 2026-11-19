"""Derive the Move-the-box map byte -> (cell0, cell1) table by tracing the switch cases of the
level loader FUN_cb1fae in a Ghidra listing (scripts/ghidra/ListRange.java cb1fae cb25d6).

Each case stores a tile code (mov r7,#V ; ... add r15,#0xe|#0x10 ; ... mov [r15],r7) for the
first (+0xe) or second (+0x10) cell of the pair, then falls through or jumps; tracing ends at
the loop-continue label 0xcb2582. The jump table (35 words) is at 0xCB4F48 in the dump.
Usage: python -I trace_loader_cases.py <listing> <dump>  -> prints JSON table
"""
import sys, re, json

def load_listing(path):
    ins = {}
    order = []
    for line in open(path):
        m = re.match(r'^([0-9a-f]{6})\t(.*)$', line.strip('\n'))
        if m:
            a = int(m.group(1), 16); ins[a] = m.group(2).strip(); order.append(a)
    nxt = {a: b for a, b in zip(order, order[1:])}
    return ins, nxt

def trace(ins, nxt, start, stop=0xcb2582):
    a, val, off, cells, steps = start, None, None, {}, 0
    while a != stop and steps < 200:
        steps += 1
        t = ins[a]
        m = re.match(r'mov r7,#0x([0-9a-f]+)$', t)
        if m: val = int(m.group(1), 16)
        m = re.match(r'add r15,#0x(e|10)$', t)
        if m: off = 0 if m.group(1) == 'e' else 1
        if t == 'mov [r15],r7': cells[off] = val
        m = re.match(r'jmp[ar] cc_UC,0x([0-9a-f]+)$', t)
        if m:
            a = int(m.group(1), 16); continue
        a = nxt[a]
    return cells

if __name__ == '__main__':
    ins, nxt = load_listing(sys.argv[1])
    d = open(sys.argv[2], 'rb').read()
    B = 0x800000
    table = {}
    for k in range(35):
        tgt = 0xcb0000 | (d[0xcb4f48 - B + 2 * k] | d[0xcb4f48 - B + 2 * k + 1] << 8)
        c = trace(ins, nxt, tgt)
        table[0x41 + k] = [c.get(0), c.get(1)]
    print(json.dumps({('0x%02x' % k): v for k, v in table.items()}))
