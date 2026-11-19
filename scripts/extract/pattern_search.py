"""Find a word in a binary whatever its character encoding, as long as it's a 1:1 code per character.

Matches the letter-equality pattern (which positions share a character) for 8-bit and 16-bit
(LE/BE) code units, then prints candidate mappings. Usage:
    python -I pattern_search.py <dump> "Stack Attack" ["Move the box" ...]
"""
import sys
from collections import defaultdict

def pattern(word):
    first = {}
    return [first.setdefault(c, i) for i, c in enumerate(word)]

def search(d, word, width, order):
    pat = pattern(word)
    n = len(word)
    if width == 1:
        units = d
    else:
        units = [int.from_bytes(d[i:i + 2], order) for i in range(0, len(d) - 1, 2)]
    hits = []
    # anchor on first repeated pair to cut work
    for i in range(len(units) - n):
        w = units[i:i + n]
        ok = True
        seen = {}
        for j in range(n):
            u = w[j]
            if u in seen:
                if seen[u] != pat[j]:
                    ok = False; break
            else:
                if pat[j] != j:
                    ok = False; break
                seen[u] = j
        if ok:
            hits.append(i * width)
    return hits

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    for word in sys.argv[2:]:
        for width, order in [(1, None), (2, 'little'), (2, 'big')]:
            hits = search(d, word, width, order)
            label = '8-bit' if width == 1 else '16-bit ' + order
            print('%-14s %-14s %d hits' % (word, label, len(hits)))
            for h in hits[:12]:
                raw = d[h:h + len(word) * width]
                print('   0x%06x  %s' % (h, raw.hex(' ')))
