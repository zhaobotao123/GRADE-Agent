from docx import Document
from pathlib import Path
d=Document('D:/Users/84130/Desktop/投稿/转投修改_20261022/GRADE-Agent_SEE_Positioning_Revised_v37.docx')
for i,p in enumerate(d.paragraphs):
 if 64<=i<=152: print(i, p.style.name, p.text)
print('SOURCE CODE CANDIDATES')
for p in Path('D:/pisa2022').glob('*.py'):
 if any(s in p.name.lower() for s in ['formal','grade','dml']):print(p)
