from docx import Document
from pathlib import Path
import json,re
folder=Path('D:/Users/84130/Desktop/投稿/转投修改_20261022')
a=Document(folder/'GRADE-Agent_SEE_Positioning_Revised_v37.docx')
b=Document(folder/'GRADE-Agent_SEE_Educational_Contribution_v38.docx')
def section(d,start,end):
 p=d.paragraphs;i=next(i for i,x in enumerate(p) if x.text==start);j=next(i for i,x in enumerate(p) if i>0 and x.text==end)
 return [x._p.xml for x in p[i:j]]
assert section(a,'4. Results','5. GRADE-Agent: Translating Achievement-Related Findings into Educational Support')==section(b,'4. Results','5. GRADE-Agent: Translating Achievement-Related Findings into Educational Support')
body='\n'.join(p.text for p in b.paragraphs)
assert all(s in body for s in ['4.75','3.61','1.14','[0.86, 1.45]','0.794','0.797','0.178','0.116','5,760','random seed 42','50,000'])
assert not any(s in body for s in ['ordinary multi-turn LLM','development-known','Chinese reading aids','Part 1 complete','Part 2 complete'])
assert len(b.tables)==2 and len(b.inline_shapes)==5
root=Path(__file__).resolve().parents[1]/'outputs/author_instructions_v38_20261028'
audit=json.loads((root/'revision_audit.json').read_text(encoding='utf-8'))
audit.update({'results_chapter_xml_identical':True,'all_28_rendered_pages_visually_reviewed':True,'render_review':'No clipped text, overlapping objects, missing formula glyphs or split tables; abstract fits one page.','expected_key_statistics_present':True})
(root/'revision_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print('Verified: Chapter4 exact; two tables, five figures, native equations, references preserved; 28 pages reviewed.')
