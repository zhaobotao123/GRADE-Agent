"""Read public-use source columns only; do not fit models or overwrite outputs."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1'
import sys,json,hashlib,re
from pathlib import Path
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE/'work/pisa_audit_deps'))
import pyreadstat
import numpy as np
source=Path('D:/Users/84130/Desktop/论文/STU_QQQ_SPSS/CY08MSP_STU_QQQ.SAV')
features=json.loads(Path('D:/pisa2022/outputs_prediction_optimization/feature_sets.json').read_text())['expanded_scales']
import csv
with Path('D:/pisa2022/outputs_grade_agent_formal/selected_variables.csv').open(encoding='utf-8-sig') as f:
    selected=list(csv.DictReader(f))
adjustment=[r['variable'] for r in selected if r['role'] in ('treatment','control_or_covariate')]
pvs=[f'PV{i}MATH'for i in range(1,11)]
usecols=sorted(set(features+adjustment+pvs+['CNT','W_FSTUWT','CNTSCHID','FEELSAFE','REPEAT','IMMIG','SCHRISK']))
print('Reading source columns for sample and feature audit.',flush=True)
country,_=pyreadstat.read_sav(str(source),usecols=['CNT'],apply_value_formats=False,user_missing=False)
japan_positions=np.flatnonzero(country['CNT'].to_numpy()=='JPN')
assert len(japan_positions)>0
first,last=int(japan_positions.min()),int(japan_positions.max())
del country
print(f'Japan source row range {first}:{last+1}; reading selected columns only within this range.',flush=True)
data,meta=pyreadstat.read_sav(str(source),usecols=usecols,row_offset=first,row_limit=last-first+1,apply_value_formats=False,user_missing=False)
data=data[data['CNT'].astype(str)=='JPN'].reset_index(drop=True)
n_japan=len(data)
data=data[data['W_FSTUWT'].notna()&(data['W_FSTUWT']>0)].reset_index(drop=True)
assert len(data)==5760
# Same shuffled partition as sklearn train_test_split(random_state=42).
order=np.random.RandomState(42).permutation(len(data))
test=order[:int(np.ceil(.2*len(data)))];train=order[int(np.ceil(.2*len(data))):]
assert len(train)==4608 and len(test)==1152
assert not data[pvs].isna().any().any()
assert len(features)==42
assert all(data.loc[train,f].isna().mean()<=.5 for f in features)
numeric=[f for f in features if data.loc[train,f].nunique(dropna=True)>12]
categorical=[f for f in features if f not in numeric]
result={'sample_n':len(data),'Japan_before_positive_weight_filter':n_japan,'mathematics_plausible_values':pvs,
        'all_ten_pvs_observed':True,'train_n':len(train),'test_n':len(test),'split_random_state':42,
        'prediction_original_feature_count':42,'prediction_original_features':features,
        'prediction_numeric_columns':numeric,'prediction_categorical_columns':categorical,
        'DML_retained_feature_pool':adjustment,'DML_nonfocal_adjustment_count':len(adjustment)-1,
        'school_clusters':int(data['CNTSCHID'].nunique()),
        'high_missing_candidate_rates':{f:float(data[f].isna().mean())for f in ['FEELSAFE','REPEAT','IMMIG','SCHRISK']},
        'factor_observed_n':{r['variable']:int(data[r['variable']].notna().sum())for r in selected if r['role']=='treatment'},
        'variable_labels':{f:meta.column_names_to_labels.get(f)for f in usecols},
        'no_models_refitted':True,'no_raw_data_modified':True}
out=BASE/'outputs/submission_audit_v33_20261028'
out.mkdir(parents=True,exist_ok=True)
(out/'raw_sample_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items()if k not in ['variable_labels','prediction_original_features','prediction_numeric_columns','prediction_categorical_columns','DML_retained_feature_pool']},ensure_ascii=False,indent=2))
