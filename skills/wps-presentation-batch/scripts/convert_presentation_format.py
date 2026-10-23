#!/usr/bin/env python3
"""Lossless PPTX <-> PPTM conversion at the package level.

The two formats differ only in the main part's content type and, for PPTM, an
optional VBA project. PPTX -> PPTM changes the content type and adds no macro
code. PPTM -> PPTX changes it back and removes the VBA project. All other ZIP
parts are copied byte-for-byte; no office application re-saves the deck.

Usage: convert_presentation_format.py <source.pptx|source.pptm>... --out-dir DIR
Requires lxml.
"""
from __future__ import annotations

import argparse
import posixpath
import sys
import zipfile
from pathlib import Path
from lxml import etree as ET

CT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"
REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
MAIN = {
    "pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml",
    "pptm": "application/vnd.ms-powerpoint.presentation.macroEnabled.main+xml",
}
VBA_REL_SUFFIX = "/vbaProject"


def xml_bytes(root: ET.Element) -> bytes:
    return ET.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


def rels_of(part: str) -> str:
    d, b = posixpath.split(part)
    return f"{d}/_rels/{b}.rels"


def main_part(data: dict[str, bytes]) -> str:
    rels = ET.fromstring(data["_rels/.rels"])
    for r in rels.findall(f"{{{REL_NS}}}Relationship"):
        if r.get("Type", "").endswith("/officeDocument"):
            return r.get("Target").lstrip("/")
    raise ValueError("no officeDocument relationship")


def convert(src: Path, out_dir: Path) -> tuple[Path, list[str]]:
    source_ext = src.suffix[1:].lower()
    if source_ext not in MAIN:
        raise ValueError(f"only .pptx and .pptm are supported: {src.name}")
    target_ext = "pptm" if source_ext == "pptx" else "pptx"
    dst = out_dir / f"{src.stem}.{target_ext}"
    if dst.exists():
        raise FileExistsError(f"target exists, not overwriting: {dst}")

    with zipfile.ZipFile(src) as z:
        infos = z.infolist()
        data = {i.filename: z.read(i.filename) for i in infos}

    main = main_part(data)
    ct = ET.fromstring(data["[Content_Types].xml"])
    override = next((o for o in ct.findall(f"{{{CT_NS}}}Override") if o.get("PartName") == "/" + main), None)
    if override is None or override.get("ContentType") != MAIN[source_ext]:
        found = override.get("ContentType") if override is not None else "missing"
        raise ValueError(f"{src.name}: main part content type is {found}, not a {source_ext} presentation")
    override.set("ContentType", MAIN[target_ext])

    removed: list[str] = []
    if target_ext == "pptx":
        main_rels_name = rels_of(main)
        main_rels = ET.fromstring(data[main_rels_name]) if main_rels_name in data else None
        vba_parts = []
        if main_rels is not None:
            for r in list(main_rels):
                if r.get("Type", "").endswith(VBA_REL_SUFFIX):
                    vba_parts.append(posixpath.normpath(posixpath.join(posixpath.dirname(main), r.get("Target"))))
                    main_rels.remove(r)
            if vba_parts:
                data[main_rels_name] = xml_bytes(main_rels)
        for part in list(vba_parts):  # vbaData.xml and similar hang off the VBA project
            if rels_of(part) in data:
                for r in ET.fromstring(data[rels_of(part)]):
                    vba_parts.append(posixpath.normpath(posixpath.join(posixpath.dirname(part), r.get("Target"))))
                vba_parts.append(rels_of(part))
        for part in vba_parts:
            if data.pop(part, None) is not None:
                removed.append(part)
            for o in ct.findall(f"{{{CT_NS}}}Override"):
                if o.get("PartName") == "/" + part:
                    ct.remove(o)
        # In a valid PPTM a VBA-typed .bin default forces every other .bin part to carry an Override,
        # so the default can go without leaving any part untyped.
        for d in ct.findall(f"{{{CT_NS}}}Default"):
            if d.get("Extension", "").lower() == "bin" and "vbaProject" in d.get("ContentType", ""):
                ct.remove(d)
    data["[Content_Types].xml"] = xml_bytes(ct)

    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    with zipfile.ZipFile(tmp, "w") as z:
        for info in infos:
            if info.filename in data:
                z.writestr(info, data[info.filename], compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(tmp) as z:
        if z.testzip() is not None:
            raise ValueError(f"written archive is corrupt: {tmp}")
    tmp.replace(dst)
    return dst, removed


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("sources", nargs="+", type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    args = ap.parse_args(argv)
    failed = 0
    for src in args.sources:
        if src.name.startswith(("~$", ".~")):
            print(f"SKIP {src}: editor lock file", file=sys.stderr)
            continue
        try:
            dst, removed = convert(src, args.out_dir)
        except (OSError, ValueError, KeyError, zipfile.BadZipFile, ET.XMLSyntaxError) as exc:
            print(f"FAIL {src}: {exc}", file=sys.stderr)
            failed += 1
            continue
        note = f" (removed VBA parts: {', '.join(removed)})" if removed else ""
        print(f"OK   {dst}{note}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
