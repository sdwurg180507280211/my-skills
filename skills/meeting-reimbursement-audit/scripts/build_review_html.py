#!/usr/bin/env python3
"""方法二：生成人工复核网页。每场一行列出课前截图、课中截图、海报，由用户在浏览器里看图标注。

只复制图片到输出目录并写一个 HTML，不识别、不判定、不修改原件。
"""
from __future__ import annotations

import argparse
import html
import json
import shutil
import sys
from pathlib import Path

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp", ".heic"}
# 列名 -> 判定规则(相对会议目录的路径包含任一关键字)；按顺序匹配，先命中先归类
SLOTS = [
    ("课前截图", ("课前", "付费服务提供者照片")),
    ("课中截图", ("课中", "会场照片")),
    ("海报", ("海报", "议程")),
]


def classify(rel: str) -> str | None:
    for slot, words in SLOTS:
        if any(word in rel for word in words):
            return slot
    return None


def images_under(folder: Path) -> list[Path]:
    return sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTS
                  and not p.name.startswith((".", "~$")) and "__MACOSX" not in p.parts)


def collect(batch: Path) -> list[dict]:
    meetings = []
    for folder in sorted(p for p in batch.iterdir() if p.is_dir() and p.name != "__MACOSX"):
        files = images_under(folder)
        if not files:
            continue
        slots: dict[str, list[Path]] = {slot: [] for slot, _ in SLOTS}
        other = []
        for f in files:
            slot = classify(str(f.relative_to(folder)))
            (slots[slot] if slot else other).append(f)
        meetings.append({"name": folder.name, "slots": slots, "other": other})
    return meetings


def build(batch: Path, out: Path, key: str) -> dict:
    meetings = collect(batch)
    if not meetings:
        raise SystemExit(f"{batch} 下没有包含图片的会议子目录")
    img_root = out / "images"
    rows, missing = [], []
    for i, m in enumerate(meetings, 1):
        cells = []
        columns = [(slot, m["slots"][slot]) for slot, _ in SLOTS]
        if m["other"]:
            columns.append(("其他图片", m["other"]))
        for slot, files in columns:
            if not files:
                missing.append(f"{m['name']}：缺{slot}")
                cells.append(f"<td><div class=cap>{slot}</div><div class=miss>未找到{slot}</div></td>")
                continue
            imgs = []
            for j, src in enumerate(files):
                rel = Path("images") / m["name"] / f"{slot}{'-' + str(j + 1) if len(files) > 1 else ''}{src.suffix.lower()}"
                (out / rel).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, out / rel)
                imgs.append(f"<img src='{html.escape(rel.as_posix())}' loading=lazy title='{html.escape(src.name)}' onclick='zoom(this.src)'>")
            cells.append(f"<td><div class=cap>{slot}</div>{''.join(imgs)}</td>")
        name = html.escape(m["name"])
        rows.append(f"<tr><th colspan={len(cells)}>{i}. {name}"
                    f"<label class=issue><input type=checkbox data-k='{name}|有问题'>有问题</label>"
                    f"<input class=note data-k='{name}|备注' placeholder='备注'></th></tr><tr>{''.join(cells)}</tr>")
    page = PAGE.replace("__TITLE__", html.escape(out.name)).replace("__KEY__", json.dumps(key + ":", ensure_ascii=False).replace("</", "<\\/")) \
               .replace("__COUNT__", str(len(meetings))).replace("__ROWS__", "".join(rows))
    out.mkdir(parents=True, exist_ok=True)
    (out / "截图复核.html").write_text(page, encoding="utf-8")
    return {"html": str(out / "截图复核.html"), "meetings": len(meetings), "storage_key": key + ":",
            "images": sum(1 for _ in img_root.rglob("*") if _.is_file()), "missing": missing}


PAGE = """<!doctype html><meta charset=utf-8><title>__TITLE__</title>
<style>
body{font-family:-apple-system,"PingFang SC";font-size:13px;margin:12px}
table{border-collapse:collapse;width:100%}td,th{border:1px solid #ccc;padding:6px;vertical-align:top;text-align:left}
th{background:#f3f3f3;font-size:15px;position:sticky;top:0}td{width:33%}
img{width:100%;max-height:520px;object-fit:contain;cursor:zoom-in;background:#fafafa;display:block;margin-bottom:4px}
.cap{margin-bottom:4px}.miss{color:#c00;font-weight:bold}.issue{margin-left:20px;color:#c00;font-weight:normal}
.note{margin-left:12px;width:40%;font-size:13px}
#z{display:none;position:fixed;inset:0;background:rgba(0,0,0,.85);z-index:9;cursor:zoom-out;overflow:auto}
#z img{width:auto;max-width:none;max-height:none;margin:auto;background:none}
#bar{margin-bottom:10px}
</style>
<div id=bar><b>__TITLE__</b>（__COUNT__ 场）：每场的课前截图、课中截图和海报。点击图片可放大看原图，再点一次关闭。
“有问题”和备注自动保存在本浏览器。 <button onclick=exportCsv()>导出有问题场次 CSV</button></div>
<table>__ROWS__</table><div id=z onclick="this.style.display='none'"><img id=zi></div>
<script>
const K=__KEY__;
document.querySelectorAll('[data-k]').forEach(e=>{const v=localStorage.getItem(K+e.dataset.k);
 if(e.type==='checkbox'){e.checked=v==='1';e.onchange=()=>localStorage.setItem(K+e.dataset.k,e.checked?'1':'0')}
 else{e.value=v||'';e.oninput=()=>localStorage.setItem(K+e.dataset.k,e.value)}});
function zoom(s){zi.src=s;z.style.display='block';z.scrollTo(0,0)}
function exportCsv(){const m={};document.querySelectorAll('[data-k]').forEach(e=>{const p=e.dataset.k.split('|');
 const r=m[p[0]]=m[p[0]]||{};r[p[1]]=e.type==='checkbox'?(e.checked?'是':''):e.value});
 let s='\\ufeff会议,有问题,备注\\n';for(const n in m)if(m[n]['有问题']||m[n]['备注'])
 s+=[n,m[n]['有问题']||'',m[n]['备注']||''].map(c=>'"'+c.replace(/"/g,'""')+'"').join(',')+'\\n';
 const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([s],{type:'text/csv'}));a.download='截图复核结果.csv';a.click()}
</script>"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("batch", help="会议批次目录(其下每个子目录是一场会议)；zip 需先解压")
    parser.add_argument("--out", required=True, help="输出目录，会写入 截图复核.html 和 images/")
    parser.add_argument("--key", help="浏览器保存标注用的键前缀，默认取输出目录名；同一批次重新生成时保持不变即可保留已有标注")
    args = parser.parse_args(argv)
    batch, out = Path(args.batch).expanduser().resolve(), Path(args.out).expanduser().resolve()
    if not batch.is_dir():
        parser.error(f"不是目录：{batch}")
    if out == batch or batch in out.parents:
        parser.error("输出目录不能放在会议批次目录里面，避免混入核销资料")
    print(json.dumps(build(batch, out, args.key or out.name), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
