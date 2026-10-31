from pathlib import Path
import sys,json,hashlib,shutil
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
sys.path.insert(0,str(BASE/'work/pisa_audit_deps'));sys.path.insert(0,str(BASE/'work/figure_python_deps'))
import numpy as np,pandas as pd
from docx import Document
data=pd.read_pickle(ROOT/'japan_analysis_data.pkl')
source=pd.read_csv('D:/pisa2022/outputs_grade_agent_formal/table_1_sample_description.csv')
print(source.head().to_string(index=False))
print('MATH_MEAN unweighted',data.MATH_MEAN.mean(),'weighted',np.average(data.MATH_MEAN,weights=data.W_FSTUWT))
desc=[]
for f in ['MATH_MEAN','ESCS','ANXMAT','MATHEF21','MATHEFF','TEACHSUP','BELONG','DISCLIM','HOMEPOS','ICTQUAL','ICTSCH','ICTENQ','BULLIED','AGE','PAREDINT','HISEI']:
 mask=data[f].notna();x=data.loc[mask,f].to_numpy();w=data.loc[mask,'W_FSTUWT'].to_numpy();mu=np.average(x,weights=w)
 desc.append(dict(variable=f,n=len(x),unweighted_mean=x.mean(),unweighted_sd=x.std(ddof=1),weighted_mean=mu,weighted_population_sd=np.sqrt(np.average((x-mu)**2,weights=w)),missing_percent=100*(1-mask.mean())))
pd.DataFrame(desc).to_csv(ROOT/'descriptive_weighting_audit.csv',index=False,encoding='utf-8-sig')
for p in Path('C:/Users/84130/Documents/Codex/2026-07-03/zhe/pisa_grade_agent_formal_experiment').glob('*.py'):
 dest=ROOT/'source_snapshot'/p.name;dest.parent.mkdir(exist_ok=True);shutil.copy2(p,dest)
summ=[]
raw=pd.read_csv('D:/pisa2022/outputs_five_models_tuned_42_features/tuned_five_model_metrics_by_pv.csv')
ref=pd.read_csv('D:/pisa2022/outputs_five_models_tuned_42_features/tuned_five_model_metrics_summary.csv')
for model,g in raw.groupby('model'):
 row=ref[ref.model==model].iloc[0]
 for metric in ['weighted_r2','weighted_rmse','weighted_mae']:
  np.testing.assert_allclose(g[metric].mean(),row[metric+'_mean'],atol=1e-12)
  np.testing.assert_allclose(g[metric].std(),row[metric+'_sd'],atol=1e-12)
 summ.append(dict(model=model,ten_PVs_aggregate_reproduced=True,refitted_in_this_script=False))
(ROOT/'five_model_saved_result_reproduction.json').write_text(json.dumps(summ,indent=2),encoding='utf-8')
print('All five saved-result aggregations independently verified; no model refits in this additional audit.')
