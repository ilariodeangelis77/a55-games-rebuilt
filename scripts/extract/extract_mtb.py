"""Extract Move the Box levels (XSB) and tiles (PNG) from a Siemens A55 fullflash.

Everything here is derived from the firmware code (see NOTES.md):
  * level table: CPU 0xCB4C0C, 14 records x 0x26 bytes          (FUN_cb1fae, FUN_cb1faa returns 14)
      +0  u16 flag: if nonzero the loader calls FUN_cb265c, which TRANSPOSES the 8x8 grid
          (swap row/col; same routine as the "Rotate map" option every 50 steps). Levels 9..14.
      +2  u8  number of boxes        (stored to state+0x10E)
      +3  u8  player row, +4 u8 player column
      +5  32 bytes = 8 rows x 4 bytes, each byte encodes 2 cells via the loader's 35-case
          switch (jump table 0xCB4F48). The byte->(cell,cell) table is traced from the code
          by trace_loader_cases.py and embedded below.
  * tile codes: 100 box, 101 goal, 102 floor, 103 wall, 104 box on goal, 105 player, 110 outside
  * picture descriptors: CPU 0xCB4ED0, 11 x {u8 w=10, u8 h=8, u16 type=1, u16 off, u16 page}
    bitmap rows are big-endian u16, top 10 bits used, 1 = black pixel.

Usage: python -I extract_mtb.py <dump> <outdir>
"""
import sys, os, json, struct

B = 0x800000
LEVELS = 0xCB4C0C
NLEVELS = 14
REC = 0x26
PICS = 0xCB4ED0
NPICS = 11

# byte -> (first cell, second cell); traced from FUN_cb1fae switch (out/mtb_pair_table.json)
PAIRS = {
    0x41: (110, 110), 0x42: (110, 103), 0x43: (103, 110), 0x44: (103, 103), 0x45: (103, 101),
    0x46: (103, 100), 0x47: (105, 100), 0x48: (103, 102), 0x49: (101, 103), 0x4a: (101, 101),
    0x4b: (101, 100), 0x4c: (101, 104), 0x4d: (101, 102), 0x4e: (100, 103), 0x4f: (100, 101),
    0x50: (100, 100), 0x51: (100, 102), 0x52: (100, 104), 0x53: (104, 101), 0x54: (104, 102),
    0x55: (102, 102), 0x56: (102, 103), 0x57: (102, 101), 0x58: (102, 100), 0x59: (105, 102),
    0x5a: (105, 103), 0x61: (104, 100), 0x62: (102, 105), 0x63: (103, 105),
}
# tile code -> picture descriptor index (FUN_cb28b4 jump table at 0xCB4F8E)
TILE_PIC = {100: 2, 101: 4, 102: 5, 103: 1, 104: 3, 105: 6, 106: 7, 107: 8, 108: 9, 109: 10, 110: 0}
XSB = {110: ' ', 103: '#', 102: ' ', 101: '.', 100: '$', 104: '*', 105: '@'}
TILE_NAMES = {100: 'box', 101: 'goal', 102: 'floor', 103: 'wall', 104: 'box_on_goal', 105: 'player', 110: 'outside'}

def rd(d, a, n): return d[a - B:a - B + n]

def levels(d):
    out = []
    for i in range(NLEVELS):
        r = rd(d, LEVELS + i * REC, REC)
        flag, nbox, prow, pcol = struct.unpack_from('<H', r, 0)[0], r[2], r[3], r[4]
        grid = []
        for row in range(8):
            cells = []
            for b in r[5 + row * 4:9 + row * 4]:
                cells += PAIRS[b]
            grid.append(cells)
        if flag:   # FUN_cb265c: transpose
            grid = [[grid[c][r] for c in range(8)] for r in range(8)]
        out.append(dict(index=i + 1, flag=flag, boxes=nbox, player=(prow, pcol), grid=grid))
    return out

def to_xsb(lv):
    lines = [''.join(XSB[c] for c in row).rstrip() for row in lv['grid']]
    while lines and not lines[-1]: lines.pop()
    while lines and not lines[0]: lines.pop(0)
    return '\n'.join(lines)

def pictures(d):
    pics = []
    for i in range(NPICS):
        w, h, typ, off, page = struct.unpack('<BBHHH', rd(d, PICS + 8 * i, 8))
        addr = page * 0x4000 + (off & 0x3FFF)
        rows = [struct.unpack('>H', rd(d, addr + 2 * y, 2))[0] for y in range(h)]
        bits = [[(rows[y] >> (15 - x)) & 1 for x in range(w)] for y in range(h)]
        pics.append(dict(index=i, w=w, h=h, type=typ, addr=addr, bits=bits))
    return pics

def validate(lv):
    g = lv['grid']; flat = [c for row in g for c in row]
    boxes = flat.count(100) + flat.count(104); goals = flat.count(101) + flat.count(104)
    players = [(r, c) for r, row in enumerate(g) for c, v in enumerate(row) if v == 105]
    return dict(boxes=boxes, goals=goals, players=players,
                ok=boxes == goals == lv['boxes'] and len(players) == 1)

# Text IDs used by the game's own screens (see NOTES.md, "Original start menu")
TEXT_IDS = {
    'title': 0x347, 'start': 0x1B2, 'options': 0x215,
    'menu': [0x1B1, 0x3DA, 0x33E, 0x480, 0x9F9],     # Start, Level, Highscore, Instructions, Rotate map
    'instructions': [0x3E4, 0xA98, 0xA99, 0xA9A],    # pages; the game separates them with text 0xE74 (" ")
    'best_score': 0x3E3, 'won': 0x3D8, 'lost': 0x3E2, 'ok': 0x15B, 'back': 0x2F9,
}

def texts(d, lang=0):
    """Decode the game's UI strings from the firmware text pack (language 0 of LG7 = English)."""
    import re
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from textpack import TextPack
    tp = TextPack(d)
    def one(tid):
        s = tp.text(tid, lang).decode('latin-1')
        s = re.sub(r'\xa4[\x00-\x1f]+', '%d', s)      # 0xA4 + width codes = number placeholder
        return s.replace('\x95', '').replace('\x8a', '\n').strip()
    return {k: ([one(t) for t in v] if isinstance(v, list) else one(v)) for k, v in TEXT_IDS.items()}

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    lvs = levels(d)
    with open(os.path.join(out, 'levels.xsb'), 'w', newline='\n') as f:
        f.write('; Move the Box - levels extracted from Siemens A55 firmware (see NOTES.md)\n\n')
        for lv in lvs:
            v = validate(lv)
            f.write('; Level %d\n%s\n\n' % (lv['index'], to_xsb(lv)))
            print('level %2d boxes=%d goals=%d player=%s header=(%d boxes, row %d, col %d) flag=%d %s'
                  % (lv['index'], v['boxes'], v['goals'], v['players'], lv['boxes'], *lv['player'], lv['flag'], 'OK' if v['ok'] else 'MISMATCH'))
    json.dump([dict(lv, grid=lv['grid']) for lv in lvs], open(os.path.join(out, 'levels.json'), 'w'))
    pics = pictures(d)
    json.dump(pics, open(os.path.join(out, 'tiles.json'), 'w'))
    try:
        from PIL import Image
        scale = 8
        sheet = Image.new('L', ((10 + 2) * len(pics) * scale, (8 + 2) * scale), 255)
        for p in pics:
            img = Image.new('L', (p['w'], p['h']), 255)
            for y in range(p['h']):
                for x in range(p['w']):
                    if p['bits'][y][x]: img.putpixel((x, y), 0)
            img.save(os.path.join(out, 'tile_%02d.png' % p['index']))
            sheet.paste(img.resize((p['w'] * scale, p['h'] * scale), Image.NEAREST), ((1 + p['index'] * 12) * scale, scale))
        sheet.save(os.path.join(out, 'tiles_sheet.png'))
    except ImportError:
        print('Pillow missing: PNGs skipped')
    for p in pics: print('pic %2d at 0x%06x %dx%d' % (p['index'], p['addr'], p['w'], p['h']))
    with open(os.path.join(out, 'texts.json'), 'w', encoding='utf-8') as f:
        json.dump(texts(d), f, ensure_ascii=False, indent=1)
    print('texts.json written')
