"""Read-only XLSX checks: blank ratings, stable IDs, and integer validation."""
import json
from pathlib import Path
from zipfile import ZipFile
import xml.etree.ElementTree as ET

OUT=Path(__file__).resolve().parents[1]/'outputs/grade_agent_flash_20261025'
NS={'x':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def main():
    results=[]
    for n in [1,2]:
        path=OUT/f'简化评分表_评分者{n}.xlsx'
        with ZipFile(path) as z:
            root=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
            strings=ET.fromstring(z.read('xl/sharedStrings.xml'))
            words=[''.join(e.itertext()) for e in strings.findall('x:si',NS)]
            cells={c.attrib['r']:c for c in root.findall('.//x:sheetData/x:row/x:c',NS)}
            for r in range(9,39):
                cell=cells[f'B{r}']
                value=cell.find('x:v',NS).text
                text=words[int(value)] if cell.attrib.get('t')=='s' else value
                assert text==f'R{r-8:03}'
                for col in 'DEF':
                    c=cells.get(f'{col}{r}')
                    assert c is None or (c.find('x:v',NS) is None and c.find('x:f',NS) is None)
            validations=root.findall('x:dataValidations/x:dataValidation',NS)
            assert any(v.attrib.get('type')=='whole' and v.attrib.get('sqref')=='D9:F38'
                and v.find('x:formula1',NS).text=='0' and v.find('x:formula2',NS).text=='2' for v in validations)
            alltext='\n'.join(words)
            assert all(code not in alltext for code in ['agent_full','llm_baseline','agent_critic_only','T01','T30'])
            if (OUT/'packet_index.json').exists():
                index=json.loads((OUT/'packet_index.json').read_text(encoding='utf-8'))
                expected=sum(r['status']=='completed' for r in index)
                assert float(cells['F6'].find('x:v',NS).text)==expected
                for row_num,item in enumerate(index,9):
                    if item['status']!='completed':
                        c=cells[f'G{row_num}']; v=c.find('x:v',NS).text
                        text=words[int(v)] if c.attrib.get('t')=='s' else v
                        assert text=='无报告，不评分'
        results.append({'file':str(path),'blank_rating_cells':90,'report_ids':30,'integer_validation':True,'condition_mapping_absent':True})
    print(json.dumps(results,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
