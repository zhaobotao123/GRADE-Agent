"""Read-only verification of teaching materials; package selected files only."""
from pathlib import Path
from collections import Counter
import hashlib,html,json,re,zipfile
import xml.etree.ElementTree as ET

BASE=Path('C:/Users/84130/Documents/Codex/2026-08-09/zh')
ROOT=BASE/'outputs/teacher_evaluation_20261026_v1'
INTERNAL=ROOT/'研究者留存_不要发给老师'
NS={'s':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
mapping=json.loads((INTERNAL/'anonymous_mapping_DO_NOT_SHARE.json').read_text(encoding='utf-8'))
original=json.loads(Path('D:/pisa2022/outputs_grade_agent_deepseek41flash300_20261026/raw_reports.json').read_text(encoding='utf-8'))
reports={(r['system'],r['caseId'],r['repeat']):r['report'] for r in original}
by_id={r['blind_id']:r for r in mapping}
assert len(mapping)==60 and len(by_id)==60
assert Counter(r['system'] for r in mapping)=={s:12 for s in {r['system'] for r in mapping}}
assert len({(r['caseId'],r['system']) for r in mapping})==60

def cells(book):
    with zipfile.ZipFile(book) as z:
        shared=[]
        if 'xl/sharedStrings.xml' in z.namelist():
            root=ET.fromstring(z.read('xl/sharedStrings.xml'))
            shared=[''.join(n.itertext()) for n in root.findall('s:si',NS)]
        sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
        result={}
        for c in sheet.findall('.//s:sheetData/s:row/s:c',NS):
            v=c.find('s:v',NS);value=v.text if v is not None else None
            if c.get('t')=='s' and value is not None:value=shared[int(value)]
            elif c.get('t')=='inlineStr':value=''.join(c.find('s:is',NS).itertext())
            result[c.attrib['r']]=value
        assert not sheet.findall('.//s:f',NS),'Unrequested scoring formulas'
        assert sheet.findall('.//s:dataValidation',NS),'Missing dropdown validation'
        return result

orders=[];packages=[]
for teacher in [1,2]:
    ad=ROOT/'先发_阶段A'/f'教师{teacher}'
    bd=ROOT/'确认A后再发_阶段B'/f'教师{teacher}'
    af=ad/f'阶段A_参考标注_教师{teacher}.xlsx'
    bf=bd/f'阶段B_报告评分_教师{teacher}.xlsx'
    ac=cells(af);bc=cells(bf)
    assert [ac[f'A{i}'] for i in range(7,19)]==[f'H{i:02d}' for i in range(1,13)]
    assert all(ac.get(f'{c}{r}') in (None,'') for r in range(7,19) for c in 'BCDE')
    assert all(bc.get(f'{c}{r}') in (None,'') for r in range(7,67) for c in 'CDEFGH')
    order=[bc[f'A{i}'] for i in range(7,67)];orders.append(order)
    assert set(order)==set(by_id)
    assert all(bc[f'B{i}']==by_id[bc[f'A{i}']]['caseId'].split('_')[0] for i in range(7,67))
    page=(bd/'60匿名报告.html').read_text(encoding='utf-8')
    raw_texts=re.findall(r'<article id="(B\d{3})"[^>]*>.*?<pre class="report" lang="en">(.*?)</pre></article>',page,re.S)
    assert len(raw_texts)==60
    for blind_id,encoded in raw_texts:
        m=by_id[blind_id];text=html.unescape(encoded)
        assert text==reports[m['system'],m['caseId'],m['repeat']]
        assert hashlib.sha256(text.encode()).hexdigest()==m['source_report_sha256']
    assert 'expectedConstraints' not in (ad/'12案例材料.html').read_text(encoding='utf-8')
    for label,directory,files in [
        ('阶段A',ad,[af,ad/'12案例材料.html']),
        ('阶段B',bd,[bf,bd/'60匿名报告.html'])]:
        target=ROOT/f'{label}_教师{teacher}_材料包.zip'
        assert not target.exists(),'Refusing to overwrite existing delivery package'
        with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED) as z:
            for p in files:z.write(p,p.name)
        with zipfile.ZipFile(target) as z:assert len(z.namelist())==2
        packages.append(str(target))
assert orders[0]!=orders[1]
result={'source_reports_unchanged_in_both_html_packets':True,'balanced_case_configuration_sample':True,
    'both_teachers_same_60_reports_different_order':True,'all_teacher_inputs_blank':True,
    'no_automatic_scores_or_formulas':True,'dropdowns_present':True,'packages_exclude_researcher_mapping_and_sidecars':True,
    'sample_size':60,'teacher_count':2,'packages':packages}
(INTERNAL/'verification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(result,ensure_ascii=False,indent=2))
