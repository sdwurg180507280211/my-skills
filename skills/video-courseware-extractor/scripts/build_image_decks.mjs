// Draft-only screenshot decks. Resolve @oai/artifact-tool through the host runtime.
import fs from 'node:fs/promises';
import path from 'node:path';
import {Presentation, PresentationFile} from '@oai/artifact-tool';
const [manifestPath, outputDir] = process.argv.slice(2);
if (!manifestPath || !outputDir) throw new Error('Usage: node build_image_decks.mjs manifest.json NEW_DRAFT_DIR');
const manifest = JSON.parse(await fs.readFile(manifestPath,'utf8'));
if(manifest.review_only) throw new Error('Candidate previews are unreviewed; use a reviewed capture manifest');
if(manifest.schema_version !== 1 || !manifest.decks?.length) throw new Error('Expected capture manifest v1');
const names=new Set();
for(const d of manifest.decks){
 if(!d.pages?.length || !d.output_name?.endsWith('.pptx') || /[/\\\0]/u.test(d.output_name) || names.has(d.output_name.toLowerCase())) throw new Error('Invalid or duplicate output filename / empty deck');
 names.add(d.output_name.toLowerCase());
}
await fs.mkdir(outputDir, {recursive:false}); // refuse an existing output directory
for(const deck of manifest.decks){
 const [width,height]=deck.size || deck.pages[0].crop.slice(2);
 if(![width,height].every(v=>Number.isFinite(v)&&v>0)) throw new Error('Invalid canvas size');
 const p=Presentation.create({slideSize:{width,height}});
 for(const page of deck.pages){
  const [iw,ih]=page.frame_size, [x,y,w,h]=page.crop;
  if(![iw,ih,w,h].every(v=>Number.isFinite(v)&&v>0)||![x,y].every(v=>Number.isFinite(v)&&v>=0)||x+w>iw||y+h>ih) throw new Error('Invalid image crop');
  const slide=p.slides.add();slide.background.fill='#FFFFFF';
  const scale=Math.min(width/w,height/h),pw=w*scale,ph=h*scale;
  slide.images.add({blob:new Uint8Array(await fs.readFile(path.resolve(path.dirname(manifestPath),page.frame))),contentType:'image/png',
   alt:`课件第${page.page}页`,fit:'cover',position:{left:(width-pw)/2,top:(height-ph)/2,width:pw,height:ph},
   crop:{left:x/iw,top:y/ih,right:(iw-x-w)/iw,bottom:(ih-y-h)/ih}});
 }
 const target=path.join(outputDir,deck.output_name);
 await(await PresentationFile.exportPptx(p)).save(target);
 console.log(JSON.stringify({draft:target,pages:p.slides.items.length,size:[width,height],notes:'empty'}));
}
