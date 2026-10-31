# 抖音封面（纸艺立体）：横 4:3（1440×1080）和竖 3:4（1080×1440）。
# 青色墙面 + 剪纸毛边的奶白标题卡 + 一块贴满便利贴的软木板，最上面那张黄色的正在飞走；投影和纸纹跟片子一致。
# 换片子时改 TITLE / SUB / KEY；账号名读节拍表的 brand.name，角色贴纸读 brand.mascot（工程 assets/xiaotuanzi/ 下的文件名），没有就不画
import json
import math
import random
from pathlib import Path
from PIL import Image, ImageDraw, ImageFilter, ImageFont

D = Path(__file__).resolve().parent
FONT = D / 'assets/fonts/NotoSansSC-VF.ttf'
TITLE = ['聊久了，', 'AI 为什么会']          # 标题前几行
KEY = '忘事'                                  # 最后一行，橙红大字
SUB = '板子贴满了，最早的就被挤掉'
BASE = json.loads((D / 'film/cues_base.json').read_text(encoding='utf-8'))
BRAND = BASE.get('brand') or {}
WALL, WALL2, WALL3 = '#2F7F7B', '#3A8E89', '#277370'
CREAM, INK, RED = '#FFF4E0', '#3A2A20', '#E8473B'
FRAME, FRAME2, CORK = '#8A5A3B', '#A26E4A', '#D9A86C'
ME, AI_, CIL = '#FF9F7A', '#FFF4E0', '#FFD43B'
SS = 2


def font(size, weight=900):
    f = ImageFont.truetype(str(FONT), int(size * SS))
    f.set_variation_by_axes([weight])
    return f


def deckle(w, h, r, amp=1.6, seed=1):
    """毛边圆角矩形的轮廓点（以中心为原点，已乘 SS）。"""
    R = random.Random(seed)
    pts = []
    hw, hh = w / 2, h / 2
    cs = [(hw - r, -hh + r, -math.pi / 2), (hw - r, hh - r, 0), (-hw + r, hh - r, math.pi / 2), (-hw + r, -hh + r, math.pi)]
    path = []
    for cx, cy, a0 in cs:
        for k in range(7):
            a = a0 + k / 6 * math.pi / 2
            path.append((cx + math.cos(a) * r, cy + math.sin(a) * r))
    path.append(path[0])
    for (x0, y0), (x1, y1) in zip(path, path[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        n = max(1, round(L / 9))
        for k in range(n):
            u = k / n
            nx, ny = -(y1 - y0) / (L or 1), (x1 - x0) / (L or 1)
            d = (R.random() - .5) * 2 * amp
            pts.append(((x0 + (x1 - x0) * u + nx * d) * SS, (y0 + (y1 - y0) * u + ny * d) * SS))
    return pts


def piece(im, cx, cy, w, h, r, fill, rot=0, lift=0., seed=1, text=None, tsize=0):
    """一张剪纸：投影 + 毛边纸片（可带一行字），转 rot 度贴到 (cx, cy)。"""
    pad = int((40 + lift * 50) * SS)
    W, H = int(w * SS) + pad * 2, int(h * SS) + pad * 2
    lay = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    pts = [(x + W / 2, y + H / 2) for x, y in deckle(w, h, r, seed=seed)]
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    off = ((3 + lift * 12) * SS, (6 + lift * 30) * SS)
    ImageDraw.Draw(sh).polygon([(x + off[0], y + off[1]) for x, y in pts], fill=(40, 22, 10, int(255 * (.34 - .1 * lift))))
    lay.alpha_composite(sh.filter(ImageFilter.GaussianBlur((7 + lift * 30) * SS / 2)))
    d = ImageDraw.Draw(lay)
    d.polygon(pts, fill=fill)
    if text:
        d.text((W / 2 - w * SS / 2 + 40 * SS, H / 2), text, font=font(tsize), fill=INK, anchor='lm')
    lay = lay.rotate(-rot, resample=Image.BICUBIC, expand=True)
    im.alpha_composite(lay, (int(cx * SS - lay.width / 2), int(cy * SS - lay.height / 2)))


def grain(w, h):
    R = random.Random(5)
    g = Image.effect_noise((w * SS, h * SS), 18).convert('L').point(lambda v: 200 + v * 55 // 255)
    d = ImageDraw.Draw(g)
    for _ in range(int(w * h / 1000)):
        x, y, a, L = R.random() * w * SS, R.random() * h * SS, R.random() * 6.28, (6 + R.random() * 22) * SS
        d.line((x, y, x + math.cos(a) * L, y + math.sin(a) * L), fill=180, width=1)
    return g


def board(im, x, y, k):
    """贴满便利贴的软木板，左上角 (x, y)，k 是缩放；最上面一格空着（那张飞走了）。"""
    bw, n, sl = 600 * k, 8, 72 * k
    bh = 16 * k + n * sl
    piece(im, x + bw / 2, y + bh / 2, bw + 64 * k, bh + 64 * k, 26 * k, FRAME, lift=.25, seed=11)
    piece(im, x + bw / 2, y + bh / 2, bw + 36 * k, bh + 36 * k, 20 * k, FRAME2, seed=12)
    piece(im, x + bw / 2, y + bh / 2, bw, bh, 12 * k, CORK, seed=13)
    for i in range(1, n):
        piece(im, x + bw / 2, y + 16 * k + i * sl + 29 * k, 540 * k, 58 * k, 9 * k, ME if i % 2 == 0 else AI_, seed=20 + i)
        d = ImageDraw.Draw(im)
        px, py = (x + bw / 2 - 270 * k + 24 * k) * SS, (y + 16 * k + i * sl + 29 * k) * SS
        d.ellipse((px - 11 * k * SS, py - 11 * k * SS, px + 11 * k * SS, py + 11 * k * SS), fill=RED)
    return x + bw / 2, y + 16 * k + 29 * k


def make(w, h, out):
    im = Image.new('RGBA', (w * SS, h * SS), WALL)
    d = ImageDraw.Draw(im)
    for bx, by, r, c in [(.08, .12, .16, WALL2), (.95, .1, .2, WALL3), (.9, .95, .22, WALL2), (.15, .97, .18, WALL3)]:
        cx, cy, rr = bx * w * SS, by * h * SS, r * max(w, h) * SS
        d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=c)
    wide = w > h
    if wide:
        sx, sy = board(im, 860, 250, .78)
        piece(im, sx - 150, sy - 120, 540 * .78, 58 * .78, 9, CIL, rot=-9, lift=1, seed=30, text='我不吃香菜', tsize=30)
        cx, cy, cw, ch = 400, 470, 640, 560
    else:
        sx, sy = board(im, 520, 860, .78)
        piece(im, sx - 170, sy - 110, 540 * .78, 58 * .78, 9, CIL, rot=-9, lift=1, seed=30, text='我不吃香菜', tsize=30)
        cx, cy, cw, ch = 540, 440, 900, 620
    piece(im, cx, cy, cw, ch, 22, CREAM, rot=-1.5, lift=.4, seed=40)
    d = ImageDraw.Draw(im)
    s1 = 96 if wide else 118
    y = cy - ch / 2 + 70 + s1 * .9
    x = cx - cw / 2 + 56
    for line in TITLE:
        d.text((x * SS, y * SS), line, font=font(s1), fill=INK, anchor='ls'); y += s1 * 1.18
    s2 = s1 * 1.5
    y += s2 * .12
    d.text((x * SS, y * SS), KEY, font=font(s2), fill=RED, anchor='ls')
    d.text((x * SS, (y + s1 * .62) * SS), SUB, font=font(s1 * .36, 700), fill='#7A6250', anchor='ls')
    if BRAND.get('mascot'):
        f = D / 'assets/xiaotuanzi' / BRAND['mascot']
        if f.exists():
            a = Image.open(f).convert('RGBA'); a = a.crop(a.getbbox())
            mw = (300 if wide else 340) * SS
            a = a.resize((mw, int(a.height * mw / a.width)), Image.LANCZOS)
            sh = Image.new('RGBA', a.size, (40, 22, 10, 0)); sh.putalpha(a.split()[3].point(lambda v: v * 90 // 255))
            mx, my = ((w - 330) if wide else (w - 380)) * SS, ((h - 330) if wide else (h - 420)) * SS
            im.alpha_composite(sh.filter(ImageFilter.GaussianBlur(14 * SS)), (int(mx + 8 * SS), int(my + 18 * SS)))
            im.alpha_composite(a, (int(mx), int(my)))
    if BRAND.get('name'):
        d.text((x * SS, (h - 60) * SS), BRAND['name'], font=font(40 if wide else 44, 800), fill='#FFE7B8', anchor='ls')
    rgb = im.convert('RGB')
    rgb = Image.composite(rgb, Image.new('RGB', rgb.size, (0, 0, 0)), Image.new('L', rgb.size, 255))
    from PIL import ImageChops
    rgb = ImageChops.multiply(rgb, Image.merge('RGB', [grain(w, h)] * 3))
    rgb.resize((w, h), Image.LANCZOS).save(out, quality=95)
    print(out)


if __name__ == '__main__':
    make(1440, 1080, D / '封面_横4比3.jpg')
    make(1080, 1440, D / '封面_竖3比4.jpg')
