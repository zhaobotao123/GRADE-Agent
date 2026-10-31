from pathlib import Path
import json,hashlib,zipfile,re
BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'outputs/manuscript_teacher_evaluation_v21_20261027'
SOURCE=Path('D:/pisa2022/outputs_grade_agent_english_comparison_v2_20261027')
DEST=Path('D:/Users/84130/Desktop/投稿/转投修改_20261022/Supplementary_Evaluation_Materials_v21.zip')
items={}
lock=json.loads((SOURCE/'protocol_lock.json').read_text(encoding='utf-8'))
hashes=lock['plan']['source_hashes'];lock['plan']['source_hashes']={Path(k).name:v for k,v in hashes.items()}
items['protocol_lock.json']=json.dumps(lock,ensure_ascii=False,indent=2).encode()
for name in ['final_replies.json','execution_order.json']:
 items[name]=(SOURCE/name).read_bytes()
for name in ['results.json','results_summary.csv','teacher_scores_long.csv','individual_rater_summary.csv','case_level_source_data.csv']:
 items[name]=(OUT/name).read_bytes()
for p in (SOURCE/'conversations').rglob('*.json'):
 items['raw/'+str(p.relative_to(SOURCE)).replace('\\','/')]=p.read_bytes()
for p,h in hashes.items():
 path=Path(p)
 if path.suffix in ('.py','.mjs','.js'):
  data=path.read_bytes();assert hashlib.sha256(data).hexdigest()==h,'Frozen source hash changed'
  items['generation_source/'+path.name]=data
for p in (OUT/'figures').glob('*'):
 if p.suffix in ('.png','.pdf','.svg'):items['figures/'+p.name]=p.read_bytes()
items['analysis/finalize_teacher_results_v21.py']=(BASE/'agent_evaluation_flash/finalize_teacher_results_v21.py').read_bytes()
items['README.md']=b'''# Supplementary Evaluation Materials

This archive accompanies the revised conversational evaluation, not the earlier five-configuration report benchmark.

## Design
12 development-known synthetic cases x 2 systems x 5 generations = 120 conversations. Both systems received four fixed English user turns and used the deepseek-flash API alias with matched generation settings. The final task requested an approximately 80-140-word natural paragraph. All original final replies and intermediate API records are retained. API credentials and teacher identities are not included.

Two independent blinded teachers rated every original final reply on four anchored 1-5 dimensions. The primary outcome is suggestion appropriateness and actionability. Chinese translations were supplied as reading aids; instructions referred to original English replies. The final confirmed ratings, including Teacher 1's independent review, are frozen in teacher_scores_long.csv. Earlier raw revisions of the rating workbooks are not reconstructable from summary statistics and are not presented as preserved here.

## Files
- protocol_lock.json: frozen protocol, prompts, cases, rubric, source hashes (paths shortened for anonymity).
- final_replies.json: all 120 original final replies.
- raw/conversations: original conversations and request/response records; API headers were never logged.
- teacher_scores_long.csv: 240 teacher-by-reply rows, matched to original source jobs; no composite score.
- case_level_source_data.csv, results_summary.csv, individual_rater_summary.csv, results.json: derived analyses.
- generation_source: hash-matched generation and application source files. Paths in the execution scripts describe the original environment; adapt paths before generation. No new API generation is needed to reproduce the reported statistics.
- analysis/reproduce_statistics.py: portable statistical reproduction from the CSV; Python 3, numpy.
- analysis/finalize_teacher_results_v21.py: original analysis and plotting script, including the full figure definitions; its input paths refer to the original project layout.
- figures: PNG, PDF, SVG versions of the updated framework, comparison protocol, and teacher results.

## Analysis
Average two teachers within reply, then five runs within case and system. Compute 12 paired case differences. Percentile intervals use 50,000 paired case-cluster bootstrap draws, seed 20261027, and are conditional on two fixed teachers. Secondary intervals are exploratory and unadjusted. Quadratic-weighted Cohen kappa is calculated across 120 matched replies, separately for each criterion.

This comparison evaluates complete applications. It does not isolate a DML component effect, demonstrate unseen-case performance, establish real-student diagnostic accuracy, or show educational outcome gains. Teacher recruitment/background and applicable ethics/consent arrangements must be verified by the authors before submission. The archive is prepared locally; it has not been uploaded to a journal or repository.
'''
items['analysis/reproduce_statistics.py']=b'''import csv,json
from pathlib import Path
import numpy as np
root=Path(__file__).resolve().parents[1]
with (root/'teacher_scores_long.csv').open(encoding='utf-8-sig') as f: rows=list(csv.DictReader(f))
dims=['Contextual relevance','Consistency with case facts','Appropriateness and actionability','Clarity']
cases=sorted({r['case_id'] for r in rows});systems=['ordinary_llm','grade_agent']
cube=np.array([[[np.mean([float(r[d]) for r in rows if r['case_id']==c and r['system']==s]) for d in dims] for s in systems] for c in cases])
delta=cube[:,1]-cube[:,0]
draws=np.random.default_rng(20261027).integers(0,12,size=(50000,12))
ci=np.quantile(delta[draws].mean(axis=1),[.025,.975],axis=0)
keys=sorted({r['source_job'] for r in rows});matched={(r['teacher'],r['source_job']):r for r in rows}
output=[]
for j,d in enumerate(dims):
 obs=np.zeros((5,5))
 for k in keys:obs[int(matched['1',k][d])-1,int(matched['2',k][d])-1]+=1
 expected=np.outer(obs.sum(axis=1),obs.sum(axis=0))/120
 weights=(np.arange(5)[:,None]-np.arange(5)[None,:])**2
 output.append(dict(dimension=d,ordinary_mean=float(cube[:,0,j].mean()),agent_mean=float(cube[:,1,j].mean()),paired_difference=float(delta[:,j].mean()),ci_low=float(ci[0,j]),ci_high=float(ci[1,j]),quadratic_weighted_kappa=float(1-(weights*obs).sum()/(weights*expected).sum())))
print(json.dumps(output,indent=2))
'''
# Reject secret-like literals in text files. Environment variable names are allowed.
for name,data in items.items():
 if name.endswith(('.json','.csv','.py','.mjs','.js','.md','.svg')):
  assert not re.search(rb'sk-[A-Za-z0-9]{20,}',data),f'Secret-like value in {name}'
manifest={k:hashlib.sha256(v).hexdigest() for k,v in items.items()}
items['SHA256SUMS.json']=json.dumps(manifest,indent=2).encode()
with zipfile.ZipFile(DEST,'w',zipfile.ZIP_DEFLATED) as z:
 for name,data in items.items():z.writestr(name,data)
print(f'{DEST}: {len(items)} files, {DEST.stat().st_size} bytes')
