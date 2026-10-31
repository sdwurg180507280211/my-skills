import copy
import importlib.util
import json
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import warnings
import zipfile

ROOT=Path(__file__).resolve().parents[1]
def module(name):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/f'{name}.py')
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
v=module('video_slides');a=module('audit_pptx')


def info():
    return dict(width=320,height=240,duration=30,rotation=0,sample_aspect_ratio='1:1',fingerprint={'sha256':'synthetic','bytes':100})

def plan():
    return dict(schema_version=1,video='synthetic.mp4',segments=[dict(id='a',speaker='Speaker A',output_name='Speaker A.pptx',start=0,end=5,crop=[0,0,320,240])])


def selection():
    return dict(source=info(),plan=plan(),candidates=[dict(candidate_id='a-1',segment_id='a',speaker='Speaker A',output_name='Speaker A.pptx',begin=0,end=5,time=2,crop=[0,0,320,240],keep=True,reason='reviewed synthetic page')])


class Contracts(unittest.TestCase):
    def test_reject_invalid_crop_and_timeline(self):
        for crop in [[-1,0,320,240],[0,0,321,240],[0,0,0,240],[0,0,1.5,240]]:
            p=plan();p['segments'][0]['crop']=crop
            with self.assertRaises(ValueError):v.validate_plan(p,info())
        p=plan();p['segments'][0]['end']=31
        with self.assertRaises(ValueError):v.validate_plan(p,info())
    def test_rotation_requires_normalization(self):
        i=info();i['rotation']=90
        with self.assertRaises(ValueError):v.validate_plan(plan(),i)
    def test_repeated_speaker_segments_merge_contract(self):
        p=plan();s=copy.deepcopy(p['segments'][0]);s.update(id='a2',start=8,end=12);p['segments'].append(s)
        v.validate_plan(p,info())
        p['segments'][1]['output_name']='different.pptx'
        with self.assertRaises(ValueError):v.validate_plan(p,info())
    def test_reject_colliding_names_or_traversal(self):
        p=plan();s=copy.deepcopy(p['segments'][0]);s.update(id='b',speaker='Speaker B',start=8,end=12);p['segments'].append(s)
        with self.assertRaises(ValueError):v.validate_plan(p,info())
        with self.assertRaises(ValueError):v.safe_name('../escape.pptx')
    def test_selection_requires_decisions_and_current_source(self):
        s=selection();s['candidates'][0]['keep']=None
        with self.assertRaises(ValueError):v.validate_selection(s,info())
        s=selection();s['source']['fingerprint']['sha256']='old'
        with self.assertRaises(ValueError):v.validate_selection(s,info())
        self.assertEqual(len(v.validate_selection(selection(),info())),1)
    def test_reject_missing_speaker_pages(self):
        s=selection();seg=copy.deepcopy(s['plan']['segments'][0]);seg.update(id='b',speaker='Speaker B',output_name='Speaker B.pptx',start=8,end=12);s['plan']['segments'].append(seg)
        with self.assertRaises(ValueError):v.validate_selection(s,info())
    def test_never_overwrite_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'data.json';v.save_new(p,{'a':1})
            with self.assertRaises(FileExistsError):v.save_new(p,{'a':2})
            self.assertEqual(json.loads(p.read_text()),{'a':1})
    def test_ppt_notes_ratio_and_ui_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'synthetic.pptx'
            self.fixture(p,'正在共享','private extraction notes')
            r=a.audit(p,1,'16:9',True)
            self.assertEqual(r['slide_count'],1);self.assertEqual(len(r['nonempty_notes']),1);self.assertEqual(len(r['native_text_hits']),1)
            self.assertIn('Non-empty notes',r['findings'])
            self.fixture(p,'报告时间：2020-01-01','')
            self.assertEqual(a.audit(p,1,'16:9',True)['findings'],[])
            self.assertIn('Slide aspect ratio mismatch',a.audit(p,1,'4:3')['findings'])
    def test_notes_page_number_is_not_speaker_note(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'synthetic.pptx';self.fixture(p,'Report','')
            with zipfile.ZipFile(p) as z:parts={n:z.read(n) for n in z.namelist()}
            parts['ppt/notesSlides/notesSlide1.xml']=('<p:notes xmlns:p="'+a.NS['p']+'" xmlns:a="'+a.NS['a']+'"><p:cSld><p:spTree><p:sp><p:nvSpPr><p:nvPr><p:ph type="sldNum"/></p:nvPr></p:nvSpPr><a:t>1</a:t></p:sp></p:spTree></p:cSld></p:notes>').encode()
            with zipfile.ZipFile(p,'w') as z:
                for name,data in parts.items():z.writestr(name,data)
            self.assertEqual(a.audit(p,1,'16:9',True)['nonempty_notes'],[])
    def test_duplicate_parts_orphan_media_and_unused_layouts(self):
        rel='<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">%s</Relationships>'
        item='<Relationship Id="%s" Type="t" Target="%s"/>'
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/'synthetic.pptx';self.fixture(p,'Report','')
            with zipfile.ZipFile(p,'a') as z:
                z.writestr('ppt/slides/_rels/slide1.xml.rels',rel%(item%('rId1','../slideLayouts/slideLayout1.xml')+item%('rId2','../media/new.jpg')))
                z.writestr('ppt/slideLayouts/slideLayout1.xml','<x/>');z.writestr('ppt/slideLayouts/slideLayout2.xml','<x/>')
                z.writestr('ppt/media/',b'');z.writestr('ppt/media/new.jpg',b'new')  # WPS writes directory entries
            r=a.audit(p,1,'16:9',True)
            self.assertEqual((r['findings'],r['orphan_media'],r['duplicate_entries']),([],[],[]))
            self.assertEqual(r['unused_layouts'],['ppt/slideLayouts/slideLayout2.xml'])
            with zipfile.ZipFile(p,'a') as z:z.writestr('ppt/media/old.png',b'old')
            r=a.audit(p,1,'16:9',True)
            self.assertEqual(r['orphan_media'],['ppt/media/old.png'])
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                with zipfile.ZipFile(p,'a') as z:z.writestr('ppt/slides/slide1.xml','<x/>')
            r=a.audit(p,1,'16:9',True)
            self.assertEqual(r['duplicate_entries'],['ppt/slides/slide1.xml']);self.assertIn('Duplicate ZIP entries',r['findings'])
    def fixture(self,p,text,notes):
        with zipfile.ZipFile(p,'w') as z:
            z.writestr('ppt/presentation.xml','<p:presentation xmlns:p="'+a.NS['p']+'"><p:sldIdLst><p:sldId id="256"/></p:sldIdLst><p:sldSz cx="12192000" cy="6858000"/></p:presentation>')
            z.writestr('ppt/slides/slide1.xml','<p:sld xmlns:p="'+a.NS['p']+'" xmlns:a="'+a.NS['a']+'"><a:t>'+text+'</a:t></p:sld>')
            z.writestr('ppt/notesSlides/notesSlide1.xml','<p:notes xmlns:p="'+a.NS['p']+'" xmlns:a="'+a.NS['a']+'"><a:t>'+notes+'</a:t></p:notes>')


@unittest.skipUnless(shutil.which('ffmpeg') and shutil.which('ffprobe'),'FFmpeg/FFprobe not installed')
class VideoIntegration(unittest.TestCase):
    def test_short_page_capture_and_original_dimensions(self):
        try:import numpy
        except ImportError:self.skipTest('NumPy not installed')
        with tempfile.TemporaryDirectory() as tmp:
            tmp=Path(tmp);video=tmp/'synthetic.mkv'
            # Three artificial frames: long black, short white, long red. No user media.
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=320x240:r=2:d=2',
                            '-f','lavfi','-i','color=white:s=320x240:r=2:d=1',
                            '-f','lavfi','-i','color=red:s=320x240:r=2:d=2',
                            '-filter_complex','[0:v][1:v][2:v]concat=n=3:v=1:a=0[out]',
                            '-map','[out]','-c:v','ffv1',str(video)],check=True,timeout=30)
            i=v.probe(video);p=plan();p['sample_fps']=2;v.validate_plan(p,i)
            rows=v.scan_segment(video,p['segments'][0],p,i)
            self.assertEqual(len(rows),3)
            self.assertEqual([r['stable'] for r in rows],[True,False,True])
            self.assertTrue(all(r['keep'] is None for r in rows))
            # Ignoring the entire region suppresses differences but never edits captures.
            ignored=copy.deepcopy(p['segments'][0]);ignored['ignore_regions']=[[0,0,1,1]]
            self.assertEqual(len(v.scan_segment(video,ignored,p,i)),1)
            preview_selection=tmp/'preview-selection.json';v.save_new(preview_selection,dict(source=i,plan=p,candidates=rows))
            preview=v.capture(preview_selection,tmp/'preview',review_only=True)
            self.assertTrue(json.loads(preview.read_text())['review_only'])
            self.assertIsNone(json.loads(preview_selection.read_text())['candidates'][0]['keep'])
            for r in rows:r.update(keep=True,reason='synthetic full-frame color transition')
            sel=tmp/'selected.json';v.save_new(sel,dict(source=i,plan=p,candidates=rows))
            manifest=v.capture(sel,tmp/'captured');d=json.loads(manifest.read_text())
            self.assertEqual(len(d['decks']),1);self.assertEqual(len(d['decks'][0]['pages']),3)
            for page in d['decks'][0]['pages']:
                blob=(manifest.parent/page['frame']).read_bytes()
                self.assertEqual(struct.unpack('>II',blob[16:24]),(320,240))
            with self.assertRaises(FileExistsError):v.capture(sel,tmp/'captured')

if __name__=='__main__':unittest.main()
