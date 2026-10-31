"""Independent consistency gates and complete, non-selective result summary."""
from pathlib import Path
import sys,json,hashlib,itertools,os
os.environ['OPENBLAS_NUM_THREADS']='1';os.environ['MKL_NUM_THREADS']='1';os.environ['OMP_NUM_THREADS']='1'
ROOT=Path(__file__).resolve().parent;BASE=ROOT.parent
sys.path.insert(0,str(BASE/'work/pisa_audit_deps'));sys.path.insert(0,str(BASE/'work/figure_python_deps'))
import numpy as np,pandas as pd
from scipy.stats import norm,spearmanr
def dump(name,obj):(ROOT/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
metrics=pd.read_csv(ROOT/'predictive_metrics_by_pv.csv');shap=pd.read_csv(ROOT/'shap_importance_by_split_pv.csv');cv=pd.read_csv(ROOT/'training_cv_all_repeated_splits.csv')
assert len(metrics)==110 and len(shap)==4620 and len(cv)==165
assert not metrics.duplicated(['seed','plausible_value']).any() and not shap.duplicated(['seed','plausible_value','feature']).any()
assert metrics.groupby('seed').size().eq(10).all() and shap.groupby(['seed','plausible_value']).size().eq(42).all()
split=metrics.groupby('seed')[['weighted_r2','weighted_rmse','weighted_mae']].mean();extra=split.drop(42)
pred={m:{'mean':float(extra[m].mean()),'sd':float(extra[m].std()),'min':float(extra[m].min()),'max':float(extra[m].max()),'primary42':float(split.loc[42,m])}for m in split.columns}
other=pd.read_csv(ROOT/'other_four_models_reproduced_by_pv.csv')
assert len(other)==40 and other.groupby('model').size().eq(10).all()
oldpred=pd.read_csv('D:/pisa2022/outputs_five_models_tuned_42_features/tuned_five_model_metrics_by_pv.csv')
pj=other.merge(oldpred,on=['model','plausible_value'],validate='one_to_one',suffixes=('_new','_old'))
for m in ['weighted_r2','weighted_rmse','weighted_mae']:np.testing.assert_allclose(pj[m+'_new'],pj[m+'_old'],rtol=1e-8,atol=1e-8)
# Independently recompute metrics from all saved held-out predictions.
prediction_files_checked=0
for _,r in pd.concat([metrics,other],ignore_index=True).iterrows():
 filename=f"predictions_seed{int(r.seed)}_{r.plausible_value}.npz" if pd.notna(r.get('seed')) else f"predictions_original_{r.model}_{r.plausible_value}.npz"
 z=np.load(ROOT/filename);y=z['observed'];p=z['predicted'];w=z['weight']
 assert len(y)==1152 and len(np.unique(z['test_index']))==1152 and np.isfinite(p).all() and (w>0).all()
 mse=np.average((y-p)**2,weights=w)
 check=dict(weighted_r2=1-np.sum(w*(y-p)**2)/np.sum(w*(y-np.average(y,weights=w))**2),weighted_rmse=np.sqrt(mse),weighted_mae=np.average(abs(y-p),weights=w))
 for key,value in check.items():np.testing.assert_allclose(value,r[key],rtol=1e-12,atol=1e-12)
 prediction_files_checked+=1
rank=pd.read_csv(ROOT/'shap_ranks_by_split.csv');s=rank[rank.seed!=42]
shap_summary={}
for feature,g in s.groupby('feature'):shap_summary[feature]=dict(mean_rank=float(g['rank'].mean()),min_rank=float(g['rank'].min()),max_rank=float(g['rank'].max()),top10_count=int((g['rank']<=10).sum()))
pair=pd.read_csv(ROOT/'shap_pairwise_stability.csv');pair_extra=pair[(pair.seed_a!=42)&(pair.seed_b!=42)]
assert len(pair_extra)==45
pair_summary={m:{'mean':float(pair_extra[m].mean()),'min':float(pair_extra[m].min()),'max':float(pair_extra[m].max())}for m in ['spearman_rho','top10_overlap','top10_jaccard']}
dml=pd.read_csv(ROOT/'dml_sensitivity_by_pv.csv');additional=pd.read_csv(ROOT/'dml_additional_baseline_by_pv.csv')
assert len(dml)==100 and len(additional)==70
main=dml.query("model=='LightGBM'").drop(columns=['model']);main=pd.concat([main,additional],ignore_index=True)
assert len(main)==120 and not main.duplicated(['treatment','plausible_value']).any()
old=pd.read_csv('D:/pisa2022/outputs_grade_agent_formal/dml_results_by_pv.csv');joined=main.merge(old,on=['treatment','plausible_value'],validate='one_to_one',suffixes=('_new','_old'))
maxerrors={}
for key in ['coef','std_error','n']:
 np.testing.assert_allclose(joined[key+'_new'],joined[key+'_old'],rtol=1e-9,atol=1e-9)
 maxerrors[key]=float(abs(joined[key+'_new']-joined[key+'_old']).max())
main.to_csv(ROOT/'dml_main_reproduced_all_120.csv',index=False,encoding='utf-8-sig')
summary=pd.read_csv(ROOT/'dml_sensitivity_results.csv')
assert len(summary)==10
for _,r in summary.iterrows():
 g=dml[(dml.model==r.model)&(dml.treatment==r.treatment)];assert len(g)==10
 v=np.mean(g.std_error**2)+1.1*g.coef.var(ddof=1)
 np.testing.assert_allclose(r.coef_pooled,g.coef.mean(),atol=1e-12)
 np.testing.assert_allclose(r.std_error_pooled,v**.5,atol=1e-12)
compare=[]
for factor in ['MATHEFF','DISCLIM','TEACHSUP','BELONG','ICTSCH']:
 a=summary[(summary.model=='LightGBM')&(summary.treatment==factor)].iloc[0];b=summary[(summary.model=='ExtraTrees')&(summary.treatment==factor)].iloc[0]
 assert a.n_mean==b.n_mean
 compare.append(dict(factor=factor,main_coef=float(a.coef_pooled),alternative_coef=float(b.coef_pooled),absolute_change=float(b.coef_pooled-a.coef_pooled),relative_change_percent=float(100*(b.coef_pooled-a.coef_pooled)/abs(a.coef_pooled)),main_se=float(a.std_error_pooled),alternative_se=float(b.std_error_pooled),main_p=float(a.p_value_pooled),alternative_p=float(b.p_value_pooled),main_sign=str(a.signal_direction),alternative_sign=str(b.signal_direction),sign_changed=bool(a.signal_direction!=b.signal_direction),significance_changed=bool((a.p_value_pooled<.05)!=(b.p_value_pooled<.05)),same_effective_sample=True,n=float(a.n_mean),alternative_all_PVs_same_sign=bool(b.direction_consistent)))
pd.DataFrame(compare).to_csv(ROOT/'dml_main_vs_alternative_comparison.csv',index=False,encoding='utf-8-sig')
loo=pd.read_csv(ROOT/'case_sensitivity_results.csv');primary=loo[loo.dimension=='Appropriateness and actionability'];assert len(primary)==12
teacher={'leave_one_out_primary_min':float(primary.paired_difference.min()),'leave_one_out_primary_max':float(primary.paired_difference.max()),'all12_positive':bool((primary.paired_difference>0).all()),'maximum_absolute_change':float(abs(primary.change_from_full).max())}
case_means=pd.read_csv(ROOT/'teacher_case_level_means.csv')
for dimension,g in loo.groupby('dimension'):
 wide=case_means.pivot(index='case_id',columns='system',values=dimension)
 delta=wide.grade_agent-wide.ordinary_llm
 for _,r in g.iterrows():np.testing.assert_allclose(delta.drop(r.excluded_case).mean(),r.paired_difference,atol=1e-12)
orig=json.loads((ROOT/'code_audit_before_fitting.json').read_text())
assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in orig['original_result_hashes'].items())
review={'validation_passed':True,'prediction':pred,'saved_prediction_files_independently_checked':prediction_files_checked,'SHAP':shap_summary,'SHAP_pairwise_extra45':pair_summary,'DML_comparison':compare,'DML_all120_main_reproduction_max_abs_error':maxerrors,'teacher':teacher,'original_sources_unchanged':True,'full_DML_BRR_completed':False,'prediction_scope':'All five selected model specifications refitted on original split and ten PVs; repeated-split stability limited to LightGBM. Original other-model hyperparameter searches inspected, not rerun.','posthoc_checks_not_preregistered':True,'ElasticNet_internal_candidate_path_convergence_warnings_observed':True}
dump('verified_results.json',review)
lines=['# 稳健性检验与方法核查结果','', '## 执行与复现','', '代码审查在新拟合之前完成，原始主结果SHA256复核未变。本次从SPSS原数据重新读取日本5760人、182所学校及80组复制权重。种子42的五个选定模型×十PV预测及LightGBM全部420个原变量SHAP结果通过逐项复现；原DML全部12因素×10PV的系数、SE、n通过复现。教师评分、50,000次案例Bootstrap及κ均复算一致。ElasticNetCV内部候选路径出现收敛警告，保留原max_iter设置及全部复现结果，没有按警告修改原参数；指标复现不等于每条正则化候选路径均已收敛。','', '## 预测模型十组新增划分','', '|指标|新增10划分均值|SD|最小|最大|原42|','|---|---:|---:|---:|---:|---:|']
for m,r in pred.items():lines.append(f"|{m}|{r['mean']:.6f}|{r['sd']:.6f}|{r['min']:.6f}|{r['max']:.6f}|{r['primary42']:.6f}|")
lines+=['','每个划分先以原五组候选参数做训练内三折CV，再对十PV分别拟合。模型和SHAP随机源保持42，只改变训练/测试及CV划分种子。42变量事先固定，保存全部165条CV记录、110条PV测试结果、4620条SHAP记录和11套划分索引。不同划分SD是划分变动，不是总体抽样SE。该检查不重新比较五个模型的名次，也不检验学校外泛化。','','## SHAP稳定性','', '|特征|平均名次|名次范围|进入前10次数/10|','|---|---:|---|---:|']
for feature in ['MATHEFF','FAMCON','ICTWKDY','DISCLIM','ESCS','HOMEPOS','COGACMCO','ICTWKEND','FAMSUP','ICTFEED','ICTHOME','EXPO21ST']:
 if feature in shap_summary:
  r=shap_summary[feature];lines.append(f"|{feature}|{r['mean_rank']:.2f}|{r['min_rank']:.0f}–{r['max_rank']:.0f}|{r['top10_count']}|")
for m,r in pair_summary.items():lines.append(f"\n45个新增划分对的{m}：均值{r['mean']:.6f}，范围{r['min']:.6f}–{r['max']:.6f}。")
lines+=['','全部42变量频率及名次均已保存；某变量预测排名稳定不代表因果影响。','','## DML替代模型','', 'ExtraTrees使用事先固定500树、叶节点最小样本3、max_features=.8、seed42、三折交叉拟合、相同调整变量/有效样本和学生权重。原LightGBM结果不被替换。','', '|因素|原系数|替代系数|原SE|替代SE|原p|替代p|方向变化|显著性变化|','|---|---:|---:|---:|---:|---:|---:|---|---|']
def show_p(value):return '<.001*' if value==0 else f'{value:.6g}'
for r in compare:lines.append(f"|{r['factor']}|{r['main_coef']:.4f}|{r['alternative_coef']:.4f}|{r['main_se']:.4f}|{r['alternative_se']:.4f}|{show_p(r['main_p'])}|{show_p(r['alternative_p'])}|{r['sign_changed']}|{r['significance_changed']}|")
lines+=['','* 原函数用 2×(1−Φ(|z|)) 计算极小p时会出现浮点下溢，CSV原数值保留0，不代表真实p恰好为零；正文报告p<.001。这不改变方向或显著性判断。']
lines+=['','估计大小的变化、全部PV方向、区间和p值见完整CSV。没有只保留显著或符合预期的结果。不同因素量尺不同，不以未标准化系数直接比较因素重要性。有效样本相同，变化不是删除不利样本造成。','','## 教师评价案例敏感性','',f"逐一排除一个案例后的主要配对差异范围为{teacher['leave_one_out_primary_min']:.6f}–{teacher['leave_one_out_primary_max']:.6f}分，全部12种方案均为正；距完整样本结果的最大绝对变化为{teacher['maximum_absolute_change']:.6f}分。五次生成始终在案例内平均，没有当成独立学生。该检查支持方向不由单一案例驱动，不证明对其他案例或教师群体的普遍效力。",'', '## PISA方差与实际更正','', '已验证80组权重和官方Fay-BRR/十PV合并；仅完成加权均值例子的800次复制，未完成DML全流程复制内重新拟合。保留学校聚类SE为主结果，不能声称完整设计式推断。技术障碍、原有固定残差扩展的不同样本/设定及后续方案见survey_variance_audit.md。','', '确认表1均值/SD实际未加权，而v38文字称加权。论文只更正描述性统计的文字及表注，不改表数值、预测或DML主结果。加权与未加权描述值逐项保存。','', '## 尚未解决','', '- 未完成完整DML复制权重推断及其调查设计适用性的独立验证。','- 五模型次序的跨划分稳定性未知；重复划分仅测试LightGBM。ElasticNet内部候选路径的收敛警告仍需单独检查。','- ExtraTrees只是一个替代干扰模型，不穷尽模型、缺失机制、协变量和样本敏感性。','- 保持原随机学生分折，未单独测试学校分组分折。','- 教师只有两位、合成案例12个；评分材料和生成阶段的既有局限不因本次重算消失。','- 伦理审批/豁免、知情同意、作者/经费/冲突及最新期刊格式限制仍需真实确认。']
(ROOT/'robustness_summary.md').write_text('\n'.join(lines),encoding='utf-8')
print(json.dumps({'prediction':pred,'DML':compare,'teacher':teacher,'pairwise':pair_summary},ensure_ascii=False,indent=2))
