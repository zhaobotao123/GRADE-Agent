"""Read-only numerical review of completed checkpoints; never scores partial BRR."""
from common import *
from sklearn.model_selection import KFold
design,data=checked_inputs();records=[];auditrows=[]
for p in sorted((ROOT/'BRR_checkpoints').glob('*.json')):
 r=json.loads(p.read_text(encoding='utf-8'));z=np.load(p.with_suffix('.npz'),allow_pickle=False)
 ix=z['source_index'];sample=data.loc[ix];w=z['weight'];d=sample[r['treatment']].to_numpy(float);dr=d-z['d_hat']
 np.testing.assert_array_equal(z['school'],sample.CNTSCHID.to_numpy())
 wcol='W_FSTUWT'if r['replicate']==0 else f"W_FSTURWT{r['replicate']}"
 np.testing.assert_array_equal(w,sample[wcol].to_numpy(float))
 folds=np.full(len(ix),-1)
 for f,(_,te)in enumerate(KFold(3,shuffle=True,random_state=42).split(ix)):folds[te]=f
 np.testing.assert_array_equal(z['fold'],folds)
 assert np.isfinite(z['y_hat']).all()and np.isfinite(z['d_hat']).all()
 assert len(ix)==r['n']and r['strict_weighted_nuisance_fits']==33
 assert r['sample_hash']==hashlib.sha256(ix.tobytes()).hexdigest()
 assert r['weight_hash']==hashlib.sha256(w.tobytes()).hexdigest()
 assert r['fold_hash']==hashlib.sha256(folds.astype(int).tobytes()).hexdigest()
 den=np.dot(w,dr**2);y=sample[design['PVs']].to_numpy(float);yr=y-z['y_hat'];coefs=np.einsum('i,ij->j',w*dr,yr)/den
 _,groups=np.unique(z['school'],return_inverse=True);G=len(np.unique(groups))
 for j,pv in enumerate(design['PVs']):
  row=next(a for a in r['rows']if a['plausible_value']==pv)
  sc=np.bincount(groups,weights=w*dr*(yr[:,j]-coefs[j]*dr))
  se=np.sqrt(G/(G-1)*np.dot(sc,sc)/den**2)
  np.testing.assert_allclose([coefs[j],se],[row['coef'],row['std_error']],rtol=1e-10,atol=1e-10)
 records.append(r);auditrows.append(dict(factor=r['treatment'],replicate=r['replicate'],PV_rows_checked=10,passed=True))
pd.DataFrame(auditrows).to_csv(ROOT/'independent_checkpoint_audit.csv',index=False,encoding='utf-8-sig')
full=[]
for factor in design['factors']:
 rs=[r for r in records if r['treatment']==factor]
 if len(rs)!=81:continue
 assert sorted(r['replicate']for r in rs)==list(range(81))
 base=next(r for r in rs if r['replicate']==0)
 mu=np.array([a['coef']for a in base['rows']]);reps=np.array([[a['coef']for a in r['rows']]for r in rs if r['replicate']>0])
 within=float(np.mean(np.sum((reps-mu)**2,axis=0)*.05));between=float(np.var(mu,ddof=1));se=np.sqrt(within+1.1*between)
 prior=json.loads((ROOT/f'{factor}_BRR_pooled.json').read_text(encoding='utf-8'))
 np.testing.assert_allclose([mu.mean(),se,within,between],[prior['coef'],prior['std_error'],prior['within_variance'],prior['between_PV_variance']],atol=1e-12)
 full.append(factor)

rfpath=ROOT/'random_forest_by_pv.csv';comparisons=[]
if rfpath.exists():
 rf=pd.read_csv(rfpath)
 old=pd.read_csv(AUDIT/'dml_sensitivity_results.csv')
 for factor,g in rf.groupby('treatment'):
  if len(g)!=10:continue
  assert set(g.plausible_value)==set(design['PVs'])
  p=pooled(g.to_dict('records'));p.update(treatment=factor,model='RandomForest_300_leaf5_seed42',all_ten_PVs_complete=True);comparisons.append(p)
  for model in ['LightGBM','ExtraTrees']:
   a=old[(old.treatment==factor)&(old.model==model)].iloc[0]
   comparisons.append(dict(treatment=factor,model=model,coef=a.coef_pooled,std_error=a.std_error_pooled,ci_low=a.ci_low,ci_high=a.ci_high,p_value=a.p_value_pooled,all_ten_PVs_complete=True))
 if comparisons:pd.DataFrame(comparisons).to_csv(ROOT/'all_learners_completed_factor_comparison.csv',index=False,encoding='utf-8-sig')

save(ROOT/'independent_audit_status.json',dict(checked_replications=len(records),checked_PV_rows=len(records)*10,planned_replications=405,complete_BRR_factors=full,all_completed_checkpoints_passed=True,entire_plan_complete=len(records)==405 and len(full)==5,partial_BRR_p_values_reported=False,check_time=time.strftime('%Y-%m-%d %H:%M:%S')))
print(json.dumps({'replications_checked':len(records),'complete_BRR_factors':full,'complete_RF_factors':sorted({r['treatment']for r in comparisons})},ensure_ascii=False))
