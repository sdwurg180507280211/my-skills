"""自动审片：python3 review.py 片段1.mp4 [片段2.mp4 ...] [--out 5_审片] [--fps 4]

每条视频输出 <名>_帧.png（检查图：每秒 fps 帧，从左到右、从上到下）和 <名>_报告.md，并打印报告。
自动检查：切镜时间点、画面文字（macOS Vision 逐帧全分辨率识别）、有声区间、首尾音量。
人脸、服装、站位、人数、肢体是否崩坏仍要看检查图；台词内容要人听。
"""
import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent


def probe(video, entries, stream=None):
    cmd = ["ffprobe", "-v", "error"] + (["-select_streams", stream] if stream else []) + \
          ["-show_entries", entries, "-of", "csv=p=0", str(video)]
    return subprocess.run(cmd, capture_output=True, text=True).stdout.strip()


def scene_cuts(showinfo_stderr):
    return [round(float(x), 2) for x in re.findall(r"pts_time:([0-9.]+)", showinfo_stderr)]


def speech_intervals(silencedetect_stderr, duration):
    """把 silencedetect 的静音区间反转成有声区间。"""
    intervals, cur, silent = [], 0.0, False
    for kind, t in re.findall(r"silence_(start|end): ([0-9.]+)", silencedetect_stderr):
        t = float(t)
        if kind == "start":
            if t - cur > 0.05:
                intervals.append((round(cur, 2), round(t, 2)))
            silent = True
        else:
            cur, silent = t, False
    if not silent and duration - cur > 0.05:
        intervals.append((round(cur, 2), round(duration, 2)))
    return intervals


def parse_ocr(stdout, fps):
    """ocr 输出行 → [(秒, 置信度, 文字, 位置)]；帧文件名形如 f_0001.png。"""
    hits = []
    for line in stdout.strip().splitlines():
        parts = line.split("\t")
        m = re.search(r"f_(\d+)", parts[0]) if parts else None
        if len(parts) < 4 or not m:
            continue
        hits.append(((int(m.group(1)) - 1) / fps, float(parts[1]), parts[2], parts[3]))
    return hits


def ocr_binary():
    """首次使用时把 ocr.swift 编译到缓存目录；非 macOS 或没有 swiftc 时返回 None（跳过文字识别）。"""
    src = SCRIPTS / "ocr.swift"
    cache = Path(os.environ.get("XDG_CACHE_HOME", "~/.cache")).expanduser() / "seedance-short-drama"
    exe = cache / "ocr"
    if exe.exists() and exe.stat().st_mtime >= src.stat().st_mtime:
        return exe
    if sys.platform != "darwin" or not shutil.which("swiftc"):
        return None
    cache.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(["swiftc", "-O", str(src), "-o", str(exe)], capture_output=True, text=True)
    return exe if r.returncode == 0 else None


def peak(args):
    r = subprocess.run(["ffmpeg", "-hide_banner"] + args + ["-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True)
    m = re.search(r"max_volume: ([-0-9.]+)", r.stderr)
    return m.group(1) if m else "?"


def review(video, outdir, fps=4, min_conf=0.5):
    name = video.stem
    dur = float(probe(video, "format=duration"))
    wh = probe(video, "stream=width,height", "v:0").replace(",", "×")
    lines = [f"# 审片：{video.name}", "", f"- 时长 {dur:.2f} 秒，分辨率 {wh}"]

    n = int(dur * fps + 0.5)
    cols = 8
    rows = (n + cols - 1) // cols
    sheet = outdir / f"{name}_帧.png"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf",
                    f"fps={fps},scale=180:-1,tile={cols}x{rows}", "-frames:v", "1", str(sheet)], check=True)
    lines.append(f"- 检查图：{sheet.name}（每秒 {fps} 帧，每行 {cols} 帧 = {cols / fps:g} 秒）")

    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-vf", "select='gt(scene,0.25)',showinfo",
                        "-f", "null", "-"], capture_output=True, text=True)
    lines.append(f"- 切镜点（秒）：{scene_cuts(r.stderr) or '无'}")

    exe = ocr_binary()
    if exe is None:
        lines.append("- 画面文字：未检查（需要 macOS 和 swiftc），请看检查图")
    else:
        with tempfile.TemporaryDirectory() as td:
            subprocess.run(["ffmpeg", "-v", "error", "-i", str(video), "-vf", f"fps={fps}", f"{td}/f_%04d.png"], check=True)
            out = subprocess.run([str(exe)] + sorted(str(f) for f in Path(td).glob("f_*.png")),
                                 capture_output=True, text=True).stdout
        hits = [h for h in parse_ocr(out, fps) if h[1] >= min_conf]
        if hits:
            lines.append(f"- ⚠️ 画面里识别到文字 {len(hits)} 处（秒 / 置信度 / 内容 / 位置 x,y,w,h）：")
            lines += [f"  - {t:5.2f}s  {c:.2f}  「{s}」  {box}" for t, c, s, box in hits]
        else:
            lines.append(f"- 画面文字：未识别到（置信度 ≥{min_conf}）；斜体或风格化的英文字可能漏检，仍需看检查图")

    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video), "-af", "silencedetect=n=-32dB:d=0.25",
                        "-f", "null", "-"], capture_output=True, text=True)
    lines.append(f"- 有声区间（秒，-32dB 以上）：{speech_intervals(r.stderr, dur)}")
    lines.append(f"- 开头 0.4 秒峰值 {peak(['-t', '0.4', '-i', str(video)])} dB，结尾 0.4 秒峰值 "
                 f"{peak(['-sseof', '-0.4', '-i', str(video)])} dB（结尾很响时检查台词是否被截断）")
    (outdir / f"{name}_报告.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="自动审片")
    ap.add_argument("videos", nargs="+")
    ap.add_argument("--out", default="5_审片")
    ap.add_argument("--fps", type=int, default=4)
    a = ap.parse_args(argv)
    outdir = Path(a.out)
    outdir.mkdir(parents=True, exist_ok=True)
    for v in a.videos:
        print(review(Path(v).resolve(), outdir, a.fps), end="\n\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
