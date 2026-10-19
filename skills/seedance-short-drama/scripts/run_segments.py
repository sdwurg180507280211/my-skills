"""按分段配置批量生成：python3 run_segments.py [--project 目录] [段号 ...] [--model 2.5|mini] [--res 720p]

读取 <项目>/3_提示词/分段.json，例如：
  {"S1": {"时长": 10, "图片": ["角色A", "角色B"], "音频": ["角色A"]}, ...}
每段的提示词在 3_提示词/<段>.txt；"图片" 按顺序对应 @图片1、@图片2…，取 2_素材/角色/<名>_三视图.png；
"音频" 按顺序对应 @音频1…，取 2_素材/声音/<名>.wav。不带段号就跑全部。
每次运行给每段新增一条候选：4_生成片段/<段>_t<序号>_<模型>_<分辨率>.mp4，日志在 日志/。
个人账户最多同时 3 个任务，所以默认 3 个并发，提交之间错开 3 秒。
"""
import argparse
import json
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
# 元/百万 token（2026-10 官方价格页；2.5 的 1080p 是 77）
MODELS = {"2.5": ("doubao-seedance-2-5-260628", {"480p": 70, "720p": 70, "1080p": 77}),
          "mini": ("doubao-seedance-2-0-mini-260615", {"480p": 23, "720p": 23}),
          "2.0": ("doubao-seedance-2-0-260128", {"480p": 46, "720p": 46, "1080p": 51})}


def next_take(out_dir, log_dir, seg):
    n = 1
    while list(Path(out_dir).glob(f"{seg}_t{n}_*")) or (Path(log_dir) / f"{seg}_t{n}.running").exists():
        n += 1
    return n


def build_command(project, seg, cfg, model_id, res, out):
    project = Path(project)
    cmd = [sys.executable, str(SCRIPTS / "ark_video.py"), "--model", model_id,
           "--prompt-file", str(project / "3_提示词" / f"{seg}.txt"), "--ratio", cfg.get("比例", "9:16"),
           "--duration", str(cfg["时长"]), "--resolution", res, "--audio", "--out", str(out)]
    for name in cfg.get("图片", []):
        cmd += ["--ref", str(project / "2_素材" / "角色" / f"{name}_三视图.png")]
    for name in cfg.get("音频", []):
        cmd += ["--ref-audio", str(project / "2_素材" / "声音" / f"{name}.wav")]
    return cmd


def missing_inputs(cmd):
    """提交前检查本地素材是否都在，避免缺图时白跑一轮。"""
    paths = [cmd[i + 1] for i, a in enumerate(cmd) if a in ("--prompt-file", "--ref", "--ref-audio")]
    return [p for p in paths if not p.startswith(("http://", "https://", "asset://")) and not Path(p).exists()]


def cost(tokens, unit_price):
    return tokens * unit_price / 1e6


def main(argv=None):
    ap = argparse.ArgumentParser(description="按分段配置批量生成 Seedance 视频")
    ap.add_argument("segments", nargs="*")
    ap.add_argument("--project", default=".")
    ap.add_argument("--model", default="2.5", choices=MODELS)
    ap.add_argument("--res", default="720p")
    ap.add_argument("--workers", type=int, default=3)
    a = ap.parse_args(argv)
    project = Path(a.project).resolve()
    conf = json.loads((project / "3_提示词" / "分段.json").read_text(encoding="utf-8"))
    segs = a.segments or list(conf)
    unknown = [s for s in segs if s not in conf]
    if unknown:
        ap.error(f"分段.json 里没有：{unknown}")
    model_id, price = MODELS[a.model]
    out_dir, log_dir = project / "4_生成片段", project / "日志"
    out_dir.mkdir(exist_ok=True)
    log_dir.mkdir(exist_ok=True)
    lock, starts = threading.Lock(), []

    def run(seg):
        with lock:
            n = next_take(out_dir, log_dir, seg)
            running = log_dir / f"{seg}_t{n}.running"
            running.touch()
            if starts:
                time.sleep(max(0, 3 - (time.time() - starts[-1])))
            starts.append(time.time())
        out = out_dir / f"{seg}_t{n}_{a.model}_{a.res}.mp4"
        cmd = build_command(project, seg, conf[seg], model_id, a.res, out)
        miss = missing_inputs(cmd)
        if miss:
            running.unlink(missing_ok=True)
            print(f"{seg} t{n}: 跳过，缺少素材 {miss}", flush=True)
            return 0.0
        log = log_dir / f"{seg}_t{n}.log"
        with open(log, "w") as f:
            rc = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT).returncode
        running.unlink(missing_ok=True)
        lines = log.read_text().strip().splitlines()
        last = lines[-1] if lines else ""
        spent = cost(json.loads(last)["usage"]["completion_tokens"], price[a.res]) if rc == 0 else 0.0
        print(f"{seg} t{n}: {'成功' if rc == 0 else '失败'}  ¥{spent:.2f}  {last[:200]}", flush=True)
        return spent

    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        total = sum(ex.map(run, segs))
    print(f"本次合计约 ¥{total:.2f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
