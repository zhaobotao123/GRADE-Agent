"""Refit BOTH weight-dependent nuisance regressions within every BRR replicate.

The D nuisance fit is shared across PVs only when the sample, folds, X and
weights are identical. No residuals or fitted learners are reused across
different replicate weights. Results remain supplementary and conditional
on the frozen student folds. All planned replicates are retained.
"""
from common import *
import copy,traceback,gc
from sklearn.model_selection import KFold
from lightgbm import LGBMRegressor

def direct_reference(data,factor,pv,replicate):
 weight='W_FSTUWT'if replicate==0 else f'W_FSTURWT{replicate}'
 formal.pass_sample_weight_if_possible=strictfit
 design=json.loads((ROOT/'frozen_design.json').read_text(encoding='utf-8'))
 formal.dml_learner=lambda logger:(LGBMRegressor(**design['LGBM_parameters']),'LGBMRegressor')
 return formal.weighted_residualized_dml(data,pv,factor,[x for x in pool_columns()if x!=factor],weight,'CNTSCHID',None)

def factor_data(data,factor,pvs):
 valid=pd.to_numeric(data[factor],errors='coerce').notna()&data.W_FSTUWT.notna()&(data.W_FSTUWT>0)&data.CNTSCHID.notna()
 for pv in pvs:
  assert (valid&data[pv].notna()).equals(valid),'Cannot reuse D nuisance across different PV samples'
 for r in range(1,81):
  w=data[f'W_FSTURWT{r}'];assert np.isfinite(w[valid]).all()and(w[valid]>0).all()
 sub=data.loc[valid].copy();source_index=sub.index.to_numpy();sub=sub.reset_index(drop=True)
 return sub,source_index

def calculate(data,factor,replicate,design,cp):
 sub,source_index=factor_data(data,factor,design['PVs']);xcols=[x for x in pool_columns()if x!=factor]
 num,cat=u.infer_feature_types(sub,xcols);X=sub[xcols]
 y=sub[design['PVs']].to_numpy(float);d=sub[factor].to_numpy(float)
 weight='W_FSTUWT'if replicate==0 else f'W_FSTURWT{replicate}'
 w=sub[weight].to_numpy(float);school=sub.CNTSCHID.to_numpy()
 yh=np.full(y.shape,np.nan);dh=np.full(len(sub),np.nan);fold_ids=np.full(len(sub),-1,dtype=int)
 fits=0
 for fold,(tr,te)in enumerate(KFold(3,shuffle=True,random_state=42).split(X)):
  assert len(np.intersect1d(tr,te))==0
  # The original transformation is outcome- and weight-independent. Refitted
  # inside each replicate/fold, then shared for identical X nuisance targets.
  pre=u.build_preprocessor(num,cat,scale_numeric=True)
  xt=pre.fit_transform(X.iloc[tr]);xe=pre.transform(X.iloc[te]);fold_ids[te]=fold
  model=LGBMRegressor(**design['LGBM_parameters'])
  model.fit(xt,d[tr],sample_weight=w[tr]);dh[te]=model.predict(xe);fits+=1
  del model
  for j,pv in enumerate(design['PVs']):
   model=LGBMRegressor(**design['LGBM_parameters'])
   model.fit(xt,y[tr,j],sample_weight=w[tr]);yh[te,j]=model.predict(xe);fits+=1
   del model
  progress('replicate_fold_refitted',factor=factor,replicate=replicate,fold=fold+1,completed_nuisance_fits=fits,folds=3)
 assert np.isfinite(yh).all()and np.isfinite(dh).all()and(fold_ids>=0).all()and fits==33
 rows=[]
 for j,pv in enumerate(design['PVs']):
  r=residual_estimate(y[:,j],yh[:,j],d,dh,w,school)
  r.update(treatment=factor,plausible_value=pv,replicate=replicate,weight_column=weight,refitted_nuisance=True)
  rows.append(r)
 np.savez_compressed(cp.with_suffix('.npz'),source_index=source_index,school=school,fold=fold_ids,weight=w,y_hat=yh,d_hat=dh)
 obj=dict(treatment=factor,replicate=replicate,n=len(sub),sample_hash=hashlib.sha256(source_index.tobytes()).hexdigest(),weight_hash=hashlib.sha256(w.tobytes()).hexdigest(),fold_hash=hashlib.sha256(fold_ids.tobytes()).hexdigest(),strict_weighted_nuisance_fits=fits,rows=rows)
 save(cp,obj);gc.collect();return obj

def summarise(factor,records,design):
 assert len(records)==81 and sorted(r['replicate']for r in records)==list(range(81))
 assert len({r['sample_hash']for r in records})==1 and len({r['fold_hash']for r in records})==1
 df=pd.DataFrame([row for record in records for row in record['rows']]);rows=[]
 for pv,g in df.groupby('plausible_value'):
  base=g[g.replicate==0].iloc[0];rep=g[g.replicate>0]
  assert len(rep)==80
  variance=float(.05*np.sum((rep.coef-base.coef)**2))
  rows.append(dict(treatment=factor,plausible_value=pv,coef=float(base.coef),BRR_std_error=float(np.sqrt(variance)),BRR_variance=variance,original_cluster_std_error=float(base.std_error),n=int(base.n)))
 pvdf=pd.DataFrame(rows);pvdf.to_csv(ROOT/f'{factor}_BRR_by_pv.csv',index=False,encoding='utf-8-sig')
 df.to_csv(ROOT/f'{factor}_all_810_estimates.csv',index=False,encoding='utf-8-sig')
 out=pooled(rows,'BRR_std_error');out.update(treatment=factor,n=int(rows[0]['n']),replicates=80,all_10_PVs_complete=True,full_weighted_nuisance_refits=True,actual_nuisance_fits=sum(r['strict_weighted_nuisance_fits']for r in records),conditional_on_frozen_student_folds=True,not_claim_of_causal_identification=True)
 save(ROOT/f'{factor}_BRR_pooled.json',out)
 summaries=[json.loads(p.read_text(encoding='utf-8'))for p in ROOT.glob('*_BRR_pooled.json')]
 pd.DataFrame(summaries).to_csv(ROOT/'BRR_pooled_available_factors.csv',index=False,encoding='utf-8-sig')
 return out

def main():
 lock=exclusive('BRR');design,data=checked_inputs();checkpoint=ROOT/'BRR_checkpoints';checkpoint.mkdir(exist_ok=True)
 baseline=pd.read_csv('D:/pisa2022/outputs_grade_agent_formal/dml_results_by_pv.csv')
 total=len(design['factors'])*81;done=len(list(checkpoint.glob('*.json')))
 progress('running_full_refit_BRR',completed_replications=done,total_replications=total)
 for factor in design['factors']:
  records=[]
  for r in [0,1,80]+list(range(2,80)):
   cp=checkpoint/f'{factor}_rep{r:02d}.json'
   obj=json.loads(cp.read_text(encoding='utf-8'))if cp.exists()else calculate(data,factor,r,design,cp)
   if r==0:
    for row in obj['rows']:
     old=baseline[(baseline.treatment==factor)&(baseline.plausible_value==row['plausible_value'])].iloc[0]
     np.testing.assert_allclose([row['coef'],row['std_error'],row['n']],[old.coef,old.std_error,old.n],rtol=1e-8,atol=1e-8)
   # Independent pipeline path confirms transformed-X reuse is equivalent,
   # using an ordinary direct source-function refit for actual rep weights.
   gate=ROOT/f'gate_{factor}_rep{r:02d}.json'
   if factor==design['factors'][0]and r in [1,80]and not gate.exists():
    checks=[]
    for pv in ['PV1MATH','PV10MATH']:
     direct=direct_reference(data,factor,pv,r);row=next(x for x in obj['rows']if x['plausible_value']==pv)
     np.testing.assert_allclose([row['coef'],row['std_error'],row['n']],[direct['coef'],direct['std_error'],direct['n']],rtol=1e-8,atol=1e-8)
     checks.append(dict(pv=pv,direct_pipeline=direct,shared_X_estimate=row['coef'],passed=True))
    save(gate,dict(passed=True,checks=checks))
   records.append(obj)
   done=len(list(checkpoint.glob('*.json')))
   progress('replication_complete',factor=factor,replicate=r,completed_replications=done,total_replications=total)
  out=summarise(factor,records,design)
  progress('factor_complete',factor=factor,completed_replications=done,total_replications=total,pooled=out)
 checked_inputs();progress('all_five_factors_computed_awaiting_independent_audit',completed_replications=405,total_replications=405)
if __name__=='__main__':
 try:main()
 except Exception:
  save(ROOT/'failure_BRR.json',dict(error=traceback.format_exc(),time=time.strftime('%Y-%m-%d %H:%M:%S')));raise
