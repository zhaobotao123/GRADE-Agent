"""Raw-weight sensitivity and fully refitted leave-one-system-out DML."""
import os
os.environ.setdefault('OMP_NUM_THREADS','4')
import sys
import config as c
sys.path.insert(0,str(c.DEPS))
import json
import hashlib
import time
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from lightgbm import LGBMRegressor
from formal_dml import atomic, digest, now
from run import senate, orthogonal

BASE=Path('D:/pisa2022/outputs_grade_agent_multicountry/formal_computation_v1')
OUT=BASE.parent/'weight_loco_v1'
FACTORS=['MATHEF21','TEACHSUP','BELONG']

def summarize(records):
    original=pd.read_csv(BASE/'pooled_completed_factors.csv')
    rows=[]
    for (stage,country,factor),g in pd.DataFrame(records).groupby(['stage','omitted_system','factor']):
        if len(g)!=10: continue
        assert set(g.pv)==set(c.PVS)
        q=g.coefficient.to_numpy(); u=g.variance.to_numpy()
        within=u.mean(); between=q.var(ddof=1); total=within+1.1*between
        df=min(float(g.schools.min()-1),9*(1+within/(1.1*between))**2) if between>0 else float(g.schools.min()-1)
        se=np.sqrt(total); critical=stats.t.ppf(.975,df)
        ref=original[(original.factor==factor)&(original.specification=='mutual')].iloc[0]
        rows.append({'stage':stage,'omitted_system':country,'factor':factor,'coefficient':q.mean(),'se':se,'ci_low':q.mean()-critical*se,'ci_high':q.mean()+critical*se,'df':df,'positive_pvs':int((q>0).sum()),'negative_pvs':int((q<0).sum()),'n':int(g.n.iloc[0]),'systems':int(g.systems.iloc[0]),'schools':int(g.schools.iloc[0]),'baseline_equal_system_coefficient':ref.coefficient,'change_from_baseline':q.mean()-ref.coefficient,'difference_significance_tested':False,'scope':'exploratory_conditional_association_sensitivity_not_causal'})
    if rows:
        frame=pd.DataFrame(rows)
        frame.to_csv(OUT/'pooled_completed.csv',index=False,encoding='utf-8-sig')
        frame[frame.stage=='raw_weight'].to_csv(OUT/'raw_weight_comparison.csv',index=False,encoding='utf-8-sig')
        loco=frame[frame.stage=='leave_one_system_out']
        loco.to_csv(OUT/'leave_one_system_out.csv',index=False,encoding='utf-8-sig')
        summary=[]
        for factor,g in loco.groupby('factor'):
            influential=g.loc[g.change_from_baseline.abs().idxmax()]
            summary.append({'factor':factor,'completed_omissions':len(g),'expected_omissions':39,'all_omissions_completed':len(g)==39,'coefficient_min':g.coefficient.min(),'coefficient_max':g.coefficient.max(),'positive_omissions':int((g.coefficient>0).sum()),'negative_omissions':int((g.coefficient<0).sum()),'largest_absolute_change_system':influential.omitted_system,'largest_absolute_change':abs(influential.change_from_baseline),'interpretation':'sensitivity_of_pooled_estimate_not_country_specific_effects'})
        if summary: pd.DataFrame(summary).to_csv(OUT/'loco_summary.csv',index=False,encoding='utf-8-sig')

def main():
    OUT.mkdir(exist_ok=True); checkpoints=OUT/'checkpoints'; checkpoints.mkdir(exist_ok=True)
    lock=json.loads((BASE/'analysis_lock.json').read_text(encoding='utf-8'))
    for file,expected in lock['code_hashes'].items(): assert digest(Path(file))==expected
    for cnt,expected in lock['input_hashes'].items(): assert digest(c.OUT/f'country_{cnt}.pkl')==expected
    countries=lock['sample']['countries']
    jobs=[('raw_weight','NONE',f,pv) for f in FACTORS for pv in c.PVS]
    jobs += [('leave_one_system_out',cnt,f,pv) for cnt in countries for f in FACTORS for pv in c.PVS]
    payload={'baseline_signature':lock['signature'],'script_hash':digest(Path(__file__)),'fold_hash':digest(BASE/'fold_assignment.npz'),'factors':FACTORS,'specification':'mutual','countries':countries,'pvs':c.PVS,'jobs':len(jobs),'threads':c.THREADS,'raw_weight_stage':'raw_student_weights_in_nuisance_and_final_score','loco_stage':'exclude_one_system_refit_both_nuisance_models_in_all_folds_equal_system_weights','folds':'retain_original_fold_ids_on_remaining_students','scope':'exploratory_followup_not_preregistered','publication_ready':False,'uncertainty':'school_clustered_plus_PV_not_full_PISA_replicate_weight_inference'}
    signature=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    runlock=OUT/'analysis_lock.json'
    if runlock.exists(): assert json.loads(runlock.read_text(encoding='utf-8'))['signature']==signature
    else: atomic(runlock,dict(payload,signature=signature,created_utc=now()))
    cols=list(dict.fromkeys(['CNT','CNTSTUID','school_key','W_FSTUWT']+c.PVS+c.FACTORS+c.BASE))
    pieces=[]
    for cnt in countries:
        part=pd.read_pickle(c.OUT/f'country_{cnt}.pkl')
        pieces.append(part.loc[part.common_sample,cols].copy()); del part
    all_data=pd.concat(pieces,ignore_index=True); del pieces
    assert len(all_data)==lock['sample']['common_students']
    assert not all_data.duplicated(['CNT','CNTSTUID']).any()
    assert all_data[c.PVS+c.FACTORS+c.BASE].notna().all().all()
    original_folds=np.load(BASE/'fold_assignment.npz')['fold']
    assert len(original_folds)==len(all_data)
    records=[]; start=time.monotonic(); previous_group=None
    for stage,omitted,factor,pv in jobs:
        path=checkpoints/f'{stage}_{omitted}_{factor}_{pv}.json'
        if path.exists():
            result=json.loads(path.read_text(encoding='utf-8')); assert result['signature']==signature
        else:
            begin=time.monotonic()
            group=(stage,omitted)
            if group!=previous_group:
                mask=np.ones(len(all_data),dtype=bool) if omitted=='NONE' else (all_data.CNT!=omitted).to_numpy()
                data=all_data.loc[mask].reset_index(drop=True)
                fold_ids=original_folds[mask]
                folds=[(np.flatnonzero(fold_ids!=i),np.flatnonzero(fold_ids==i)) for i in range(c.FOLDS)]
                for tr,te in folds:
                    assert len(tr)>0 and len(te)>0
                    assert set(data.school_key.iloc[tr]).isdisjoint(data.school_key.iloc[te])
                if omitted!='NONE': assert omitted not in set(data.CNT)
                w=data.W_FSTUWT.to_numpy(float)
                w=w/w.mean() if stage=='raw_weight' else senate(w,data.CNT)
                assert np.isfinite(w).all() and (w>0).all()
                previous_group=group
            x=data[c.controls(factor,'mutual')].copy()
            for col in ['CNT','ST004D01T','LANGN']: x[col]=x[col].astype('category')
            y=data[pv].to_numpy(float); d=data[factor].to_numpy(float)
            yh=np.full(len(data),np.nan); dh=yh.copy()
            for i,(tr,te) in enumerate(folds):
                for target,output in [(y,yh),(d,dh)]:
                    model=LGBMRegressor(n_estimators=c.TREES,num_leaves=15,min_child_samples=30,learning_rate=.05,n_jobs=c.THREADS,verbosity=-1,random_state=c.SEED+i,deterministic=True,force_col_wise=True)
                    model.fit(x.iloc[tr],target[tr],sample_weight=w[tr]/w[tr].mean())
                    output[te]=model.predict(x.iloc[te]); del model
            assert np.isfinite(yh).all() and np.isfinite(dh).all()
            theta,var,g=orthogonal(y-yh,d-dh,w,data.school_key)
            result={'signature':signature,'stage':stage,'omitted_system':omitted,'factor':factor,'pv':pv,'coefficient':theta,'variance':var,'n':len(data),'schools':g,'systems':data.CNT.nunique(),'school_overlap':0,'outcome_oof_rmse':float(np.sqrt(np.average((y-yh)**2,weights=w))),'factor_oof_rmse':float(np.sqrt(np.average((d-dh)**2,weights=w))),'seconds':time.monotonic()-begin,'completed_utc':now()}
            atomic(path,result); del x,yh,dh
        records.append(result)
        if len(records)%10==0: summarize(records)
        atomic(OUT/'status.json',{'status':'running','completed':len(records),'total':len(jobs),'current':[stage,omitted,factor,pv],'elapsed_seconds':time.monotonic()-start,'updated_utc':now(),'publication_ready':False})
        print(f'{len(records)}/{len(jobs)} {stage} omit={omitted} {factor} {pv} coefficient={result["coefficient"]:.5f}',flush=True)
    summarize(records)
    pd.DataFrame(records).to_csv(OUT/'results_by_pv.csv',index=False,encoding='utf-8-sig')
    atomic(OUT/'status.json',{'status':'completed','completed':len(records),'total':len(jobs),'updated_utc':now(),'publication_ready':False,'limitations':['not causal identification','not full survey-design inference','not country-specific DML estimates','no paired difference significance test','no simultaneous intervals for exploratory omission analyses']})

if __name__=='__main__':
    try: main()
    except Exception as exc:
        if OUT.exists(): atomic(OUT/'failure.json',{'error':str(exc),'type':type(exc).__name__,'time_utc':now()})
        raise
