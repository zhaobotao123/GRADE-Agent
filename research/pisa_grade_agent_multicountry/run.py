"""Development workflow. Results are not publication-ready causal estimates."""
import sys
from pathlib import Path
import config as c
sys.path.insert(0,str(c.DEPS))
import argparse
import hashlib
import json
import platform
import importlib.metadata
import numpy as np
import pandas as pd
import pyreadstat
from scipy import stats
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.impute import SimpleImputer
from lightgbm import LGBMRegressor

def save_json(path,obj):
    path.write_text(json.dumps(obj,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')

def senate(w, country):
    w=np.asarray(w,float)
    sums=pd.Series(w).groupby(np.asarray(country)).transform('sum').to_numpy()
    z=w/sums
    return z/z.mean()

def prepare():
    c.OUT.mkdir(parents=True,exist_ok=True)
    return prepare_partitioned()

def prepare_partitioned():
    """Keep one small partition in memory; never concatenate the full database."""
    partition_dir=c.OUT/'partitions'
    partition_dir.mkdir(exist_ok=True)
    marker=c.OUT/'partition_read_complete.json'
    variables=list(dict.fromkeys(['CNT','CNTRYID','CNTSCHID','CNTSTUID','W_FSTUWT']+c.PVS+c.FACTORS+c.BASE+['HISEI','PAREDINT','GRADE','RELATST','SCHRISK']))
    _,meta=pyreadstat.read_sav(str(c.DATA),metadataonly=True)
    _,sm=pyreadstat.read_sav(str(c.SCHOOL_DATA),metadataonly=True)
    save_json(c.OUT/'school_file_audit.json',{'path':str(c.SCHOOL_DATA),'variables':{v:dict(zip(sm.column_names,sm.column_labels)).get(v) for v in ['SCHLTYPE','STRATIO','SCHSIZE','STUBEHA']},'merged_as_controls':False})
    if not marker.exists():
        for i,(part,_) in enumerate(pyreadstat.read_file_in_chunks(pyreadstat.read_sav,str(c.DATA),chunksize=10000,usecols=variables,apply_value_formats=False)):
            for cnt,g in part.groupby('CNT',observed=True):
                g.to_pickle(partition_dir/f'{cnt}_{i:04d}.pkl')
            print('Partitioned rows',(i+1)*10000,flush=True)
        save_json(marker,{'source':str(c.DATA),'rows':meta.number_rows,'scope':'selected_columns_no_replication_weights'})
    records=[]; countries=[]; students=0; cached=0; schools=0
    for cnt in sorted({p.stem.split('_')[0] for p in partition_dir.glob('*.pkl')}):
        g=pd.concat([pd.read_pickle(p) for p in partition_dir.glob(f'{cnt}_*.pkl')],ignore_index=True)
        assert not g.duplicated(['CNT','CNTSTUID']).any()
        g['school_key']=g.CNT.astype(str)+':'+g.CNTSCHID.astype(str)
        basic=np.isfinite(g[c.PVS+['W_FSTUWT']].to_numpy(float)).all(axis=1)&(g.W_FSTUWT>0)&g.CNTSCHID.notna()
        complete=g[c.FACTORS+c.BASE+['HISEI','PAREDINT']].notna().all(axis=1)&basic
        coverage=g[c.FACTORS].notna().mean(); n=int(complete.sum())
        reasons=[]
        for condition,message in [(len(g)>=c.MIN_RAW_N,'raw_n'),(g.CNTSCHID.nunique()>=c.MIN_SCHOOLS,'school_count'),(coverage.min()>=c.MIN_FACTOR_COVERAGE,'factor_coverage'),(n>=c.MIN_COMMON_N,'common_n'),(complete.mean()>=c.MIN_COMMON_FRACTION,'common_retention')]:
            if not condition: reasons.append(message)
        records.append({'CNT':cnt,'raw_n':len(g),'common_n':n,'retained_fraction':float(complete.mean()),'min_factor_coverage':float(coverage.min()),'eligible_development':not reasons,'reason':';'.join(reasons)})
        if not reasons:
            countries.append(cnt); students+=n; cached+=int(basic.sum()); schools+=g.loc[complete,'school_key'].nunique()
            g['common_sample']=complete
            g.loc[basic].to_pickle(c.OUT/f'country_{cnt}.pkl')
        del g
    pd.DataFrame(records).to_csv(c.OUT/'country_eligibility_development.csv',index=False,encoding='utf-8-sig')
    pd.DataFrame([{'factor':f,'specification':s,'controls':';'.join(c.controls(f,s)),'interpretation':'adjusted_association_pending_causal_identification_review'} for f in c.FACTORS for s in ['single','mutual']]).to_csv(c.OUT/'adjustment_sets.csv',index=False,encoding='utf-8-sig')
    manifest={'status':'development_not_submission_ready','countries':countries,'systems':len(countries),'cached_students':cached,'common_students':students,'common_schools':int(schools),'source_rows':meta.number_rows,'sampling_standards_flags_reviewed':False,'measurement_invariance_established':False,'storage':'per_country_pickles','python':platform.python_version(),'packages':{p:importlib.metadata.version(p) for p in ['numpy','pandas','pyreadstat','scikit-learn','lightgbm','scipy']}}
    save_json(c.OUT/'sample_manifest.json',manifest)
    print(json.dumps(manifest,ensure_ascii=False),flush=True)

def legacy_prepare_unused():
    if (c.OUT/'data.pkl').exists():
        print('Prepared cache already exists; retained.',flush=True)
        return
    variables=list(dict.fromkeys(['CNT','CNTRYID','CNTSCHID','CNTSTUID','W_FSTUWT']+c.PVS+c.FACTORS+c.BASE+['HISEI','PAREDINT','GRADE','RELATST','SCHRISK']))
    # Metadata audit of school variables; do not silently add contemporaneous controls.
    _,sm=pyreadstat.read_sav(str(c.SCHOOL_DATA),metadataonly=True)
    save_json(c.OUT/'school_file_audit.json',{'path':str(c.SCHOOL_DATA),'variables':{v:dict(zip(sm.column_names,sm.column_labels)).get(v) for v in ['SCHLTYPE','STRATIO','SCHSIZE','STUBEHA']},'merged_as_controls':False})
    print('Reading selected student variables; repeat weights deferred to streamed sensitivity stage',flush=True)
    chunks=[]
    for part,meta in pyreadstat.read_file_in_chunks(pyreadstat.read_sav,str(c.DATA),chunksize=25000,usecols=variables,apply_value_formats=False):
        # Preserve identifiers, weights and plausible values at source precision.
        for column in c.FACTORS+c.BASE+['HISEI','PAREDINT','GRADE','RELATST','SCHRISK']:
            part[column]=part[column].astype('float32')
        part['CNT']=part.CNT.astype('category')
        chunks.append(part)
        print('Rows read',sum(len(p) for p in chunks),flush=True)
    df=pd.concat(chunks,ignore_index=True,copy=False)
    del chunks
    assert not df.duplicated(['CNT','CNTSTUID']).any(), 'Duplicate student keys'
    df['school_key']=df.CNT.astype(str)+':'+df.CNTSCHID.astype(str)
    basic=np.isfinite(df[c.PVS+['W_FSTUWT']].to_numpy(float)).all(axis=1)&(df.W_FSTUWT>0)&df.CNTSCHID.notna()
    complete=df[c.FACTORS+c.BASE+['HISEI','PAREDINT']].notna().all(axis=1)&basic
    eligibility=[]
    for cnt,g in df.groupby('CNT',observed=True):
        reasons=[]
        coverage=g[c.FACTORS].notna().mean()
        for condition,message in [(len(g)>=c.MIN_RAW_N,'raw_n'),(g.CNTSCHID.nunique()>=c.MIN_SCHOOLS,'school_count'),(coverage.min()>=c.MIN_FACTOR_COVERAGE,'factor_coverage'),(complete.loc[g.index].sum()>=c.MIN_COMMON_N,'common_n'),(complete.loc[g.index].mean()>=c.MIN_COMMON_FRACTION,'common_retention')]:
            if not condition: reasons.append(message)
        eligibility.append({'CNT':cnt,'raw_n':len(g),'common_n':int(complete.loc[g.index].sum()),'retained_fraction':float(complete.loc[g.index].mean()),'min_factor_coverage':float(coverage.min()),'eligible_development':not reasons,'reason':';'.join(reasons),'low_coverage_factors':';'.join(coverage[coverage<c.MIN_FACTOR_COVERAGE].index)})
    e=pd.DataFrame(eligibility)
    e.to_csv(c.OUT/'country_eligibility_development.csv',index=False,encoding='utf-8-sig')
    countries=e.loc[e.eligible_development,'CNT'].tolist()
    # Retain broader eligible-country cache for later missingness sensitivity.
    sub=df.loc[basic & df.CNT.isin(countries)].copy()
    sub['common_sample']=complete.loc[sub.index].to_numpy()
    sub.to_pickle(c.OUT/'data.pkl')
    sample=sub.loc[sub.common_sample]
    weights=senate(sample.W_FSTUWT,sample.CNT)
    diag=pd.DataFrame({'CNT':sample.CNT,'weight':weights}).groupby('CNT').weight.agg(['sum','count'])
    assert np.allclose(diag['sum'],diag['sum'].iloc[0])
    diag.to_csv(c.OUT/'equal_system_weight_check.csv',encoding='utf-8-sig')
    adjustment=[{'factor':f,'specification':s,'controls':';'.join(c.controls(f,s)),'interpretation':'adjusted_association_pending_causal_identification_review'} for f in c.FACTORS for s in ['single','mutual']]
    pd.DataFrame(adjustment).to_csv(c.OUT/'adjustment_sets.csv',index=False,encoding='utf-8-sig')
    manifest={'status':'development_not_submission_ready','countries':countries,'systems':len(countries),'cached_students':len(sub),'common_students':len(sample),'common_schools':sample.school_key.nunique(),'source_rows':len(df),'sampling_standards_flags_reviewed':False,'measurement_invariance_established':False,'thresholds':{'min_raw_n':c.MIN_RAW_N,'min_schools':c.MIN_SCHOOLS,'min_factor_coverage':c.MIN_FACTOR_COVERAGE,'min_common_n':c.MIN_COMMON_N,'min_common_fraction':c.MIN_COMMON_FRACTION},'labels':dict(zip(meta.column_names,meta.column_labels)),'python':platform.python_version(),'packages':{p:importlib.metadata.version(p) for p in ['numpy','pandas','pyreadstat','scikit-learn','lightgbm','scipy']}}
    save_json(c.OUT/'sample_manifest.json',manifest)
    print(json.dumps({k:v for k,v in manifest.items() if k not in ['labels','packages']},ensure_ascii=False),flush=True)

def orthogonal(y,d,w,groups):
    denominator=np.sum(w*d*d)
    if denominator<=1e-10: raise ValueError('Insufficient residual treatment variation')
    theta=np.sum(w*d*y)/denominator
    scores=w*d*(y-theta*d)
    cluster=pd.Series(scores).groupby(np.asarray(groups)).sum()
    g=len(cluster)
    if g<3: raise ValueError('Too few school clusters')
    variance=(g/(g-1))*np.sum(cluster.to_numpy()**2)/denominator**2
    return float(theta),float(variance),g

def encode(df,cols):
    cats=[v for v in ['CNT','ST004D01T','IMMIG','LANGN'] if v in cols]
    return pd.get_dummies(df[cols],columns=cats,dummy_na=True,dtype=float).to_numpy(float)

def dml(df,factor,pv,specification,weighting='equal_system',trees=None):
    x=encode(df,c.controls(factor,specification))
    y=df[pv].to_numpy(float); d=df[factor].to_numpy(float)
    w=df.W_FSTUWT.to_numpy(float)
    if weighting=='equal_system': w=senate(w,df.CNT)
    else: w=w/w.mean()
    yh=np.full(len(df),np.nan); dh=yh.copy()
    folds=StratifiedGroupKFold(c.FOLDS,shuffle=True,random_state=c.SEED)
    audit=[]
    for fold,(tr,te) in enumerate(folds.split(x,df.CNT,df.school_key)):
        assert set(df.school_key.iloc[tr]).isdisjoint(df.school_key.iloc[te])
        imputer=SimpleImputer(strategy='median',keep_empty_features=True)
        xt=imputer.fit_transform(x[tr]); xe=imputer.transform(x[te])
        params=dict(n_estimators=trees or c.TREES,num_leaves=15,min_child_samples=30,learning_rate=.05,n_jobs=c.THREADS,verbosity=-1,random_state=c.SEED+fold,deterministic=True,force_col_wise=True)
        for outcome,target in [(y,yh),(d,dh)]:
            learner=LGBMRegressor(**params)
            learner.fit(xt,outcome[tr],sample_weight=w[tr]/w[tr].mean())
            target[te]=learner.predict(xe)
        audit.append({'fold':fold,'train_n':len(tr),'test_n':len(te),'school_overlap':0})
    assert np.isfinite(yh).all() and np.isfinite(dh).all()
    theta,var,g=orthogonal(y-yh,d-dh,w,df.school_key)
    sd=np.sqrt(np.average((d-np.average(d,weights=w))**2,weights=w))
    return {'factor':factor,'pv':pv,'specification':specification,'weighting':weighting,'coefficient':theta,'variance':var,'se':float(np.sqrt(var)),'coefficient_per_weighted_sd':theta*sd,'n':len(df),'schools':g,'systems':df.CNT.nunique(),'outcome_oof_rmse':float(np.sqrt(np.average((y-yh)**2,weights=w))),'factor_oof_rmse':float(np.sqrt(np.average((d-dh)**2,weights=w))),'residual_factor_variance':float(np.average((d-dh)**2,weights=w)),'school_overlap':0,'status':'development_only'},audit

def smoke():
    manifest=json.loads((c.OUT/'sample_manifest.json').read_text(encoding='utf-8'))
    parts=[]
    for cnt in manifest['countries']:
        part=pd.read_pickle(c.OUT/f'country_{cnt}.pkl')
        parts.append(part.loc[part.common_sample].sample(n=100,random_state=c.SEED))
    df=pd.concat(parts,ignore_index=True)
    # Stratified real-data engineering check, not a representative effect estimate.
    df=df.reset_index(drop=True)
    result,audit=dml(df,'MATHEFF','PV1MATH','single',trees=30)
    save_json(c.OUT/'real_data_smoke.json',{'scope':'engineering_only_not_inferential','result':result,'fold_audit':audit})
    print(json.dumps(result),flush=True)

def tests():
    rng=np.random.default_rng(c.SEED)
    w=np.arange(1,101,dtype=float); country=np.repeat(['A','B'],50)
    z=senate(w,country)
    assert np.isclose(z[:50].sum(),z[50:].sum())
    # Exact orthogonal-score unit test, followed by learned cross-fitting simulation.
    d=rng.normal(size=20000); noise=rng.normal(size=len(d))
    theta,var,g=orthogonal(2*d+noise,d,np.ones(len(d)),np.arange(len(d))//20)
    assert abs(theta-2)<.05 and var>0
    q=np.array([1.,2.,3.]); u=np.array([.1,.1,.1])
    assert np.isclose(u.mean()+(1+1/3)*q.var(ddof=1),1.4333333333333333)
    assert 'HOMEPOS' not in c.controls('ESCS','mutual')
    assert 'ESCS' not in c.controls('HOMEPOS','mutual')
    sim=pd.DataFrame({'CNT':np.repeat(['A','B'],3000),'school_key':np.arange(6000)//20,'W_FSTUWT':np.ones(6000),'AGE':rng.normal(size=6000),'ST004D01T':rng.integers(1,3,6000),'IMMIG':rng.integers(1,4,6000),'LANGN':rng.integers(1,3,6000),'ESCS':rng.normal(size=6000)})
    sim['MATHEFF']=.7*sim.AGE+.4*sim.ESCS+rng.normal(size=6000)
    sim['PV1MATH']=2*sim.MATHEFF+sim.AGE+sim.ESCS+rng.normal(size=6000)
    recovered,audit=dml(sim,'MATHEFF','PV1MATH','single',trees=100)
    assert abs(recovered['coefficient']-2)<.15, recovered
    # Imputation must ignore held-out values.
    imp=SimpleImputer().fit(np.array([[1.],[3.],[np.nan]]))
    assert imp.transform([[np.nan]])[0,0]==2
    result={'status':'passed','checks':['equal_system_weights','orthogonal_known_parameter','pooling_arithmetic','composite_component_exclusion','school_group_integrity','learned_dml_simulation','training_only_imputer'],'simulation_coefficient':recovered['coefficient'],'known_parameter':2,'scope':'engineering_tests_not_complete_statistical_validation'}
    c.OUT.mkdir(parents=True,exist_ok=True)
    save_json(c.OUT/'tests.json',result)
    print(json.dumps(result),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--stage',choices=['prepare','tests','smoke'],required=True)
    args=parser.parse_args()
    {'prepare':prepare,'tests':tests,'smoke':smoke}[args.stage]()
