"""把纯色底的贴纸抠成透明底：python3 cutout.py <原图目录> <输出目录>

做法：先把原图里本来就透明的地方铺回底色（底色取左上角），再从四条边上每隔 16 像素往里做容差填充，
填到的就是背景；角色有白色描边，和浅色底分得开，所以不会吃进角色里面。最后裁掉空边、留 16 像素，最长边缩到 800。
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

KEY = (255, 0, 255)


def cut(src):
    im = Image.open(src).convert('RGBA')
    bg = im.getpixel((2, 2))[:3]
    flat = Image.new('RGBA', im.size, bg + (255,))
    flat.alpha_composite(im)
    work = flat.convert('RGB')
    w, h = work.size
    seeds = [(x, y) for x in range(0, w, 16) for y in (0, h - 1)] + [(x, y) for y in range(0, h, 16) for x in (0, w - 1)]
    for xy in seeds:
        if work.getpixel(xy) != KEY:
            ImageDraw.floodfill(work, xy, KEY, thresh=42)
    mask = work.point(lambda v: 0).convert('L')
    px, mp = work.load(), mask.load()
    for y in range(h):
        for x in range(w):
            mp[x, y] = 0 if px[x, y] == KEY else 255
    out = flat.convert('RGB').convert('RGBA')
    out.putalpha(mask)
    x0, y0, x1, y1 = out.getbbox()
    out = out.crop((max(0, x0 - 16), max(0, y0 - 16), min(w, x1 + 16), min(h, y1 + 16)))
    out.thumbnail((800, 800), Image.LANCZOS)
    return out


if __name__ == '__main__':
    src, dst = Path(sys.argv[1]), Path(sys.argv[2])
    dst.mkdir(parents=True, exist_ok=True)
    for f in sorted(src.glob('*.png')):
        cut(f).save(dst / f.name)
        print(dst / f.name)
