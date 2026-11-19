"""Decoder for the Siemens x55 language/text pack (A55 V9 LG7 at CPU 0xDA0000), reimplemented
from the firmware routine FUN_d4850e (text API FUN_d4a242 / FUN_d4a316). See NOTES.md.

Usage: python -I textpack.py <dump> [lang_index] [--grep WORD]
"""
import sys, struct

BASE = 0x800000
PACK = 0xDA0000          # page 0x368

class TextPack:
    def __init__(self, dump):
        self.d = dump
        p = PACK - BASE
        self.p = p
        w = lambda o: struct.unpack_from('<H', dump, p + o)[0]
        assert w(0) == 0xBBBB, 'bad magic'
        self.nblocks = w(0x06)
        self.slot_tab = w(0x08)
        self.desc_tab = w(0x0A)
        self.nlang_hint = w(0x0C)
        self.per_id = w(0x0E)          # strings per text id (language slots)
        self.index_tab = w(0x12)
        self.thresh = [w(0x3C + 2 * i) for i in range(self.nblocks - 1)]
        self.name = dump[p + 0x16:p + 0x1A].split(b'\0')[0].decode()

    def w(self, off):       # word inside page 0 of the pack
        return struct.unpack_from('<H', self.d, self.p + off)[0]

    def b(self, page, off):  # byte at (page, 14-bit offset)
        return self.d[page * 0x4000 + (off & 0x3FFF) - BASE]

    def desc(self, lang):
        o = self.desc_tab + lang * 14
        return [self.w(o + 2 * i) for i in range(7)]

    def slot(self, lang):
        return self.d[self.p + self.slot_tab + lang]

    def raw(self, n):
        page = 0x368
        for t in self.thresh:          # same loop as firmware: advance while n >= threshold
            if n < t: break
            page += 1
        off = self.w(self.index_tab + (n >> 3) * 2)
        for _ in range(n & 7):
            off += self.b(page, off)
        ln = self.b(page, off)
        return [self.b(page, off + 1 + i) for i in range(ln - 1)]

    def decode_codes(self, codes, lang):
        t1, n1, t2, n2, t3, n3, t4 = self.desc(lang)
        out = bytearray()
        for c in codes:
            if c < n1:   src, k = t1 + c, 1
            elif c < n2: src, k = t2 + (c - n1) * 2, 2
            elif c < n3: src, k = t3 + (c - n2) * 3, 3
            else:        src, k = t4 + (c - n3) * 4, 4
            out += self.d[self.p + src:self.p + src + k]
        return bytes(out)

    def text(self, tid, lang):
        return self.decode_codes(self.raw(tid * self.per_id + self.slot(lang)), lang)

def to_str(b):
    return b.decode('latin-1')

if __name__ == '__main__':
    d = open(sys.argv[1], 'rb').read()
    tp = TextPack(d)
    lang = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith('-') else 0
    grep = sys.argv[sys.argv.index('--grep') + 1].lower() if '--grep' in sys.argv else None
    print('pack', tp.name, 'blocks', tp.nblocks, 'per_id', tp.per_id, 'lang', lang, 'slot', tp.slot(lang), 'desc', [hex(x) for x in tp.desc(lang)])
    for tid in range(0xBE3):
        try:
            s = to_str(tp.text(tid, lang))
        except Exception as e:
            s = '<err %s>' % e
        if grep is None or grep in s.lower():
            print('%04x %r' % (tid, s))
