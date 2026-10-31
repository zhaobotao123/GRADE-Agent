"""Read-only XLSX verification and explicit-whitelist teacher packages."""
import json,hashlib,zipfile,xml.etree.ElementTree as ET
from pathlib import Path
ROOT=Path('C:/Users/84130/Documents/Codex/2026-08-09/zh/outputs/teacher_comparison_english_v2_20261027')
SOURCE=Path('D:/pisa2022/outputs_grade_agent_english_comparison_v2_20261027')
ns={'m':'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
mapping=json.loads((ROOT/'internal/blinding_key_DO_NOT_SEND.json').read_text(encoding='utf-8'))['mapping']
original={r['job']['id']:r for r in json.loads((SOURCE/'final_replies.json').read_text(encoding='utf-8'))}
checks=[]
for teacher in (1,2):
 folder=ROOT/f'教师{teacher}';file=folder/f'教师{teacher}_英文匿名对照评分表.xlsx'
 with zipfile.ZipFile(file) as z:
  strings=[]
  if 'xl/sharedStrings.xml' in z.namelist():
   strings=[''.join(t.text or '' for t in e.findall('.//m:t',ns)) for e in ET.fromstring(z.read('xl/sharedStrings.xml')).findall('m:si',ns)]
  sheet=ET.fromstring(z.read('xl/worksheets/sheet1.xml'))
  cells={c.attrib['r']:c for c in sheet.findall('.//m:sheetData/m:row/m:c',ns)}
  def value(address):
   c=cells.get(address)
   if c is None:return None
   if c.attrib.get('t')=='inlineStr':return ''.join(t.text or '' for t in c.findall('.//m:t',ns))
   v=c.find('m:v',ns)
   if v is None:return None
   return strings[int(v.text)] if c.attrib.get('t')=='s' else v.text
  group=[m for m in mapping if m['teacher']==teacher]
  assert len(group)==120 and len({m['source_job'] for m in group})==120
  for item in group:
   row=item['excel_row'];reply=value(f'D{row}')
   assert value(f'A{row}')==item['pair_id'] and value(f'B{row}')==item['reply_id']
   assert reply==original[item['source_job']]['final_reply']
   assert hashlib.sha256(reply.encode()).hexdigest()==item['reply_sha256']
   assert all(value(f'{col}{row}') in (None,'') for col in 'EFGH')
  assert not any(c.find('m:f',ns) is not None for c in cells.values())
  validation=sheet.find('m:dataValidations/m:dataValidation',ns)
  assert validation is not None and validation.attrib.get('sqref')=='E6:H125'
  assert validation.find('m:formula1',ns).text=='1' and validation.find('m:formula2',ns).text=='5'
  workbook=ET.fromstring(z.read('xl/workbook.xml'))
  sheets=[s.attrib['name'] for s in workbook.findall('m:sheets/m:sheet',ns)]
  assert sheets==['对照评分','评分说明']
  assert all(s.attrib.get('state','visible')=='visible' for s in workbook.findall('m:sheets/m:sheet',ns))
  pane=sheet.find('m:sheetViews/m:sheetView/m:pane',ns)
  package=ROOT/f'教师{teacher}_英文对照评分材料包.zip'
  with zipfile.ZipFile(package,'w',zipfile.ZIP_DEFLATED) as out:
   for p in [file,folder/f'教师{teacher}_英文回复对照阅读.html']:out.write(p,p.name)
  with zipfile.ZipFile(package) as out:assert len(out.namelist())==2 and not any('internal' in n or 'key' in n for n in out.namelist())
  checks.append({'teacher':teacher,'exact_original_reply_matches':120,'blank_score_cells':480,'validation_range':'E6:H125','no_hidden_identity_sheets':True,'pane':pane.attrib if pane is not None else None,'package_files':2})
(ROOT/'qa/saved_xlsx_verification.json').write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(checks,ensure_ascii=False))
