"""Extract Balloon Shooter (game id 1) data from a Siemens A55 fullflash (A55 V9 LG7).

Everything is located through the firmware's own tables (see NOTES.md, "Balloon Shooter"):
  * level table 0xCA926E: 14 x {u16 variety, u16 score threshold, u16 balloons, u16 min speed}
  * object template = 12 bytes {s8 x, s8 y, s8 dx, s8 dy, u8 nframes, u8 frame, u8 kind, u8 speed,
    far *frame_table}; frame_table = nframes far pointers to frame descriptors
    {u8 w, u8 h, u16 off, u16 page} whose data is the bitmap followed by a mask (mask 1 = transparent)
  * balloon templates: far-pointer table 0xCAB336 (12: 4 designs x 3 sizes)
  * attachments: tables 0xCAB366 / 0xCAB36A / 0xCAB36E (balloon size 0/1/2), entries 0,3,6 =
    kind 9 dynamite, kind 0xA greeting card, kind 0xB string
  * pop animations: far pointers 0xCAB38A (one frame table per balloon size)
  * crosshair template 0xCA931C, banner (pause/status bar) template 0xCA93B4
  * digits: 10 glyphs, 5x7, 1 byte per row, page 0x328 offsets 0x3C2A (0), 0x3C31 (1) .. 0x3C69 (9)
  * pause icon: frame descriptor 0xCA3EF4, blinking dots offsets table 0xCA3EEC
  * start-screen splash: UI descriptor 0xCA8DC0 +0x18 -> {x,y,w,h, -> picture id list} (id 0xCA)
Usage: python -I extract_balloon.py <dump> <outdir>
"""
import sys, os, json, struct, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import siemens_pics
from textpack import TextPack

B = 0x800000
def w16(d, a): return struct.unpack_from('<H', d, a - B)[0]
def far(d, a): return w16(d, a + 2) * 0x4000 + (w16(d, a) & 0x3FFF)

def bits(d, a, w, h, rb):
    return [[(d[a - B + y * rb + (x >> 3)] >> (7 - (x & 7))) & 1 for x in range(w)] for y in range(h)]

def frame(d, desc):
    w, h, off, page = struct.unpack_from('<BBHH', d, desc - B)
    a = page * 0x4000 + (off & 0x3FFF); rb = (w + 7) // 8
    return dict(w=w, h=h, bits=bits(d, a, w, h, rb), mask=bits(d, a + rb * h, w, h, rb))

def frame_table(d, ft, n):
    return [frame(d, far(d, ft + 4 * i)) for i in range(n)]

def template(d, a):
    x, y, dx, dy, nf, fr, kind, spd = struct.unpack_from('<bbbbBBBB', d, a - B)
    return dict(x=x, y=y, dx=dx, dy=dy, nframes=nf, frame=fr, kind=kind, speed=spd,
                frames=frame_table(d, far(d, a + 8), max(1, nf)))

def extract(d):
    levels = []
    for i in range(15):   # 15th entry (past level 14) is read by the game too: threshold 2 -> instant end
        v, thr, cnt, spd = struct.unpack_from('<HHHH', d, 0xCA926E + 8 * i - B)
        levels.append(dict(variety=v, threshold=thr, balloons=cnt, min_speed=spd))
    balloons = [template(d, far(d, 0xCAB336 + 4 * k)) for k in range(12)]
    attach = [[template(d, far(d, base + 4 * k)) for k in (0, 3, 6)] for base in (0xCAB366, 0xCAB36A, 0xCAB36E)]
    pops = [frame_table(d, far(d, 0xCAB38A + 4 * k), balloons[k]['nframes']) for k in range(3)]
    digits = []
    for n in range(10):
        off = 0x3C2A if n == 0 else 0x3C31 + 7 * (n - 1)
        # temporary descriptor built by FUN_ca505e: h=7, w=5; glyphs are stored inverted (1 = white),
        # they are printed white-on-black on the status banner
        digits.append(dict(w=5, h=7, inverted=True, bits=bits(d, 0x328 * 0x4000 + off, 5, 7, 1)))
    # FUN_ca262a descriptors (pause icon, HUD digits) store HEIGHT first: {u8 h, u8 w, u16 flags, u16 off, u16 page}
    ph, pw, _pflags, poff, ppage = struct.unpack_from('<BBHHH', d, 0xCA3EF4 - B)
    pause = dict(w=pw, h=ph, bits=bits(d, ppage * 0x4000 + (poff & 0x3FFF), pw, ph, (pw + 7) // 8))
    dots = [[w16(d, 0xCA3EEC + 2 * i) >> 8, w16(d, 0xCA3EEC + 2 * i) & 0xFF] for i in range(4)]
    return dict(levels=levels, balloons=balloons, attach=attach, pops=pops,
                crosshair=template(d, 0xCA931C), banner=template(d, 0xCA93B4),
                digits=digits, pause=pause, pause_dots=dots)

def splash(d):
    sub = far(d, 0xCA8DC0 + 0x18)
    pid = w16(d, far(d, sub + 8))
    desc = siemens_pics.descriptor(d, pid)
    return dict(id=pid, w=desc['w'], h=desc['h'], bits=siemens_pics.decode(d, desc))

TEXT_IDS = {'title': 0x4CE, 'start': 0x1B2, 'options': 0x215,
            'menu': [0x1B1, 0x33F, 0x33E, 0x5B5], 'points': 0x692, 'instructions': [0x6E7], 'back': 0x2F9}

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
    for i, l in enumerate(data['levels']): print('level %2d %s' % (i + 1, l))
    try:
        from PIL import Image
        imgs = [f for t in data['balloons'] for f in t['frames'][:1]] + [t['frames'][0] for row in data['attach'] for t in row] \
             + [p[2] for p in data['pops']] + [data['crosshair']['frames'][0], data['pause']] + data['digits']
        S = 4; sheet = Image.new('L', (len(imgs) * 18 * S, 18 * S), 200)
        for i, f in enumerate(imgs):
            im = Image.new('L', (f['w'], f['h']), 255)
            for y, row in enumerate(f['bits']):
                for x, v in enumerate(row):
                    if v: im.putpixel((x, y), 0)
            sheet.paste(im.resize((f['w'] * S, f['h'] * S), Image.NEAREST), (i * 18 * S + S, S))
        sheet.save(os.path.join(out, 'sprites_sheet.png'))
        b = data['banner']['frames'][0]; im = Image.new('L', (b['w'], b['h']), 255)
        for y, row in enumerate(b['bits']):
            for x, v in enumerate(row):
                if v: im.putpixel((x, y), 0)
        im.resize((b['w'] * 4, b['h'] * 4), Image.NEAREST).save(os.path.join(out, 'banner.png'))
    except ImportError:
        pass
    print('written to', out)
