"""Re-fit the four other main prediction specifications on original seed42."""
from pathlib import Path
import os,sys,json,gc,warnings
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='2';os.environ['MKL_NUM_THREADS']='1'
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
def logwarning(message,category,filename,lineno,file=None,line=None):
 with (ROOT/'other_models_warnings.log').open('a',encoding='utf-8')as out:out.write(f'{category.__name__}: {message}\n')
warnings.showwarning=logwarning
sys.path.insert(0,str(BASE/'work/pisa_audit_deps'));sys.path.insert(0,str(BASE/'work/figure_python_deps'))
SRC=Path('C:/Users/84130/Documents/Codex/2026-07-03/zhe/pisa_grade_agent_formal_experiment');sys.path.insert(0,str(SRC))
import pandas as pd,numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from optimize_prediction_models import make_preprocessor
from tune_existing_five_models import build_model
import utils_pisa as u
data=pd.read_pickle(ROOT/'japan_analysis_data.pkl')
features=json.loads(Path('D:/pisa2022/outputs_prediction_optimization/feature_sets.json').read_text())['expanded_scales']
tr,te=train_test_split(np.arange(len(data)),test_size=.2,random_state=42)
prep=make_preprocessor(data.loc[tr],features);xt=prep.fit_transform(data.loc[tr,features]);xe=prep.transform(data.loc[te,features])
scaler=StandardScaler();xl=scaler.fit_transform(xt);el=scaler.transform(xe)
selected=pd.read_csv('D:/pisa2022/outputs_five_models_tuned_42_features/training_cv_selected_models.csv')
ref=pd.read_csv('D:/pisa2022/outputs_five_models_tuned_42_features/tuned_five_model_metrics_by_pv.csv')
dest=ROOT/'other_four_models_reproduced_by_pv.csv';rows=pd.read_csv(dest).to_dict('records')if dest.exists()else[]
for _,selection in selected.iterrows():
 name=selection.model
 if name=='LightGBM':continue
 for i in range(1,11):
  pv=f'PV{i}MATH'
  if any(r['model']==name and r['plausible_value']==pv for r in rows):continue
  print('Original prediction reproduction',name,pv,flush=True)
  model=build_model(name,json.loads(selection.params))
  if 'n_jobs' in model.get_params():model.set_params(n_jobs=1)
  x,z=(xl,el)if name in ['Ridge','ElasticNet']else(xt,xe)
  model.fit(x,data.loc[tr,pv],sample_weight=data.loc[tr,'W_FSTUWT'])
  p=model.predict(z);y=data.loc[te,pv].to_numpy();w=data.loc[te,'W_FSTUWT'].to_numpy()
  row=dict(model=name,plausible_value=pv,weighted_r2=u.weighted_r2(y,p,w),weighted_rmse=u.weighted_rmse(y,p,w),weighted_mae=u.weighted_mae(y,p,w))
  old=ref[(ref.model==name)&(ref.plausible_value==pv)].iloc[0]
  for key in ['weighted_r2','weighted_rmse','weighted_mae']:np.testing.assert_allclose(row[key],old[key],atol=1e-8,rtol=1e-8,err_msg=f'{name}/{pv}/{key}')
  np.savez_compressed(ROOT/f'predictions_original_{name}_{pv}.npz',test_index=te,observed=y,predicted=p,weight=w)
  rows.append(row);pd.DataFrame(rows).to_csv(dest,index=False,encoding='utf-8-sig')
  del model;gc.collect()
print('All40 other-model PV specifications reproduced.',flush=True)
