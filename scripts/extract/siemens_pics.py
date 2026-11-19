"""Siemens x55 picture table + packed-bitmap decoder (A55 V9 LG7).

Reimplemented from the firmware:
  * FUN_a95df8: picture id -> 8-byte descriptor at theme_table + id*8. For this dump the table
    is at CPU 0xE6C5B8 (525 entries; found by scanning, matches the id->picture checks below).
    Descriptor: u8 w, u8 h, u16 type, u16 offset, u16 page (data = page*0x4000 + offset&0x3FFF).
  * type & 0x7F == 1: 1 bit per pixel. Bit 0x80 set = packed, decoded by FUN_a9f67a:
      pixels are emitted row-major (w per row); a token can span rows.
      token byte b:  b & 0x80 == 0 -> literal: 7 pixels = bits 6..0 (MSB first)
                     b & 0x80 != 0 -> run: (b & 0x3F) pixels of colour (b >> 6) & 1   (1 = black)
    Unpacked type 1: rows of ceil(w/8) bytes, MSB first.
Usage: python -I siemens_pics.py <dump> <id> [<id> ...] -> writes pic_<id>.png in cwd/out dir
"""
import struct, sys, os

B = 0x800000
PIC_TABLE = 0xE6C5B8
PIC_COUNT = 525

def descriptor(d, pid, table=PIC_TABLE):
    w, h, typ, off, page = struct.unpack_from('<BBHHH', d, table + pid * 8 - B)
    return dict(id=pid, w=w, h=h, type=typ, addr=page * 0x4000 + (off & 0x3FFF))

def decode(d, desc):
    w, h, a = desc['w'], desc['h'], desc['addr'] - B
    if desc['type'] & 0x7F != 1:
        raise ValueError('unsupported picture type 0x%x' % desc['type'])
    px = []
    if desc['type'] & 0x80:
        while len(px) < w * h:
            b = d[a]; a += 1
            if b & 0x80:
                px += [(b >> 6) & 1] * (b & 0x3F)
            else:
                px += [(b >> k) & 1 for k in range(6, -1, -1)]
        px = px[:w * h]
    else:
        rb = (w + 7) // 8
        for y in range(h):
            for x in range(w):
                px.append(d[a + y * rb + (x >> 3)] >> (7 - (x & 7)) & 1)
    return [px[y * w:(y + 1) * w] for y in range(h)]

if __name__ == '__main__':
    from PIL import Image
    d = open(sys.argv[1], 'rb').read()
    for s in sys.argv[2:]:
        desc = descriptor(d, int(s, 0))
        bits = decode(d, desc)
        im = Image.new('L', (desc['w'], desc['h']), 255)
        for y, row in enumerate(bits):
            for x, v in enumerate(row):
                if v: im.putpixel((x, y), 0)
        name = 'pic_%03x.png' % desc['id']
        im.save(name); print(name, desc)
