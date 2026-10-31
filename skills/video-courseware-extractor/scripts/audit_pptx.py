#!/usr/bin/env python3
"""Read-only supplementary PPTX audit. Does not replace rendering or a host validator."""
import argparse
import json
import posixpath
import re
import zipfile
import xml.etree.ElementTree as E
from pathlib import Path

NS = {'p':'http://schemas.openxmlformats.org/presentationml/2006/main',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main'}


def audit(path, expected_slides=None, ratio=None, require_empty_notes=False):
    findings=[]; notes=[]; hits=[]
    with zipfile.ZipFile(path) as z:
        if z.testzip() is not None:
            findings.append('ZIP integrity failure')
        names=z.namelist()
        # Delete-then-add slides in python-pptx can write the same part twice.
        duplicates=sorted({n for n in names if names.count(n)>1})
        if duplicates:findings.append('Duplicate ZIP entries')
        targets={}
        for rels in names:
            m=re.fullmatch(r'(.*?)_rels/([^/]+)\.rels',rels)
            if not m:continue
            for r in E.fromstring(z.read(rels)):
                if r.get('TargetMode')=='External':continue
                t=r.get('Target','')
                t=t.lstrip('/') if t.startswith('/') else posixpath.normpath(posixpath.join(m.group(1),t))
                targets.setdefault(t,set()).add(m.group(1)+m.group(2))
        orphan_media=sorted(n for n in set(names) if n.startswith('ppt/media/') and not n.endswith('/') and n not in targets)
        if orphan_media:findings.append('Unreferenced media (old background left in package?)')
        layouts=sorted(n for n in set(names) if re.fullmatch(r'ppt/slideLayouts/slideLayout\d+\.xml',n))
        unused_layouts=[n for n in layouts if not any(s.startswith('ppt/slides/slide') for s in targets.get(n,()))]
        presentation=E.fromstring(z.read('ppt/presentation.xml'))
        slide_ids=presentation.findall('p:sldIdLst/p:sldId', NS)
        slides=[n for n in z.namelist() if re.fullmatch(r'ppt/slides/slide\d+\.xml',n)]
        if len(slide_ids)!=len(slides):
            findings.append('Slide list/part count mismatch')
        if expected_slides is not None and len(slide_ids)!=expected_slides:
            findings.append(f'Expected {expected_slides} slides, found {len(slide_ids)}')
        size=presentation.find('p:sldSz',NS)
        cx,cy=int(size.attrib['cx']),int(size.attrib['cy'])
        if ratio:
            rw,rh=map(float,ratio.split(':'))
            if min(rw,rh)<=0 or abs(cx/cy-rw/rh)>0.002:
                findings.append('Slide aspect ratio mismatch')
        for name in z.namelist():
            if re.fullmatch(r'ppt/notesSlides/notesSlide\d+\.xml',name):
                root=E.fromstring(z.read(name))
                # Standard notes headers/page numbers are not speaker-note content.
                for shape in list(root.findall('.//p:sp',NS)):
                    ph=shape.find('p:nvSpPr/p:nvPr/p:ph',NS)
                    if ph is not None and ph.get('type') in ('sldNum','hdr','ftr','dt'):
                        for t in shape.findall('.//a:t',NS):t.text=''
                text=''.join(t.text or '' for t in root.findall('.//a:t',NS)).strip()
                if text:notes.append(name)
        for name in slides:
            text=''.join(t.text or '' for t in E.fromstring(z.read(name)).findall('.//a:t',NS))
            if any(token in text for token in ['正在共享','原视频时间：','课件裁切区域','来源视频：']):
                hits.append(name)
        if require_empty_notes and notes:findings.append('Non-empty notes')
        if hits:findings.append('Possible UI/extraction text: inspect listed slides')
    return {'file':str(Path(path).resolve()),'slide_count':len(slide_ids),'size_emu':[cx,cy],
            'nonempty_notes':notes,'native_text_hits':hits,'duplicate_entries':duplicates,
            'orphan_media':orphan_media,'unused_layouts':unused_layouts,'findings':findings,
            'scope':'Counts/ratio/notes/native text, duplicate parts, unreferenced media and unused layouts (informational) only; images, proportions, clipping, visual quality and full relationship integrity require host validation and rendered review.'}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('pptx');p.add_argument('--expected-slides',type=int)
    p.add_argument('--ratio');p.add_argument('--require-empty-notes',action='store_true');a=p.parse_args()
    result=audit(a.pptx,a.expected_slides,a.ratio,a.require_empty_notes)
    print(json.dumps(result,ensure_ascii=False,indent=2));return 1 if result['findings'] else 0

if __name__=='__main__':raise SystemExit(main())
