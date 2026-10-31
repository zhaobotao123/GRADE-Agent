"""Verify the other seven ORIGINAL factors; not additional sensitivity selection."""
from pathlib import Path
import os,sys,json,time
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='4';os.environ['MKL_NUM_THREADS']='1'
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
sys.path.insert(0,str(BASE/'work/pisa_audit_deps'));sys.path.insert(0,str(BASE/'work/figure_python_deps'))
SRC=Path('C:/Users/84130/Documents/Codex/2026-07-03/zhe/pisa_grade_agent_formal_experiment');sys.path.insert(0,str(SRC))
import numpy as np,pandas as pd,lightgbm as lgb
import config as c
import run_formal_pisa_experiment as formal
data=pd.read_pickle(ROOT/'japan_analysis_data.pkl')
pool=pd.read_csv('D:/pisa2022/outputs_grade_agent_formal/selected_variables.csv').query("role in ['treatment','control_or_covariate']").variable.tolist()
factors=[f for f in c.TREATMENT_CANDIDATES if f in pool and f not in ['MATHEFF','DISCLIM','TEACHSUP','BELONG','ICTSCH']]
(ROOT/'additional_baseline_design.json').write_text(json.dumps({'factors':factors,'purpose':'all remaining original factors without any filtering by estimates','before_fitting_utc':time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime())},indent=2),encoding='utf-8')
formal.dml_learner=lambda logger:(lgb.LGBMRegressor(**dict(c.LGBM_PARAMS,n_jobs=4)),'LGBMRegressor')
def strictfit(pipe,X,y,w):pipe.fit(X,y,model__sample_weight=w);return pipe
formal.pass_sample_weight_if_possible=strictfit
dest=ROOT/'dml_additional_baseline_by_pv.csv';rows=pd.read_csv(dest).to_dict('records') if dest.exists()else[]
ref=pd.read_csv('D:/pisa2022/outputs_grade_agent_formal/dml_results_by_pv.csv')
for factor in factors:
 for pv in c.PV_MATH_VARS:
  if any(r['treatment']==factor and r['plausible_value']==pv for r in rows):continue
  print('Additional original-factor reproduction',factor,pv,flush=True)
  r=formal.weighted_residualized_dml(data,pv,factor,[x for x in pool if x!=factor],'W_FSTUWT','CNTSCHID',None)
  old=ref[(ref.treatment==factor)&(ref.plausible_value==pv)].iloc[0]
  for key in ['coef','std_error','n']:np.testing.assert_allclose(r[key],old[key],rtol=1e-9,atol=1e-9,err_msg=f'{factor} {pv} {key}')
  rows.append(r);pd.DataFrame(rows).to_csv(dest,index=False,encoding='utf-8-sig')
print('All70 remaining original-factor PV rows reproduced.',flush=True)
