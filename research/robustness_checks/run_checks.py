"""Frozen, resumable supplementary checks. Original files are read-only.
Run with bundled Python; explicit output records are checkpointed after every PV.
"""
from pathlib import Path
import os,sys,json,time,hashlib,logging,ast,copy,itertools,traceback
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='4';os.environ['MKL_NUM_THREADS']='1'
sys.path.insert(0,str(BASE/'work/pisa_audit_deps'));sys.path.insert(0,str(BASE/'work/figure_python_deps'))
SRC=Path('C:/Users/84130/Documents/Codex/2026-07-03/zhe/pisa_grade_agent_formal_experiment')
sys.path.insert(0,str(SRC))
import numpy as np,pandas as pd,pyreadstat,lightgbm as lgb,shap
from scipy.stats import spearmanr,norm
from sklearn.model_selection import train_test_split,KFold
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import ExtraTreesRegressor
from sklearn.metrics import cohen_kappa_score
import config as c
import utils_pisa as u
from optimize_prediction_models import make_preprocessor,select_features
import run_formal_pisa_experiment as formal
import tune_existing_five_models as tuned
from recompute_final_shap import original_feature

logging.basicConfig(level=logging.INFO,format='%(asctime)s %(message)s',handlers=[logging.FileHandler(ROOT/'run.log',encoding='utf-8'),logging.StreamHandler(sys.stdout)])
log=logging.getLogger('robustness')
def save(name,obj):
 (ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
def csvout(name,rows):pd.DataFrame(rows).to_csv(ROOT/name,index=False,encoding='utf-8-sig')
def readrows(name):
 p=ROOT/name
 return pd.read_csv(p).to_dict('records')if p.exists()else[]
def status(stage,**kw):
 save('status.json',dict(stage=stage,updated=time.strftime('%Y-%m-%d %H:%M:%S'),**kw));log.info('%s %s',stage,kw)
def load_data():
 cache=ROOT/'japan_analysis_data.pkl'
 if cache.exists():return pd.read_pickle(cache)
 path=Path(c.DATA_PATH)
 _,meta=pyreadstat.read_sav(str(path),metadataonly=True)
 features,_=select_features(meta)
 usecols=sorted(set(features+c.TREATMENT_CANDIDATES+c.CONTROL_CANDIDATES+c.PV_MATH_VARS+['W_FSTUWT']+[f'W_FSTURWT{i}'for i in range(1,81)]))
 usecols=[x for x in usecols if x in meta.column_names]
 status('read_raw_country_column')
 country,_=pyreadstat.read_sav(str(path),usecols=['CNT'],apply_value_formats=False,user_missing=False)
 ix=np.flatnonzero(country.CNT.to_numpy()=='JPN');first,last=int(ix.min()),int(ix.max());del country
 data,_=pyreadstat.read_sav(str(path),usecols=usecols,row_offset=first,row_limit=last-first+1,apply_value_formats=False,user_missing=False)
 data=data[(data.CNT=='JPN')&data.W_FSTUWT.notna()&(data.W_FSTUWT>0)].reset_index(drop=True)
 data['MATH_MEAN']=data[c.PV_MATH_VARS].mean(axis=1)
 assert len(data)==5760 and data.CNTSCHID.nunique()==182 and not data[c.PV_MATH_VARS].isna().any().any()
 data.to_pickle(cache)
 save('sample_audit.json',{'source':str(path),'source_bytes':path.stat().st_size,'source_modified_ns':path.stat().st_mtime_ns,'source_row_start':first,'source_row_end':last,'n':len(data),'schools':data.CNTSCHID.nunique(),'CNT_unique':data.CNT.unique().tolist(),'PVs_complete':True,'replicate_weights':[f'W_FSTURWT{i}'for i in range(1,81)],'all_replicates_finite_positive':bool(np.isfinite(data[[f'W_FSTURWT{i}'for i in range(1,81)]]).all().all()and(data[[f'W_FSTURWT{i}'for i in range(1,81)]]>0).all().all())})
 return data

def teacher_check():
 df=pd.read_csv(BASE/'outputs/manuscript_teacher_evaluation_v21_20261027/teacher_scores_long.csv')
 dims=['Contextual relevance','Consistency with case facts','Appropriateness and actionability','Clarity']
 assert len(df)==240 and len(df.source_job.unique())==120
 means=df.groupby(['case_id','system'])[dims].mean()
 cases=sorted(df.case_id.unique());systems=['ordinary_llm','grade_agent']
 cube=np.array([[means.loc[(case,s),dims].to_numpy(float) for s in systems]for case in cases])
 delta=cube[:,1]-cube[:,0];rng=np.random.default_rng(42);draws=rng.integers(0,12,size=(50000,12));ci=np.quantile(delta[draws].mean(axis=1),[.025,.975],axis=0)
 results=[]
 for j,dim in enumerate(dims):
  x=df.pivot(index='source_job',columns='teacher',values=dim)
  k=cohen_kappa_score(x.iloc[:,0],x.iloc[:,1],weights='quadratic')
  results.append({'dimension':dim,'ordinary_mean':cube[:,0,j].mean(),'agent_mean':cube[:,1,j].mean(),'paired_difference':delta[:,j].mean(),'ci_low':ci[0,j],'ci_high':ci[1,j],'kappa':k})
 frozen=json.loads((BASE/'outputs/teacher_bootstrap_seed42_20261028/results_seed42.json').read_text())['summary']
 for j,row in enumerate(results):
  for key in ['ordinary_mean','agent_mean','paired_difference','ci_low','ci_high']:np.testing.assert_allclose(row[key],frozen[j][key],atol=1e-12)
  np.testing.assert_allclose(row['kappa'],frozen[j]['quadratic_weighted_kappa'],atol=1e-12)
 csvout('teacher_reproduced_results.csv',results)
 means.reset_index().to_csv(ROOT/'teacher_case_level_means.csv',index=False,encoding='utf-8-sig')
 df.groupby(['teacher','system'])[dims].mean().reset_index().to_csv(ROOT/'teacher_specific_means.csv',index=False,encoding='utf-8-sig')
 rows=[]
 for omitted in cases:
  keep=[i for i,x in enumerate(cases)if x!=omitted]
  for j,dim in enumerate(dims):rows.append({'excluded_case':omitted,'dimension':dim,'remaining_cases':11,'paired_difference':delta[keep,j].mean(),'full_difference':delta[:,j].mean(),'change_from_full':delta[keep,j].mean()-delta[:,j].mean()})
 csvout('case_sensitivity_results.csv',rows)
 status('teacher_reproduction_and_12_leave_one_case_out_complete')

def predictive(data,features):
 metrics=readrows('predictive_metrics_by_pv.csv');ranks=readrows('shap_importance_by_split_pv.csv');cv=readrows('training_cv_all_repeated_splits.csv')
 expected=pd.read_csv('D:/pisa2022/outputs_five_models_tuned_42_features/tuned_five_model_metrics_by_pv.csv')
 original_shap=pd.read_csv('D:/pisa2022/outputs_final_shap_42_features/shap_importance_by_pv.csv')
 seeds=[42,0,1,7,13,21,73,101,202,365,999]
 for seed in seeds:
  tr,te=train_test_split(np.arange(len(data)),test_size=.2,random_state=seed)
  np.savez_compressed(ROOT/f'split_indices_seed{seed}.npz',train=tr,test=te)
  chosenpath=ROOT/f'selected_parameters_seed{seed}.json'
  if chosenpath.exists():params=json.loads(chosenpath.read_text())
  else:
   for fi,(it,iv)in enumerate(KFold(3,shuffle=True,random_state=seed).split(tr),1):
    a,b=tr[it],tr[iv];prep=make_preprocessor(data.loc[a],features)
    xa=prep.fit_transform(data.loc[a,features]);xb=prep.transform(data.loc[b,features])
    for ci,params in enumerate(tuned.LGBM_CANDIDATES,1):
     if any(r['seed']==seed and r['fold']==fi and r['candidate_id']==ci for r in cv):continue
     model=lgb.LGBMRegressor(**params,random_state=42,n_jobs=4,verbose=-1)
     model.fit(xa,data.loc[a,'MATH_MEAN'],sample_weight=data.loc[a,'W_FSTUWT'])
     yp=model.predict(xb);y=data.loc[b,'MATH_MEAN'].to_numpy();w=data.loc[b,'W_FSTUWT'].to_numpy()
     cv.append(dict(seed=seed,fold=fi,candidate_id=ci,weighted_r2=u.weighted_r2(y,yp,w),weighted_rmse=u.weighted_rmse(y,yp,w),weighted_mae=u.weighted_mae(y,yp,w),params=json.dumps(params,sort_keys=True)))
     csvout('training_cv_all_repeated_splits.csv',cv)
   x=pd.DataFrame([r for r in cv if r['seed']==seed]).groupby('candidate_id').weighted_r2.mean().sort_values(ascending=False)
   params=tuned.LGBM_CANDIDATES[int(x.index[0])-1];save(chosenpath.name,params)
  prep=make_preprocessor(data.loc[tr],features);xt=prep.fit_transform(data.loc[tr,features]);xe=prep.transform(data.loc[te,features])
  mapped=[original_feature(x,features)for x in prep.get_feature_names_out()];wt=data.loc[tr,'W_FSTUWT'].to_numpy();we=data.loc[te,'W_FSTUWT'].to_numpy()
  rng=np.random.default_rng(42)
  for pv in c.PV_MATH_VARS:
   pos=rng.choice(np.arange(len(tr)),min(3000,len(tr)),replace=False)
   if any(r['seed']==seed and r['plausible_value']==pv for r in metrics)and any(r['seed']==seed and r['plausible_value']==pv for r in ranks):continue
   status('predictive_and_SHAP',split_seed=seed,pv=pv,completed_pvs=len(metrics))
   model=lgb.LGBMRegressor(**params,random_state=42,n_jobs=4,verbose=-1);model.fit(xt,data.loc[tr,pv],sample_weight=wt)
   pred=model.predict(xe);y=data.loc[te,pv].to_numpy()
   row=dict(seed=seed,plausible_value=pv,n_train=len(tr),n_test=len(te),weighted_r2=u.weighted_r2(y,pred,we),weighted_rmse=u.weighted_rmse(y,pred,we),weighted_mae=u.weighted_mae(y,pred,we))
   np.savez_compressed(ROOT/f'predictions_seed{seed}_{pv}.npz',test_index=te,observed=y,predicted=pred,weight=we)
   if seed==42:
    ref=expected[(expected.model=='LightGBM')&(expected.plausible_value==pv)].iloc[0]
    for m in ['weighted_r2','weighted_rmse','weighted_mae']:np.testing.assert_allclose(row[m],ref[m],rtol=1e-9,atol=1e-9,err_msg=f'Primary predictive mismatch {pv} {m}')
   vals=np.asarray(shap.TreeExplainer(model).shap_values(xt[pos]));imp=np.average(abs(vals),axis=0,weights=wt[pos]);agg=pd.DataFrame({'feature':mapped,'mean_abs_shap':imp}).groupby('feature').mean_abs_shap.sum()
   for f,value in agg.items():
    if seed==42:
     ref=original_shap[(original_shap.feature==f)&(original_shap.plausible_value==pv)].iloc[0]
     np.testing.assert_allclose(value,ref.mean_abs_shap,rtol=1e-8,atol=1e-8,err_msg=f'Primary SHAP mismatch {pv} {f}')
    ranks.append(dict(seed=seed,plausible_value=pv,feature=f,mean_abs_shap=value,sample_n=len(pos)))
   np.savez_compressed(ROOT/f'shap_rows_seed{seed}_{pv}.npz',training_positions=pos,original_row=tr[pos],weight=wt[pos])
   metrics.append(row);csvout('predictive_metrics_by_pv.csv',metrics);csvout('shap_importance_by_split_pv.csv',ranks)
   model.booster_.save_model(str(ROOT/f'lightgbm_seed{seed}_{pv}.txt'))
  pooled=pd.DataFrame(metrics).groupby('seed')[['weighted_r2','weighted_rmse','weighted_mae']].agg(['mean','std']);pooled.columns=['_'.join(x)for x in pooled.columns];pooled.reset_index().to_csv(ROOT/'predictive_repeated_splits.csv',index=False,encoding='utf-8-sig')
  status('split_complete',seed=seed)
 shapdf=pd.DataFrame(ranks).groupby(['seed','feature'],as_index=False).mean_abs_shap.mean();shapdf['rank']=shapdf.groupby('seed').mean_abs_shap.rank(ascending=False,method='min');shapdf.to_csv(ROOT/'shap_ranks_by_split.csv',index=False,encoding='utf-8-sig')
 extra=shapdf[shapdf.seed!=42];agg=extra.groupby('feature')['rank'].agg(['mean','std','min','max']);agg['top10_count']=extra.assign(top10=extra['rank']<=10).groupby('feature').top10.sum();agg['top10_frequency']=agg.top10_count/10;agg.to_csv(ROOT/'shap_rank_stability.csv',encoding='utf-8-sig')
 pair=[]
 for a,b in itertools.combinations(seeds,2):
  x=shapdf[shapdf.seed==a].set_index('feature');y=shapdf[shapdf.seed==b].set_index('feature').loc[x.index]
  topa=set(x.index[x['rank']<=10]);topb=set(y.index[y['rank']<=10]);pair.append(dict(seed_a=a,seed_b=b,spearman_rho=spearmanr(x['rank'],y['rank']).statistic,top10_overlap=len(topa&topb),top10_jaccard=len(topa&topb)/len(topa|topb)))
 csvout('shap_pairwise_stability.csv',pair)
 pd.DataFrame(metrics).query('seed!=42').groupby('seed')[['weighted_r2','weighted_rmse','weighted_mae']].mean().agg(['mean','std','min','max']).to_csv(ROOT/'predictive_stability_summary.csv',encoding='utf-8-sig')
 status('predictive_checks_complete')

def dml(data,pool):
 rows=readrows('dml_sensitivity_by_pv.csv');primary=pd.read_csv('D:/pisa2022/outputs_grade_agent_formal/dml_results_by_pv.csv')
 factors=['MATHEFF','DISCLIM','TEACHSUP','BELONG','ICTSCH'];original_learner=formal.dml_learner
 # Keep the original sample-weight pipeline helper; explicitly verify routing.
 routed=[];origfit=formal.pass_sample_weight_if_possible
 def strictfit(pipe,X,y,w):
  pipe.fit(X,y,model__sample_weight=w);routed.append(True);return pipe
 formal.pass_sample_weight_if_possible=strictfit
 for learner in ['LightGBM','ExtraTrees']:
  if learner=='LightGBM':
   formal.dml_learner=lambda logger:(lgb.LGBMRegressor(**dict(c.LGBM_PARAMS,n_jobs=4)),'LGBMRegressor')
  else:formal.dml_learner=lambda logger:(ExtraTreesRegressor(**dict(c.EXTRA_TREES_PARAMS,n_jobs=4)),'ExtraTreesRegressor')
  for factor in factors:
   for pv in c.PV_MATH_VARS:
    if any(r['model']==learner and r['treatment']==factor and r['plausible_value']==pv for r in rows):continue
    status('DML',model=learner,factor=factor,pv=pv,completed=len(rows))
    row=formal.weighted_residualized_dml(data,pv,factor,[x for x in pool if x!=factor],'W_FSTUWT','CNTSCHID',log)
    if learner=='LightGBM':
     ref=primary[(primary.treatment==factor)&(primary.plausible_value==pv)].iloc[0]
     for m in ['coef','std_error','n']:np.testing.assert_allclose(row[m],ref[m],rtol=1e-9,atol=1e-9,err_msg=f'Primary DML mismatch {factor} {pv} {m}')
    row['model']=learner;rows.append(row);csvout('dml_sensitivity_by_pv.csv',rows)
  if learner=='LightGBM':save('primary_key_DML_reproduction.json',{'five_factors_ten_PVs':True,'weighted_nuisance_fit_calls':len(routed),'strict_sample_weight':True})
  parts=[]
  for name,g in pd.DataFrame(rows).groupby('model'):
   p=u.pool_dml_results(g);p['model']=name;p['ci_low']=p.coef_pooled-1.959963984540054*p.std_error_pooled;p['ci_high']=p.coef_pooled+1.959963984540054*p.std_error_pooled;parts.append(p)
  pd.concat(parts).to_csv(ROOT/'dml_sensitivity_results.csv',index=False,encoding='utf-8-sig')
 formal.dml_learner=original_learner;formal.pass_sample_weight_if_possible=origfit
 status('DML_checks_complete')

def survey_validation(data):
 w=data.W_FSTUWT.to_numpy();rep=data[[f'W_FSTURWT{i}'for i in range(1,81)]].to_numpy()
 rows=[];rep_rows=[]
 for pv in c.PV_MATH_VARS:
  y=data[pv].to_numpy();theta=np.average(y,weights=w);rt=np.sum(rep*y[:,None],axis=0)/rep.sum(axis=0);v=.05*np.sum((rt-theta)**2)
  rows.append(dict(plausible_value=pv,weighted_mean=theta,BRR_variance=v,BRR_se=v**.5,n=len(y)))
  rep_rows.extend(dict(plausible_value=pv,replicate=i+1,estimate=t)for i,t in enumerate(rt))
 csvout('survey_weighted_mean_validation_by_pv.csv',rows);csvout('survey_weighted_mean_all_replicates.csv',rep_rows)
 values=np.array([r['weighted_mean']for r in rows]);within=np.mean([r['BRR_variance']for r in rows]);between=values.var(ddof=1);total=within+1.1*between
 save('survey_weighted_mean_validation.json',dict(pooled_mean=values.mean(),within_BRR_variance=within,between_PV_variance=between,total_variance=total,pooled_se=total**.5,formula='mean(0.05*sum_r(theta_pv_r-theta_pv)^2)+1.1*sample_var(theta_pv)',replicates=80,PVs=10,scope='weighted_mean_only_NOT_DML_variance'))
 # Independent zero-perturbation/unit-scaling identities, not a claim about DML.
 assert np.isclose(.05*np.sum((np.full(80,3.)-3.)**2),0)
 assert np.isclose(.05*np.sum((np.full(80,4.)-3.)**2),4)
 status('survey_mean_BRR_unit_validation_complete_NOT_DML')

def main():
 assert (ROOT/'code_audit_before_fitting.json').exists(),'Complete code audit first'
 frozen={'new_split_seeds':[0,1,7,13,21,73,101,202,365,999],'primary_seed':42,'model_random_seed':42,'SHAP_rng_seed':42,'LGBM_candidate_grid':tuned.LGBM_CANDIDATES,'DML_alternative':dict(c.EXTRA_TREES_PARAMS,n_jobs=4),'DML_main':dict(c.LGBM_PARAMS,n_jobs=4),'DML_factors':['MATHEFF','DISCLIM','TEACHSUP','BELONG','ICTSCH'],'threads':4,'fixed_before_fitting':True,'no_primary_outputs_overwritten':True}
 if (ROOT/'frozen_design.json').exists():assert json.loads((ROOT/'frozen_design.json').read_text())==frozen
 else:save('frozen_design.json',frozen)
 data=load_data();teacher_check();survey_validation(data)
 features=json.loads(Path('D:/pisa2022/outputs_prediction_optimization/feature_sets.json').read_text())['expanded_scales'];assert len(features)==42
 pool=pd.read_csv('D:/pisa2022/outputs_grade_agent_formal/selected_variables.csv').query("role in ['treatment','control_or_covariate']").variable.tolist()
 assert len(pool)==21
 predictive(data,features);dml(data,pool)
 old=json.loads((ROOT/'code_audit_before_fitting.json').read_text())
 assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in old['original_result_hashes'].items())
 status('all_planned_predictive_DML_teacher_checks_complete',primary_files_hashes_unchanged=True,full_DML_BRR='not_completed; see survey_variance_audit.md')
if __name__=='__main__':
 try:main()
 except Exception:
  log.exception('STOP: failed check, no selective result replacement');status('stopped_on_error',error=traceback.format_exc());raise
