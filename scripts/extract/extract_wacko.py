"""Extract Wacko (game id 8) assets from a Siemens A55 fullflash (A55 V9 LG7).

Everything is located through the firmware's own structures (see NOTES.md, "Wacko"):
  * draw switch FUN_d52506: jump table 0xD53ADE, 18 cases for hole states 1..18; every case
    starts with `mov r12,#off` (E6 FC lo hi) naming the picture descriptor in page 0x354.
  * picture descriptors (same format as Move the Box tiles): {u8 w, u8 h, u16 type, u16 off, u16 page}
  * level icons: descriptors 0xD53A64 / 0xD53A6C / 0xD53A74 (10x10, drawn at (85,25))
  * start-screen splash: UI descriptor 0xD53B28 -> +0x18 sub-struct -> picture id list (id 0xCD)
  * UI strings from the text pack (language 0 = English)
Usage: python -I extract_wacko.py <dump> <outdir>
"""
import sys, os, json, struct, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import siemens_pics
from textpack import TextPack

B = 0x800000
PAGE = 0x354
DRAW_TABLE = 0xD53ADE
NSTATES = 18
LEVEL_ICONS = [0xD53A64, 0xD53A6C, 0xD53A74]
START_DESC = 0xD53B28
INSTR_LIST = 0xD51B4C          # text-id list for "Instructions" (FUN_d51bf6 -> d56ce6), ends with 0x7FFF

TEXT_IDS = {
    'title': 0x3D2, 'start': 0x1B2, 'options': 0x215,
    'menu': [0x1B1, 0x3D9, 0x3DB, 0x5B5],          # Start, Level, Highscore, Instructions
    'levels': [0x3DD, 0x3DE, 0x3DF],               # "Level 1".."Level 3"
    'best_score': 0x3D6, 'result': 0x3D7, 'back': 0x2F9,
}

def w16(d, a): return struct.unpack_from('<H', d, a - B)[0]

def picture(d, desc_addr):
    w, h, typ, off, page = struct.unpack_from('<BBHHH', d, desc_addr - B)
    return siemens_pics.decode(d, dict(w=w, h=h, type=typ, addr=page * 0x4000 + (off & 0x3FFF)))

def sprites(d):
    out, state_map = {}, {}
    for k in range(NSTATES):
        case = 0xD50000 | w16(d, DRAW_TABLE + 2 * k)
        assert d[case - B] == 0xE6 and d[case - B + 1] == 0xFC, 'unexpected case code at %06x' % case
        desc = PAGE * 0x4000 + (w16(d, case + 2) & 0x3FFF)
        key = '%06x' % desc
        if key not in out:
            bits = picture(d, desc)
            out[key] = dict(w=len(bits[0]), h=len(bits), bits=bits)
        state_map[k + 1] = key
    icons = []
    for a in LEVEL_ICONS:
        bits = picture(d, a); key = '%06x' % a
        out[key] = dict(w=len(bits[0]), h=len(bits), bits=bits); icons.append(key)
    return dict(sprites=out, state_sprite=state_map, level_icons=icons)

def splash(d):
    lst_off, lst_page = struct.unpack_from('<HH', d, START_DESC + 0x18 + 8 - B)
    pid = w16(d, lst_page * 0x4000 + (lst_off & 0x3FFF))
    desc = siemens_pics.descriptor(d, pid)
    return dict(id=pid, w=desc['w'], h=desc['h'], bits=siemens_pics.decode(d, desc))

def texts(d):
    tp = TextPack(d)
    def one(tid):
        s = tp.text(tid, 0).decode('latin-1')
        s = re.sub(r'\xa4[\x00-\x1f]+', '%d', s)
        return s.replace('\x95', '').replace('\x8a', '\n').strip()
    t = {k: ([one(x) for x in v] if isinstance(v, list) else one(v)) for k, v in TEXT_IDS.items()}
    pages, a = [], INSTR_LIST
    while w16(d, a) != 0x7FFF:
        pages.append(one(w16(d, a))); a += 2
    t['instructions'] = pages
    return t

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    s = sprites(d)
    json.dump(s, open(os.path.join(out, 'sprites.json'), 'w'))
    json.dump(splash(d), open(os.path.join(out, 'splash.json'), 'w'))
    with open(os.path.join(out, 'texts.json'), 'w', encoding='utf-8') as f:
        json.dump(texts(d), f, ensure_ascii=False, indent=1)
    print('states -> sprites:', s['state_sprite'])
    try:
        from PIL import Image
        keys = list(s['sprites']); S = 4
        sheet = Image.new('L', (len(keys) * 27 * S, 20 * S), 200)
        for i, k in enumerate(keys):
            sp = s['sprites'][k]; im = Image.new('L', (sp['w'], sp['h']), 255)
            for y, row in enumerate(sp['bits']):
                for x, v in enumerate(row):
                    if v: im.putpixel((x, y), 0)
            sheet.paste(im.resize((sp['w'] * S, sp['h'] * S), Image.NEAREST), (i * 27 * S + S, S))
        sheet.save(os.path.join(out, 'sprites_sheet.png'))
    except ImportError:
        pass
    print('written to', out)
