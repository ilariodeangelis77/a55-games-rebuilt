"""Minimal Sokoban solver (BFS over pushes, player position normalised to its reachable region,
simple dead-square pruning). Verifies every level in an XSB file is solvable and reports the
minimum number of pushes plus the moves of that solution.
Usage: python -I solve_xsb.py levels.xsb [--json out.json]
"""
import sys, json
from collections import deque

def parse(path):
    levels, cur, name = [], [], None
    for line in open(path):
        line = line.rstrip('\n')
        if line.startswith(';'):
            if cur: levels.append((name, cur)); cur = []
            name = line[1:].strip(); continue
        if line.strip() == '':
            if cur: levels.append((name, cur)); cur = []
            continue
        cur.append(line)
    if cur: levels.append((name, cur))
    return [(n, l) for n, l in levels if any('#' in r for r in l)]

DIRS = {'u': (-1, 0), 'd': (1, 0), 'l': (0, -1), 'r': (0, 1)}

def solve(rows):
    H = len(rows); W = max(len(r) for r in rows)
    g = [r.ljust(W) for r in rows]
    walls = {(r, c) for r in range(H) for c in range(W) if g[r][c] == '#'}
    goals = frozenset((r, c) for r in range(H) for c in range(W) if g[r][c] in '.*+')
    boxes = frozenset((r, c) for r in range(H) for c in range(W) if g[r][c] in '$*')
    player = next((r, c) for r in range(H) for c in range(W) if g[r][c] in '@+')
    # dead squares: cells from which a box can never reach a goal (reverse pull reachability)
    live = set(goals); dq = deque(goals)
    while dq:
        r, c = dq.popleft()
        for dr, dc in DIRS.values():
            b, p = (r + dr, c + dc), (r + 2 * dr, c + 2 * dc)
            if b not in walls and p not in walls and b not in live and 0 <= b[0] < H and 0 <= p[0] < H:
                live.add(b); dq.append(b)
    def reach(p, bx):
        seen = {p: ''}; q = deque([p])
        while q:
            cur = q.popleft()
            for k, (dr, dc) in DIRS.items():
                n = (cur[0] + dr, cur[1] + dc)
                if n in walls or n in bx or n in seen or not (0 <= n[0] < H and 0 <= n[1] < W): continue
                seen[n] = seen[cur] + k; q.append(n)
        return seen
    start_reach = reach(player, boxes)
    key = (boxes, min(start_reach))
    prev = {key: None}; q = deque([(boxes, player, key)])
    while q:
        bx, p, k = q.popleft()
        if bx == goals:
            path = []; cur = k
            while prev[cur] is not None:
                pk, moves = prev[cur]; path.append(moves); cur = pk
            return ''.join(reversed(path)), len(path)
        rch = reach(p, bx)
        for b in bx:
            for d, (dr, dc) in DIRS.items():
                stand = (b[0] - dr, b[1] - dc); to = (b[0] + dr, b[1] + dc)
                if stand not in rch or to in walls or to in bx or to not in live: continue
                nb = (bx - {b}) | {to}
                nr = reach(b, nb); nk = (nb, min(nr))
                if nk in prev: continue
                prev[nk] = (k, rch[stand] + d.upper()); q.append((nb, b, nk))
    return None, None

if __name__ == '__main__':
    res = {}
    allok = True
    for name, rows in parse(sys.argv[1]):
        moves, pushes = solve(rows)
        ok = moves is not None; allok &= ok
        res[name] = dict(solvable=ok, pushes=pushes, moves=len(moves) if ok else None, solution=moves)
        print('%-10s %s pushes=%s steps=%s' % (name, 'SOLVABLE' if ok else 'UNSOLVABLE', pushes, len(moves) if ok else '-'))
    if '--json' in sys.argv: json.dump(res, open(sys.argv[sys.argv.index('--json') + 1], 'w'), indent=1)
    sys.exit(0 if allok else 1)
