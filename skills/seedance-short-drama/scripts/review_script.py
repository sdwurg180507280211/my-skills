"""剧本审稿：把剧本交给 DeepSeek，分两路挑刺，直到两路都"必须改：无"再进入素材和生成。

  python3 review_script.py 剧本.md                      两路一起审，结果写到 剧本同目录/审稿_<时间>.md
  python3 review_script.py 剧本.md --route A            只审一路（A 专业事实与真实性，B 台词表演与可拍性）
  python3 review_script.py 剧本.md --prev 上一轮.md      复查：附上上一轮意见，让它先核对落实情况
  python3 review_script.py 剧本.md --context "给真实医生做个人 IP 的样片，第一要求是真实"

密钥读环境变量 DEEPSEEK_API_KEY，或 ~/.config/deepseek/api-key；不打印、不写进输出。
DeepSeek 在国内，固定直连，不走会话里的代理。
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

API = "https://api.deepseek.com/chat/completions"
DEFAULT_MODEL = "deepseek-flash"  # 即 DeepSeek-V4.1-Flash-1017；写 deepseek-v4.1-flash 会被拒
DEFAULT_EFFORT = "max"

ROUTES = {
    "A": ("专业事实与真实性",
          "1. 专业事实和表述：台词和'事实核对'里的专业内容有没有硬错误、会不会误导观众，"
          "有没有把有条件的建议写成绝对的说法。只看内容对不对，不追批文号、注册证号、广告法、超说明书这类合规问题。\n"
          "2. 场景真实性：流程、称呼、人物行为在现实里会不会这样发生，有没有不合规、或让业内人士一看就觉得假的地方；"
          "还缺什么最能体现真实的细节（只提一两个最值得加的）。"),
    "B": ("台词表演与可拍性",
          "1. 台词和表演：像不像真人说话，有没有书面腔、表演腔、抖包袱；同一个信息有没有说两遍；"
          "每句台词有没有说给谁听的人；主角的人设是加分还是减分。\n"
          "2. 时长：逐段逐镜核对台词字数和秒数（按每秒 4～5 个字，动作和接话也要占时间）。"
          "不要自己推断'模型容易拍坏'的画面限制（人数、道具、构图、文字等），除非剧本或上下文里给了实测依据。"),
}

SYSTEM = (
    "你是挑刺的剧本审稿人。剧本之后会用 Seedance 2.x 逐段生成写实视频：每段一次生成（2.5 单段最长 30 秒），"
    "参考图锁人脸，模型自带对白和口型。只审用户指定的两个方面，不讨论版权、合规（批文、注册证号、广告法、超说明书）、平台规则等话题，这些不算必须改。"
    "只把真正会拍坏、明显假或事实错误的问题列进必须改，措辞偏好放进可以更好。中文，简洁。"
)

FORMAT = ("输出格式：\n## 必须改\n（编号；每条写清在哪一段、问题是什么、建议怎么改；没有就写'无'）\n"
          "## 可以更好\n## 不用改\n（一句话）")


def load_key():
    key = os.environ.get("DEEPSEEK_API_KEY", "").strip()
    if key:
        return key
    path = Path.home() / ".config" / "deepseek" / "api-key"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    raise SystemExit("缺少 DeepSeek 密钥：设置 DEEPSEEK_API_KEY，或存到 ~/.config/deepseek/api-key（权限 600）")


def build_messages(script, route, context="", prev="", today=None):
    name, aspects = ROUTES[route]
    parts = [f"今天是 {today or time.strftime('%Y-%m-%d')}，剧本里早于今天的报道和研究都已经发表，不要按你自己的时间判断它们还没发生。"]
    if context:
        parts.append("背景：" + context)
    parts.append(f"这一路（{route}：{name}）只看下面两个方面：\n{aspects}")
    if prev:
        parts.append("这是复查。下面是你上一轮的意见，先逐条核对是否落实（没采纳的看理由是否成立），"
                     "再看改稿有没有带进新问题。输出最后加一节 ## 上次必须改的落实情况。\n\n<上一轮意见>\n" + prev + "\n</上一轮意见>")
    parts.append(FORMAT)
    parts.append("<剧本>\n" + script + "\n</剧本>")
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": "\n\n".join(parts)}]


def build_body(script, route, model=DEFAULT_MODEL, effort=DEFAULT_EFFORT, context="", prev=""):
    return {"model": model, "messages": build_messages(script, route, context, prev),
            "reasoning_effort": effort, "stream": False}


def call(body, key, timeout=900):
    """直连 DeepSeek；网络错误重试一次，HTTP 错误直接报出。"""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    for attempt in range(2):
        req = urllib.request.Request(API, data=data, headers={
            "Authorization": "Bearer " + key, "Content-Type": "application/json"})
        try:
            with opener.open(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            raise SystemExit(f"DeepSeek 返回 HTTP {e.code}：{e.read().decode('utf-8', 'replace')[:300]}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt:
                raise SystemExit(f"连不上 DeepSeek：{e}")
            time.sleep(3)


def must_fix_clear(content):
    """"## 必须改"一节写的是"无"就返回 True，有条目返回 False，找不到这一节返回 None。"""
    m = re.search(r"^#+\s*必须改[^\n]*\n(.*?)(?=^#+\s|\Z)", content, re.S | re.M)
    if not m:
        return None
    body = m.group(1).strip().lstrip("*").strip()
    return body.startswith("无")


def render(results):
    """results: [(route, 回复 JSON)] → 一份 Markdown，末尾记用量。"""
    out = []
    for route, d in results:
        msg = d["choices"][0]["message"]
        usage = d.get("usage", {})
        out.append(f"# {route} 路：{ROUTES[route][0]}\n\n{(msg.get('content') or '').strip()}\n\n"
                   f"<sub>模型 {d.get('model')}，输入 {usage.get('prompt_tokens')} tokens，输出 {usage.get('completion_tokens')} tokens</sub>\n")
    return "\n".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="用 DeepSeek 分两路审剧本")
    ap.add_argument("script")
    ap.add_argument("--route", choices=["A", "B", "AB"], default="AB")
    ap.add_argument("--context", default="", help="一两句背景：用途、第一要求、给谁看")
    ap.add_argument("--prev", help="上一轮的审稿结果文件（复查时用）")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument("--effort", default=DEFAULT_EFFORT)
    ap.add_argument("--out")
    a = ap.parse_args(argv)
    script_path = Path(a.script)
    script = script_path.read_text(encoding="utf-8")
    prev = Path(a.prev).read_text(encoding="utf-8") if a.prev else ""
    key = load_key()
    routes = list(a.route) if a.route != "AB" else ["A", "B"]
    with ThreadPoolExecutor(len(routes)) as ex:
        futures = {r: ex.submit(call, build_body(script, r, a.model, a.effort, a.context, prev), key) for r in routes}
        results = [(r, futures[r].result()) for r in routes]
    out = Path(a.out) if a.out else script_path.with_name(f"审稿_{time.strftime('%Y%m%d_%H%M')}.md")
    out.write_text(render(results), encoding="utf-8")
    verdict = {}
    for r, d in results:
        clear = must_fix_clear(d["choices"][0]["message"].get("content") or "")
        verdict[r] = {True: "必须改：无", False: "有必须改", None: "没找到必须改一节，看原文"}[clear]
    print(json.dumps({"out": str(out), "结论": verdict}, ensure_ascii=False))


if __name__ == "__main__":
    main()
