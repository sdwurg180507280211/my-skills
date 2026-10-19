"""拆解参考视频：python3 breakdown.py 参考视频/某剧_第01集.mp4 [--out 目录] [--compare 6_成片/成片.mp4]

把一条别人的短剧拆成逐镜头的素材，供 Claude 看图写拆解：
- 切镜点 → 镜头列表（每个镜头取中间一帧，存进 帧/，每 12 个拼一张 镜头总览_N.jpg，标好编号和时间）
- 中间一帧会骗人（淡入淡出、叠化切不出来），所以另外抽帧：开头 20 秒每秒一帧拼成 开头_每秒.jpg，
  超过 10 秒的"镜头"每 4 秒一帧拼成 镜头NN_每4秒.jpg
- 画面底部的字幕（macOS Vision 识别）→ 去重成台词，按时间挂到镜头上
- 拆解.md 草稿：整体数字、逐镜头表（"画面"一栏留空，由 Claude 看总览图后填写）
- --compare 给出另一条视频（通常是自己的成片）的时长和镜头数，方便对比节奏

声音（配乐、音效、语气）脚本听不出来，要用户听。参考视频由用户自己保存，只在本机学习用。
"""
import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

import review

SHEET_N = 12      # 每张总览图放几个镜头
HOOK = 12.0       # 统计"开头多少秒里有几个镜头"
OPENING = 20.0    # 开头这么多秒每秒抽一帧
LONG = 10.0       # 比这长的"镜头"可能藏着叠化，每 4 秒抽一帧


def detect_cuts(video, threshold=0.25):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf",
                        f"select='gt(scene,{threshold})',showinfo", "-f", "null", "-"],
                       capture_output=True, text=True)
    return review.scene_cuts(r.stderr)


def shots_from_cuts(cuts, duration):
    """切镜点 → [(编号, 起, 止)]；太靠近开头或结尾的切点不单独成镜。"""
    bounds = [0.0] + [c for c in sorted(cuts) if 0.05 < c < duration - 0.05] + [duration]
    return [(i + 1, round(a, 2), round(b, 2)) for i, (a, b) in enumerate(zip(bounds, bounds[1:]))]


def subtitle_lines(hits, fps, min_y=0.65):
    """OCR 命中 [(秒, 置信度, 文字, "x,y,w,h")] → 去重后的字幕 [{start, end, text}]。

    只取画面下部（y ≥ min_y，y 从上往下量）的字当字幕；同一句在相邻帧里连续出现就合并成一条。
    """
    step = 1 / fps
    lines = []
    for t, _conf, text, box in sorted(hits):
        try:
            y = float(box.split(",")[1])
        except (IndexError, ValueError):
            continue
        text = text.strip()
        if y < min_y or not text:
            continue
        last = lines[-1] if lines else None
        if last and last["text"] == text and t - last["end"] <= step + 0.01:
            last["end"] = round(t + step, 2)
        elif not (last and last["text"] == text and t < last["end"]):
            lines.append({"start": round(t, 2), "end": round(t + step, 2), "text": text})
    return lines


def lines_for_shot(lines, start, end):
    """开始时间落在这个镜头里的字幕。"""
    return [x["text"] for x in lines if start <= x["start"] < end]


def ocr_hits(video, fps):
    exe = review.ocr_binary()
    if exe is None:
        return None
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={fps}", f"{td}/f_%04d.png"], check=True)
        out = subprocess.run([str(exe)] + sorted(str(f) for f in Path(td).glob("f_*.png")),
                             capture_output=True, text=True).stdout
    return review.parse_ocr(out, fps)


def tile(images, labels, cols, path):
    """把一组同尺寸的帧拼成一张图，每帧上方写一行标签。"""
    from PIL import Image, ImageDraw
    w, h = images[0].size
    cols = min(cols, len(images))
    rows = (len(images) + cols - 1) // cols
    sheet = Image.new("RGB", (w * cols, (h + 28) * rows), "white")
    draw = ImageDraw.Draw(sheet)
    for j, (im, label) in enumerate(zip(images, labels)):
        x, y = (j % cols) * w, (j // cols) * (h + 28)
        sheet.paste(im, (x, y + 28))
        draw.text((x + 6, y + 7), label, fill="black")
    sheet.save(path, quality=85)


def contact_sheets(video, shots, outdir):
    from PIL import Image
    frames = outdir / "帧"
    frames.mkdir(parents=True, exist_ok=True)
    for n, a, b in shots:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{(a + b) / 2:.2f}", "-i", str(video),
                        "-frames:v", "1", "-vf", "scale=360:-2", str(frames / f"{n:02d}.jpg")], check=True)
    sheets = []
    for k in range(0, len(shots), SHEET_N):
        part = shots[k:k + SHEET_N]
        path = outdir / f"镜头总览_{k // SHEET_N + 1}.jpg"
        tile([Image.open(frames / f"{n:02d}.jpg") for n, _, _ in part],
             [f"#{n}  {a:.1f}-{b:.1f}s  ({b - a:.1f}s)" for n, a, b in part], 6, path)
        sheets.append(path.name)
    return sheets


def long_sheet(n, a, b):
    """长镜头要加抽的图名；不用加抽返回 None。整个落在开头里的，开头那张已经覆盖。"""
    return f"镜头{n:02d}_每4秒.jpg" if b - a > LONG and b > OPENING else None


def sample_plan(shots, duration):
    """要加抽的帧：[(文件名, 起, 止, 每几秒一帧, 每行几张)]。开头一张；切镜检测没切开的长镜头各一张。"""
    return [("开头_每秒.jpg", 0.0, min(OPENING, duration), 1, 5)] + \
        [(long_sheet(n, a, b), a, b, 4, 6) for n, a, b in shots if long_sheet(n, a, b)]


def sample_sheets(video, plan, outdir):
    from PIL import Image
    for name, a, b, step, cols in plan:
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{a:.2f}", "-t", f"{b - a:.2f}", "-i", str(video),
                            "-vf", f"fps=1/{step},scale=320:-2", f"{td}/f_%04d.jpg"], check=True)
            files = sorted(Path(td).glob("f_*.jpg"))
            if files:
                tile([Image.open(f) for f in files], [f"{a + i * step:.0f}s" for i in range(len(files))],
                     cols, outdir / name)
    return [name for name, *_ in plan if (outdir / name).exists()]


def stats(duration, shots, lines=None):
    s = {"时长": f"{duration:.1f} 秒", "镜头数": len(shots),
         "平均每个镜头": f"{duration / max(1, len(shots)):.1f} 秒",
         f"前 {HOOK:g} 秒的镜头数": sum(1 for _, a, _ in shots if a < HOOK)}
    if lines is not None:
        s["字幕条数"] = len(lines)
    return s


def draft(video, duration, wh, shots, lines, sheets, compare=None, samples=()):
    ref = stats(duration, shots, lines)
    head = ["", video.stem] + ([compare["name"]] if compare else [])
    rows = [f"| {k} | {v} |" + (f" {compare['stats'].get(k, '—')} |" if compare else "") for k, v in ref.items()]
    out = [f"# 拆解：{video.stem}", "",
           f"- 文件：{video.name}，{wh}，{duration:.1f} 秒。只在本机学习用。",
           f"- 镜头总览：{'、'.join(sheets)}（每个镜头取中间一帧，只能粗看）",
           f"- 加抽的帧：{'、'.join(samples) or '无'}。镜头数是按画面突变切的，淡入淡出、叠化切不开、闪电会多切；"
           "开头和长镜头以加抽的帧为准，数字不对就在表里改。",
           "- 台词来自画面底部字幕的文字识别，个别字可能识别错；没有字幕的片子这一栏会是空的。",
           "- 声音（配乐、音效、语气）还没听，要用户听。", "",
           "## 整体数字", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head), *rows, "",
           "## 整集结构", "", "（Claude 看完总览图后，按段落写：时间、镜头数、这一段做了什么）", "",
           "## 逐镜头表", "", "| # | 时间（秒） | 时长 | 画面 | 台词（字幕） |", "|---:|---|---:|---|---|"]
    for n, a, b in shots:
        note = f"可能不止一个镜头，看 {long_sheet(n, a, b)}" if long_sheet(n, a, b) else ""
        out.append(f"| {n} | {a:.1f}–{b:.1f} | {b - a:.1f} | {note} | {' / '.join(lines_for_shot(lines, a, b))} |")
    out += ["", "## 值得学的地方", "", "（对照 references/reference-breakdown.md 的清单写）", "",
            "## 换我们来拍", "", "（挑一段，按 prompting.md 的写法改写成提示词；只写不生成，真拍前先报价）", ""]
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="拆解参考视频")
    ap.add_argument("video")
    ap.add_argument("--out", help="输出目录，默认 <视频同目录>/<视频名>_拆解")
    ap.add_argument("--compare", help="拿来对比的另一条视频，例如自己的成片")
    ap.add_argument("--fps", type=int, default=2, help="识别字幕的采样帧率（默认 2）")
    a = ap.parse_args(argv)
    video = Path(a.video).resolve()
    outdir = Path(a.out) if a.out else video.with_name(video.stem + "_拆解")
    outdir.mkdir(parents=True, exist_ok=True)

    duration = float(review.probe(video, "format=duration"))
    wh = review.probe(video, "stream=width,height", "v:0").replace(",", "×")
    shots = shots_from_cuts(detect_cuts(video), duration)
    hits = ocr_hits(video, a.fps)
    lines = subtitle_lines(hits, a.fps) if hits is not None else []
    sheets = contact_sheets(video, shots, outdir)
    samples = sample_sheets(video, sample_plan(shots, duration), outdir)
    compare = None
    if a.compare:
        cv = Path(a.compare).resolve()
        cd = float(review.probe(cv, "format=duration"))
        compare = {"name": cv.stem, "stats": stats(cd, shots_from_cuts(detect_cuts(cv), cd))}

    (outdir / "镜头与台词.json").write_text(json.dumps(
        {"shots": [{"n": n, "start": s, "end": e, "lines": lines_for_shot(lines, s, e)} for n, s, e in shots],
         "subtitles": lines}, ensure_ascii=False, indent=1), encoding="utf-8")
    md = outdir / "拆解.md"
    if md.exists():
        md = outdir / "拆解_草稿.md"   # 不覆盖已经写好的拆解
    md.write_text(draft(video, duration, wh, shots, lines, sheets, compare, samples), encoding="utf-8")
    print(f"{len(shots)} 个镜头，{len(lines)} 条字幕{'' if hits is not None else '（没做文字识别：需要 macOS 和 swiftc）'}")
    print(f"输出：{outdir}（{md.name}、{'、'.join(sheets + samples)}、镜头与台词.json）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
