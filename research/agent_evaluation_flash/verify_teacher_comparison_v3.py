from pathlib import Path
import html,json,re,zipfile
from collections import Counter
import xml.etree.ElementTree as ET

BASE=Path('C:/Users/84130/Documents/Codex/2026-08-09/zh')
ROOT=BASE/'outputs/teacher_comparison_20261027_v3'
SOURCE=BASE/'outputs/teacher_summary_20261026_v2/研究者留存_不要发给老师/summaries'
INTERNAL=ROOT/'研究者留存_不要发给老师'
manifest=json.loads((INTERNAL/'manifest.json').read_text(encoding='utf-8'))
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
def get_cells(book):
    with zipfile.ZipFile(book) as z:
        strings=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            strings=[''.join(x.itertext()) for x in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('s:si',NS)]
        sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'));cells={}
        for c in sheet.findall('.//s:sheetData/s:row/s:c',NS):
            v=c.find('s:v',NS);value=v.text if v is not None else None
            if c.get('t')=='s' and value is not None:value=strings[int(value)]
            if c.get('t')=='inlineStr':value=''.join(c.find('s:is',NS).itertext())
            cells[c.attrib['r']]=value
        assert not sheet.findall('.//s:f',NS)
        assert len(sheet.findall('.//s:dataValidation',NS))==2
        return cells

packages=[]
for teacher in [1,2]:
    directory=ROOT/f'教师{teacher}';book=directory/f'五种配置回复对照评分_教师{teacher}.xlsx'
    cells=get_cells(book);order=manifest['teacher_orders'][str(teacher)]
    assert len(order)==60 and len({r['blind_id'] for r in order})==60
    assert Counter(r['caseId'] for r in order)=={f'H{i:02d}':5 for i in range(1,13)}
    page=(directory/'同案例五回复对照表.html').read_text(encoding='utf-8')
    assert len(re.findall(r'<table>',page))==1
    assert page.count('<tr data-blind-id=')==60 and page.count('<tr class="case"')==12
    assert re.findall(r'<tr data-blind-id="(B\d{3})">',page)==[r['blind_id'] for r in order]
    for i,r in enumerate(order,7):
        assert cells[f'A{i}']==r['caseId'] and cells[f'B{i}']==r['slot']+'（'+r['blind_id']+'）'
        a=json.loads((SOURCE/(r['blind_id']+'.json')).read_text(encoding='utf-8'))['reading_aid']
        expected='主要判断：'+a['main']['summary_zh']+'\n支持建议：'+a['advice']['summary_zh']+'\n边界表述：'+a['boundary']['summary_zh']
        assert cells[f'C{i}']==expected
        assert all(cells.get(f'{c}{i}') in (None,'') for c in 'DEFGH')
    for start in range(0,60,5):
        group=order[start:start+5];assert len({r['system'] for r in group})==5
    package=ROOT/f'教师{teacher}_五回复对照评分材料包.zip';assert not package.exists()
    with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as z:
        for p in [book,directory/'同案例五回复对照表.html',directory/'使用说明.txt']:z.write(p,p.name)
    with zipfile.ZipFile(package) as z:
        assert len(z.namelist())==3 and z.read(book.name)==book.read_bytes()
        assert not any('manifest' in name or 'mapping' in name for name in z.namelist())
    packages.append(str(package))
assert manifest['teacher_orders']['1']!=manifest['teacher_orders']['2']
result={'same_case_five_configurations_per_block':True,'one_continuous_60_reply_table_per_teacher':True,
    'chinese_aids_unchanged_from_checked_v2':True,'all_teacher_scores_and_comments_blank':True,
    'native_dropdowns_present':True,'no_score_formulas_or_fabricated_ratings':True,
    'two_independent_within_case_orders':True,'source_report_blind_ids_preserved':True,
    'packages_exclude_researcher_mapping_and_export_sidecars':True,'packages':packages}
(INTERNAL/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
