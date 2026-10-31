from pathlib import Path
from docx import Document
from docx.shape import InlineShape
from docx.shared import Inches,Pt
from docx.text.paragraph import Paragraph
import json
base=Path('D:/Users/84130/Desktop/投稿/转投修改_20261022')
source=base/'GRADE-Agent_SEE_Teacher_Evaluation_v25.docx'
target=base/'GRADE-Agent_SEE_Teacher_Evaluation_v26.docx'
d=Document(source)
alltext=sorted(p.text for p in d.paragraphs)
figures=[s._inline.xml for s in d.inline_shapes]
tables=[t._tbl.xml for t in d.tables]
methods=next(p for p in d.paragraphs if p.text=='3. Materials and Methods')
caption=next(p for p in d.paragraphs if p.text.startswith('Figure 1.'))
picture=caption._p.getprevious();assert picture.xpath('.//w:drawing')
methods._p.addprevious(picture);methods._p.addprevious(caption._p)
assert sorted(p.text for p in d.paragraphs)==alltext
assert figures==[s._inline.xml for s in d.inline_shapes]
assert tables==[t._tbl.xml for t in d.tables]
ps=list(d.paragraphs)
i=next(i for i,p in enumerate(ps) if p.text.startswith('Figure 1.'))
assert ps[i+1].text=='3. Materials and Methods'
assert ps[i-2].text.startswith('Figure 1 summarises')
# Fit the figure and caption below the first introduction without changing text
# or raster content. Only its physical display dimensions and caption spacing change.
shape=InlineShape(picture.xpath('.//wp:inline')[0]);ratio=shape.height/shape.width
shape.width=Inches(5.6);shape.height=int(shape.width*ratio)
ip=Paragraph(picture,d._body)
ip.paragraph_format.line_spacing=1;ip.paragraph_format.space_before=Pt(0);ip.paragraph_format.space_after=Pt(0)
caption.paragraph_format.line_spacing=1;caption.paragraph_format.space_before=Pt(3);caption.paragraph_format.space_after=Pt(6)
for r in caption.runs:r.font.size=Pt(10)
d.save(target)
qa=Path(__file__).resolve().parents[1]/'outputs/manuscript_chapter5_figure1_v26_20261027/qa'
qa.mkdir(parents=True,exist_ok=True)
(qa/'verification.json').write_text(json.dumps({'source':str(source),'output':str(target),'figure1_and_caption_moved':'End of Section 2, immediately after Figure 1 introduction and before Section 3 heading','all_wording_unchanged':True,'all_images_tables_unchanged':True},ensure_ascii=False,indent=2),encoding='utf-8')
print(target)
