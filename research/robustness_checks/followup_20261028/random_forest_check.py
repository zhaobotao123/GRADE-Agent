from common import *
import traceback
from sklearn.ensemble import RandomForestRegressor

def main():
 lock=exclusive('RF');design,data=checked_inputs();pool=pool_columns()
 formal.pass_sample_weight_if_possible=strictfit
 formal.dml_learner=lambda logger:(RandomForestRegressor(**design['RF_parameters']),'RandomForestRegressor')
 dest=ROOT/'random_forest_by_pv.csv';rows=pd.read_csv(dest).to_dict('records')if dest.exists()else[]
 for factor in design['factors']:
  for pv in design['PVs']:
   if any(r['treatment']==factor and r['plausible_value']==pv for r in rows):continue
   progress('RF_fixed_specification',worker='RF',factor=factor,pv=pv,completed=len(rows),total=50)
   r=formal.weighted_residualized_dml(data,pv,factor,[x for x in pool if x!=factor],'W_FSTUWT','CNTSCHID',None)
   r['learner']='RandomForest_300_leaf5_seed42';rows.append(r)
   pd.DataFrame(rows).to_csv(dest,index=False,encoding='utf-8-sig')
 summaries=[]
 for factor,g in pd.DataFrame(rows).groupby('treatment'):
  assert len(g)==10
  p=pooled(g.to_dict('records'));p['treatment']=factor;p['all_PVs_same_sign']=bool((np.sign(g.coef)==np.sign(p['coef'])).all());p['n']=int(g.n.iloc[0]);summaries.append(p)
 pd.DataFrame(summaries).to_csv(ROOT/'random_forest_pooled.csv',index=False,encoding='utf-8-sig')
 checked_inputs();progress('complete',worker='RF',completed=50,total=50)
if __name__=='__main__':
 try:main()
 except Exception:
  save(ROOT/'failure_RF.json',dict(error=traceback.format_exc(),time=time.strftime('%Y-%m-%d %H:%M:%S')));raise

