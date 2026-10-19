"""片尾卡：python3 end_card.py 输出.png --title "第一行|第二行" [--tag 下集] [--note "普通文字|红色强调"]
                                  [--sub 小字] [--footer 剧情纯属虚构] [--size 720x1280] [--font 字体路径]

黑底竖版卡片：上方标签和标题（下集钩子），分隔线下是一句知识点（"|" 后半段标红）和小字，底部是声明。
按 2 倍分辨率渲染再缩小，字更清楚。需要 Pillow；默认使用 macOS 自带的冬青黑体。
"""
import argparse
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

FONTS = ["/System/Library/Fonts/Hiragino Sans GB.ttc", "/System/Library/Fonts/STHeiti Medium.ttc"]


def find_font(path=None):
    for f in ([path] if path else FONTS):
        if f and Path(f).exists():
            return f
    raise SystemExit("找不到中文字体，请用 --font 指定")


def render(out, title, tag=None, note=None, sub=None, footer=None, size=(720, 1280), font_path=None):
    S = 2
    W, H = size[0] * S, size[1] * S
    k = size[1] / 1280  # 以 720×1280 的版式为基准按高度缩放
    fp = find_font(font_path)

    def font(px, bold=True):
        try:
            return ImageFont.truetype(fp, int(px * k * S), index=1 if bold else 0)
        except OSError:
            return ImageFont.truetype(fp, int(px * k * S))

    img = Image.new("RGB", (W, H), "black")
    d = ImageDraw.Draw(img)

    def width(t, f):
        return d.textbbox((0, 0), t, font=f)[2]

    def center(y, t, f, fill):
        d.text(((W - width(t, f)) // 2, int(y * k * S)), t, font=f, fill=fill)

    lines = title.split("|")
    y = 520 - 40 * (len(lines) - 2)
    if tag:
        ft = font(26)
        tw = width(tag, ft)
        d.rounded_rectangle([((W - tw) // 2 - 16 * S, int((y - 90) * k * S)), ((W + tw) // 2 + 16 * S, int((y - 42) * k * S))],
                            radius=8 * S, fill=(200, 40, 40))
        center(y - 83, tag, ft, "white")
    for i, line in enumerate(lines):
        center(y + 80 * i, line, font(52), "white")
    if note:
        yn = y + 80 * (len(lines) - 1) + 195
        d.line([((W - 180 * S) // 2, int((yn - 35) * k * S)), ((W + 180 * S) // 2, int((yn - 35) * k * S))],
               fill=(90, 90, 90), width=2 * S)
        a, _, b = note.partition("|")
        fa, fb = font(30, False), font(30)
        x0 = (W - width(a, fa) - width(b, fb)) // 2
        d.text((x0, int(yn * k * S)), a, font=fa, fill=(210, 210, 210))
        d.text((x0 + width(a, fa), int(yn * k * S)), b, font=fb, fill=(255, 96, 96))
        if sub:
            center(yn + 53, sub, font(26, False), (170, 170, 170))
    if footer:
        center(1200, footer, font(20, False), (110, 110, 110))
    img.resize(size, Image.LANCZOS).save(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="渲染片尾卡")
    ap.add_argument("out")
    ap.add_argument("--title", required=True, help='标题，多行用 "|" 分隔')
    ap.add_argument("--tag")
    ap.add_argument("--note", help='知识点，"|" 后的部分标红')
    ap.add_argument("--sub")
    ap.add_argument("--footer")
    ap.add_argument("--size", default="720x1280")
    ap.add_argument("--font")
    a = ap.parse_args(argv)
    w, h = (int(v) for v in a.size.lower().split("x"))
    render(a.out, a.title, a.tag, a.note, a.sub, a.footer, (w, h), a.font)
    print(a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
