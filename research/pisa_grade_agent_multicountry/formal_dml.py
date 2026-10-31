"""Checkpointed full-cohort DML computation; validation limits remain explicit."""
import os
os.environ.setdefault('OMP_NUM_THREADS','4')
import sys
import config as c
sys.path.insert(0,str(c.DEPS))
import json
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from sklearn.model_selection import StratifiedGroupKFold
from lightgbm import LGBMRegressor
from run import senate, orthogonal, tests

OUT=Path('D:/pisa2022/outputs_grade_agent_multicountry/formal_computation_v1')

def now():
    return datetime.now(timezone.utc).isoformat()

def atomic(path,obj):
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    temp.replace(path)

def digest(path):
    h=hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda:handle.read(1024*1024),b''): h.update(chunk)
    return h.hexdigest()

def pool(records):
    frame=pd.DataFrame(records)
    rows=[]
    for (factor,spec),g in frame.groupby(['factor','specification']):
        if len(g)!=10: continue
        assert set(g.pv)==set(c.PVS)
        q=g.coefficient.to_numpy(); u=g.variance.to_numpy()
        within=u.mean(); between=q.var(ddof=1); total=within+1.1*between
        df=min(float(g.schools.min()-1),9*(1+within/(1.1*between))**2) if between>0 else float(g.schools.min()-1)
        se=np.sqrt(total); critical=stats.t.ppf(.975,df)
        rows.append({'factor':factor,'specification':spec,'coefficient':q.mean(),'standard_error':se,'ci_low':q.mean()-critical*se,'ci_high':q.mean()+critical*se,'p_value':2*stats.t.sf(abs(q.mean()/se),df),'within_pv_variance':within,'between_pv_variance':between,'df':df,'positive_pvs':int((q>0).sum()),'negative_pvs':int((q<0).sum()),'n':int(g.n.iloc[0]),'schools':int(g.schools.iloc[0]),'systems':39,'interpretation':'adjusted_association_not_validated_causal_effect'})
    result=pd.DataFrame(rows)
    if len(result):
        # BH values are provisional until all 12 hypotheses in the family exist.
        result['bh_q_value']=np.nan
        result['multiplicity_family_complete']=False
        for spec,indices in result.groupby('specification').groups.items():
            if len(indices)!=len(c.FACTORS): continue
            ids=np.asarray(list(indices)); order=np.argsort(result.loc[ids,'p_value'].to_numpy())
            ordered=ids[order]; p=result.loc[ordered,'p_value'].to_numpy()
            adjusted=np.minimum(1,np.minimum.accumulate((p*len(p)/np.arange(1,len(p)+1))[::-1])[::-1])
            result.loc[ordered,'bh_q_value']=adjusted
            result.loc[ids,'multiplicity_family_complete']=True
        result.to_csv(OUT/'pooled_completed_factors.csv',index=False,encoding='utf-8-sig')

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    checkpoints=OUT/'checkpoints'; checkpoints.mkdir(exist_ok=True)
    manifest=json.loads((c.OUT/'sample_manifest.json').read_text(encoding='utf-8'))
    assert manifest['systems']==39 and manifest['common_students']==212591
    sources=[Path(__file__),Path(c.__file__),Path(__file__).with_name('run.py')]
    hashes={str(p):digest(p) for p in sources}
    input_hashes={cnt:digest(c.OUT/f'country_{cnt}.pkl') for cnt in manifest['countries']}
    signature=hashlib.sha256(json.dumps({'code':hashes,'inputs':input_hashes},sort_keys=True).encode()).hexdigest()
    lock=OUT/'analysis_lock.json'
    design={'signature':signature,'created_utc':now(),'code_hashes':hashes,'input_hashes':input_hashes,'sample':manifest,'factors':c.FACTORS,'pvs':c.PVS,'specifications':['single','mutual'],'seed':c.SEED,'folds':c.FOLDS,'learner':{'class':'LGBMRegressor','trees':c.TREES,'num_leaves':15,'min_child_samples':30,'learning_rate':.05,'threads':c.THREADS},'weighting':'equal_system','adjustment_sets':{f:{s:c.controls(f,s) for s in ['single','mutual']} for f in c.FACTORS},'inference':'school_clustered_plus_PV_Rubin_t_df_capped_by_school_clusters','not_completed':['measurement_comparability_review','sampling_standard_flags_review','replicate_weight_inference','alternative_weighting','alternative_samples_and_adjustment_sets','prediction_SHAP','independent_agent_evaluation_update'],'publication_ready':False}
    if lock.exists():
        assert json.loads(lock.read_text(encoding='utf-8'))['signature']==signature,'Source or data changed; use a new run directory'
    else: atomic(lock,design)
    tests()
    cols=list(dict.fromkeys(['CNT','school_key','CNTSTUID','W_FSTUWT']+c.PVS+c.FACTORS+c.BASE+['HISEI','PAREDINT']))
    pieces=[]
    for cnt in manifest['countries']:
        d=pd.read_pickle(c.OUT/f'country_{cnt}.pkl')
        pieces.append(d.loc[d.common_sample,cols].copy())
        del d
    data=pd.concat(pieces,ignore_index=True); del pieces
    assert len(data)==manifest['common_students']
    assert not data.duplicated(['CNT','CNTSTUID']).any()
    assert data[c.PVS+c.FACTORS+c.BASE+['HISEI','PAREDINT']].notna().all().all()
    weights=senate(data.W_FSTUWT,data.CNT)
    totals=pd.DataFrame({'CNT':data.CNT,'weight':weights}).groupby('CNT').weight.sum()
    assert np.allclose(totals,totals.iloc[0])
    totals.to_csv(OUT/'weight_totals.csv',encoding='utf-8-sig')
    folds=list(StratifiedGroupKFold(c.FOLDS,shuffle=True,random_state=c.SEED).split(data,data.CNT,data.school_key))
    fold_ids=np.full(len(data),-1,dtype=np.int8); audits=[]
    for i,(tr,te) in enumerate(folds):
        overlap=set(data.school_key.iloc[tr])&set(data.school_key.iloc[te])
        assert not overlap
        fold_ids[te]=i
        audits.append({'fold':i,'train_n':len(tr),'validation_n':len(te),'school_overlap':len(overlap)})
    assert (fold_ids>=0).all()
    np.savez_compressed(OUT/'fold_assignment.npz',fold=fold_ids)
    atomic(OUT/'fold_audit.json',audits)
    jobs=[(s,f,pv) for s in ['single','mutual'] for f in c.FACTORS for pv in c.PVS]
    records=[]; started=time.monotonic()
    atomic(OUT/'status.json',{'status':'running','completed':0,'total':len(jobs),'started_utc':now()})
    for spec,factor,pv in jobs:
        path=checkpoints/f'{spec}_{factor}_{pv}.json'
        if path.exists():
            r=json.loads(path.read_text(encoding='utf-8')); assert r['signature']==signature
        else:
            begin=time.monotonic()
            x=data[c.controls(factor,spec)].copy()
            # Native categorical encoding avoids a huge dense language/country dummy matrix.
            # Category identities contain no outcomes; no imputation is performed on this complete sample.
            for col in ['CNT','ST004D01T','LANGN']:
                x[col]=x[col].astype('category')
            y=data[pv].to_numpy(float); treatment=data[factor].to_numpy(float)
            yh=np.full(len(data),np.nan); dh=yh.copy()
            for fold,(tr,te) in enumerate(folds):
                params=dict(n_estimators=c.TREES,num_leaves=15,min_child_samples=30,learning_rate=.05,n_jobs=c.THREADS,verbosity=-1,random_state=c.SEED+fold,deterministic=True,force_col_wise=True)
                for target,output in [(y,yh),(treatment,dh)]:
                    model=LGBMRegressor(**params)
                    model.fit(x.iloc[tr],target[tr],sample_weight=weights[tr]/weights[tr].mean())
                    output[te]=model.predict(x.iloc[te])
                    del model
            assert np.isfinite(yh).all() and np.isfinite(dh).all()
            theta,var,g=orthogonal(y-yh,treatment-dh,weights,data.school_key)
            r={'signature':signature,'factor':factor,'pv':pv,'specification':spec,'coefficient':theta,'variance':var,'n':len(data),'schools':g,'systems':manifest['systems'],'outcome_oof_rmse':float(np.sqrt(np.average((y-yh)**2,weights=weights))),'factor_oof_rmse':float(np.sqrt(np.average((treatment-dh)**2,weights=weights))),'residual_factor_variance':float(np.average((treatment-dh)**2,weights=weights)),'seconds':time.monotonic()-begin,'completed_utc':now()}
            atomic(path,r)
            del x,yh,dh
        records.append(r)
        pool(records)
        atomic(OUT/'status.json',{'status':'running','completed':len(records),'total':len(jobs),'current_job':[spec,factor,pv],'elapsed_seconds':time.monotonic()-started,'last_update_utc':now(),'publication_ready':False})
        print(f'{len(records)}/{len(jobs)} {spec} {factor} {pv} coefficient={r["coefficient"]:.5f}',flush=True)
    pd.DataFrame(records).to_csv(OUT/'dml_by_pv.csv',index=False,encoding='utf-8-sig')
    atomic(OUT/'status.json',{'status':'full_cohort_DML_computation_completed','completed':len(records),'total':len(jobs),'publication_ready':False,'last_update_utc':now(),'remaining':design['not_completed']})

if __name__=='__main__':
    try: main()
    except Exception as exc:
        if OUT.exists(): atomic(OUT/'failure.json',{'time_utc':now(),'error_type':type(exc).__name__,'error':str(exc)})
        raise
