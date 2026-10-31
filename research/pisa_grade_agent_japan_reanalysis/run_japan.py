"""Locked Japan reanalysis packet. Retain all results, including inconvenient signs."""
import os
os.environ.setdefault('OMP_NUM_THREADS','4')
import sys
from pathlib import Path
PROJECT=Path(__file__).resolve().parent
sys.path.insert(0,str(PROJECT.parent/'pisa_grade_agent_multicountry'))
import config as c
sys.path.insert(0,str(c.DEPS))
import json
import time
import hashlib
import uuid
import gc
import numpy as np
import pandas as pd
import pyreadstat
from scipy import stats
from sklearn.model_selection import GroupKFold
from sklearn.impute import SimpleImputer
from sklearn.ensemble import ExtraTreesRegressor
from lightgbm import LGBMRegressor
from formal_dml import digest, now
from run import orthogonal
from run_control_sensitivity import DESIGNS

OUT=Path('D:/pisa2022/outputs_grade_agent_japan_reanalysis_v1')
TARGETS=['MATHEFF','MATHEF21','TEACHSUP','BELONG']

def atomic(path,obj):
    tmp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    for i in range(120):
        try: os.replace(tmp,path); return
        except PermissionError:
            if i==119: raise
            time.sleep(.25)

def read_weights(data):
    cache=OUT/'japan_replicate_weights.pkl'
    if cache.exists():
        rep=pd.read_pickle(cache)
    else:
        print('Locating Japanese rows in original SPSS file',flush=True)
        codes,_=pyreadstat.read_sav(str(c.DATA),usecols=['CNT'],apply_value_formats=False)
        positions=np.flatnonzero(codes.CNT.eq('JPN').to_numpy()); del codes
        span=int(positions[-1]-positions[0]+1)
        wanted=['CNT','CNTSTUID','W_FSTUWT']+[f'W_FSTURWT{i}' for i in range(1,81)]
        if span<=25000:
            rep,_=pyreadstat.read_sav(str(c.DATA),usecols=wanted,row_offset=int(positions[0]),row_limit=span,apply_value_formats=False)
            rep=rep.loc[rep.CNT.eq('JPN')].copy()
        else:
            parts=[]; count=0
            for part,_ in pyreadstat.read_file_in_chunks(pyreadstat.read_sav,str(c.DATA),chunksize=10000,usecols=wanted,apply_value_formats=False):
                selected=part.loc[part.CNT.eq('JPN')].copy()
                if len(selected): parts.append(selected); count+=len(selected)
                if count==len(positions): break
            rep=pd.concat(parts,ignore_index=True)
        assert len(rep)==len(data)==5760
        assert not rep.duplicated('CNTSTUID').any()
        rep.to_pickle(cache)
    joined=data[['CNTSTUID','W_FSTUWT']].merge(rep,on='CNTSTUID',how='left',validate='one_to_one',suffixes=('','_read'))
    assert np.allclose(joined.W_FSTUWT,joined.W_FSTUWT_read)
    rw=joined[[f'W_FSTURWT{i}' for i in range(1,81)]].to_numpy(float)
    assert np.isfinite(rw).all() and (rw>0).all()
    return rw

def controls(factor,spec):
    return [v for v in c.controls(factor,spec) if v!='CNT']

def jobs():
    plans=[]
    for spec in ['single','mutual']:
        plans += [(factor,spec,controls(factor,spec),'common','lgbm',c.SEED) for factor in c.FACTORS]
    # Four predeclared targets; no selection using new Japan coefficients.
    for factor in TARGETS:
        for label,sample,learner,seed,extra in [
            ('factor_available','available','lgbm',c.SEED,[]),
            ('alternate_seed','common','lgbm',c.SEED+1,[]),
            ('extra_trees','common','extra_trees',c.SEED,[]),
            ('include_grade','common','lgbm',c.SEED,['GRADE'])]:
            plans.append((factor,label,controls(factor,'mutual')+extra,sample,learner,seed))
    for factor,label,omitted in DESIGNS:
        plans.append((factor,label,[v for v in controls(factor,'mutual') if v not in omitted],'common','lgbm',c.SEED))
    return plans

def pool(q,u,clusters):
    q=np.asarray(q,float); u=np.asarray(u,float)
    within=u.mean(); between=q.var(ddof=1); total=within+1.1*between
    dof=min(clusters-1,9*(1+within/(1.1*between))**2) if between>0 else clusters-1
    se=np.sqrt(total); crit=stats.t.ppf(.975,dof); estimate=q.mean()
    return {'coefficient':float(estimate),'se':float(se),'ci_low':float(estimate-crit*se),'ci_high':float(estimate+crit*se),'p_value':float(2*stats.t.sf(abs(estimate/se),dof)),'df':float(dof),'within_var':float(within),'between_var':float(between)}

def summarize(records):
    frame=pd.DataFrame(records); rows=[]
    for (factor,spec),g in frame.groupby(['factor','specification']):
        if len(g)!=10: continue
        assert set(g.pv)==set(c.PVS)
        row={'factor':factor,'specification':spec,'n':int(g.n.iloc[0]),'schools':int(g.schools.iloc[0]),'positive_pvs':int((g.coefficient>0).sum()),'negative_pvs':int((g.coefficient<0).sum()),'factor_sd':float(g.factor_sd.iloc[0])}
        row.update(pool(g.coefficient,g.variance,int(g.schools.min())))
        row['coefficient_per_factor_sd']=row['coefficient']*row['factor_sd']
        row['bh_q_value']=np.nan
        if g.brr_variance.notna().all():
            brr=pool(g.coefficient,g.brr_variance,int(g.schools.min()))
            row.update({f'brr_{k}':v for k,v in brr.items()})
            row['brr_scope']='fixed_nuisance_final_score_only'
        rows.append(row)
    if not rows: return
    result=pd.DataFrame(rows)
    for spec in ['single','mutual']:
        ids=result.index[result.specification.eq(spec)].to_numpy()
        if len(ids)!=12: continue
        ordered=ids[np.argsort(result.loc[ids,'p_value'].to_numpy())]
        p=result.loc[ordered,'p_value'].to_numpy()
        result.loc[ordered,'bh_q_value']=np.minimum(1,np.minimum.accumulate((p*12/np.arange(1,13))[::-1])[::-1])
    result.to_csv(OUT/'pooled_all_specifications.csv',index=False,encoding='utf-8-sig')
    result[result.specification.isin(['single','mutual'])].to_csv(OUT/'japan_main_results.csv',index=False,encoding='utf-8-sig')
    result[~result.specification.isin(['single','mutual'])].to_csv(OUT/'japan_sensitivity_results.csv',index=False,encoding='utf-8-sig')

def main():
    OUT.mkdir(exist_ok=True); ck=OUT/'checkpoints'; ck.mkdir(exist_ok=True)
    data=pd.read_pickle(c.OUT/'country_JPN.pkl').reset_index(drop=True)
    assert len(data)==5760 and data.common_sample.sum()==5112 and data.school_key.nunique()==182
    assert not data.duplicated('CNTSTUID').any()
    plans=jobs(); total=len(plans)*10
    payload={'scope':'Japan_primary_reanalysis_with_multicountry_extension','factors':c.FACTORS,'targets_for_additional_checks':TARGETS,'plans':plans,'sample_raw':5760,'sample_common':5112,'schools_raw':182,'sample_common_rule':'12 factors, AGE, gender, LANGN, HISEI and PAREDINT complete, carried over for paired multinational comparability','fixed_score_brr':{'replicates':80,'Fay':.5,'refit_nuisance':False,'not_full_design_inference':True},'folds':5,'main_seed':c.SEED,'trees':150,'threads':4,'input_hash':digest(c.OUT/'country_JPN.pkl'),'source_code_hashes':{str(p):digest(p) for p in [Path(__file__),Path(c.__file__),Path(__file__).parent.parent/'pisa_grade_agent_multicountry/run.py']},'comparison_scope':'same sample versus old Japan results has different controls and splitting; no claim that differences arise solely from national context','causal_identification_verified':False,'sampling_quality_and_population_scope_review':'not replaced by engineering tests','planned_jobs':total}
    signature=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    lock=OUT/'analysis_lock.json'
    if lock.exists(): assert json.loads(lock.read_text(encoding='utf-8'))['signature']==signature
    else: atomic(lock,dict(payload,signature=signature,created_utc=now()))
    reps=read_weights(data)
    raw_weight=data.W_FSTUWT.to_numpy(float)
    assert np.isfinite(raw_weight).all() and (raw_weight>0).all()
    sample_audit=[]
    for variable in c.FACTORS+c.BASE+['HISEI','PAREDINT']:
        s=data[variable]
        sample_audit.append({'variable':variable,'raw_n':len(s),'nonmissing_n':int(s.notna().sum()),'missing_rate':float(s.isna().mean())})
    pd.DataFrame(sample_audit).to_csv(OUT/'japan_missingness.csv',index=False,encoding='utf-8-sig')
    retained=data.common_sample.to_numpy(bool)
    weighted_rate=float(raw_weight[retained].sum()/raw_weight.sum())
    atomic(OUT/'sample_audit.json',{'raw_n':len(data),'common_n':int(retained.sum()),'unweighted_retained':float(retained.mean()),'weighted_retained':weighted_rate,'raw_schools':data.school_key.nunique(),'common_schools':data.loc[retained,'school_key'].nunique(),'raw_final_weight_sum':float(raw_weight.sum()),'common_final_weight_sum':float(raw_weight[retained].sum())})
    records=[]; started=time.monotonic()
    for factor,spec,xcols,sample,learner,seed in plans:
        mask=retained.copy() if sample=='common' else (data[factor].notna().to_numpy()&np.isfinite(raw_weight)&(raw_weight>0))
        selected=np.flatnonzero(mask); sub=data.loc[mask].reset_index(drop=True)
        w=raw_weight[mask]; w=w/w.mean(); rep=reps[mask]
        fold_ids=np.full(len(data),-1,dtype=np.int8)
        # Construct school folds on all Japan records, then restrict to the chosen sample.
        for i,(_,te) in enumerate(GroupKFold(5,shuffle=True,random_state=seed).split(data,groups=data.school_key)):
            fold_ids[te]=i
        ids=fold_ids[mask]; folds=[(np.flatnonzero(ids!=i),np.flatnonzero(ids==i)) for i in range(5)]
        for tr,te in folds: assert set(sub.school_key.iloc[tr]).isdisjoint(sub.school_key.iloc[te])
        if spec in ['single','mutual']:
            np.savez_compressed(OUT/f'folds_{factor}_{spec}.npz',source_row=selected,fold=ids)
        x=pd.get_dummies(sub[xcols],columns=[v for v in ['ST004D01T','LANGN'] if v in xcols],dummy_na=True,dtype=float).to_numpy(float)
        d=sub[factor].to_numpy(float); dsd=float(np.sqrt(np.average((d-np.average(d,weights=w))**2,weights=w)))
        dh=None
        for pv in c.PVS:
            path=ck/f'{factor}_{spec}_{pv}.json'
            if path.exists():
                r=json.loads(path.read_text(encoding='utf-8')); assert r['signature']==signature
            else:
                y=sub[pv].to_numpy(float); yh=np.full(len(sub),np.nan)
                need_d=dh is None
                if need_d: dh=np.full(len(sub),np.nan)
                for i,(tr,te) in enumerate(folds):
                    prep=SimpleImputer(strategy='median',keep_empty_features=True)
                    xt=prep.fit_transform(x[tr]); xe=prep.transform(x[te])
                    targets=[(y,yh)]+([(d,dh)] if need_d else [])
                    for target,dest in targets:
                        if learner=='lgbm':
                            model=LGBMRegressor(n_estimators=150,num_leaves=15,min_child_samples=30,learning_rate=.05,n_jobs=4,verbosity=-1,random_state=seed+i,deterministic=True,force_col_wise=True)
                        else:
                            model=ExtraTreesRegressor(n_estimators=150,min_samples_leaf=10,max_features=.8,n_jobs=4,random_state=seed+i)
                        model.fit(xt,target[tr],sample_weight=w[tr]/w[tr].mean())
                        dest[te]=model.predict(xe); del model
                assert np.isfinite(yh).all() and np.isfinite(dh).all()
                yr=y-yh; dr=d-dh; theta,var,g=orthogonal(yr,dr,w,sub.school_key)
                brr=None
                if spec in ['single','mutual']:
                    numer=(rep*(yr*dr)[:,None]).sum(axis=0)
                    denom=(rep*(dr*dr)[:,None]).sum(axis=0)
                    assert (denom>0).all()
                    replicate_theta=numer/denom
                    brr=float(np.sum((replicate_theta-theta)**2)/(80*(1-.5)**2))
                    np.savez_compressed(OUT/f'residuals_{factor}_{spec}_{pv}.npz',source_row=selected,outcome_residual=yr,factor_residual=dr,replicate_coefficients=replicate_theta)
                r={'signature':signature,'factor':factor,'specification':spec,'pv':pv,'coefficient':theta,'variance':var,'brr_variance':brr,'n':len(sub),'schools':g,'factor_sd':dsd,'outcome_oof_rmse':float(np.sqrt(np.average(yr*yr,weights=w))),'factor_oof_rmse':float(np.sqrt(np.average(dr*dr,weights=w))),'school_overlap':0,'controls':xcols,'learner':learner,'fold_seed':seed,'sample_strategy':sample,'completed_utc':now()}
                atomic(path,r)
            records.append(r)
            if len(records)%10==0: summarize(records)
            atomic(OUT/'status.json',{'status':'running','completed':len(records),'total':total,'current':[factor,spec,pv],'elapsed_seconds':time.monotonic()-started,'publication_ready':False,'updated_utc':now()})
            print(f'{len(records)}/{total} {factor} {spec} {pv} coef={r["coefficient"]:.5f}',flush=True)
        del sub,x,dh; gc.collect()
    pd.DataFrame(records).to_csv(OUT/'all_results_by_pv.csv',index=False,encoding='utf-8-sig')
    summarize(records)
    atomic(OUT/'status.json',{'status':'completed','completed':len(records),'total':total,'updated_utc':now(),'publication_ready':False,'remaining':['independent statistical interpretation review','full nuisance-refitted survey replication if design-based precision is claimed','predictive/SHAP update if manuscript retains those comparisons','agent evidence update and evaluation consistency'],'interpretation':'adjusted conditional associations; causal assumptions not verified'})

if __name__=='__main__':
    try: main()
    except Exception as exc:
        if OUT.exists(): atomic(OUT/'failure.json',{'error':str(exc),'type':type(exc).__name__,'time_utc':now()})
        raise
