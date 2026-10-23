#!/usr/bin/env python3
"""Clean-up after a template/background swap: find, and optionally delete, text that collides
with the new series mark or does not belong in the deck. Rules are in
references/post-swap-cleanup.md.

audit: read-only report per deck.
apply: write cleaned copies to --out-dir (never in place).

apply deletes compliance codes only (user rule, 2026-10-23), on slides, layouts and
masters (幻灯编号, 本幻灯仅针对…专业人士, 仅供…专业人士…, PP-XXX-CN-…): only the matching
paragraphs go, and the shape goes only when nothing else is left in it.
Everything else is reported and left in place: footnotes, references, body text and
content on the series mark (--mark), page numbers, text boxes parked outside the
slide, and case-template fill-ins (2026.xx.xx, （文字描述）).
With --png-dir (PNG renders named <stem>-<page>.png) and --background (the bare
content image), audit also measures how much of the mark is actually covered.
"""
from __future__ import annotations

import argparse
import re
import sys
import zipfile
from pathlib import Path

from lxml import etree

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
NS = {"p": P, "a": A, "r": R}
PT = 12700
COMPLIANCE = re.compile(r"幻灯编号|仅针对.{0,12}专业人士|仅供.{0,12}专业人士|PP-[A-Z]{2,4}-[A-Z]{2}-\d")
REFERENCE = re.compile(r"et\.? ?al|等[.．]|[12][09]\d\d[;,，.]\s*\d|doi|https?://|杂志|Lancet|N Engl|指南|共识|"
                       r"^\s*\[?\d{1,2}[\].、]", re.I)
ABBREVIATION = re.compile(r"[A-Za-z][A-Za-z0-9-]{1,}\s*[，,:：]\s*[一-鿿][^；;]*[；;]")
NOTE = re.compile(r"^\s*[*※#]|[√×].{0,6}[:：]")
FILL_IN = re.compile(r"xx|（文字描述）|\(文字描述\)", re.I)


def slide_parts(z):
    pres = etree.fromstring(z.read("ppt/presentation.xml"))
    size = pres.find("p:sldSz", NS)
    rels = {r.get("Id"): r.get("Target") for r in etree.fromstring(z.read("ppt/_rels/presentation.xml.rels"))}
    order = ["ppt/" + rels[e.get(f"{{{R}}}id")] for e in pres.find("p:sldIdLst", NS)]
    return order, int(size.get("cx")), int(size.get("cy"))


def box(el):
    tag = etree.QName(el).localname
    xf = el.find("p:xfrm" if tag == "graphicFrame" else ("p:grpSpPr/a:xfrm" if tag == "grpSp" else "p:spPr/a:xfrm"), NS)
    if xf is None or xf.find("a:off", NS) is None or xf.find("a:ext", NS) is None:
        return None
    o, e = xf.find("a:off", NS), xf.find("a:ext", NS)
    return [int(o.get("x")), int(o.get("y")), int(e.get("cx")), int(e.get("cy"))]


def hits(b, rect):
    return not (b[0] + b[2] <= rect[0] or b[0] >= rect[2] or b[1] + b[3] <= rect[1] or b[1] >= rect[3])


def classify(el, text):
    if el.find(".//p:ph[@type='sldNum']", NS) is not None or re.fullmatch(r"\d{1,3}|<number>|‹#›", text):
        return "page-number"
    if COMPLIANCE.search(text):
        return "compliance"
    if REFERENCE.search(text):
        return "reference"
    if ABBREVIATION.search(text):
        return "abbreviation"
    if NOTE.search(text):
        return "note"
    if FILL_IN.search(text):
        return "fill-in"
    return "body"


def strip_compliance(el):
    """Remove the compliance paragraphs of a shape; True when nothing else is left in it."""
    for p in list(el.iter(f"{{{A}}}p")):
        if COMPLIANCE.search("".join(p.itertext())):
            body = p.getparent()
            if len(body.findall("a:p", NS)) > 1:
                body.remove(p)
            else:
                for r in p.findall("a:r", NS) + p.findall("a:fld", NS) + p.findall("a:br", NS):
                    p.remove(r)
    return not "".join(el.itertext()).strip()


def scan(xml, width, height, mark, mark_page):
    """Yield (action, class, element, text) for one slide; action is delete or report."""
    tree = xml.find("p:cSld/p:spTree", NS)
    animated = {t.get("spid") for t in xml.iter(f"{{{P}}}spTgt")}
    for el in tree.iter(f"{{{P}}}sp"):
        if el.getparent() is not tree and COMPLIANCE.search("".join(el.itertext())):
            yield "strip", "compliance", el, "".join(el.itertext()).strip()
    for el in tree:
        tag = etree.QName(el).localname
        if tag not in ("sp", "pic", "grpSp", "graphicFrame", "cxnSp"):
            continue
        b = box(el)
        text = "".join(el.itertext()).strip()
        nv = el.find(".//p:cNvPr", NS)
        anim = nv is not None and nv.get("id") in animated
        cls = classify(el, text) if tag == "sp" and text else None
        if cls == "compliance":
            yield "strip", "compliance", el, text
            continue
        if b is None:
            continue
        if tag == "sp" and text and (b[0] >= width or b[1] >= height or b[0] + b[2] <= 0 or b[1] + b[3] <= 0):
            yield "report", "off-slide", el, text
            continue
        if mark_page and hits(b, mark):
            filled = any(el.find(f"p:spPr/a:{f}", NS) is not None for f in ("solidFill", "gradFill", "blipFill"))
            if tag == "sp" and not text and not filled:
                continue
            if cls in ("reference", "abbreviation", "note") and not anim:
                yield "report", f"mark:{cls}", el, text
            elif cls != "page-number":
                yield "report", f"mark:{cls or tag}", el, text
        elif tag == "sp" and cls == "fill-in":
            yield "report", "fill-in", el, text


def mark_coverage(png, background, rect_pt, width_pt, height_pt):
    from PIL import Image, ImageChops
    im = Image.open(png).convert("RGB")
    bg = Image.open(background).convert("RGB").resize(im.size)
    sx, sy = im.size[0] / width_pt, im.size[1] / height_pt
    crop = tuple(int(v * s) for v, s in zip(rect_pt, (sx, sy, sx, sy)))
    d = ImageChops.difference(im.crop(crop), bg.crop(crop)).convert("L").point(lambda v: 255 if v > 40 else 0)
    return sum(d.histogram()[255:]) / (d.size[0] * d.size[1])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cmd", choices=["audit", "apply"])
    ap.add_argument("decks", nargs="+", type=Path)
    ap.add_argument("--mark", required=True, help="x1,y1,x2,y2 of the series mark in points (960x540 slide)")
    ap.add_argument("--out-dir", type=Path)
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--png-dir", type=Path)
    ap.add_argument("--background", type=Path)
    args = ap.parse_args(argv)
    if args.cmd == "apply" and not args.out_dir:
        ap.error("apply needs --out-dir")
    mark_pt = [float(v) for v in args.mark.split(",")]
    failed = 0
    for src in args.decks:
        z = zipfile.ZipFile(src)
        order, width, height = slide_parts(z)
        k = width / (960 * PT)
        mark = [int(v * PT * k) for v in mark_pt]
        data = {n: z.read(n) for n in z.namelist()}
        lines, deleted = [], 0
        for part in sorted(n for n in data if re.fullmatch(r"ppt/(slideLayouts/slideLayout|slideMasters/slideMaster)\d+\.xml", n)):
            xml = etree.fromstring(data[part])
            gone = [el for el in xml.iter(f"{{{P}}}sp") if COMPLIANCE.search("".join(el.itertext()))]
            for el in gone:
                lines.append(f"  {part.split('/')[-1]} strip  compliance {''.join(el.itertext()).strip()[:40]!r}")
                if args.cmd == "apply" and strip_compliance(el):
                    el.getparent().remove(el)
                    deleted += 1
            if gone and args.cmd == "apply":
                data[part] = etree.tostring(xml, xml_declaration=True, encoding="UTF-8", standalone=True)
        for i, part in enumerate(order, 1):
            xml = etree.fromstring(data[part])
            found = list(scan(xml, width, height, mark, i not in (1, len(order))))
            for action, cls, el, text in found:
                lines.append(f"  p{i} {action:6} {cls:18} {text[:40]!r}")
                if args.cmd == "apply" and action == "strip" and strip_compliance(el):
                    el.getparent().remove(el)
                    deleted += 1
            if args.cmd == "apply" and any(a == "strip" for a, *_ in found):
                data[part] = etree.tostring(xml, xml_declaration=True, encoding="UTF-8", standalone=True)
            if args.png_dir and args.background and i not in (1, len(order)):
                pngs = sorted(args.png_dir.glob(f"{src.stem}-*{i}.png"))
                pngs = [p for p in pngs if int(p.stem.rsplit("-", 1)[1]) == i]
                if pngs:
                    cov = mark_coverage(pngs[0], args.background, mark_pt, 960, 960 * height / width)
                    if cov > 0.03:
                        lines.append(f"  p{i} covered {cov:.0%} of the mark (render check)")
        print(f"## {src.name}")
        print("\n".join(lines) if lines else "  nothing found")
        if args.cmd == "apply":
            dst = args.out_dir / src.name
            if dst.exists() and not args.overwrite or dst.resolve() == src.resolve():
                print(f"  SKIP {dst} exists or is the source", file=sys.stderr)
                failed += 1
                continue
            args.out_dir.mkdir(parents=True, exist_ok=True)
            tmp = dst.with_name(dst.name + ".tmp")
            with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
                for n in z.namelist():
                    out.writestr(n, data[n])
            tmp.replace(dst)
            for n in data:
                if n.endswith((".xml", ".rels")):
                    etree.fromstring(data[n])
            print(f"  deleted {deleted} text boxes -> {dst}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
