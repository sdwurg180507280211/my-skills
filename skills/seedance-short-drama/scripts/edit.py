"""按剪辑表拼成片：python3 edit.py [--project 目录] [剪辑表.json]（默认 <项目>/6_成片/剪辑表.json）

剪辑表里的路径相对项目目录。字段（时间单位秒，坐标单位像素，基于"画布"）：
{
  "输出": "6_成片/成片_v1.mp4",
  "画布": [720, 1280], "帧率": 24,                  可省略，默认 720×1280、24fps
  "段落": [
    {"段": "S1", "文件": "4_生成片段/S1_t1_2.5_720p.mp4",
     "入点": 0, "出点": null,                        可省略；null 表示到结尾
     "响度": -16,                                    该段目标响度 LUFS；纯环境声的段设 -19~-22
     "推近": [{"起": 2.9, "止": 4.7, "裁切": [x, y, w, h]}],   这段时间裁切后放大回全画面（裁掉字幕或假字）
     "打码": [{"起": 0, "止": 2, "区域": [x, y, w, h]}],       区域模糊；硬边方块很显眼，优先用推近
     "画面替换": {"文件": "...", "起": 2.6, "止": 5.3, "源入点": 1.25},   只换这段画面，声音保留原片
     "定格": 1.0, "淡出": 0.8}                      结尾停留后淡出到黑
  ],
  "片尾卡": {"图片": "2_素材/片尾/片尾卡.png", "时长": 4.5, "淡入": 0.5, "淡出": 0.5},
  "段间音频淡化": 0.08
}
"""
import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ENC = ["-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "160k", "-ar", "48000", "-ac", "2"]


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True).stdout
    return float(out)


def ffmpeg(args):
    r = subprocess.run(["ffmpeg", "-v", "error", "-y"] + args, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError("ffmpeg 失败：" + r.stderr[-1500:])


def segment_graph(seg, length, canvas=(720, 1280), fps=24, fade_a=0.08):
    """返回 (filter_complex, 输出时长)。输入 0 是本段视频；有画面替换时输入 1 是替换素材。"""
    W, H = canvas
    norm = f"scale={W}:{H}:force_original_aspect_ratio=decrease,pad={W}:{H}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps}"
    a0 = float(seg.get("入点") or 0)
    a1 = a0 + length
    fc = [f"[0:v]trim={a0}:{a1},setpts=PTS-STARTPTS,{norm}[v0]"]
    cur = "v0"
    rep = seg.get("画面替换")
    if rep:
        s, e, src = rep["起"], rep["止"], rep.get("源入点", 0)
        fc.append(f"[{cur}]split=2[ra][rc];[ra]trim=0:{s},setpts=PTS-STARTPTS[r0];"
                  f"[1:v]trim={src}:{round(src + e - s, 3)},setpts=PTS-STARTPTS,{norm}[r1];"
                  f"[rc]trim={e}:{length},setpts=PTS-STARTPTS[r2];[r0][r1][r2]concat=n=3:v=1:a=0[vr]")
        cur = "vr"
    zooms = sorted(seg.get("推近", []), key=lambda z: z["起"])
    if zooms:
        pieces, t = [], 0.0
        for z in zooms:
            if z["起"] > t:
                pieces.append((t, z["起"], None))
            pieces.append((z["起"], z["止"], z["裁切"]))
            t = z["止"]
        if t < length:
            pieces.append((t, length, None))
        fc.append(f"[{cur}]split={len(pieces)}" + "".join(f"[p{i}]" for i in range(len(pieces))))
        for i, (s, e, box) in enumerate(pieces):
            f = f"[p{i}]trim={s}:{e},setpts=PTS-STARTPTS"
            if box:
                x, y, w, h = box
                # 裁切比例和画布不完全一致时，缩放会改变像素宽高比，拼接时报错，所以补 setsar=1
                f += f",crop={w}:{h}:{x}:{y},scale={W}:{H},setsar=1"
            fc.append(f + f"[q{i}]")
        fc.append("".join(f"[q{i}]" for i in range(len(pieces))) + f"concat=n={len(pieces)}:v=1:a=0[vz]")
        cur = "vz"
    for i, m in enumerate(seg.get("打码", [])):
        x, y, w, h = m["区域"]
        fc.append(f"[{cur}]split[b{i}a][b{i}b];[b{i}b]crop={w}:{h}:{x}:{y},boxblur=18:2[b{i}c];"
                  f"[b{i}a][b{i}c]overlay={x}:{y}:enable='between(t,{m['起']},{m['止']})'[vb{i}]")
        cur = f"vb{i}"
    hold, fo = float(seg.get("定格", 0)), float(seg.get("淡出", 0))
    total = length + hold
    tail = f"tpad=stop_mode=clone:stop_duration={hold}," if hold else ""
    tail += f"fade=t=out:st={total - fo:.3f}:d={fo}," if fo else ""
    fc.append(f"[{cur}]{tail}format=yuv420p[vout]")
    a_tail = f"apad=pad_dur={hold}," if hold else ""
    a_out = f"afade=t=out:st={total - fo:.3f}:d={fo}" if fo else f"afade=t=out:st={total - fade_a:.3f}:d={fade_a}"
    fc.append(f"[0:a]atrim={a0}:{a1},asetpts=PTS-STARTPTS,loudnorm=I={seg.get('响度', -16)}:TP=-1.5:LRA=11,"
              f"aresample=48000,afade=t=in:st=0:d={fade_a},{a_tail}{a_out}[aout]")
    return ";".join(fc), total


def render_segment(project, seg, out, canvas, fps, fade_a):
    src = project / seg["文件"]
    a0 = float(seg.get("入点") or 0)
    a1 = float(seg["出点"]) if seg.get("出点") is not None else duration(src)
    graph, total = segment_graph(seg, a1 - a0, canvas, fps, fade_a)
    inputs = ["-i", str(src)]
    if seg.get("画面替换"):
        inputs += ["-i", str(project / seg["画面替换"]["文件"])]
    ffmpeg(inputs + ["-filter_complex", graph, "-map", "[vout]", "-map", "[aout]", "-t", f"{total:.3f}",
                     "-r", str(fps)] + ENC + [str(out)])
    return total


def render_card(project, card, out, canvas, fps):
    W, H = canvas
    d, fi, fo = card["时长"], card.get("淡入", 0.5), card.get("淡出", 0.5)
    ffmpeg(["-loop", "1", "-t", str(d), "-i", str(project / card["图片"]), "-f", "lavfi", "-t", str(d),
            "-i", "anullsrc=r=48000:cl=stereo", "-vf",
            f"scale={W}:{H},setsar=1,fps={fps},fade=t=in:st=0:d={fi},fade=t=out:st={d - fo}:d={fo},format=yuv420p",
            "-shortest", "-r", str(fps)] + ENC + [str(out)])
    return d


def main(argv=None):
    ap = argparse.ArgumentParser(description="按剪辑表拼成片")
    ap.add_argument("edl", nargs="?")
    ap.add_argument("--project", default=".")
    a = ap.parse_args(argv)
    project = Path(a.project).resolve()
    edl_path = Path(a.edl) if a.edl else project / "6_成片" / "剪辑表.json"
    edl = json.loads(edl_path.read_text(encoding="utf-8"))
    canvas, fps = tuple(edl.get("画布", (720, 1280))), edl.get("帧率", 24)
    fade_a = edl.get("段间音频淡化", 0.08)
    rows, t = [], 0.0
    try:
        with tempfile.TemporaryDirectory() as td:
            parts = []
            for i, seg in enumerate(edl["段落"]):
                p = Path(td) / f"{i:02d}.mp4"
                d = render_segment(project, seg, p, canvas, fps, fade_a)
                parts.append(p)
                rows.append(f"{seg.get('段', i):>4}  {t:6.2f} → {t + d:6.2f}  ({d:.2f}s)  {seg['文件']}")
                t += d
            if edl.get("片尾卡"):
                p = Path(td) / "card.mp4"
                d = render_card(project, edl["片尾卡"], p, canvas, fps)
                parts.append(p)
                rows.append(f"片尾卡  {t:6.2f} → {t + d:6.2f}  ({d:.2f}s)")
                t += d
            lst = Path(td) / "list.txt"
            lst.write_text("".join(f"file '{p}'\n" for p in parts))
            out = project / edl["输出"]
            out.parent.mkdir(parents=True, exist_ok=True)
            ffmpeg(["-f", "concat", "-safe", "0", "-i", str(lst), "-r", str(fps)] + ENC + [str(out)])
    except RuntimeError as e:
        print(e, file=sys.stderr)
        return 1
    print("\n".join(rows))
    print(f"输出：{edl['输出']}  总长 {duration(out):.2f} 秒")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
