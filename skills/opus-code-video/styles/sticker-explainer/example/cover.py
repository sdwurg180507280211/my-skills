# 抖音封面：横 4:3（1440×1080）和竖 3:4（1080×1440），和片子同一套配色、字体和回车键贴纸
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

D = Path(__file__).resolve().parent
FONT = D / 'assets/fonts/NotoSansSC-VF.ttf'
MONO = D / 'assets/fonts/JetBrainsMono-VF.ttf'
BG, SLATE, MID, ACC, BLUE, PALE = '#E9EEF2', '#263646', '#5E6E7E', '#FF5A36', '#3D6FE0', '#C8D2DB'
SS = 2                                       # 先画 2 倍再缩小，边缘更干净
# 账号名读节拍表的 brand.name（和片尾落款一致），没有就不写
import json
BRAND = (json.loads((D / 'film/cues_base.json').read_text(encoding='utf-8')).get('brand') or {}).get('name', '')


def font(size, weight, path=FONT):
    f = ImageFont.truetype(str(path), size * SS)
    f.set_variation_by_axes([weight])
    return f


def background(w, h):
    im = Image.new('RGB', (w * SS, h * SS), BG)
    d = ImageDraw.Draw(im)
    step = 60 * SS
    for y in range(step // 2, h * SS, step):
        for x in range(step // 2, w * SS, step):
            r = 2.6 * SS
            d.ellipse((x - r, y - r, x + r, y + r), fill=PALE)
    return im


def sticker(layer, outline=10):
    """给透明图层加粗白描边和柔和投影，返回合成好的 RGBA。"""
    a = layer.split()[3]
    grown = a.filter(ImageFilter.MaxFilter(outline * 2 * SS + 1))
    shadow = grown.filter(ImageFilter.GaussianBlur(10 * SS))
    out = Image.new('RGBA', layer.size, (0, 0, 0, 0))
    sh = Image.new('RGBA', layer.size, (29, 43, 56, 0)); sh.putalpha(shadow.point(lambda v: int(v * .22)))
    out.alpha_composite(sh, (0, 9 * SS))
    white = Image.new('RGBA', layer.size, (255, 255, 255, 0)); white.putalpha(grown)
    out.alpha_composite(white)
    out.alpha_composite(layer)
    return out


def enter_key(scale=1.0):
    s = SS * scale
    W, H = int(330 * s), int(320 * s)
    L = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(L)
    ox, oy = W / 2, H / 2 - 10 * s
    d.rounded_rectangle((ox - 135 * s, oy - 95 * s, ox + 135 * s, oy + 135 * s), 38 * s, fill='#B9C6D2')
    d.rounded_rectangle((ox - 125 * s, oy - 125 * s, ox + 125 * s, oy + 85 * s), 32 * s, fill='white', outline='#D9E1E8', width=int(3 * s))
    f = ImageFont.truetype(str(FONT), int(54 * s)); f.set_variation_by_axes([800])
    d.text((ox - 88 * s, oy - 30 * s), 'Enter', font=f, fill=SLATE, anchor='ls')
    w = int(13 * s)
    pts = [(ox + 70 * s, oy - 6 * s), (ox + 70 * s, oy + 30 * s), (ox - 40 * s, oy + 30 * s)]
    d.line(pts, fill=ACC, width=w, joint='curve')
    d.line([(ox - 40 * s, oy + 30 * s), (ox - 14 * s, oy + 8 * s)], fill=ACC, width=w)
    d.line([(ox - 40 * s, oy + 30 * s), (ox - 14 * s, oy + 52 * s)], fill=ACC, width=w)
    for x, y in pts + [(ox - 14 * s, oy + 8 * s), (ox - 14 * s, oy + 52 * s)]:
        d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=ACC)
    return sticker(L)


def pills(d, x, y, items, size):
    for i, s in enumerate(items):
        f = font(size, 700, MONO if s.isascii() else FONT)   # 代码字体没有中文字形
        tw = d.textlength(s, font=f)
        h = size * 1.9 * SS
        col = ACC if i % 2 == 0 else BLUE
        d.rounded_rectangle((x, y, x + tw + size * 1.6 * SS, y + h), h / 2, fill=col)
        d.text((x + size * .8 * SS, y + h / 2), s, font=f, fill='white', anchor='lm')
        x += tw + size * 1.6 * SS + size * .7 * SS
    return x


def title_block(im, x, y, size):
    d = ImageDraw.Draw(im)
    f = font(size, 900)
    d.text((x * SS, y * SS), '按下回车', font=f, fill=SLATE, anchor='ls')
    y2 = y + size * 1.2
    w1 = d.textlength('之后的', font=f)
    # 下划线高亮放在"1"后面
    f1 = font(int(size * 1.27), 900)
    wn = d.textlength('1', font=f1)
    d.rounded_rectangle((x * SS + w1 + 10 * SS, y2 * SS - size * .32 * SS, x * SS + w1 + wn + d.textlength('秒', font=f) + 40 * SS, y2 * SS - size * .08 * SS), 14 * SS, fill='#FBD3C6')
    d.text((x * SS, y2 * SS), '之后的', font=f, fill=SLATE, anchor='ls')
    d.text((x * SS + w1 + 16 * SS, y2 * SS), '1', font=f1, fill=ACC, anchor='ls')
    d.text((x * SS + w1 + wn + 40 * SS, y2 * SS), '秒', font=f, fill=SLATE, anchor='ls')
    return y2


def make(w, h, out):
    im = background(w, h).convert('RGBA')
    d = ImageDraw.Draw(im)
    if w > h:      # 横 4:3
        y2 = title_block(im, 96, 330, 168)
        d.text((100 * SS, (y2 + 96) * SS), '浏览器替你跑完了 6 步', font=font(52, 600), fill=MID, anchor='ls')
        pills(d, 100 * SS, int((y2 + 150) * SS), ['DNS', 'TCP', 'TLS', 'HTTP', '渲染'], 34)
        k = enter_key(1.25); im.alpha_composite(k, (int(1010 * SS), int(640 * SS)))
        d.text((100 * SS, (h - 70) * SS), BRAND, font=font(40, 800), fill=ACC, anchor='ls')
    else:          # 竖 3:4
        y2 = title_block(im, 90, 360, 176)
        d.text((96 * SS, (y2 + 100) * SS), '浏览器替你跑完了 6 步', font=font(54, 600), fill=MID, anchor='ls')
        x = pills(d, 96 * SS, int((y2 + 160) * SS), ['DNS', 'TCP', 'TLS'], 36)
        pills(d, 96 * SS, int((y2 + 250) * SS), ['HTTP', '渲染'], 36)
        k = enter_key(1.35); im.alpha_composite(k, (int(560 * SS), int(950 * SS)))
        d.text((96 * SS, (h - 80) * SS), BRAND, font=font(44, 800), fill=ACC, anchor='ls')
    im.convert('RGB').resize((w, h), Image.LANCZOS).save(out, quality=95)
    print(out)


if __name__ == '__main__':
    make(1440, 1080, D / '封面_横4比3.jpg')
    make(1080, 1440, D / '封面_竖3比4.jpg')
