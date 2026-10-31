"""Replace Chapter 5 with the author's Markdown, retaining all source figures."""
from pathlib import Path
from copy import deepcopy
import re,json,hashlib
from docx import Document
from docx.shared import Pt, Inches
from docx.shape import InlineShape
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.table import Table

folder=Path('D:/Users/84130/Desktop/投稿/转投修改_20261022')
source=folder/'GRADE-Agent_SEE_Teacher_Evaluation_v24.docx'
target=folder/'GRADE-Agent_SEE_Teacher_Evaluation_v25.docx'
author=Path('C:/Users/84130/.codex/attachments/471bc57a-1fb9-4820-ae46-12be1eea79fe/已粘贴的文本.txt')
md=author.read_text(encoding='utf-8-sig')
d=Document(source);old=list(d.paragraphs)
start=next(p for p in old if p.text=='5. GRADE-Agent Design and Evaluation')
end=next(p for p in old if p.text=='6. Discussion')
a,b=old.index(start),old.index(end)
before=[p._p.xml for p in old[:a]];after=[p._p.xml for p in old[b:]]
media=[s._inline.xml for s in d.inline_shapes]
image_contents=[d.part.related_parts[s._inline.xpath('.//a:blip')[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')].blob for s in d.inline_shapes]
table=deepcopy(d.tables[1]._tbl)
table1=d.tables[0]._tbl.xml
bodypr=deepcopy(old[a+2]._p.pPr)
images={}
for n in (3,4,5):
 cap=next(p for p in old if p.text.startswith(f'Figure {n}.'))
 prev=cap._p.getprevious();assert prev.xpath('.//w:drawing')
 images[n]=deepcopy(prev)
# Modest layout scaling only; the original interface image itself is untouched.
ui=InlineShape(images[3].xpath('.//wp:inline')[0])
ratio=ui.height/ui.width;ui.width=Inches(5.2);ui.height=int(ui.width*ratio)
result_figure=InlineShape(images[5].xpath('.//wp:inline')[0])
ratio=result_figure.height/result_figure.width
result_figure.width=Inches(5.45);result_figure.height=int(result_figure.width*ratio)
node=start._p
while node is not end._p:
 nxt=node.getnext();node.getparent().remove(node);node=nxt

expected=[]
def add_text(s,style='Normal',caption=False,italic=False,bold=False):
 p=end.insert_paragraph_before('',style=style)
 if style.startswith('Heading'):
  props=start._p.pPr if style=='Heading 1' else old[a+1]._p.pPr
  if p._p.pPr is not None:p._p.remove(p._p.pPr)
  if props is not None:p._p.insert(0,deepcopy(props))
  p.alignment=WD_ALIGN_PARAGRAPH.LEFT
  p.paragraph_format.keep_with_next=True
 if style=='List Bullet':
  p.paragraph_format.space_before=Pt(0);p.paragraph_format.space_after=Pt(3)
  p.paragraph_format.line_spacing=1.15
 if style=='Normal':
  if p._p.pPr is not None:p._p.remove(p._p.pPr)
  if bodypr is not None:p._p.insert(0,deepcopy(bodypr))
  p.alignment=WD_ALIGN_PARAGRAPH.JUSTIFY
  p.paragraph_format.keep_with_next=False
  p.paragraph_format.keep_together=False
 if caption:
  p.paragraph_format.line_spacing=1.05
  p.paragraph_format.space_after=Pt(7)
  p.paragraph_format.keep_with_next=False
 # Keep author-supplied wording; only interpret Markdown emphasis.
 for i,part in enumerate(re.split(r'(\*\*.*?\*\*)',s)):
  if not part:continue
  strong=part.startswith('**') and part.endswith('**')
  r=p.add_run(part[2:-2] if strong else part)
  r.bold=bold or strong or style.startswith('Heading');r.italic=italic
  r.font.name='Times New Roman';r.font.size=Pt(10 if caption else 12)
 expected.append(p.text)
 return p

table_rows=None
for block in re.split(r'\n\s*\n',md.strip()):
 block=block.strip()
 if not block:continue
 if block.startswith('# '):add_text(block[2:],'Heading 1');continue
 if block.startswith('## '):add_text(block[3:],'Heading 2');continue
 if block.startswith('|'):
  table_rows=[]
  for line in block.splitlines():
   cells=[x.strip() for x in line.strip().strip('|').split('|')]
   if all(re.fullmatch(r':?-+:?',x) for x in cells):continue
   table_rows.append(cells)
  end._p.addprevious(table)
  t=Table(table,d._body)
  assert len(t.rows)==len(table_rows)
  for ri,(row,vals) in enumerate(zip(t.rows,table_rows)):
   assert len(vals)==len(row.cells)
   for ci,(cell,value) in enumerate(zip(row.cells,vals)):
    p=cell.paragraphs[0];p.clear()
    p.paragraph_format.keep_with_next=(ri<len(table_rows)-1)
    p.alignment=WD_ALIGN_PARAGRAPH.LEFT if ci==0 else WD_ALIGN_PARAGRAPH.CENTER
    r=p.add_run(value);r.font.name='Times New Roman';r.font.size=Pt(10);r.bold=(ri==0)
  continue
 if block.startswith('- '):
  for line in block.splitlines():add_text(line[2:],'List Bullet')
  continue
 if block.startswith('**') and block.endswith('**'):
  content=block[2:-2]
  fig=re.match(r'Figure ([345])\.',content)
  if fig:end._p.addprevious(images[int(fig.group(1))])
  p=add_text(content,caption=True,bold=True)
  if content.startswith('Table 2.'):p.paragraph_format.keep_with_next=True
  if content.startswith('Figure 5.'):p.paragraph_format.keep_with_next=True
  continue
 if block.startswith('*') and block.endswith('*'):
  add_text(block[1:-1],caption=True,italic=True);continue
 add_text(block)

new=list(d.paragraphs)
ns=next(p for p in new if p.text.startswith('5. GRADE-Agent:'))
ne=next(p for p in new if p.text=='6. Discussion')
assert before==[p._p.xml for p in new[:new.index(ns)]]
assert after==[p._p.xml for p in new[new.index(ne):]]
assert expected==[p.text for p in new[new.index(ns):new.index(ne)] if p.text]
assert image_contents==[d.part.related_parts[s._inline.xpath('.//a:blip')[0].get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')].blob for s in d.inline_shapes]
assert table1==d.tables[0]._tbl.xml
assert table_rows==[[c.text for c in r.cells] for r in d.tables[1].rows]
assert len(d.inline_shapes)==5
d.save(target)
qa=Path(__file__).resolve().parents[1]/'outputs/manuscript_chapter5_v25_20261027/qa'
qa.mkdir(parents=True,exist_ok=True)
(qa/'verification.json').write_text(json.dumps({'base':str(source),'output':str(target),'author_source':str(author),'author_sha256':hashlib.sha256(author.read_bytes()).hexdigest(),'author_chapter_and_captions_verbatim':True,'all_other_paragraphs_unchanged':True,'all_five_figures_unchanged':True,'table1_unchanged':True,'table2_matches_author':True,'paragraph_count':len(expected)},ensure_ascii=False,indent=2),encoding='utf-8')
print(target)
