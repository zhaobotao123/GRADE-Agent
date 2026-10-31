from pathlib import Path
from zipfile import ZipFile
from lxml import etree

folder = Path('D:/Users/84130/Desktop/投稿/转投修改_20261022')
src = folder / 'GRADE-Agent_SEE_Teacher_Evaluation_v26.docx'
dst = folder / 'GRADE-Agent_SEE_Teacher_Evaluation_v27.docx'
ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
W = '{' + ns['w'] + '}'
with ZipFile(src) as z:
    root = etree.fromstring(z.read('word/document.xml'))
    original_text = root.xpath('//w:t/text()', namespaces=ns)
    active = False
    changed = []
    for p in root.findall('w:body/w:p', ns):
        text = ''.join(p.xpath('.//w:t/text()', namespaces=ns))
        if text.startswith('5. GRADE-Agent:'):
            active = True
        if text.startswith('6. Discussion'):
            active = False
        if not active or not text:
            continue
        pp = p.find(W+'pPr')
        style = pp.find(W+'pStyle') if pp is not None else None
        sid = style.get(W+'val', '') if style is not None else ''
        if sid not in ('', '1'):
            continue
        if text.startswith(('Figure 3.', 'Figure 4.', 'Figure 5.', 'Table 2.', 'Note.', '(a) Mean ratings')):
            continue
        if pp is None:
            pp = etree.Element(W+'pPr')
            p.insert(0, pp)
        ind = pp.find(W+'ind')
        if ind is None:
            ind = etree.SubElement(pp, W+'ind')
        for attr in ('hanging', 'hangingChars', 'firstLineChars'):
            ind.attrib.pop(W+attr, None)
        ind.set(W+'firstLine', '360')
        changed.append(text[:70])
    assert original_text == root.xpath('//w:t/text()', namespaces=ns)
    with ZipFile(dst, 'w') as out:
        for item in z.infolist():
            data = etree.tostring(root, xml_declaration=True, encoding='UTF-8', standalone=True) if item.filename == 'word/document.xml' else z.read(item.filename)
            out.writestr(item, data)
print('Updated body paragraphs:', len(changed))
print(dst)
