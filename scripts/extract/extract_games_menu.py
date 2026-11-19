"""Extract the phone's Games menu (A55 V9 LG7) for the launcher port/games.html.

Menu descriptor (confirmed, see NOTES.md "Games menu"):
  0xD1A1F0: far ptr to the item table (page 0x346:0x2164 -> 0xD1A164), far ptr to the handler
            table (0xD1A1BE), u16 item count (5), u16 0x127 ("End of menu")
  header text list at 0xD1A20C: [0x19F "Games", 0x7FFF]
  item record, 18 bytes: {u16 0, u16 0, u16 title, u16 title2, u16 0, u16 0, u16 0, u16 3, u16 x}
  handlers: far pointers -> JMPS trampolines -> game entry points
Usage: python -I extract_games_menu.py <dump> <outdir>
"""
import sys, os, json, struct, re

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from textpack import TextPack

B = 0x800000
def w16(d, a): return struct.unpack_from('<H', d, a - B)[0]
def far(d, a): return w16(d, a + 2) * 0x4000 + (w16(d, a) & 0x3FFF)

# game entry point -> port page (entry points from NOTES.md)
PORTS = {0xCAF8F8: 'stack.html', 0xCA8E38: 'balloon.html', 0xCB5074: 'index.html', 0xD53C96: 'wacko.html',
         0xCA8AF0: None}   # 0xCA8AF0 = games Setup (game id 0)

def extract(d):
    tp = TextPack(d)
    def txt(t):
        s = tp.text(t, 0).decode('latin-1')
        return re.sub(r'\xa4[\x00-\x1f]+', '%d', s).replace('\x95', '').replace('\x8a', '\n').strip()
    desc = 0xD1A1F0
    items_at, handlers_at = far(d, desc + 2), far(d, desc + 6)
    count, end_text = w16(d, desc + 10), w16(d, desc + 12)
    header = w16(d, 0xD1A20C)                      # header text list [0x19F "Games", 0x7FFF]
    items = []
    for i in range(count):
        rec = items_at + 18 * i
        title, title2 = w16(d, rec + 4), w16(d, rec + 6)
        h = far_seg = (w16(d, handlers_at + 4 * i + 2) << 16) | w16(d, handlers_at + 4 * i)
        if d[h - B] == 0xFA:                        # JMPS seg, addr trampoline
            h = (d[h - B + 1] << 16) | struct.unpack_from('<H', d, h - B + 2)[0]
        items.append(dict(title=txt(title), title2=txt(title2), title_id=title, entry=h,
                          port=PORTS.get(h, None)))
    return dict(header=txt(header), end_of_menu=txt(end_text), select=txt(0x52), back=txt(0x2F9),
                sound=txt(0x79D), items=items)

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    out = sys.argv[2]; os.makedirs(out, exist_ok=True)
    m = extract(d)
    with open(os.path.join(out, 'menu.json'), 'w', encoding='utf-8') as f:
        json.dump(m, f, ensure_ascii=False, indent=1)
    print(m['header'], [(i['title'], hex(i['entry']), i['port']) for i in m['items']])
