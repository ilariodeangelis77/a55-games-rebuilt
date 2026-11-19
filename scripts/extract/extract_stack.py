"""Extract Stack Attack (game id 2) data from a Siemens A55 fullflash (A55 V9 LG7).

All graphics live in one sprite resource block used through the shared game library
(FUN_ca45ac / FUN_ca493e / FUN_ca4536). The block is passed to FUN_ca45ac by the game's create
function FUN_cae73a as page 0x32B offset 0x3932 = CPU 0xCAF932:
  +0x26: u16 offset table, image id -> block + offset
  id 1  : animation set {u16 1, u16 nstates, u16 state-table id}
  state table: {u16 n, u16 size, anim id x n}; anim: {u16 8, u16 nframes, u16 0x0810, u16 list id}
  list : {u16 n, u16 size, frame id x n}; frame = 8x16 bitmap (16 bytes) + mask (16 bytes)
  ids 0x1E..0x29: 8x8 cells for grid types 2..13 (FUN_cae73a stores id 0x1E+i at state+0x14+8i,
                  FUN_cae1ce draws type t from state + t*8 + 4)
  ids 0x2A / 0x2B: crane 16x16 + mask (claw closed / open)
  ids 0x2C ground 4x4, 0x2D rail 8x4, 0x2E wall 4x4, 0x2F sky band 24 wide (FUN_cae268)
Other: pause hourglass descriptor 0xCA3EF4 (shared with Balloon Shooter), start-screen splash via
UI descriptor 0xCAF880 (+0x18 -> picture id 0xCC), texts from the text pack.
Usage: python -I extract_stack.py <dump> <outdir>
"""
import sys, os, json, struct, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import siemens_pics
from textpack import TextPack

B = 0x800000
BLOCK = 0xCAF932
def w16(d, a): return struct.unpack_from('<H', d, a - B)[0]
def far(d, a): return w16(d, a + 2) * 0x4000 + (w16(d, a) & 0x3FFF)
def bits(d, a, w, h, rb):
    return [[(d[a - B + y * rb + (x >> 3)] >> (7 - (x & 7))) & 1 for x in range(w)] for y in range(h)]
def img_addr(d, i): return BLOCK + w16(d, BLOCK + 0x26 + 2 * i)
def words(d, i, n): return [w16(d, img_addr(d, i) + 2 * k) for k in range(n)]

def player_anims(d):
    _, nstates, table = words(d, 1, 3)
    st = words(d, table, 2 + nstates)
    anims = []
    for aid in st[2:]:
        _, nframes, _size, lst = words(d, aid, 4)
        fl = words(d, lst, 2 + nframes)
        frames = []
        for fid in fl[2:2 + nframes]:
            a = img_addr(d, fid)
            frames.append(dict(id=fid, w=8, h=16, bits=bits(d, a, 8, 16, 1), mask=bits(d, a + 16, 8, 16, 1)))
        anims.append(frames)
    return anims

def extract(d):
    cells = {t: bits(d, img_addr(d, 0x1E + t - 2), 8, 8, 1) for t in range(2, 14)}
    crane = [dict(w=16, h=16, bits=bits(d, img_addr(d, i), 16, 16, 2), mask=bits(d, img_addr(d, i) + 32, 16, 16, 2))
             for i in (0x2A, 0x2B)]
    ph, pw, _f, poff, ppage = struct.unpack_from('<BBHHH', d, 0xCA3EF4 - B)
    return dict(
        cells=cells, crane=crane, anims=player_anims(d),
        ground=dict(w=4, h=4, bits=bits(d, img_addr(d, 0x2C), 4, 4, 1)),
        rail=dict(w=8, h=4, bits=bits(d, img_addr(d, 0x2D), 8, 4, 1)),
        wall=dict(w=4, h=4, bits=bits(d, img_addr(d, 0x2E), 4, 4, 1)),
        sky=dict(w=24, h=24, bits=bits(d, img_addr(d, 0x2F), 24, 24, 3)),
        pause=dict(w=pw, h=ph, bits=bits(d, ppage * 0x4000 + (poff & 0x3FFF), pw, ph, (pw + 7) // 8)),
        pause_dots=[[w16(d, 0xCA3EEC + 2 * i) >> 8, w16(d, 0xCA3EEC + 2 * i) & 0xFF] for i in range(4)])

def splash(d):
    sub = far(d, 0xCAF880 + 0x18)
    pid = w16(d, far(d, sub + 8))
    desc = siemens_pics.descriptor(d, pid)
    return dict(id=pid, w=desc['w'], h=desc['h'], bits=siemens_pics.decode(d, desc))

TEXT_IDS = {'title': 0x4D0, 'start': 0x1B2, 'options': 0x215,
            'menu': [0x1B1, 0x33F, 0x33E, 0x5B5], 'points': 0x692, 'instructions': [0x6E8], 'back': 0x2F9}

def texts(d):
    tp = TextPack(d)
    def one(t):
        s = re.sub(r'\xa4[\x00-\x1f]+', '%d', tp.text(t, 0).decode('latin-1'))
        return s.replace('\x95', '').replace('\x8a', '\n').strip()
    return {k: ([one(x) for x in v] if isinstance(v, list) else one(v)) for k, v in TEXT_IDS.items()}

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    data = extract(d)
    json.dump(data, open(os.path.join(out, 'data.json'), 'w'))
    json.dump(splash(d), open(os.path.join(out, 'splash.json'), 'w'))
    with open(os.path.join(out, 'texts.json'), 'w', encoding='utf-8') as f:
        json.dump(texts(d), f, ensure_ascii=False, indent=1)
    print('anim states:', [[fr['id'] for fr in a] for a in data['anims']])
    try:
        from PIL import Image
        imgs = [dict(w=8, h=8, bits=v) for v in data['cells'].values()] + data['crane'] + [f for a in data['anims'] for f in a] \
            + [data['ground'], data['rail'], data['wall'], data['sky'], data['pause']]
        S = 4; sheet = Image.new('L', (len(imgs) * 26 * S, 26 * S), 200)
        for i, f in enumerate(imgs):
            im = Image.new('L', (f['w'], f['h']), 255)
            for y, row in enumerate(f['bits']):
                for x, v in enumerate(row):
                    if v: im.putpixel((x, y), 0)
            sheet.paste(im.resize((f['w'] * S, f['h'] * S), Image.NEAREST), (i * 26 * S + S, S))
        sheet.save(os.path.join(out, 'sprites_sheet.png'))
    except ImportError:
        pass
    print('written to', out)
