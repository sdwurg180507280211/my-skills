"""Optional host-runtime smoke test; uses only a generated FFmpeg test pattern."""
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as E
import zipfile

ROOT=Path(__file__).resolve().parents[1]
NODE=os.getenv('RUNTIME_NODE')
MODULES=os.getenv('RUNTIME_NODE_MODULES')

@unittest.skipUnless(NODE and MODULES and shutil.which('ffmpeg'),'Set discovered RUNTIME_NODE and RUNTIME_NODE_MODULES to run PPT smoke test')
class ArtifactSmoke(unittest.TestCase):
    def test_crop_export_import_and_render(self):
        with tempfile.TemporaryDirectory(prefix='courseware-smoke-') as tmp:
            w=Path(tmp)
            subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc=size=640x480:rate=1','-frames:v','1',str(w/'frame.png')],check=True,timeout=30)
            manifest={'schema_version':1,'decks':[{'speaker':'Synthetic','output_name':'synthetic.pptx','size':[1280,720],
                      'pages':[{'page':1,'frame':'frame.png','frame_size':[640,480],'crop':[80,60,480,360]}]}]}
            (w/'manifest.json').write_text(json.dumps(manifest))
            shutil.copyfile(ROOT/'scripts/build_image_decks.mjs',w/'build.mjs')
            (w/'node_modules').symlink_to(Path(MODULES).resolve(),target_is_directory=True)
            subprocess.run([NODE,'build.mjs','manifest.json','draft'],cwd=w,check=True,capture_output=True,timeout=120)
            with zipfile.ZipFile(w/'draft/synthetic.pptx') as z:
                ns={'a':'http://schemas.openxmlformats.org/drawingml/2006/main','p':'http://schemas.openxmlformats.org/presentationml/2006/main'}
                slide=E.fromstring(z.read('ppt/slides/slide1.xml'))
                crop=slide.find('.//a:srcRect',ns)
                self.assertEqual([int(crop.get(k)) for k in ['l','t','r','b']],[12500]*4)
                xf=slide.find('.//p:pic/p:spPr/a:xfrm',ns);ext=xf.find('a:ext',ns);off=xf.find('a:off',ns)
                self.assertAlmostEqual(int(ext.get('cx'))/int(ext.get('cy')),4/3)
                self.assertEqual(int(off.get('x')),160*9525)
                for n in z.namelist():
                    if n.startswith('ppt/notesSlides/notesSlide') and n.endswith('.xml'):
                        self.assertFalse(any(t.text for t in E.fromstring(z.read(n)).findall('.//a:t',ns)))
            (w/'render.mjs').write_text("import fs from 'node:fs/promises';import {PresentationFile,FileBlob} from '@oai/artifact-tool';const p=await PresentationFile.importPptx(await FileBlob.load('draft/synthetic.pptx'));if(p.slides.items.length!==1)throw Error('count');const b=await p.export({slide:p.slides.items[0],format:'png',scale:1});await fs.writeFile('render.png',new Uint8Array(await b.arrayBuffer()));")
            subprocess.run([NODE,'render.mjs'],cwd=w,check=True,capture_output=True,timeout=120)
            self.assertEqual(struct.unpack('>II',(w/'render.png').read_bytes()[16:24]),(1280,720))
            result=subprocess.run([NODE,'build.mjs','manifest.json','draft'],cwd=w,capture_output=True,timeout=30)
            self.assertNotEqual(result.returncode,0)

if __name__=='__main__':unittest.main()
