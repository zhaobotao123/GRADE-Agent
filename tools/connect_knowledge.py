from pathlib import Path
import json,hashlib,zipfile,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
P=Path('C:/Users/84130/Documents/Codex/2026-07-03/zhe/gradeagent')
snapshot=ROOT/'outputs/GRADE-Agent_PreKnowledge_Runtime_20261030_complete.zip'
assert not snapshot.exists(), 'Do not replace frozen snapshot'
with zipfile.ZipFile(snapshot,'w',zipfile.ZIP_DEFLATED) as z:
 for folder in ['functions','src']:
  for f in (P/folder).rglob('*'):
   if f.is_file():z.writestr(str(f.relative_to(P)),f.read_bytes())
 z.writestr('README.txt','Original runtime before knowledge integration, 2026-10-30. Historical experiments retain their original meaning. These sources are not the new website runtime.')
original=(ROOT/'work/build_local_kb.py').read_text(encoding='utf-8-sig')
updated=original.replace('pisa-jpn-2022-v1','pisa-jpn-2022-v2').replace('GRADE-Agent_Local_Knowledge_v1.zip','GRADE-Agent_Local_Knowledge_v2.zip').replace('GRADE-Agent_Knowledge_v1.md','GRADE-Agent_Knowledge_v2.md')
old="alternatives={k:{r['treatment']:r for r in read(k)} for k in ['extra_trees','random_forest','brr']}"
new="""alternatives={}
for k in ['extra_trees','random_forest','brr']:
 rows=read(k)
 if k=='extra_trees':rows=[r for r in rows if r.get('model')=='ExtraTrees']
 assert len(rows)==5 and len({r['treatment'] for r in rows})==5, k
 alternatives[k]={r['treatment']:r for r in rows}
assert float(alternatives['extra_trees']['TEACHSUP']['p_value_pooled'])>.05
"""
assert old in updated;updated=updated.replace(old,new)
# Independent validation later checks every mapped field and model identity.
builder=ROOT/'work/build_local_kb_v2.py';builder.write_text(updated,encoding='utf-8')
subprocess.run([sys.executable,'-B','-X','utf8',str(builder)],check=True)
print('Original runtime archived; v2 generated with model-aware ExtraTrees mapping.')

