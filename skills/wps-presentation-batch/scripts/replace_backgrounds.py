#!/usr/bin/env python3
"""Batch-replace PPTX backgrounds at the master level, with an optional cover image.

inspect: show where each deck's visible background actually comes from.
apply:   write new decks in which the masters use the content image, slide 1 (or
         --cover-slides) uses the cover image, every other slide inherits the
         master, and full-slide background pictures on masters/layouts are removed.

Only background parts are edited. Text, shapes, autofit and other ZIP parts are
copied unchanged. Requires lxml.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import posixpath
import struct
import sys
import zipfile
from pathlib import Path

from lxml import etree

P = "http://schemas.openxmlformats.org/presentationml/2006/main"
A = "http://schemas.openxmlformats.org/drawingml/2006/main"
R = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PR = "http://schemas.openxmlformats.org/package/2006/relationships"
CT = "http://schemas.openxmlformats.org/package/2006/content-types"
IMG_REL = R + "/image"
NS = {"p": P, "a": A, "r": R}
FULL = 0.9  # a picture covering >= 90% of both slide dimensions counts as a background
CONTENT_TYPES = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg"}


def md5(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def rels_path(part: str) -> str:
    d, b = posixpath.split(part)
    return f"{d}/_rels/{b}.rels"


def resolve(source_part: str, target: str) -> str:
    if target.startswith("/"):
        return target[1:]
    return posixpath.normpath(posixpath.join(posixpath.dirname(source_part), target))


def image_size(data: bytes) -> tuple[int, int] | None:
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", data[16:24])
    if data[:2] == b"\xff\xd8":
        i = 2
        while i < len(data) - 9:
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack(">H", data[i + 2:i + 4])[0]
    return None


class Package:
    def __init__(self, path: Path):
        with zipfile.ZipFile(path) as z:
            self.order = z.namelist()
            self.data = {n: z.read(n) for n in self.order}
        self._xml: dict[str, etree._Element] = {}

    def xml(self, part: str) -> etree._Element:
        if part not in self._xml:
            self._xml[part] = etree.fromstring(self.data[part])
        return self._xml[part]

    def rels(self, part: str) -> etree._Element:
        rp = rels_path(part)
        if rp not in self.data:
            self.data[rp] = f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?><Relationships xmlns="{PR}"/>'.encode()
            self.order.append(rp)
        return self.xml(rp)

    def targets(self, part: str) -> dict[str, tuple[str, str]]:
        if rels_path(part) not in self.data:
            return {}
        return {
            r.get("Id"): (r.get("Type").rsplit("/", 1)[-1], resolve(part, r.get("Target")))
            for r in self.rels(part)
            if r.get("TargetMode") != "External"
        }

    def add_image_rel(self, part: str, media: str) -> str:
        rels = self.rels(part)
        ids = {r.get("Id") for r in rels}
        n = 1
        while f"rIdBg{n}" in ids:
            n += 1
        el = etree.SubElement(rels, f"{{{PR}}}Relationship")
        el.set("Id", f"rIdBg{n}")
        el.set("Type", IMG_REL)
        el.set("Target", posixpath.relpath(media, posixpath.dirname(part)))
        return f"rIdBg{n}"

    def save(self, path: Path) -> None:
        for part, x in self._xml.items():
            self.data[part] = etree.tostring(x, xml_declaration=True, encoding="UTF-8", standalone=True)
        names = ["[Content_Types].xml"] + [n for n in self.order if n != "[Content_Types].xml" and n in self.data]
        tmp = path.with_name(path.name + ".tmp")
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as z:
            for n in names:
                z.writestr(n, self.data[n])
        os.replace(tmp, path)


class Deck:
    """Read-only view of the slide -> layout -> master chain."""

    def __init__(self, pkg: Package):
        self.pkg = pkg
        pres = pkg.xml("ppt/presentation.xml")
        size = pres.find("p:sldSz", NS)
        self.width, self.height = int(size.get("cx")), int(size.get("cy"))
        t = pkg.targets("ppt/presentation.xml")
        self.masters = [t[e.get(f"{{{R}}}id")][1] for e in pres.find("p:sldMasterIdLst", NS)]
        lst = pres.find("p:sldIdLst", NS)
        self.slides = [t[e.get(f"{{{R}}}id")][1] for e in (lst if lst is not None else [])]
        self.layouts = [tgt for m in self.masters for kind, tgt in pkg.targets(m).values() if kind == "slideLayout"]

    def parent(self, part: str, kind: str) -> str:
        return next(tgt for k, tgt in self.pkg.targets(part).values() if k == kind)

    def bg(self, part: str) -> dict | None:
        bg = self.pkg.xml(part).find("p:cSld/p:bg", NS)
        if bg is None:
            return None
        blip = bg.find(".//a:blip", NS)
        if blip is None:
            return {"kind": "bgRef" if bg.find("p:bgRef", NS) is not None else "fill"}
        media = self.pkg.targets(part).get(blip.get(f"{{{R}}}embed"), (None, None))[1]
        return {"kind": "image", "media": media, "md5": md5(self.pkg.data[media]) if media in self.pkg.data else None}

    def full_pictures(self, part: str) -> list[tuple[etree._Element, str | None]]:
        found = []
        targets = self.pkg.targets(part)
        for el in self.pkg.xml(part).find("p:cSld/p:spTree", NS):
            tag = etree.QName(el).localname
            if tag not in ("pic", "sp") or el.find(".//p:nvPr/p:ph", NS) is not None:
                continue
            blip = el.find("p:blipFill/a:blip", NS) if tag == "pic" else el.find("p:spPr/a:blipFill/a:blip", NS)
            ext = el.find("p:spPr/a:xfrm/a:ext", NS)
            if blip is None or ext is None:
                continue
            if int(ext.get("cx")) >= FULL * self.width and int(ext.get("cy")) >= FULL * self.height:
                found.append((el, targets.get(blip.get(f"{{{R}}}embed"), (None, None))[1]))
        return found

    def effective(self, index: int) -> dict:
        """What is visible behind slide `index` (1-based): the bg owner and any covering pictures."""
        slide = self.slides[index - 1]
        layout = self.parent(slide, "slideLayout")
        master = self.parent(layout, "slideMaster")
        owner = next((p for p in (slide, layout, master) if self.bg(p)), None)
        covering = [p for p in (slide, layout) if self.full_pictures(p)]
        if self.pkg.xml(layout).get("showMasterSp") != "0" and self.pkg.xml(slide).get("showMasterSp") != "0":
            covering += [master] if self.full_pictures(master) else []
        return {"bg_part": owner, "bg": self.bg(owner) if owner else None, "covered_by": covering}


def broken_rels(pkg: Package) -> set[tuple[str, str]]:
    broken = set()
    for name in list(pkg.data):
        if not name.endswith(".rels"):
            continue
        source = name.replace("_rels/", "")[:-5]
        for r in pkg.xml(name):
            if r.get("TargetMode") != "External":
                target = resolve(source, r.get("Target"))
                if target not in pkg.data:
                    broken.add((name, target))
    return broken


def lock_files(path: Path) -> list[str]:
    return [p.name for p in (path.with_name(".~" + path.name), path.with_name("~$" + path.name)) if p.exists()]


# ---------------------------------------------------------------- inspect

def inspect_deck(path: Path) -> dict:
    pkg = Package(path)
    deck = Deck(pkg)
    usage: dict[str, list[int]] = {}
    for i, s in enumerate(deck.slides, 1):
        usage.setdefault(deck.parent(s, "slideLayout"), []).append(i)

    def describe(part):
        bg = deck.bg(part)
        return {
            "part": part,
            "bg": bg["kind"] if bg else None,
            "full_pictures": len(deck.full_pictures(part)),
        }

    masters = [describe(m) for m in deck.masters]
    layouts = [dict(describe(l), used_by=usage[l]) for l in deck.layouts if l in usage]
    slides = [dict(describe(s), slide=i) for i, s in enumerate(deck.slides, 1)]
    hidden = sorted(i for l in layouts if l["full_pictures"] for i in l["used_by"])
    return {
        "file": path.name,
        "slide_size_pt": [deck.width // 12700, deck.height // 12700],
        "slides": len(deck.slides),
        "masters": masters,
        "used_layouts": layouts,
        "slide_overrides": [s for s in slides if s["bg"] or s["full_pictures"]],
        "slides_hiding_master_bg": hidden,
        "locks": lock_files(path),
    }


def print_inspection(info: dict) -> None:
    w, h = info["slide_size_pt"]
    print(f"## {info['file']}  {w}x{h}pt  slides={info['slides']}")
    if info["locks"]:
        print(f"  ! open in an editor (lock files: {', '.join(info['locks'])})")
    for m in info["masters"]:
        print(f"  master {m['part'].rsplit('/', 1)[-1]}: bg={m['bg']} full_pictures={m['full_pictures']}")
    for l in info["used_layouts"]:
        used = l["used_by"]
        shown = ",".join(map(str, used[:8])) + ("..." if len(used) > 8 else "")
        print(f"    layout {l['part'].rsplit('/', 1)[-1]}: bg={l['bg']} full_pictures={l['full_pictures']} slides=[{shown}]")
    for s in info["slide_overrides"]:
        print(f"    slide {s['slide']}: bg={s['bg']} full_pictures={s['full_pictures']}")
    hidden = info["slides_hiding_master_bg"]
    if hidden:
        shown = ",".join(map(str, hidden[:12])) + ("..." if len(hidden) > 12 else "")
        print(f"  -> layout pictures hide the master background on {len(hidden)}/{info['slides']} slides [{shown}];"
              " changing only the master will not show there")


# ---------------------------------------------------------------- apply

def set_bg(pkg: Package, part: str, media: str) -> None:
    csld = pkg.xml(part).find("p:cSld", NS)
    old = csld.find("p:bg", NS)
    if old is not None:
        csld.remove(old)
    rid = pkg.add_image_rel(part, media)
    csld.insert(0, etree.fromstring(
        f'<p:bg xmlns:p="{P}" xmlns:a="{A}" xmlns:r="{R}"><p:bgPr>'
        f'<a:blipFill dpi="0" rotWithShape="1"><a:blip r:embed="{rid}"/><a:srcRect/>'
        f"<a:stretch><a:fillRect/></a:stretch></a:blipFill><a:effectLst/></p:bgPr></p:bg>"))


def clear_bg(pkg: Package, part: str) -> bool:
    csld = pkg.xml(part).find("p:cSld", NS)
    old = csld.find("p:bg", NS)
    if old is None:
        return False
    csld.remove(old)
    return True


def drop_unused_image_rels(pkg: Package, part: str) -> None:
    text = etree.tostring(pkg.xml(part)).decode()
    rels = pkg.rels(part)
    for r in list(rels):
        if r.get("Type") == IMG_REL and r.get("TargetMode") != "External" and f'"{r.get("Id")}"' not in text:
            rels.remove(r)


def drop_orphan_media(pkg: Package) -> list[str]:
    used = set()
    for name in list(pkg.data):
        if name.endswith(".rels"):
            source = name.replace("_rels/", "")[:-5]
            used |= {resolve(source, r.get("Target")) for r in pkg.xml(name) if r.get("TargetMode") != "External"}
    orphans = [n for n in pkg.data if n.startswith("ppt/media/") and not n.endswith("/") and n not in used]
    ct = pkg.xml("[Content_Types].xml")
    for n in orphans:
        del pkg.data[n]
        for o in ct.findall(f"{{{CT}}}Override"):
            if o.get("PartName") == "/" + n:
                ct.remove(o)
    return orphans


def add_media(pkg: Package, stem: str, data: bytes, ext: str) -> str:
    ct = pkg.xml("[Content_Types].xml")
    if not any(d.get("Extension", "").lower() == ext for d in ct.findall(f"{{{CT}}}Default")):
        d = etree.Element(f"{{{CT}}}Default", Extension=ext, ContentType=CONTENT_TYPES[ext])
        ct.insert(0, d)
    n, part = 1, f"ppt/media/{stem}.{ext}"
    while part in pkg.data:
        n += 1
        part = f"ppt/media/{stem}{n}.{ext}"
    pkg.data[part] = data
    pkg.order.append(part)
    return part


def apply_deck(src: Path, dst: Path, content: tuple[bytes, str], cover: tuple[bytes, str] | None,
               cover_slides: set[int]) -> dict:
    pkg = Package(src)
    deck = Deck(pkg)
    before_broken = broken_rels(pkg)
    content_media = add_media(pkg, "bg_content", *content)
    cover_media = add_media(pkg, "bg_cover", *cover) if cover else None
    log = {"removed_pictures": [], "cleared_layout_bg": [], "cleared_slide_bg": [], "cover_slides": []}

    for part in deck.masters + deck.layouts:
        for el, media in deck.full_pictures(part):
            el.getparent().remove(el)
            log["removed_pictures"].append({"part": part, "media": media,
                                            "md5": md5(pkg.data[media]) if media in pkg.data else None})
    for m in deck.masters:
        set_bg(pkg, m, content_media)
    for l in deck.layouts:
        if clear_bg(pkg, l):
            log["cleared_layout_bg"].append(l)
    for i, s in enumerate(deck.slides, 1):
        if cover_media and i in cover_slides:
            set_bg(pkg, s, cover_media)
            log["cover_slides"].append(i)
        elif clear_bg(pkg, s):
            log["cleared_slide_bg"].append(i)
    for part in deck.masters + deck.layouts + deck.slides:
        drop_unused_image_rels(pkg, part)
    log["dropped_media"] = drop_orphan_media(pkg)
    pkg.save(dst)
    log["problems"] = verify_deck(dst, md5(content[0]), md5(cover[0]) if cover else None, cover_slides, before_broken)
    return log


def verify_deck(path: Path, content_md5: str, cover_md5: str | None, cover_slides: set[int],
                known_broken: set[tuple[str, str]]) -> list[str]:
    pkg = Package(path)
    for name in pkg.data:
        if name.endswith((".xml", ".rels")):
            pkg.xml(name)  # raises on malformed XML
    deck = Deck(pkg)
    problems = []
    for i in range(1, len(deck.slides) + 1):
        eff = deck.effective(i)
        want = cover_md5 if cover_md5 and i in cover_slides else content_md5
        got = eff["bg"]["md5"] if eff["bg"] and eff["bg"]["kind"] == "image" else None
        if got != want:
            problems.append(f"slide {i}: background is not the requested image")
        if eff["covered_by"]:
            problems.append(f"slide {i}: full-slide picture still covers the background in {eff['covered_by']}")
    for rel, target in sorted(broken_rels(pkg) - known_broken):
        problems.append(f"new broken relationship {rel} -> {target}")
    return problems


def read_image(path: Path) -> tuple[bytes, str]:
    ext = path.suffix[1:].lower()
    if ext not in CONTENT_TYPES:
        raise SystemExit(f"unsupported image type: {path}")
    return path.read_bytes(), ext


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    ins = sub.add_parser("inspect", help="show background sources without changing anything")
    ins.add_argument("decks", nargs="+", type=Path)
    ins.add_argument("--json", action="store_true")
    app = sub.add_parser("apply", help="write decks with replaced backgrounds to --out-dir")
    app.add_argument("decks", nargs="+", type=Path)
    app.add_argument("--content", required=True, type=Path, help="image for the masters (all non-cover slides)")
    app.add_argument("--cover", type=Path, help="image for cover slides; omit to use --content everywhere")
    app.add_argument("--cover-slides", default="1", help="comma-separated 1-based slide numbers (default: 1)")
    app.add_argument("--out-dir", required=True, type=Path)
    app.add_argument("--report-dir", type=Path, help="write report.json and one copy of each removed image here")
    app.add_argument("--overwrite", action="store_true", help="replace existing files in --out-dir")
    args = ap.parse_args(argv)

    if args.cmd == "inspect":
        infos = [inspect_deck(p) for p in args.decks]
        if args.json:
            print(json.dumps(infos, ensure_ascii=False, indent=1))
        else:
            for info in infos:
                print_inspection(info)
        return 0

    content = read_image(args.content)
    cover = read_image(args.cover) if args.cover else None
    cover_slides = {int(x) for x in args.cover_slides.split(",") if x.strip()}
    args.out_dir.mkdir(parents=True, exist_ok=True)
    report, failed = {}, 0
    for src in args.decks:
        dst = args.out_dir / src.name
        if dst.resolve() == src.resolve():
            print(f"SKIP {src.name}: output would overwrite the source", file=sys.stderr)
            failed += 1
            continue
        if dst.exists() and not args.overwrite:
            print(f"SKIP {src.name}: {dst} exists (use --overwrite)", file=sys.stderr)
            failed += 1
            continue
        if lock_files(src):
            print(f"WARN {src.name}: lock file present, the saved file may not include unsaved edits", file=sys.stderr)
        deck = Deck(Package(src))
        ratio = deck.width / deck.height
        for label, img in (("content", content), ("cover", cover)):
            size = img and image_size(img[0])
            if size and abs(size[0] / size[1] - ratio) > 0.01:
                print(f"WARN {src.name}: {label} image {size[0]}x{size[1]} will be stretched to slide ratio {ratio:.3f}",
                      file=sys.stderr)
        log = apply_deck(src, dst, content, cover, cover_slides)
        report[src.name] = log
        status = "OK  " if not log["problems"] else "FAIL"
        failed += bool(log["problems"])
        print(f"{status} {src.name}: removed {len(log['removed_pictures'])} full-slide pictures, "
              f"cleared {len(log['cleared_layout_bg'])} layout / {len(log['cleared_slide_bg'])} slide backgrounds"
              + "".join(f"\n     {p}" for p in log["problems"]))

    if args.report_dir:
        removed_dir = args.report_dir / "removed-images"
        removed_dir.mkdir(parents=True, exist_ok=True)
        (args.report_dir / "report.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        seen = set()
        for name, log in report.items():
            data = zipfile.ZipFile(args.decks[[p.name for p in args.decks].index(name)])
            for item in log["removed_pictures"]:
                if item["md5"] and item["md5"] not in seen and item["media"]:
                    seen.add(item["md5"])
                    (removed_dir / f"{item['md5'][:8]}{posixpath.splitext(item['media'])[1]}").write_bytes(
                        data.read(item["media"]))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
