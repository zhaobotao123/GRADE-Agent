"""Shared frozen follow-up utilities; no access to private model-service keys."""
from pathlib import Path
import os,sys,json,time,hashlib,msvcrt
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='2'
ROOT=Path(__file__).resolve().parent;AUDIT=ROOT.parent;BASE=AUDIT.parent
sys.path.insert(0,str(BASE/'work/pisa_audit_deps'));sys.path.insert(0,str(BASE/'work/figure_python_deps'))
SOURCE=Path('C:/Users/84130/Documents/Codex/2026-07-03/zhe/pisa_grade_agent_formal_experiment')
sys.path.insert(0,str(SOURCE))
import numpy as np,pandas as pd
from scipy.stats import norm
import config as c
import utils_pisa as u
import run_formal_pisa_experiment as formal

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,obj):
 path=Path(path);tmp=path.with_suffix(path.suffix+'.tmp')
 tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),encoding='utf-8');os.replace(tmp,path)
def progress(stage,**kw):
 name=kw.pop('worker','BRR');obj=dict(stage=stage,updated=time.strftime('%Y-%m-%d %H:%M:%S'),**kw)
 save(ROOT/f'status_{name}.json',obj)
 line=time.strftime('%Y-%m-%d %H:%M:%S')+' '+json.dumps(obj,ensure_ascii=False,default=str)
 with (ROOT/f'run_{name}.log').open('a',encoding='utf-8')as f:f.write(line+'\n')
 print(line,flush=True)
def exclusive(name):
 lock=(ROOT/f'{name}.lock').open('a+b');lock.seek(0)
 if not lock.read(1):lock.write(b'0');lock.flush()
 lock.seek(0);msvcrt.locking(lock.fileno(),msvcrt.LK_NBLCK,1)
 return lock
def checked_inputs():
 design=json.loads((ROOT/'frozen_design.json').read_text(encoding='utf-8'))
 for path,digest in design['hashes'].items():assert sha(path)==digest,f'Frozen input/code changed: {path}'
 return design,pd.read_pickle(AUDIT/'japan_analysis_data.pkl')
def pool_columns():
 return pd.read_csv('D:/pisa2022/outputs_grade_agent_formal/selected_variables.csv').query("role in ['treatment','control_or_covariate']").variable.tolist()
def strictfit(pipe,X,y,w):pipe.fit(X,y,model__sample_weight=w);return pipe
def residual_estimate(y,yhat,d,dhat,w,school):
 yr=y-yhat;dr=d-dhat;den=float(np.sum(w*dr**2));assert den>1e-12
 coef=float(np.sum(w*dr*yr)/den);score=w*dr*(yr-coef*dr)
 sums=pd.Series(score).groupby(pd.Series(school).astype(str)).sum().to_numpy()
 G=len(sums);var=G/(G-1)*np.sum(sums**2)/den**2
 return dict(coef=coef,std_error=float(np.sqrt(var)),n=len(y),n_clusters=G,denominator=den)
def pooled(rows,se_field='std_error'):
 co=np.array([r['coef']for r in rows]);within=float(np.mean([r[se_field]**2 for r in rows]));between=float(co.var(ddof=1));se=float(np.sqrt(within+(1+1/len(co))*between));mu=float(co.mean())
 return dict(coef=mu,std_error=se,ci_low=mu-1.959963984540054*se,ci_high=mu+1.959963984540054*se,p_value=float(2*norm.sf(abs(mu/se))),within_variance=within,between_PV_variance=between,PV_count=len(rows))

