"""Numerical verification and final bounded experiment packet, not submission approval."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.parent/'pisa_grade_agent_multicountry'))
import config as c
sys.path.insert(0,str(c.DEPS))
import json
import numpy as np
import pandas as pd
from formal_dml import digest,now
from complete_prediction import metrics

ROOT=Path('D:/pisa2022/outputs_grade_agent_japan_reanalysis_v1')
P=ROOT/'predictive_completion_v1'

def main():
    lock=json.loads((P/'analysis_lock.json').read_text(encoding='utf-8'))
    assert digest(P/'japan_prediction_data.pkl')==lock['input_hash']
    assert digest(Path(__file__).with_name('complete_prediction.py'))==lock['script_hash']
    data=pd.read_pickle(P/'japan_prediction_data.pkl')
    split=np.load(P/'school_holdout.npz'); tr=split['train']; te=split['test']
    assert set(tr).isdisjoint(te) and len(tr)+len(te)==5112
    assert set(data.school_key.iloc[tr]).isdisjoint(data.school_key.iloc[te])
    d=pd.read_csv(P/'prediction_by_pv.csv'); s=pd.read_csv(P/'prediction_summary.csv')
    cv=pd.read_csv(P/'training_cv_metrics.csv'); attribution=pd.read_csv(P/'shap_by_pv.csv')
    assert len(d)==50==len(d.drop_duplicates(['model','pv']))
    assert len(cv)==65==len(cv.drop_duplicates(['model','candidate','fold']))
    assert d.signature.eq(lock['signature']).all() and cv.signature.eq(lock['signature']).all()
    assert (d.groupby('model').pv.nunique()==10).all()
    errors=[]
    for record in d.itertuples():
        saved=np.load(P/f'test_predictions_{record.model}_{record.pv}.npz')
        assert np.array_equal(te,saved['test_row'])
        assert np.isfinite(saved['prediction']).all()
        assert np.allclose(saved['truth'],data[record.pv].iloc[te].to_numpy())
        computed=metrics(saved['truth'],saved['prediction'],saved['weight'])
        errors += [abs(computed[k]-getattr(record,k)) for k in computed]
    assert max(errors)<1e-9
    shap_errors=[]
    for pv in c.PVS:
        saved=np.load(P/f'shap_values_{pv}.npz')
        assert set(saved['test_row']).issubset(te)
        importance=np.average(abs(saved['grouped_shap']),axis=0,weights=saved['weight'])
        expected=attribution[attribution.pv.eq(pv)].set_index('feature').loc[saved['feature'],'mean_abs_shap'].to_numpy()
        shap_errors.append(float(np.max(abs(importance-expected))))
    assert max(shap_errors)<1e-9 and attribution.max_additivity_error.max()<1e-5
    core=json.loads((ROOT/'audit_report.json').read_text(encoding='utf-8')); assert core['status']=='passed'
    summary=pd.read_csv(P/'prediction_summary.csv').set_index('model')
    importance=pd.read_csv(P/'shap_summary.csv')
    selected=json.loads((P/'selected_parameters.json').read_text(encoding='utf-8'))
    assert selected['shap_model']=='LightGBM'
    assert summary.weighted_rmse_mean.idxmin()=='LightGBM'
    result={'status':'completed_and_numerically_audited','scope':'Japan first-work statistical and prediction packet, with existing multinational extension','created_utc':now(),'DML_analysis_units':480,'DML_main_units':240,'DML_sensitivity_units':240,'fixed_nuisance_BRR_units':240,'replicates_per_BRR':80,'CV_model_fits':65,'final_prediction_model_fits':50,'SHAP_plausible_values':10,'raw_students':5760,'common_students':5112,'schools':182,'train_n':len(tr),'test_n':len(te),'train_schools':data.school_key.iloc[tr].nunique(),'test_schools':data.school_key.iloc[te].nunique(),'school_overlap':0,'max_prediction_recalculation_error':max(errors),'max_SHAP_aggregation_recalculation_error':max(shap_errors),'max_SHAP_additivity_error':float(attribution.max_additivity_error.max()),'best_CV_selected_tree':selected['shap_model'],'best_test_RMSE_model':summary.weighted_rmse_mean.idxmin(),'causal_identification_established':False,'full_nuisance_refitted_BRR_done':False,'agent_evaluation_updated':False,'manuscript_modified':False,'all_checks_run':True,'publication_approval':False}
    (ROOT/'FINAL_EXPERIMENT_STATUS.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    # Enrich a candidate export without modifying the live agent or its old benchmark.
    candidate=json.loads((ROOT/'grade_agent_japan_candidate_factors.json').read_text(encoding='utf-8'))
    shap_map=importance.set_index('feature').mean_abs_shap.to_dict()
    for record in candidate['records']:
        record['mean_absolute_predictive_SHAP']=float(shap_map[record['variable_code']])
        record['SHAP_scope']='held_out_schools_LightGBM_ten_PVs_weighted_500_cases_per_PV'
    candidate['prediction_model_summary']=summary.reset_index().to_dict(orient='records')
    candidate['deployment_status']='not_deployed_or_re_evaluated'
    (ROOT/'grade_agent_japan_complete_candidate.json').write_text(json.dumps(candidate,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 日本主分析最终实验包','','## 一句话结论','','在日本这一限定情境下，数学自我效能、家庭社会经济与资源条件、课堂纪律氛围在两套主调整规格中保持正向关联；教师支持、归属感、焦虑与另一类自我效能的解释依赖调整集。预测与SHAP也突出数学自我效能，但都不能替代因果识别。','','## 已完成','','- 480项日本DML与敏感性分析；全部分别处理十个数学合理值。','- 240项主模型的80重复权重末端估计方程检查；辅助模型固定。','- 同一5112人样本、42个预定预测特征的5模型比较；训练集学校分组五折选择参数，最终对十个合理值分别训练评价。','- 十个合理值的加权SHAP，并核验预测加和与特征分组汇总。','- 原多国240项主分析、80项控制集敏感性、1200项权重与逐系统留出结果保留为扩展；未因日本结果而删除。','','## 样本与验证','','原样本5760人，主样本5112人，均覆盖182所学校。共同样本包含所有目标因素和声明背景条件；4个预定目标因素另作可用样本检查。',f'预测训练集{len(tr)}人、{data.school_key.iloc[tr].nunique()}所学校；测试集{len(te)}人、{data.school_key.iloc[te].nunique()}所学校；学校零重叠。参数选择仅使用训练集PV1与学校分组CV，再固定参数处理全部十个合理值。','', '这是一项既有数据的回顾性重分析，测试学校是本轮建模留出，不是全新外部数据。指标的跨合理值标准差是描述性变异，不是复杂抽样设计标准误。','','## 预测结果','','| 模型 | 平均加权R² | 平均加权RMSE | 平均加权MAE |','|---|---:|---:|---:|']
    for name,row in summary.iterrows(): lines.append(f'| {name} | {row.weighted_r2_mean:.3f} | {row.weighted_rmse_mean:.2f} | {row.weighted_mae_mean:.2f} |')
    lines += ['', 'LightGBM由训练CV规则选为SHAP模型，也在本次测试结果中取得最低平均RMSE。没有根据测试集反复调参。该结果约有一半加权测试变异未解释，不等于能够准确诊断具体学生。','','## SHAP预测贡献前十项','','| 特征 | 平均绝对SHAP |','|---|---:|']
    for row in importance.head(10).itertuples(index=False): lines.append(f'| {row.feature} | {row.mean_abs_shap:.2f} |')
    lines += ['', 'SHAP的FAMCON、ICTWKDY等排名不能被改写为这些因素的因果效应；它们并非原12个DML目标因素。SHAP按500名留出学生及其权重汇总，每个合理值分别拟合。','','## DML主结论','','完整系数、95%区间和BH校正在main_results_audited.csv。MATHEFF约+30.78、ESCS约+26.86、HOMEPOS约+17.60、DISCLIM约+13.93（每个原始指标单位）；四者均在两套主模型中为正。不能将不同量表的原始系数直接作影响排序。','','教师支持在多因素模型中约-2.37，未通过主模型BH校正；样本、种子、学习器替代后区间跨零。因此不能作为稳定负向因果因素。归属感在多因素模型中约-5.59，但背景调整和移除心理组后区间跨零，属于条件解释边界。MATHEF21和焦虑在背景调整中关联明显，多因素模型中估计不精确；不能说它们对教育无关紧要。','','ICTSCH的负向条件关联不支持削减ICT资源；欺凌估计不精确不能改变学生安全保护要求。','','## 不能由继续运行模型解决的边界','','横截面数据不能通过DML或重复运行自行证明时间先后和无未测混杂。研究可以保留因果推断目标，并陈述识别假设；本实验实际结果仍应报告为所声明调整下的条件关联，不给出个体确定性原因。','','重复权重只重新加权最终分数，未逐重复样本重拟合辅助函数，不称完整流程设计推断。若论文必须声称这一点，需要单独安排全流程重复权重计算；本包选择如实保留边界，不伪称完成。','','GRADE在日本全部为0，加入年级模型不提供独立稳健性证据。样本敏感性仅覆盖4个预定目标，不能声称所有变量均已充分处理非随机缺失。','','## 到此收束的实验决策','','保留日本主分析和多国扩展；保留全部两套主模型和预定敏感性规格，不依据符号、显著性选择国家或模型。主叙事是因素识别及其规格差异，随后用于智能体的追问与解释。不得将总体统计规律直接变为个体因果判断或教学干预排序。','','第一项工作的统计和预测结果已经成包。第二项智能体评价尚未用新证据重跑；grade_agent_japan_complete_candidate.json只是核对过的候选数据，不是部署或效果验证。旧的智能体准确率/规则指标不能自动视为新版结果。','','## 文件','','- main_results_audited.csv：DML主结果与有限范围BRR。','- japan_sensitivity_results.csv：逐因素替代规格。','- predictive_completion_v1/prediction_summary.csv：预测汇总。','- predictive_completion_v1/shap_summary.csv：预测贡献。','- FINAL_EXPERIMENT_STATUS.json：本轮完成范围及审计。','- grade_agent_japan_complete_candidate.json：仅候选接口，不含原始学生数据。','']
    (ROOT/'最终实验结果总览.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
