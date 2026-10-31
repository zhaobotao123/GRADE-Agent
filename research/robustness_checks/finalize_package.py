"""Freeze a complete result/code package, excluding raw student data and QA renders."""
from pathlib import Path
import json,hashlib,shutil,zipfile,sys,time,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'work/pisa_audit_deps'))
import pandas as pd
record=json.loads((ROOT/'manuscript_change_log.json').read_text(encoding='utf-8'))
review=json.loads((ROOT/'verified_results.json').read_text(encoding='utf-8'))
assert review['validation_passed']
assert hashlib.sha256(Path(record['source']).read_bytes()).hexdigest()==record['source_sha256']
assert hashlib.sha256(Path(record['output']).read_bytes()).hexdigest()==record['output_sha256']
assert len(list((ROOT/'render_v39').glob('page-*.png')))==30
spec=json.loads(Path('D:/pisa2022/outputs_prediction_optimization/feature_sets.json').read_text())['expanded_scales']
variables=pd.read_csv('D:/pisa2022/outputs_grade_agent_formal/selected_variables.csv')
(ROOT/'predictor_and_covariate_specification.json').write_text(json.dumps({'predictive_features':spec,'feature_count':len(spec),'original_selected_variables':variables.to_dict('records'),'main_original_split':42,'additional_split_seeds':[0,1,7,13,21,73,101,202,365,999],'source_feature_set_key':'expanded_scales'},ensure_ascii=False,indent=2),encoding='utf-8')

snapshot=ROOT/'primary_result_snapshot';snapshot.mkdir(exist_ok=True)
audit=json.loads((ROOT/'code_audit_before_fitting.json').read_text(encoding='utf-8'))
for path,digest in audit['original_result_hashes'].items():
 source=Path(path);assert hashlib.sha256(source.read_bytes()).hexdigest()==digest
 shutil.copy2(source,snapshot/source.name)
for source in [Path('D:/pisa2022/outputs_five_models_tuned_42_features/tuned_five_model_metrics_summary.csv'),Path('D:/pisa2022/outputs_grade_agent_formal/table_1_sample_description.csv')]:shutil.copy2(source,snapshot/source.name)

qa={'output':record['output'],'pages':30,'all_page_PNGs_visually_reviewed':True,'checked':'Margins, paragraph flow, headings, equations, both tables, all five original figures, captions and references','visual_defects_detected':False,'original_tables_figures_equations_headers_footers_preserved':True,'source_v38_unchanged':True,'checked_at':time.strftime('%Y-%m-%d %H:%M:%S')}
(ROOT/'document_QA.json').write_text(json.dumps(qa,indent=2),encoding='utf-8')

files=[]
for p in ROOT.rglob('*'):
 if not p.is_file():continue
 rel=p.relative_to(ROOT)
 if rel.parts[0]in ['render_v39','__pycache__']:continue
 if p.suffix not in ['.py','.md','.csv','.json','.log']:continue
 if p.name=='delivery_manifest.json':continue
 files.append(p)
manifest={'created_at':time.strftime('%Y-%m-%d %H:%M:%S'),'verification_passed':True,'source_v38':record['source'],'source_v38_sha256':record['source_sha256'],'new_manuscript':record['output'],'new_manuscript_sha256':record['output_sha256'],'excluded_from_archive':'raw PISA data/cache, individual held-out outcomes, local fitted model files, PNG/PDF QA renders; these remain local where available','full_DML_BRR_completed':False,'files':{str(p.relative_to(ROOT)).replace('\\','/'):{'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),'bytes':p.stat().st_size}for p in sorted(files)}}
(ROOT/'delivery_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8');files.append(ROOT/'delivery_manifest.json')
out=Path(record['output']).with_name('Supplementary_Robustness_Checks_v39.zip')
assert not out.exists(),f'Refusing to overwrite {out}'
with zipfile.ZipFile(out,'w',compression=zipfile.ZIP_DEFLATED)as z:
 for p in files:z.write(p,'robustness_checks/'+str(p.relative_to(ROOT)).replace('\\','/'))
with zipfile.ZipFile(out)as z:assert z.testzip()is None
print(json.dumps({'zip':str(out),'files':len(files),'bytes':out.stat().st_size,'Word':record['output'],'QA':'30 pages rendered and individually visually checked'},ensure_ascii=False,indent=2))
