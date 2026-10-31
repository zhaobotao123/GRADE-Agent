"""Exploratory control-set diagnostics, fixed before new estimates; not model selection."""
import os
os.environ.setdefault('OMP_NUM_THREADS','4')
import sys
import config as c
sys.path.insert(0,str(c.DEPS))
import json
import time
import hashlib
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats
from lightgbm import LGBMRegressor
from formal_dml import atomic, digest, now
from run import senate, orthogonal

ROOT=Path('D:/pisa2022/outputs_grade_agent_multicountry')
BASE=ROOT/'formal_computation_v1'
OUT=ROOT/'control_sensitivity_v1'
PSYCH=['MATHEFF','MATHEF21','ANXMAT']
# Exhaustively report this declared set; do not stop when a desired sign appears.
DESIGNS=[
    ('MATHEF21','omit_MATHEFF',['MATHEFF']),
    ('MATHEF21','omit_ANXMAT',['ANXMAT']),
    ('MATHEF21','omit_MATHEFF_ANXMAT',['MATHEFF','ANXMAT']),
    ('TEACHSUP','omit_DISCLIM',['DISCLIM']),
    ('TEACHSUP','omit_psychological_block',PSYCH),
    ('BELONG','omit_BULLIED',['BULLIED']),
    ('BELONG','omit_ANXMAT',['ANXMAT']),
    ('BELONG','omit_psychological_block',PSYCH),
]

def summary(records):
    original=pd.read_csv(BASE/'pooled_completed_factors.csv')
    rows=[]
    for (factor,design),g in pd.DataFrame(records).groupby(['factor','design']):
        if len(g)!=10: continue
        assert set(g.pv)==set(c.PVS)
        q=g.coefficient.to_numpy(); u=g.variance.to_numpy()
        within=u.mean(); between=q.var(ddof=1); total=within+1.1*between
        df=min(float(g.schools.min()-1),9*(1+within/(1.1*between))**2) if between>0 else float(g.schools.min()-1)
        se=np.sqrt(total); critical=stats.t.ppf(.975,df)
        ref=original[(original.factor==factor)&(original.specification=='mutual')].iloc[0]
        rows.append({'factor':factor,'design':design,'coefficient':q.mean(),'se':se,'ci_low':q.mean()-critical*se,'ci_high':q.mean()+critical*se,'p_value':2*stats.t.sf(abs(q.mean()/se),df),'df':df,'positive_pvs':int((q>0).sum()),'negative_pvs':int((q<0).sum()),'original_mutual_coefficient':ref.coefficient,'change_from_mutual':q.mean()-ref.coefficient,'n':int(g.n.iloc[0]),'schools':int(g.schools.iloc[0]),'interpretation':'adjustment_set_sensitivity_not_causal_or_mediation','change_significance_tested':False})
    if rows:
        result=pd.DataFrame(rows)
        result['bh_q_value']=np.nan
        result['multiplicity_family_complete']=len(rows)==len(DESIGNS)
        if len(rows)==len(DESIGNS):
            order=np.argsort(result.p_value.to_numpy()); p=result.p_value.to_numpy()[order]
            adjusted=np.minimum(1,np.minimum.accumulate((p*len(p)/np.arange(1,len(p)+1))[::-1])[::-1])
            result.loc[order,'bh_q_value']=adjusted
        result.to_csv(OUT/'pooled_control_sensitivity.csv',index=False,encoding='utf-8-sig')

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    checkpoints=OUT/'checkpoints'; checkpoints.mkdir(exist_ok=True)
    baseline=json.loads((BASE/'analysis_lock.json').read_text(encoding='utf-8'))
    for file,expected in baseline['code_hashes'].items():
        assert digest(Path(file))==expected,'Baseline source changed'
    for cnt,expected in baseline['input_hashes'].items():
        assert digest(c.OUT/f'country_{cnt}.pkl')==expected,'Baseline data changed'
    controls={f'{factor}:{design}':[v for v in c.controls(factor,'mutual') if v not in omitted] for factor,design,omitted in DESIGNS}
    payload={'baseline_signature':baseline['signature'],'script_hash':digest(Path(__file__)),'designs':DESIGNS,'controls':controls,'fold_file_hash':digest(BASE/'fold_assignment.npz'),'scope':'exploratory_followup_of_observed_reversals_not_preregistered','interpretation':'Conditional association sensitivity; removed variables may be confounders, mediators, consequences, or correlated measures. This analysis alone does not distinguish them.','no_model_selection':True,'publication_ready':False}
    signature=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    lock=OUT/'analysis_lock.json'
    if lock.exists(): assert json.loads(lock.read_text(encoding='utf-8'))['signature']==signature
    else: atomic(lock,dict(payload,signature=signature,created_utc=now()))
    cols=list(dict.fromkeys(['CNT','school_key','CNTSTUID','W_FSTUWT']+c.PVS+c.FACTORS+c.BASE))
    pieces=[]
    for cnt in baseline['sample']['countries']:
        d=pd.read_pickle(c.OUT/f'country_{cnt}.pkl')
        pieces.append(d.loc[d.common_sample,cols].copy())
        del d
    data=pd.concat(pieces,ignore_index=True); del pieces
    assert len(data)==baseline['sample']['common_students']
    assert not data.duplicated(['CNT','CNTSTUID']).any()
    assert data[c.PVS+c.FACTORS+c.BASE].notna().all().all()
    fold_ids=np.load(BASE/'fold_assignment.npz')['fold']
    assert len(fold_ids)==len(data)
    folds=[(np.flatnonzero(fold_ids!=i),np.flatnonzero(fold_ids==i)) for i in range(c.FOLDS)]
    for tr,te in folds: assert set(data.school_key.iloc[tr]).isdisjoint(data.school_key.iloc[te])
    w=senate(data.W_FSTUWT,data.CNT)
    records=[]; started=time.monotonic(); total=len(DESIGNS)*len(c.PVS)
    atomic(OUT/'status.json',{'status':'running','completed':0,'total':total,'publication_ready':False})
    for factor,design,omitted in DESIGNS:
        for pv in c.PVS:
            path=checkpoints/f'{factor}_{design}_{pv}.json'
            if path.exists():
                result=json.loads(path.read_text(encoding='utf-8')); assert result['signature']==signature
            else:
                x=data[controls[f'{factor}:{design}']].copy()
                for col in ['CNT','ST004D01T','LANGN']: x[col]=x[col].astype('category')
                y=data[pv].to_numpy(float); d=data[factor].to_numpy(float)
                yh=np.full(len(data),np.nan); dh=yh.copy()
                for i,(tr,te) in enumerate(folds):
                    for target,output in [(y,yh),(d,dh)]:
                        model=LGBMRegressor(n_estimators=c.TREES,num_leaves=15,min_child_samples=30,learning_rate=.05,n_jobs=c.THREADS,verbosity=-1,random_state=c.SEED+i,deterministic=True,force_col_wise=True)
                        model.fit(x.iloc[tr],target[tr],sample_weight=w[tr]/w[tr].mean())
                        output[te]=model.predict(x.iloc[te])
                        del model
                assert np.isfinite(yh).all() and np.isfinite(dh).all()
                theta,var,g=orthogonal(y-yh,d-dh,w,data.school_key)
                result={'signature':signature,'factor':factor,'design':design,'pv':pv,'coefficient':theta,'variance':var,'n':len(data),'schools':g,'systems':baseline['sample']['systems'],'controls':controls[f'{factor}:{design}'],'outcome_oof_rmse':float(np.sqrt(np.average((y-yh)**2,weights=w))),'factor_oof_rmse':float(np.sqrt(np.average((d-dh)**2,weights=w))),'completed_utc':now()}
                atomic(path,result)
                del x,yh,dh
            records.append(result)
            summary(records)
            atomic(OUT/'status.json',{'status':'running','completed':len(records),'total':total,'current':[factor,design,pv],'elapsed_seconds':time.monotonic()-started,'updated_utc':now(),'publication_ready':False})
            print(f'{len(records)}/{total} {factor} {design} {pv} coefficient={result["coefficient"]:.5f}',flush=True)
    pd.DataFrame(records).to_csv(OUT/'sensitivity_by_pv.csv',index=False,encoding='utf-8-sig')
    atomic(OUT/'status.json',{'status':'completed','completed':len(records),'total':total,'updated_utc':now(),'publication_ready':False,'limitations':['not a causal identification or mediation test','coefficient differences have no paired uncertainty test','country-specific and survey-replication checks remain']})

if __name__=='__main__':
    try: main()
    except Exception as exc:
        if OUT.exists(): atomic(OUT/'failure.json',{'error':str(exc),'type':type(exc).__name__,'time_utc':now()})
        raise
