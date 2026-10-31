"""Japan same-sample school-held-out prediction and validation-selected tree SHAP."""
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
import numpy as np
import pandas as pd
import pyreadstat
from sklearn.model_selection import GroupShuffleSplit,GroupKFold
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import OneHotEncoder,StandardScaler
from sklearn.ensemble import RandomForestRegressor,ExtraTreesRegressor
from sklearn.linear_model import Ridge,ElasticNet
from lightgbm import LGBMRegressor
from run_japan import atomic,OUT as JAPAN
from formal_dml import digest,now

OUT=JAPAN/'predictive_completion_v1'
ORIGINAL=Path('D:/pisa2022/outputs_five_models_42_features/comparison_design.json')
GRIDS={
 'LightGBM':[{'num_leaves':15,'reg_lambda':2.},{'num_leaves':31,'reg_lambda':2.}],
 'RandomForest':[{'min_samples_leaf':5},{'min_samples_leaf':10}],
 'ExtraTrees':[{'min_samples_leaf':3},{'min_samples_leaf':10}],
 'Ridge':[{'alpha':a} for a in [1.,10.,100.]],
 'ElasticNet':[{'alpha':a,'l1_ratio':r} for a in [.1,1.] for r in [.5,.9]],
}

def learner(name,params):
    if name=='LightGBM': return LGBMRegressor(n_estimators=500,learning_rate=.03,min_child_samples=25,n_jobs=4,verbosity=-1,random_state=c.SEED,deterministic=True,force_col_wise=True,**params)
    if name=='RandomForest': return RandomForestRegressor(n_estimators=200,max_features=.8,n_jobs=4,random_state=c.SEED,**params)
    if name=='ExtraTrees': return ExtraTreesRegressor(n_estimators=200,max_features=.8,n_jobs=4,random_state=c.SEED,**params)
    if name=='Ridge': return Ridge(**params)
    return ElasticNet(max_iter=20000,tol=1e-5,selection='cyclic',random_state=c.SEED,**params)

def preprocess(features,linear):
    cat=[v for v in ['ST004D01T','LANGN'] if v in features]
    num=[v for v in features if v not in cat]
    numeric=[('imputer',SimpleImputer(strategy='median',keep_empty_features=True))]
    if linear: numeric.append(('scale',StandardScaler()))
    return ColumnTransformer([('num',Pipeline(numeric),num),('cat',Pipeline([('imputer',SimpleImputer(strategy='most_frequent',keep_empty_features=True)),('onehot',OneHotEncoder(handle_unknown='ignore',sparse_output=False))]),cat)],verbose_feature_names_out=False)

def metrics(y,pred,w):
    mse=np.average((y-pred)**2,weights=w)
    return {'weighted_r2':float(1-mse/np.average((y-np.average(y,weights=w))**2,weights=w)),'weighted_rmse':float(np.sqrt(mse)),'weighted_mae':float(np.average(abs(y-pred),weights=w))}

def get_data(features):
    path=OUT/'japan_prediction_data.pkl'
    base=pd.read_pickle(c.OUT/'country_JPN.pkl').reset_index(drop=True)
    if not path.exists():
        codes,_=pyreadstat.read_sav(str(c.DATA),usecols=['CNT'],apply_value_formats=False)
        positions=np.flatnonzero(codes.CNT.eq('JPN').to_numpy()); del codes
        assert positions[-1]-positions[0]+1==5760,'Need chunked extraction for noncontiguous rows'
        columns=list(dict.fromkeys(['CNT','CNTSTUID']+features+c.PVS))
        d,_=pyreadstat.read_sav(str(c.DATA),usecols=columns,row_offset=int(positions[0]),row_limit=5760,apply_value_formats=False)
        assert d.CNT.eq('JPN').all() and not d.CNTSTUID.duplicated().any()
        merged=base[['CNTSTUID','school_key','W_FSTUWT','common_sample']].merge(d,on='CNTSTUID',validate='one_to_one',how='left')
        merged=merged.loc[merged.common_sample].reset_index(drop=True)
        assert len(merged)==5112 and merged[c.PVS].notna().all().all()
        merged.to_pickle(path)
    return pd.read_pickle(path)

def main():
    OUT.mkdir(exist_ok=True); ck=OUT/'checkpoints'; ck.mkdir(exist_ok=True)
    features=json.loads(ORIGINAL.read_text(encoding='utf-8'))['features']
    assert len(features)==42 and not any(v.startswith('PV') or v.startswith('W_') or v in ['CNTSTUID','CNTSCHID'] for v in features)
    data=get_data(features)
    tr,te=next(GroupShuffleSplit(n_splits=1,test_size=.2,random_state=c.SEED).split(data,groups=data.school_key))
    assert set(data.school_key.iloc[tr]).isdisjoint(data.school_key.iloc[te])
    cv=list(GroupKFold(n_splits=5,shuffle=True,random_state=c.SEED).split(data.iloc[tr],groups=data.school_key.iloc[tr]))
    for a,b in cv: assert set(data.school_key.iloc[tr[a]]).isdisjoint(data.school_key.iloc[tr[b]])
    payload={'input_hash':digest(OUT/'japan_prediction_data.pkl'),'original_feature_list_hash':digest(ORIGINAL),'script_hash':digest(Path(__file__)),'features':features,'grids':GRIDS,'seed':c.SEED,'n':len(data),'train_n':len(tr),'test_n':len(te),'train_schools':data.school_key.iloc[tr].nunique(),'test_schools':data.school_key.iloc[te].nunique(),'school_overlap':0,'tuning_outcome':'PV1MATH_training_only','tuning_score':'mean_weighted_RMSE_five_training_school_folds','reporting_pvs':c.PVS,'shap_model_selection':'best_tree_training_CV_RMSE_not_test_performance','historical_dataset_reuse':'retrospective_reanalysis_not_independent_external_validation','scope':'prediction_and_attribution_not_causal_effects','constant_grade':bool(data.GRADE.nunique()==1)}
    signature=hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest()
    lock=OUT/'analysis_lock.json'
    if lock.exists(): assert json.loads(lock.read_text(encoding='utf-8'))['signature']==signature
    else: atomic(lock,dict(payload,signature=signature,created_utc=now()))
    np.savez_compressed(OUT/'school_holdout.npz',train=tr,test=te,student_key=data.CNTSTUID.to_numpy())
    cv_rows=[]; chosen={}; w=data.W_FSTUWT.to_numpy(float)
    for name,candidates in GRIDS.items():
        for candidate,params in enumerate(candidates):
            for fold,(a,b) in enumerate(cv):
                path=ck/f'cv_{name}_{candidate}_{fold}.json'
                if path.exists(): r=json.loads(path.read_text(encoding='utf-8')); assert r['signature']==signature
                else:
                    train=tr[a]; valid=tr[b]
                    prep=preprocess(features,name in ['Ridge','ElasticNet'])
                    xtr=prep.fit_transform(data.iloc[train][features]); xv=prep.transform(data.iloc[valid][features])
                    model=learner(name,params)
                    model.fit(xtr,data.PV1MATH.iloc[train].to_numpy(),sample_weight=w[train]/w[train].mean())
                    r=dict(signature=signature,model=name,candidate=candidate,fold=fold,**metrics(data.PV1MATH.iloc[valid].to_numpy(),model.predict(xv),w[valid]))
                    atomic(path,r)
                cv_rows.append(r)
        group=pd.DataFrame([r for r in cv_rows if r['model']==name]).groupby('candidate').weighted_rmse.mean()
        index=int(group.idxmin()); chosen[name]={'params':candidates[index],'cv_rmse':float(group.loc[index])}
        print('Selected',name,chosen[name],flush=True)
    pd.DataFrame(cv_rows).to_csv(OUT/'training_cv_metrics.csv',index=False,encoding='utf-8-sig')
    best_tree=min(['LightGBM','RandomForest','ExtraTrees'],key=lambda n:chosen[n]['cv_rmse'])
    atomic(OUT/'selected_parameters.json',{'signature':signature,'models':chosen,'shap_model':best_tree,'selection_uses_test':False})
    rows=[]; shap_rows=[]
    sample=np.random.default_rng(c.SEED).choice(len(te),size=min(500,len(te)),replace=False)
    for pv in c.PVS:
        for name in GRIDS:
            path=ck/f'test_{name}_{pv}.json'; shapfile=ck/f'shap_{name}_{pv}.json'
            if path.exists() and (name!=best_tree or shapfile.exists()):
                r=json.loads(path.read_text(encoding='utf-8')); assert r['signature']==signature
                if name==best_tree: shap_rows+=json.loads(shapfile.read_text(encoding='utf-8'))['rows']
            else:
                prep=preprocess(features,name in ['Ridge','ElasticNet'])
                xtr=prep.fit_transform(data.iloc[tr][features]); xt=prep.transform(data.iloc[te][features])
                model=learner(name,chosen[name]['params'])
                model.fit(xtr,data[pv].iloc[tr].to_numpy(),sample_weight=w[tr]/w[tr].mean())
                pred=model.predict(xt)
                r=dict(signature=signature,model=name,pv=pv,train_n=len(tr),test_n=len(te),**metrics(data[pv].iloc[te].to_numpy(),pred,w[te]))
                np.savez_compressed(OUT/f'test_predictions_{name}_{pv}.npz',test_row=te,prediction=pred,truth=data[pv].iloc[te].to_numpy(),weight=w[te])
                if name==best_tree:
                    if name=='LightGBM':
                        contribution=model.booster_.predict(xt[sample],pred_contrib=True)
                        values=contribution[:,:-1]; base=contribution[:,-1]
                    else:
                        import shap
                        explainer=shap.TreeExplainer(model)
                        values=np.asarray(explainer.shap_values(xt[sample],check_additivity=True)); base=explainer.expected_value
                    err=float(np.max(abs(values.sum(axis=1)+base-pred[sample])))
                    assert err<1e-5
                    names=list(prep.get_feature_names_out()); grouped=np.zeros((len(sample),len(features)))
                    for column,encoded in enumerate(names):
                        matches=[f for f in features if encoded==f or encoded.startswith(f+'_')]
                        assert matches,encoded
                        original=max(matches,key=len); grouped[:,features.index(original)]+=values[:,column]
                    importance=np.average(abs(grouped),axis=0,weights=w[te[sample]])
                    current=[{'feature':f,'pv':pv,'mean_abs_shap':float(v),'model':name,'shap_n':len(sample),'max_additivity_error':err} for f,v in zip(features,importance)]
                    shap_rows+=current; atomic(shapfile,{'signature':signature,'rows':current})
                    np.savez_compressed(OUT/f'shap_values_{pv}.npz',test_row=te[sample],grouped_shap=grouped,feature=np.array(features),weight=w[te[sample]])
                atomic(path,r)
            rows.append(r)
            atomic(OUT/'status.json',{'status':'running','prediction_completed':len(rows),'prediction_total':50,'current':[pv,name],'updated_utc':now()})
            print(len(rows),'/50',pv,name,'R2',round(r['weighted_r2'],4),flush=True)
    bypv=pd.DataFrame(rows); bypv.to_csv(OUT/'prediction_by_pv.csv',index=False,encoding='utf-8-sig')
    summary=bypv.groupby('model').agg(weighted_r2_mean=('weighted_r2','mean'),weighted_r2_sd=('weighted_r2','std'),weighted_rmse_mean=('weighted_rmse','mean'),weighted_rmse_sd=('weighted_rmse','std'),weighted_mae_mean=('weighted_mae','mean'),weighted_mae_sd=('weighted_mae','std'),pv_count=('pv','nunique')).sort_values('weighted_rmse_mean')
    summary.to_csv(OUT/'prediction_summary.csv',encoding='utf-8-sig')
    s=pd.DataFrame(shap_rows); s.to_csv(OUT/'shap_by_pv.csv',index=False,encoding='utf-8-sig')
    importance=s.groupby('feature').agg(mean_abs_shap=('mean_abs_shap','mean'),sd_across_pvs=('mean_abs_shap','std'),pv_count=('pv','nunique')).sort_values('mean_abs_shap',ascending=False)
    importance.to_csv(OUT/'shap_summary.csv',encoding='utf-8-sig')
    atomic(OUT/'status.json',{'status':'completed','cv_fits':len(cv_rows),'prediction_fits':len(rows),'shap_pvs':s.pv.nunique(),'shap_model':best_tree,'updated_utc':now(),'not_design_based_confidence_intervals':'PV metric SD is descriptive, not a sampling SE','scope':'retrospective_school_holdout_prediction_not_causal_or_individual_diagnosis'})

if __name__=='__main__':
    try: main()
    except Exception as exc:
        if OUT.exists(): atomic(OUT/'failure.json',{'error':str(exc),'type':type(exc).__name__,'time_utc':now()})
        raise
