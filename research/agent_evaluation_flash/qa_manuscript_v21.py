from pathlib import Path
from PIL import Image,ImageOps,ImageDraw
from pypdf import PdfReader
from docx import Document
import json,re
BASE=Path(__file__).resolve().parents[1]
ROOT=BASE/'outputs/manuscript_teacher_evaluation_v21_20261027'
RENDER=ROOT/'qa/render_delivery'
pages=sorted(RENDER.glob('page-*.png'),key=lambda x:int(x.stem.split('-')[1]))
for start in range(0,len(pages),6):
 canvas=Image.new('RGB',(1350,1950),'#dddddd');draw=ImageDraw.Draw(canvas)
 for n,p in enumerate(pages[start:start+6]):
  im=Image.open(p).convert('RGB');im.thumbnail((665,610))
  x=(n%2)*675+(675-im.width)//2;y=(n//2)*650+25
  canvas.paste(im,(x,y));draw.text(((n%2)*675+15,(n//2)*650+5),p.stem,fill='black')
 canvas.save(ROOT/'qa'/f'montage_{start+1:02d}_{min(start+6,len(pages)):02d}.png')
pdf=PdfReader(RENDER/'GRADE-Agent_SEE_Teacher_Evaluation_v21.pdf')
audit=[]
for i,p in enumerate(pdf.pages):
 t=p.extract_text() or ''
 audit.append({'page':i+1,'chars':len(t),'start':t[:110],'end':t[-110:]})
(ROOT/'qa/pages.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(audit,ensure_ascii=False,indent=2))
