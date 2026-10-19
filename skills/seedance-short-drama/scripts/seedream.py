"""Seedream 文生图（用于有人脸的角色图）：python3 seedream.py 输出.png 提示词.txt [--size 2048x1152]

Seedance API 拒绝含真人人脸的参考图，写实风格的 AI 人像也会被拦；本账号用 Seedream 文生图生成、
未经任何改动的原图属于受信产物，可以作为参考图。所以原图按原样保存，不裁剪、不压缩、不转格式；
原始网址另存到 <输出>.url.txt（24 小时有效）。
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ark_common  # noqa: E402

DEFAULT_MODEL = "doubao-seedream-5-0-pro-260628"


def main(argv=None):
    ap = argparse.ArgumentParser(description="Seedream 文生图")
    ap.add_argument("out")
    ap.add_argument("prompt_file")
    ap.add_argument("--size", default="1080x1920", help="三视图用 2048x1152，竖版单人像用 1080x1920")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    a = ap.parse_args(argv)
    body = {"model": a.model, "prompt": Path(a.prompt_file).read_text(encoding="utf-8").strip(),
            "size": a.size, "response_format": "url", "watermark": False}
    try:
        d = ark_common.request("POST", "/images/generations", body)
        url = d["data"][0]["url"]
        ark_common.download(url, a.out)
    except ark_common.ArkError as e:
        print(e, file=sys.stderr)
        return 1
    Path(a.out + ".url.txt").write_text(url)
    print(json.dumps({"out": a.out, "size": d["data"][0].get("size"), "usage": d.get("usage")}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
