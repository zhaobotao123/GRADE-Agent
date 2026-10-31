"""Freeze author-confirmed teacher ratings and derive manuscript source data."""
import os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
import sys,json,csv,hashlib,shutil,collections
from pathlib import Path
from decimal import Decimal,ROUND_HALF_UP
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'work/figure_python_deps'))
import numpy as np
import openpyxl
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib import font_manager
BASE=Path(__file__).resolve().parents[1]
OUT=BASE/'outputs/manuscript_teacher_evaluation_v21_20261027'
DATA=BASE/'outputs/teacher_comparison_bilingual_v2_20261027'
MAP=BASE/'outputs/teacher_comparison_english_v2_20261027/internal/blinding_key_DO_NOT_SEND.json'
PROTOCOL=Path('D:/pisa2022/outputs_grade_agent_english_comparison_v2_20261027/protocol_lock.json')
EXPECTED={1:'405e66f86ed1fd148c5f82f83e519fccfb410b2b4005ef317b804aa046b1352a',2:'fa5ee7262c3913c6071cfb7072c493590958d96664bd11cecdcbb81aa2b23b1a'}
NAMES=['Contextual relevance','Consistency with case facts','Appropriateness and actionability','Clarity']
def save(p,v):p.write_text(json.dumps(v,ensure_ascii=False,indent=2),encoding='utf-8')
def csvout(p,rows):
 with p.open('w',encoding='utf-8-sig',newline='') as f:
  w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
def main():
 for folder in [OUT,OUT/'internal',OUT/'figures',OUT/'qa']:folder.mkdir(parents=True,exist_ok=True)
 mapping=json.loads(MAP.read_text(encoding='utf-8'))['mapping'];ratings={};flat=[];provenance=[]
 for teacher in (1,2):
  p=DATA/f'教师{teacher}_中英对照评分材料包/教师{teacher}_英文匿名对照评分表_已评分.xlsx'
  h=hashlib.sha256(p.read_bytes()).hexdigest();assert h==EXPECTED[teacher],'Teacher file changed; confirm before freezing.'
  snapshot=OUT/'internal'/f'teacher{teacher}_confirmed_final.xlsx'
  if snapshot.exists():assert hashlib.sha256(snapshot.read_bytes()).hexdigest()==h
  else:shutil.copy2(p,snapshot)
  provenance.append({'teacher':teacher,'sha256':h,'snapshot':snapshot.name})
  w=openpyxl.load_workbook(p,data_only=True);m={x['reply_id']:x for x in mapping if x['teacher']==teacher};current={}
  for row in w['对照评分'].iter_rows(min_row=6,max_row=125,values_only=True):
   item=m[row[1]];assert hashlib.sha256(row[3].encode()).hexdigest()==item['reply_sha256'];s=list(row[4:8]);assert all(type(x) in (int,float) and x in (1,2,3,4,5) for x in s)
   assert item['source_job'] not in current
   current[item['source_job']]={**item,'scores':np.array(s,dtype=float)}
   flat.append({'teacher':teacher,'source_job':item['source_job'],'case_id':item['case_id'],'system':item['system'],'repeat':item['repeat'],**dict(zip(NAMES,s))})
  assert len(current)==120;ratings[teacher]=current
 assert set(ratings[1])==set(ratings[2]);keys=sorted(ratings[1]);cases=sorted({ratings[1][k]['case_id'] for k in keys})
 combined={k:{**ratings[1][k],'scores':(ratings[1][k]['scores']+ratings[2][k]['scores'])/2} for k in keys}
 cube=np.array([[np.mean([r['scores'] for r in combined.values() if r['case_id']==c and r['system']==s],axis=0) for s in ['ordinary_llm','grade_agent']] for c in cases])
 differences=cube[:,1]-cube[:,0];rng=np.random.default_rng(20261027);draws=rng.integers(0,12,size=(50000,12));ci=np.quantile(differences[draws].mean(axis=1),[.025,.975],axis=0)
 summary=[];individual=[]
 for j,name in enumerate(NAMES):
  a=np.array([ratings[1][k]['scores'][j] for k in keys]);b=np.array([ratings[2][k]['scores'][j] for k in keys]);obs=np.zeros((5,5))
  for x,y in zip(a.astype(int),b.astype(int)):obs[x-1,y-1]+=1
  exp=np.outer(obs.sum(axis=1),obs.sum(axis=0))/120;weights=(np.arange(5)[:,None]-np.arange(5)[None,:])**2
  kappa=1-float((weights*obs).sum()/(weights*exp).sum())
  summary.append({'dimension':name,'ordinary_mean':float(cube[:,0,j].mean()),'agent_mean':float(cube[:,1,j].mean()),'paired_difference':float(differences[:,j].mean()),'ci_low':float(ci[0,j]),'ci_high':float(ci[1,j]),'quadratic_weighted_kappa':kappa,'exact_agreement':float(np.mean(a==b)),'within_one':float(np.mean(abs(a-b)<=1))})
  for t in (1,2):
   for s in ('ordinary_llm','grade_agent'):
    v=[r['scores'][j] for r in ratings[t].values() if r['system']==s]
    individual.append({'teacher':t,'system':s,'dimension':name,'mean':float(np.mean(v)),'n':len(v)})
 save(OUT/'results.json',{'summary':summary,'individual_raters':individual,'case_differences':differences.tolist(),'cases':cases,'n_cases':12,'generations_per_case_system':5,'n_teachers':2,'bootstrap_draws':50000,'seed':20261027,'primary_outcome':NAMES[2],'secondary_outcomes_exploratory':True,'intervals_conditional_on_two_fixed_teachers':True})
 save(OUT/'internal/data_freeze.json',{'teacher_files':provenance,'author_confirmation':'Author reports that teacher1 independently reviewed the ratings without seeing teacher2 scores and without knowing system identities. Teacher1 final reviewed ratings adopted; no agent changes to ratings. Earlier raw revisions were not preserved by the agent and cannot be reconstructed from summary statistics.','protocol_signature':json.loads(PROTOCOL.read_text(encoding='utf-8'))['signature'],'source_reply_matching':True,'no_raw_generations_or_ratings_changed':True})
 csvout(OUT/'teacher_scores_long.csv',flat);csvout(OUT/'results_summary.csv',summary);csvout(OUT/'individual_rater_summary.csv',individual)
 csvout(OUT/'case_level_source_data.csv',[{'case_id':c,'dimension':name,'ordinary_mean':float(cube[i,0,j]),'agent_mean':float(cube[i,1,j]),'paired_difference':float(differences[i,j])} for i,c in enumerate(cases) for j,name in enumerate(NAMES)])
 font_manager.findfont('Times New Roman',fallback_to_default=False)
 plt.rcParams.update({'font.family':'Times New Roman','font.size':9,'svg.fonttype':'none','pdf.fonttype':42,'axes.spines.top':False,'axes.spines.right':False,'axes.linewidth':.7,'legend.frameon':False})
 def export(fig,name):
  for ext in ('png','pdf','svg','tiff'):fig.savefig(OUT/'figures'/f'{name}.{ext}',dpi=600,bbox_inches='tight',facecolor='white')
  plt.close(fig)
 # Figure contract: comparison of observed teacher ratings, not effectiveness.
 # Paired case-cluster intervals are shown separately from rating means.
 fig,(ax,bx)=plt.subplots(1,2,figsize=(7.2,3.3),gridspec_kw={'width_ratios':[1.25,1]});fig.subplots_adjust(wspace=.6,bottom=.27,top=.87)
 x=np.arange(4);width=.34
 for offset,key,label,color in [(-width/2,'ordinary_mean','Ordinary LLM','#A7B6C6'),(width/2,'agent_mean','GRADE-Agent','#367C82')]:
  y=np.array([r[key] for r in summary]);ax.bar(x+offset,y,width,color=color,edgecolor='#41586B',linewidth=.5,label=label)
  for xx,yy in zip(x+offset,y):ax.text(xx,yy+.07,str(Decimal(str(round(float(yy),12))).quantize(Decimal('.01'),rounding=ROUND_HALF_UP)),ha='center',fontsize=7.5)
 ax.set_ylim(0,5.55);ax.set_yticks(range(6));ax.set_ylabel('Mean teacher rating (1–5)');ax.set_xticks(x,['Contextual\nrelevance','Case-fact\nconsistency','Suggestion\nappropriateness','Clarity'],fontsize=6.8);ax.legend(loc='upper center',bbox_to_anchor=(.5,1.20),ncol=2,fontsize=8);ax.set_title('(a) Mean final-reply ratings',loc='left',fontsize=10,pad=38)
 for j,r in enumerate(summary):
  color='#367C82' if j==2 else '#63748B';bx.errorbar(r['paired_difference'],3-j,xerr=[[r['paired_difference']-r['ci_low']],[r['ci_high']-r['paired_difference']]],fmt='o',capsize=3,color=color,markersize=5,lw=1.1)
 bx.axvline(0,color='#89949F',ls='--',lw=.7);bx.set_yticks([3,2,1,0],['Contextual relevance','Case-fact consistency','Suggestion appropriateness','Clarity'],fontsize=8);bx.set_xlim(-.05,1.65);bx.set_xlabel('GRADE-Agent − ordinary LLM\nRating-point difference (95% CI)',fontsize=8);bx.set_title('(b) Paired case-level differences',loc='left',fontsize=10,pad=24);bx.set_ylim(-.6,3.6)
 export(fig,'Figure5_teacher_comparison')
 def box(ax,x,y,w,h,text,color='#EDF3F8',size=8):
  ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.01,rounding_size=0.015',facecolor=color,edgecolor='#667D93',lw=.8));ax.text(x+w/2,y+h/2,text,ha='center',va='center',fontsize=size)
 def arrow(ax,x,y,u,v):ax.annotate('',xy=(u,v),xytext=(x,y),arrowprops={'arrowstyle':'->','color':'#667D93','lw':.8})
 fig,ax=plt.subplots(figsize=(7.2,3.5));ax.set_axis_off();ax.set_xlim(0,1);ax.set_ylim(0,1)
 for yy,label,color in [(.68,'STAGE 1  Empirical analysis','#EFF4FA'),(.35,'STAGE 2  Conversational application','#F7F0F0'),(.02,'STAGE 3  Teacher evaluation','#EFF6F2')]:
  ax.add_patch(FancyBboxPatch((.01,yy),.98,.28,boxstyle='round,pad=.01',facecolor=color,edgecolor='#B7C4CE',lw=.7));ax.text(.035,yy+.24,label,fontsize=9,fontweight='bold')
 box(ax,.035,.72,.2,.13,'Japan PISA 2022\nWeighted student data');box(ax,.30,.72,.29,.13,'Predictive modelling + SHAP\nPrespecified-factor DML');box(ax,.67,.72,.28,.13,'Empirical findings\nAdjusted associations\nand uncertainty',size=7.5);arrow(ax,.24,.785,.29,.785);arrow(ax,.60,.785,.66,.785)
 box(ax,.035,.39,.2,.13,'User observations\nLearning circumstances');box(ax,.30,.39,.29,.13,'Contextual follow-up\nResearch-informed interpretation');box(ax,.67,.39,.28,.13,'Brief provisional reply\nContinued discussion');arrow(ax,.24,.455,.29,.455);arrow(ax,.60,.455,.66,.455)
 box(ax,.035,.06,.2,.13,'12 synthetic cases\n2 systems × 5 runs');box(ax,.30,.06,.29,.13,'120 English final replies\nTwo independent blinded teachers');box(ax,.67,.06,.28,.13,'Four rating dimensions\nPaired case-level comparisons');arrow(ax,.24,.125,.29,.125);arrow(ax,.60,.125,.66,.125);arrow(ax,.80,.68,.80,.64);arrow(ax,.80,.35,.80,.31)
 export(fig,'Figure1_updated_framework')
 fig,ax=plt.subplots(figsize=(7.2,2.3));ax.set_axis_off();ax.set_xlim(0,1);ax.set_ylim(0,1)
 box(ax,.02,.65,.25,.22,'Same staged case information\nFour English user turns',size=8)
 box(ax,.37,.74,.25,.18,'Ordinary multi-turn LLM',size=9);box(ax,.37,.43,.25,.18,'GRADE-Agent',color='#E5F0ED',size=9);arrow(ax,.28,.78,.36,.83);arrow(ax,.28,.70,.36,.52)
 box(ax,.72,.61,.25,.26,'Same DeepSeek Flash model\nMatched generation settings\n60 final replies per system',size=8.5);arrow(ax,.63,.83,.71,.78);arrow(ax,.63,.52,.71,.68)
 box(ax,.04,.08,.39,.20,'Randomised anonymous A/B presentation\nTwo teachers rate each original reply',color='#EDF4F0',size=9)
 box(ax,.56,.08,.40,.20,'Relevance · Case-fact consistency\nSuggestion appropriateness · Clarity',color='#EDF4F0',size=9);arrow(ax,.85,.60,.85,.34);arrow(ax,.85,.34,.25,.34);arrow(ax,.25,.34,.25,.29);arrow(ax,.44,.18,.55,.18)
 export(fig,'Figure4_evaluation_protocol')
 save(OUT/'qa/figure_contract.json',{'claim':'GRADE-Agent received higher average teacher ratings, with the largest paired difference in suggestion appropriateness.','backend':'Python only','font':'Times New Roman verified installed','source':'case_level_source_data.csv','interval':'50000 paired case-cluster percentile bootstrap replicates, n=12 cases; two fixed teachers','scope':'Synthetic final-reply comparison, no component effect or educational-outcome claim','formats':['png','pdf','svg','tiff']})
 print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
