#!/usr/bin/env python3
"""Apply a series template (cover / title / content / end images) to whole decks.

Builds on replace_backgrounds.py. For every deck:
  slide 1 = --cover, slide 2 and the last slide = --title (or --end), every other
  slide inherits the masters, which get --content. Full-slide pictures on masters and
  layouts are removed, as in replace_backgrounds.py.

Options for decks from another template family:
  --restyle N,...   decks (file-name number prefix or full name) that have no picture-only
                    cover: remove on-slide, text-free, non-placeholder decorations from
                    masters/layouts, remove copies of those decorations pasted onto slides
                    (matched across all --restyle decks), remove full-slide pictures on the
                    old slide 1, and insert a new empty slide 1 for the cover image.
  --logo-box x1,y1,x2,y2   points; on --restyle decks, text boxes running into this box
                    (the new background's logo) move right to --title-left, keeping their
                    right edge.
  --end-text "感谢聆听|THANKS"   replace the last slide's shapes with centred lines; if
                    the last slide is not a thanks page, append one.
  --end-clear       the end image already carries the thank-you words: empty the last slide
                    when it is a thanks page.
  --cover-title-box x,y,w   points on a 960pt-wide slide; move the cover's title text boxes
                    (as one block, left-aligned) to x,y and keep them within width w.
  --title-color HEX colour only: cover title, title placeholders and the master title style;
                    on slides without a title placeholder, the topmost non-white text box in
                    the top-left band.
Without --title, slide 2 is an ordinary content slide.

Writes to --out-dir only; the report and a copy of every removed image go to --report-dir.
To redo a single deck, pass only that deck plus --overwrite.
"""
from __future__ import annotations

import argparse
import json
import posixpath
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import replace_backgrounds as rb  # noqa: E402
from lxml import etree  # noqa: E402

P, A, R, NS = rb.P, rb.A, rb.R, rb.NS
PT = 12700
EP = "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties"
SLIDE_CT = "application/vnd.openxmlformats-officedocument.presentationml.slide+xml"
THANKS_WORDS = ("感谢", "您的", "聆听", "谢谢", "观看", "thankyou", "thanks")
SHAPES = ("sp", "pic", "grpSp", "cxnSp", "graphicFrame")


def xfrm_of(el):
    xfrm = el.find("p:grpSpPr/a:xfrm" if etree.QName(el).localname == "grpSp" else "p:spPr/a:xfrm", NS)
    if xfrm is None or xfrm.find("a:off", NS) is None or xfrm.find("a:ext", NS) is None:
        return None
    return xfrm


def box_of(xfrm):
    off, ext = xfrm.find("a:off", NS), xfrm.find("a:ext", NS)
    return int(off.get("x")), int(off.get("y")), int(ext.get("cx")), int(ext.get("cy"))


def signature(pkg, part, el):
    """(kind, box in pt, media md5s, preset geometry) used to recognise copies of a decoration."""
    xfrm = xfrm_of(el)
    targets = pkg.targets(part)
    media = tuple(sorted(rb.md5(pkg.data[t]) for b in el.iter(f"{{{A}}}blip")
                         for t in [targets.get(b.get(f"{{{R}}}embed"), (None, None))[1]] if t in pkg.data))
    geom = el.find(".//a:prstGeom", NS)
    return (etree.QName(el).localname, tuple(v // PT for v in box_of(xfrm)) if xfrm is not None else None,
            media, geom.get("prst") if geom is not None else None)


def same_shape(a, b, tol=2):
    if a[0] == "sp" and a[1] and a[1][2] >= 900 and a[1][3] <= 4 and 60 <= a[1][1] <= 90:
        return True  # header rule under the title; copies differ in rect/roundRect and by 1pt
    return (a[0], a[3]) == (b[0], b[3]) and a[1] and b[1] and all(abs(x - y) <= tol for x, y in zip(a[1], b[1]))


def strip_decorations(pkg, deck, part):
    """Remove on-slide, text-free, non-placeholder shapes and pictures from a master or layout."""
    removed = []
    tree = pkg.xml(part).find("p:cSld/p:spTree", NS)
    targets = pkg.targets(part)
    for el in list(tree):
        if etree.QName(el).localname not in ("pic", "sp", "grpSp", "cxnSp"):
            continue
        if el.find(".//p:nvPr/p:ph", NS) is not None or "".join(el.itertext()).strip():
            continue
        xfrm = xfrm_of(el)
        if xfrm is None:
            continue
        x, y, cx, cy = box_of(xfrm)
        if x + cx <= 0 or y + cy <= 0 or x >= deck.width or y >= deck.height:
            continue  # off-slide swatches are invisible
        media = [targets.get(b.get(f"{{{R}}}embed"), (None, None))[1] for b in el.iter(f"{{{A}}}blip")]
        sig = signature(pkg, part, el)
        tree.remove(el)
        removed.append({"part": part, "kind": sig[0], "box_pt": list(sig[1]), "media": media, "sig": sig})
    return removed


def decoration_pool(paths):
    """Signatures of the decorations on the masters/layouts of all given decks."""
    media_set, shape_sigs = set(), set()
    for path in paths:
        pkg = rb.Package(path)
        deck = rb.Deck(pkg)
        for part in deck.masters + deck.layouts:
            for item in strip_decorations(pkg, deck, part):
                media_set |= set(item["sig"][2])
                if not item["sig"][2]:
                    shape_sigs.add(item["sig"])
    return media_set, shape_sigs


def strip_slide_copies(pkg, part, media_set, shape_sigs):
    removed = []
    tree = pkg.xml(part).find("p:cSld/p:spTree", NS)
    for el in list(tree):
        if etree.QName(el).localname not in ("pic", "sp", "grpSp", "cxnSp"):
            continue
        if el.find(".//p:nvPr/p:ph", NS) is not None or "".join(el.itertext()).strip():
            continue
        sig = signature(pkg, part, el)
        if (sig[2] and set(sig[2]) <= media_set) or (not sig[2] and any(same_shape(sig, s) for s in shape_sigs)):
            tree.remove(el)
            removed.append({"part": part, "kind": sig[0], "box_pt": list(sig[1] or []), "media": []})
    return removed


def shift_titles(pkg, part, logo, left):
    """Move text boxes that run into the logo box right to `left`, keeping their right edge."""
    moved = []
    for el in pkg.xml(part).find("p:cSld/p:spTree", NS):
        if etree.QName(el).localname not in ("sp", "grpSp"):
            continue
        if not "".join(el.itertext()).strip() and el.find(".//p:nvPr/p:ph", NS) is None:
            continue
        xfrm = xfrm_of(el)
        if xfrm is None:
            continue
        x, y, cx, cy = box_of(xfrm)
        if x >= logo[2] or y >= logo[3] or x + cx <= logo[0] or y + cy <= logo[1] or x >= left:
            continue
        xfrm.find("a:off", NS).set("x", str(left))
        if etree.QName(el).localname == "sp" and cx - (left - x) > 200 * PT:
            xfrm.find("a:ext", NS).set("cx", str(cx - (left - x)))
        moved.append({"part": part, "from_pt": [x // PT, y // PT, cx // PT, cy // PT]})
    return moved


def is_thanks(pkg, part):
    t = "".join(ch for ch in "".join(pkg.xml(part).find("p:cSld", NS).itertext()).lower() if ch.isalnum())
    shapes = [etree.QName(el).localname for el in pkg.xml(part).find("p:cSld/p:spTree", NS)
              if etree.QName(el).localname in SHAPES]
    if not t and shapes == ["pic"]:
        return True  # some templates draw 感谢聆听 THANKS as one picture
    hit = any(w in t for w in THANKS_WORDS)
    for w in THANKS_WORDS:
        t = t.replace(w, "")
    return hit and not t


def end_page_text(pkg, part, lines, width, height):
    """Replace a slide's shapes with centred black 54pt lines, as on the template's end page."""
    tree = pkg.xml(part).find("p:cSld/p:spTree", NS)
    for el in list(tree):
        if etree.QName(el).localname in SHAPES:
            tree.remove(el)
    ids = [int(e.get("id")) for e in pkg.xml(part).iter(f"{{{P}}}cNvPr") if e.get("id", "").isdigit()]
    run = ('<a:r><a:rPr lang="zh-CN" altLang="en-US" sz="5400" dirty="0"><a:solidFill><a:srgbClr val="000000"/>'
           '</a:solidFill><a:latin typeface="Microsoft YaHei"/><a:ea typeface="Microsoft YaHei"/></a:rPr>'
           '<a:t>{}</a:t></a:r>')
    paras = "".join(f'<a:p><a:pPr algn="ctr"/>{run.format(line)}</a:p>' for line in lines)
    x, w = int(width * 0.097), int(width * 0.806)
    h = 70 * PT * len(lines)
    y = int(height * 0.41) - h // 2
    tree.append(etree.fromstring(
        f'<p:sp xmlns:p="{P}" xmlns:a="{A}"><p:nvSpPr><p:cNvPr id="{max(ids + [1]) + 1}" name="End text"/>'
        '<p:cNvSpPr txBox="1"/><p:nvPr/></p:nvSpPr><p:spPr>'
        f'<a:xfrm><a:off x="{x}" y="{y}"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
        '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom><a:noFill/></p:spPr>'
        '<p:txBody><a:bodyPr wrap="square" anchor="ctr"><a:noAutofit/></a:bodyPr><a:lstStyle/>'
        f'{paras}</p:txBody></p:sp>'))


def move_cover_titles(pkg, part, box, width, height, color=None):
    """Move the text boxes in the upper 85% of the cover as one block to box (x, y, w), left-aligned."""
    els = []
    for el in pkg.xml(part).find("p:cSld/p:spTree", NS):
        xfrm = xfrm_of(el) if etree.QName(el).localname == "sp" else None
        if xfrm is not None and "".join(el.itertext()).strip() and box_of(xfrm)[1] < height * 0.85:
            els.append((el, xfrm))
    if not els:
        return []
    x0 = min(box_of(x)[0] for _, x in els)
    y0 = min(box_of(x)[1] for _, x in els)
    moved = []
    for el, xfrm in els:
        x, y, cx, cy = box_of(xfrm)
        nx, ny = box[0] + (x - x0), box[1] + (y - y0)
        xfrm.find("a:off", NS).set("x", str(nx))
        xfrm.find("a:off", NS).set("y", str(ny))
        xfrm.find("a:ext", NS).set("cx", str(min(cx, box[0] + box[2] - nx)))
        for p in el.iter(f"{{{A}}}p"):
            ppr = p.find("a:pPr", NS)
            if ppr is None:
                ppr = etree.SubElement(p, f"{{{A}}}pPr")
                p.insert(0, ppr)
            ppr.set("algn", "l")
        if color:
            recolor_text(el, color)
        moved.append({"part": part, "from_pt": [x // PT, y // PT, cx // PT, cy // PT]})
    return moved


FILLS = ("noFill", "solidFill", "gradFill", "blipFill", "pattFill", "grpFill")


def set_text_fill(rpr, hexcolor):
    for f in [c for c in rpr if etree.QName(c).localname in FILLS]:
        rpr.remove(f)
    fill = etree.fromstring(f'<a:solidFill xmlns:a="{A}"><a:srgbClr val="{hexcolor}"/></a:solidFill>')
    rpr.insert(1 if len(rpr) and etree.QName(rpr[0]).localname == "ln" else 0, fill)


def recolor_text(el, hexcolor):
    """Colour every run of a shape and its level-1 list style default; nothing else changes."""
    for tag in ("rPr", "endParaRPr", "defRPr"):
        for rpr in el.iter(f"{{{A}}}{tag}"):
            set_text_fill(rpr, hexcolor)
    for p in el.iter(f"{{{A}}}p"):
        for r in p.findall("a:r", NS) + p.findall("a:fld", NS):
            if r.find("a:rPr", NS) is None:
                r.insert(0, etree.Element(f"{{{A}}}rPr"))
                set_text_fill(r.find("a:rPr", NS), hexcolor)
    body = el.find("p:txBody", NS)
    if body is not None:
        lst = body.find("a:lstStyle", NS)
        if lst is None:
            lst = etree.Element(f"{{{A}}}lstStyle")
            body.insert(1, lst)
        lvl = lst.find("a:lvl1pPr", NS)
        if lvl is None:
            lvl = etree.Element(f"{{{A}}}lvl1pPr")
            lst.insert(0, lvl)
        if lvl.find("a:defRPr", NS) is None:
            ext = lvl.find("a:extLst", NS)
            d = etree.Element(f"{{{A}}}defRPr")
            if ext is None:
                lvl.append(d)
            else:
                ext.addprevious(d)
            set_text_fill(d, hexcolor)


def is_title_ph(el):
    ph = el.find(".//p:nvPr/p:ph", NS)
    return ph is not None and ph.get("type") in ("title", "ctrTitle")


def recolor_titles(pkg, deck, hexcolor, cover_parts=()):
    """Title placeholders on masters/layouts/slides, the master title style, and on slides
    without a title placeholder the topmost non-white text box in the top-left band."""
    done = []
    for m in deck.masters:
        style = pkg.xml(m).find("p:txStyles/p:titleStyle", NS)
        if style is not None:
            for d in style.iter(f"{{{A}}}defRPr"):
                set_text_fill(d, hexcolor)
    for part in deck.masters + deck.layouts + deck.slides[1:]:
        tree = pkg.xml(part).find("p:cSld/p:spTree", NS)
        titles = [el for el in tree.iter(f"{{{P}}}sp") if is_title_ph(el)]
        if part in deck.slides and not any("".join(t.itertext()).strip() for t in titles):
            k = deck.width / (960 * PT)
            cands = []
            for el in tree.findall("p:sp", NS):
                xfrm = xfrm_of(el)
                if xfrm is None or not "".join(el.itertext()).strip() or el.find(".//p:nvPr/p:ph", NS) is not None:
                    continue
                x, y, cx, cy = box_of(xfrm)
                colors = {c.get("val", "").upper() for c in el.iter(f"{{{A}}}srgbClr")}
                if y < 70 * PT * k and x < 240 * PT * k and cy < 80 * PT * k and "FFFFFF" not in colors:
                    cands.append((y, el))
            titles = [min(cands, key=lambda c: c[0])[1]] if cands else []
        for el in titles:
            recolor_text(el, hexcolor)
            done.append(part)
    for el in cover_parts:
        recolor_text(el, hexcolor)
    return done


def add_slide(pkg, layout, first):
    """Add an empty slide on `layout` at the start or end of the deck; returns its part name."""
    n = 1
    while f"ppt/slides/slide{n}.xml" in pkg.data:
        n += 1
    part = f"ppt/slides/slide{n}.xml"
    pkg.data[part] = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        f'<p:sld xmlns:a="{A}" xmlns:r="{R}" xmlns:p="{P}"><p:cSld><p:spTree>'
        '<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr><p:grpSpPr/>'
        '</p:spTree></p:cSld><p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr></p:sld>').encode()
    pkg.order.append(part)
    rel = etree.SubElement(pkg.rels(part), f"{{{rb.PR}}}Relationship")
    rel.set("Id", "rId1")
    rel.set("Type", R + "/slideLayout")
    rel.set("Target", posixpath.relpath(layout, "ppt/slides"))
    ov = etree.SubElement(pkg.xml("[Content_Types].xml"), f"{{{rb.CT}}}Override")
    ov.set("PartName", "/" + part)
    ov.set("ContentType", SLIDE_CT)
    prels = pkg.rels("ppt/presentation.xml")
    ids = {r.get("Id") for r in prels}
    k = 1
    while f"rIdTpl{k}" in ids:
        k += 1
    rel = etree.SubElement(prels, f"{{{rb.PR}}}Relationship")
    rel.set("Id", f"rIdTpl{k}")
    rel.set("Type", R + "/slide")
    rel.set("Target", f"slides/slide{n}.xml")
    lst = pkg.xml("ppt/presentation.xml").find("p:sldIdLst", NS)
    sid = etree.Element(f"{{{P}}}sldId")
    sid.set("id", str(max([int(e.get("id")) for e in lst] + [255]) + 1))
    sid.set(f"{{{R}}}id", f"rIdTpl{k}")
    lst.insert(0 if first else len(lst), sid)
    if "docProps/app.xml" in pkg.data:
        slides = pkg.xml("docProps/app.xml").find(f"{{{EP}}}Slides")
        if slides is not None:
            slides.text = str(len(lst))
    return part


def process(src, dst, imgs, restyle, pool, logo, left, end_lines, end_clear=False, cover_box=None,
            title_color=None):
    pkg = rb.Package(src)
    deck = rb.Deck(pkg)
    before = rb.broken_rels(pkg)
    log = {"removed": [], "inserted_cover": None, "moved_titles": [], "end_page": None}
    if restyle:
        for part in deck.masters + deck.layouts:
            for item in strip_decorations(pkg, deck, part):
                item.pop("sig")
                log["removed"].append(item)
        tree = pkg.xml(deck.slides[0]).find("p:cSld/p:spTree", NS)
        for el, media in deck.full_pictures(deck.slides[0]):
            tree.remove(el)
            log["removed"].append({"part": deck.slides[0], "kind": "pic", "full": True, "media": [media]})
        for s in deck.slides:
            log["removed"] += strip_slide_copies(pkg, s, *pool)
    for part in deck.masters + deck.layouts:
        for el, media in deck.full_pictures(part):
            el.getparent().remove(el)
            log["removed"].append({"part": part, "kind": "pic", "full": True, "media": [media]})
    if restyle and logo:
        for part in deck.layouts + deck.slides:
            log["moved_titles"] += shift_titles(pkg, part, logo, left)
    media = {k: rb.add_media(pkg, f"bg_{k}", *v) for k, v in imgs.items()}
    if restyle:
        log["inserted_cover"] = add_slide(pkg, deck.parent(deck.slides[0], "slideLayout"), first=True)
        deck = rb.Deck(pkg)
    if cover_box:
        k = deck.width / (960 * PT)
        log["moved_titles"] += move_cover_titles(pkg, deck.slides[0], [int(v * PT * k) for v in cover_box],
                                                 deck.width, deck.height, title_color)
    if title_color:
        log["recolored_titles"] = len(recolor_titles(pkg, deck, title_color))
    if end_clear and is_thanks(pkg, deck.slides[-1]):
        tree = pkg.xml(deck.slides[-1]).find("p:cSld/p:spTree", NS)
        for el in list(tree):
            if etree.QName(el).localname in SHAPES:
                tree.remove(el)
        log["end_page"] = "cleared"
    if end_lines:
        last = deck.slides[-1]
        if is_thanks(pkg, last):
            log["end_page"] = "replaced"
        else:
            last = add_slide(pkg, deck.parent(last, "slideLayout"), first=False)
            log["end_page"] = "appended"
            deck = rb.Deck(pkg)
        end_page_text(pkg, last, end_lines, deck.width, deck.height)
    n = len(deck.slides)
    want = {1: "cover", 2: "title" if "title" in imgs else "content", n: "end"}
    for m in deck.masters:
        rb.set_bg(pkg, m, media["content"])
    for layout in deck.layouts:
        rb.clear_bg(pkg, layout)
    for i, s in enumerate(deck.slides, 1):
        if i in want:
            rb.set_bg(pkg, s, media[want[i]])
        else:
            rb.clear_bg(pkg, s)
    for part in deck.masters + deck.layouts + deck.slides:
        rb.drop_unused_image_rels(pkg, part)
    log["dropped_media"] = rb.drop_orphan_media(pkg)
    pkg.save(dst)
    expect = {i: rb.md5(imgs[want.get(i, "content")][0]) for i in range(1, n + 1)}
    log["problems"] = verify(dst, expect, before, restyle)
    log["slides"] = n
    return log


def verify(path, expect, before, restyle):
    pkg = rb.Package(path)
    for name in pkg.data:
        if name.endswith((".xml", ".rels")):
            pkg.xml(name)
    deck = rb.Deck(pkg)
    problems = []
    if len(deck.slides) != len(expect):
        problems.append(f"slide count {len(deck.slides)} != {len(expect)}")
    for i in range(1, len(deck.slides) + 1):
        eff = deck.effective(i)
        got = eff["bg"]["md5"] if eff["bg"] and eff["bg"]["kind"] == "image" else None
        if got != expect.get(i):
            problems.append(f"slide {i}: background is not the requested image")
        if eff["covered_by"]:
            problems.append(f"slide {i}: full-slide picture still covers it in {eff['covered_by']}")
    if restyle:
        for part in deck.masters + deck.layouts:
            if strip_decorations(pkg, deck, part):
                problems.append(f"{part}: decorations left")
    for rel, target in sorted(rb.broken_rels(pkg) - before):
        problems.append(f"new broken relationship {rel} -> {target}")
    return problems


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("decks", nargs="+", type=Path)
    ap.add_argument("--cover", required=True, type=Path)
    ap.add_argument("--title", type=Path, help="image for slide 2 (and the last slide when --end is omitted)")
    ap.add_argument("--content", required=True, type=Path)
    ap.add_argument("--end", type=Path, help="image for the last slide (default: --title)")
    ap.add_argument("--restyle", default="", help="comma-separated deck number prefixes or file names")
    ap.add_argument("--logo-box", help="x1,y1,x2,y2 in points")
    ap.add_argument("--title-left", type=float, help="new left edge in points (default: logo x2 + 7)")
    ap.add_argument("--end-text", help='lines separated by "|", e.g. "感谢聆听|THANKS"')
    ap.add_argument("--end-clear", action="store_true", help="empty the thanks page; the end image has the words")
    ap.add_argument("--cover-title-box", help="x,y,w in points on a 960pt-wide slide")
    ap.add_argument("--title-color", help="hex such as 2986C4: cover title and page titles, colour only")
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--report-dir", required=True, type=Path)
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args(argv)

    if not (args.end or args.title):
        ap.error("--end is required without --title")
    imgs = {"cover": rb.read_image(args.cover), "content": rb.read_image(args.content),
            "end": rb.read_image(args.end or args.title)}
    if args.title:
        imgs["title"] = rb.read_image(args.title)
    cover_box = [float(v) for v in args.cover_title_box.split(",")] if args.cover_title_box else None
    keys = {x.strip() for x in args.restyle.split(",") if x.strip()}
    restyled = lambda p: p.name in keys or p.name.split(".")[0] in keys  # noqa: E731
    logo = [int(float(v) * PT) for v in args.logo_box.split(",")] if args.logo_box else None
    left = int((args.title_left if args.title_left is not None else (logo[2] / PT + 7 if logo else 0)) * PT)
    end_lines = [s for s in args.end_text.split("|") if s] if args.end_text else None
    args.out_dir.mkdir(parents=True, exist_ok=True)
    removed_dir = args.report_dir / "removed-images"
    removed_dir.mkdir(parents=True, exist_ok=True)
    pool = decoration_pool([p for p in args.decks if restyled(p)])
    report_path = args.report_dir / "report.json"
    report = json.loads(report_path.read_text(encoding="utf-8")) if report_path.exists() else {}
    failed, seen = 0, set()
    for src in args.decks:
        dst = args.out_dir / src.name
        if dst.resolve() == src.resolve() or (dst.exists() and not args.overwrite):
            print(f"SKIP {src.name}: {dst} exists or is the source (use --overwrite for an output)", file=sys.stderr)
            failed += 1
            continue
        if rb.lock_files(src):
            print(f"WARN {src.name}: lock file present, unsaved edits are not included", file=sys.stderr)
        log = process(src, dst, imgs, restyled(src), pool, logo, left, end_lines, args.end_clear, cover_box,
                      args.title_color)
        report[src.name] = log
        failed += bool(log["problems"])
        print(("OK   " if not log["problems"] else "FAIL ") + f"{src.name}: slides={log['slides']} "
              f"removed={len(log['removed'])} cover_inserted={bool(log['inserted_cover'])} "
              f"titles_moved={len(log['moved_titles'])} recolored={log.get('recolored_titles', 0)} end={log['end_page']}"
              + "".join(f"\n     {p}" for p in log["problems"]))
        z = zipfile.ZipFile(src)
        for item in log["removed"]:
            for m in item["media"]:
                if m and m in z.namelist():
                    h = rb.md5(z.read(m))
                    if h not in seen:
                        seen.add(h)
                        (removed_dir / f"{h[:8]}{posixpath.splitext(m)[1]}").write_bytes(z.read(m))
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
