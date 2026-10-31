from pathlib import Path
from PIL import Image,ImageDraw
from pypdf import PdfReader
import sys
root=Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).resolve().parents[1]/'outputs/manuscript_teacher_evaluation_v22_20261027/qa'
render=root/(sys.argv[2] if len(sys.argv)>2 else 'render')
pages=sorted(render.glob('page-*.png'),key=lambda x:int(x.stem.split('-')[1]))
for start in range(0,len(pages),6):
 canvas=Image.new('RGB',(1350,1950),'#ddd');draw=ImageDraw.Draw(canvas)
 for n,p in enumerate(pages[start:start+6]):
  im=Image.open(p).convert('RGB');im.thumbnail((665,610))
  canvas.paste(im,((n%2)*675+(675-im.width)//2,(n//2)*650+25))
  draw.text(((n%2)*675+15,(n//2)*650+5),p.stem,fill='black')
 canvas.save(root/f'montage_{start+1:02d}.png')
r=PdfReader(next(render.glob('*.pdf')))
print('pages',len(r.pages))
for i,p in enumerate(r.pages):
 t=p.extract_text() or ''
 if 'Table 2.' in t or '5.5 Teacher' in t:print('RESULT_PAGE',i+1)
