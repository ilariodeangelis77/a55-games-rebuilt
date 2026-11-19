"""Render every extracted level as the phone would show it at start (101x64, 10x8 tiles, cell
(0,0) replaced by the level number like FUN_cb1fae/FUN_cb276c do), into one contact sheet.
Usage: python -I render_levels.py <outdir-with-levels.json+tiles.json> [scale]"""
import sys, os, json
from PIL import Image, ImageDraw
sys.path.insert(0, os.path.dirname(__file__))
from extract_mtb import TILE_PIC

DIGITS = {  # 3x5 digit glyphs (approximation of the phone's small font, used for the level number)
    '0': '111101101101111', '1': '010110010010111', '2': '111001111100111', '3': '111001111001111',
    '4': '101101111001001', '5': '111100111001111', '6': '111100111101111', '7': '111001010010010',
    '8': '111101111101111', '9': '111101111001111'}

def screen(lv, tiles):
    scr = Image.new('L', (101, 64), 255)
    imgs = {}
    for code, pic in TILE_PIC.items():
        t = tiles[pic]; im = Image.new('L', (10, 8), 255)
        for y in range(8):
            for x in range(10):
                if t['bits'][y][x]: im.putpixel((x, y), 0)
        imgs[code] = im
    for r, row in enumerate(lv['grid']):
        for c, code in enumerate(row):
            if (r, c) != (0, 0): scr.paste(imgs[code], (c * 10, r * 8))
    for i, ch in enumerate(str(lv['index'])):
        for k, bit in enumerate(DIGITS[ch]):
            if bit == '1': scr.putpixel((1 + i * 4 + k % 3, 1 + k // 3), 0)
    return scr

if __name__ == '__main__':
    out = sys.argv[1]; S = int(sys.argv[2]) if len(sys.argv) > 2 else 3
    lv = json.load(open(os.path.join(out, 'levels.json'))); tiles = json.load(open(os.path.join(out, 'tiles.json')))
    PADX, PADY, LABEL, cols = 14, 10, 16, 5
    rows = (len(lv) + cols - 1) // cols
    sheet = Image.new('RGB', (cols * (101 * S + PADX) + PADX, rows * (64 * S + PADY + LABEL) + PADY), (235, 235, 230))
    dr = ImageDraw.Draw(sheet)
    for i, L in enumerate(lv):
        x = PADX + (i % cols) * (101 * S + PADX); y = PADY + (i // cols) * (64 * S + PADY + LABEL)
        dr.text((x, y), 'Level %d  (%d boxes)%s' % (L['index'], L['boxes'], '  [stored transposed]' if L['flag'] else ''), fill=(0, 0, 0))
        sheet.paste(screen(L, tiles).resize((101 * S, 64 * S), Image.NEAREST).convert('RGB'), (x, y + LABEL))
        dr.rectangle([x - 1, y + LABEL - 1, x + 101 * S, y + LABEL + 64 * S], outline=(120, 120, 120))
    sheet.save(os.path.join(out, 'levels_sheet.png')); print(os.path.join(out, 'levels_sheet.png'))
