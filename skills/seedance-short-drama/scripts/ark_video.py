"""火山方舟 Seedance 视频生成：提交 → 轮询 → 下载。

  python3 ark_video.py --model doubao-seedance-2-5-260628 --prompt-file S1.txt \\
      --ref 角色A_三视图.png --ref-audio 角色A.wav --ratio 9:16 --duration 8 --resolution 720p --audio --out S1.mp4
  python3 ark_video.py --resume <任务ID> --out S1.mp4   只取结果，不重新提交
  python3 ark_video.py --list                          最近的任务（提交中断后先查这里，避免重复扣费）

本地图片和音频按原始字节内联为 base64，不转码：Seedream 生成的角色图要保持原样才算受信产物。
网址和 asset:// 原样传入。
"""
import argparse
import base64
import json
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ark_common  # noqa: E402

MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp",
        ".wav": "audio/wav", ".mp3": "audio/mpeg"}


def media_url(path):
    s = str(path)
    if s.startswith(("http://", "https://", "asset://")):
        return s
    p = Path(path)
    mime = MIME.get(p.suffix.lower())
    if not mime:
        raise ValueError(f"不支持的素材格式：{p.name}（可用 {', '.join(MIME)}）")
    return f"data:{mime};base64," + base64.b64encode(p.read_bytes()).decode()


def build_body(model, prompt, refs=(), ref_audios=(), first_frame=None, last_frame=None,
               ratio="9:16", duration=5, resolution="720p", audio=True, seed=None):
    content = [{"type": "text", "text": prompt}]
    for role, p in (("first_frame", first_frame), ("last_frame", last_frame)):
        if p:
            content.append({"type": "image_url", "image_url": {"url": media_url(p)}, "role": role})
    for p in refs:
        content.append({"type": "image_url", "image_url": {"url": media_url(p)}, "role": "reference_image"})
    for p in ref_audios:
        content.append({"type": "audio_url", "audio_url": {"url": media_url(p)}, "role": "reference_audio"})
    body = {"model": model, "content": content, "ratio": ratio, "duration": duration,
            "resolution": resolution, "generate_audio": audio, "watermark": False}
    if seed is not None:
        body["seed"] = seed
    return body


def wait_and_download(tid, out, timeout=900):
    t0 = time.time()
    while True:
        r = ark_common.request("GET", f"/contents/generations/tasks/{tid}")
        st = r.get("status")
        if st == "succeeded":
            break
        if st in ("failed", "cancelled", "expired"):
            raise ark_common.ArkError(f"任务 {tid} {st}：{json.dumps(r.get('error'), ensure_ascii=False)}")
        if time.time() - t0 > timeout:
            raise ark_common.ArkError(f"等待超时，任务 {tid} 仍是 {st}；稍后用 --resume {tid} 取结果")
        time.sleep(10)
    try:
        ark_common.download(r["content"]["video_url"], out)
    except Exception as e:
        raise ark_common.ArkError(f"任务 {tid} 已生成但下载失败（{e}）；视频地址 24 小时内有效，用 --resume {tid} 重试") from None
    return {"out": str(out), "task": tid, "secs": round(time.time() - t0), "usage": r.get("usage"),
            "ratio": r.get("ratio"), "resolution": r.get("resolution"), "duration": r.get("duration"),
            "seed": r.get("seed")}


def list_recent(n=10):
    d = ark_common.request("GET", f"/contents/generations/tasks?page_num=1&page_size={n}")
    for t in d.get("items", []):
        when = datetime.fromtimestamp(t["created_at"]).strftime("%m-%d %H:%M:%S")
        print(t["id"], t["status"], t.get("model"), f"{t.get('duration')}s", t.get("resolution"), when)


def main(argv=None):
    ap = argparse.ArgumentParser(description="火山方舟 Seedance 视频生成")
    ap.add_argument("--list", action="store_true", help="列出最近的任务")
    ap.add_argument("--resume", help="已提交的任务 ID：只轮询并下载")
    ap.add_argument("--model")
    ap.add_argument("--prompt")
    ap.add_argument("--prompt-file")
    ap.add_argument("--first-frame")
    ap.add_argument("--last-frame")
    ap.add_argument("--ref", action="append", default=[], help="参考图，可多次传入，按顺序对应 @图片1、@图片2…")
    ap.add_argument("--ref-audio", action="append", default=[], help="参考音频（wav/mp3，单段 2~30 秒，总长 ≤30 秒）")
    ap.add_argument("--ratio", default="9:16")
    ap.add_argument("--duration", type=int, default=5)
    ap.add_argument("--resolution", default="720p")
    ap.add_argument("--audio", action="store_true", help="生成有声视频")
    ap.add_argument("--seed", type=int)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    try:
        if a.list:
            list_recent()
            return 0
        if not a.out:
            ap.error("缺少 --out")
        if a.resume:
            print(json.dumps(wait_and_download(a.resume, a.out), ensure_ascii=False))
            return 0
        if not a.model or not (a.prompt or a.prompt_file):
            ap.error("提交新任务需要 --model 和 --prompt/--prompt-file")
        prompt = a.prompt or Path(a.prompt_file).read_text(encoding="utf-8").strip()
        body = build_body(a.model, prompt, a.ref, a.ref_audio, a.first_frame, a.last_frame,
                          a.ratio, a.duration, a.resolution, a.audio, a.seed)
        try:
            task = ark_common.request("POST", "/contents/generations/tasks", body)
        except ark_common.ArkError:
            raise
        except Exception as e:
            raise ark_common.ArkError(
                f"提交时网络中断（{type(e).__name__}）。任务可能已建成：先运行 --list 查看，"
                "已建成的用 --resume 取结果，没有再重新提交。") from None
        print("task", task["id"], flush=True)
        print(json.dumps(wait_and_download(task["id"], a.out), ensure_ascii=False))
        return 0
    except ark_common.ArkError as e:
        print(e, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
