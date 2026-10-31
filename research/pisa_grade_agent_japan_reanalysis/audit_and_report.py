"""Independent arithmetic audit and bounded handoff; no manuscript/deployed-agent edits."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).parent.parent/'pisa_grade_agent_multicountry'))
import config as c
sys.path.insert(0,str(c.DEPS))
import json
import numpy as np
import pandas as pd
from scipy import stats
from formal_dml import digest

OUT=Path('D:/pisa2022/outputs_grade_agent_japan_reanalysis_v1')
NAMES={'ESCS':'社会经济文化地位','HOMEPOS':'家庭物品资源','ANXMAT':'数学焦虑','MATHEFF':'正式与应用数学自我效能','MATHEF21':'数学推理及21世纪技能自我效能','TEACHSUP':'教师支持','BELONG':'学校归属感','DISCLIM':'数学课堂纪律氛围','ICTQUAL':'ICT访问质量','ICTSCH':'学校ICT可用性','ICTENQ':'探究式学习中的ICT使用','BULLIED':'遭受欺凌'}

def main():
    lock=json.loads((OUT/'analysis_lock.json').read_text(encoding='utf-8'))
    records=pd.read_csv(OUT/'all_results_by_pv.csv')
    pooled=pd.read_csv(OUT/'pooled_all_specifications.csv')
    data=pd.read_pickle(c.OUT/'country_JPN.pkl').reset_index(drop=True)
    assert digest(c.OUT/'country_JPN.pkl')==lock['input_hash']
    for file,expected in lock['source_code_hashes'].items(): assert digest(Path(file))==expected
    assert len(records)==480==len(records.drop_duplicates(['factor','specification','pv']))
    assert len(list((OUT/'checkpoints').glob('*.json')))==480
    assert records.signature.eq(lock['signature']).all()
    assert np.isfinite(records[['coefficient','variance']]).all().all() and (records.variance>0).all()
    assert records.school_overlap.eq(0).all()
    errors=[]
    for (factor,spec),g in records.groupby(['factor','specification']):
        assert len(g)==10 and set(g.pv)==set(c.PVS)
        row=pooled[(pooled.factor==factor)&(pooled.specification==spec)].iloc[0]
        errors.append(abs(g.coefficient.mean()-row.coefficient))
        errors.append(abs(g.variance.mean()+1.1*g.coefficient.var(ddof=1)-row.se**2))
    assert max(errors)<1e-8
    rep=pd.read_pickle(OUT/'japan_replicate_weights.pkl')
    rep=data[['CNTSTUID']].merge(rep,on='CNTSTUID',validate='one_to_one',how='left')
    rw=rep[[f'W_FSTURWT{i}' for i in range(1,81)]].to_numpy(float)
    brr_errors=[]; coefficient_errors=[]; cluster_errors=[]
    for record in records[records.specification.isin(['single','mutual'])].itertuples():
        residual=np.load(OUT/f'residuals_{record.factor}_{record.specification}_{record.pv}.npz')
        index=residual['source_row']; yr=residual['outcome_residual']; dr=residual['factor_residual']
        w=data.W_FSTUWT.to_numpy(float)[index]
        theta=np.sum(w*yr*dr)/np.sum(w*dr*dr)
        coefficient_errors.append(abs(theta-record.coefficient))
        score=w*dr*(yr-theta*dr)
        cluster=pd.Series(score).groupby(data.school_key.iloc[index].to_numpy()).sum().to_numpy()
        variance=len(cluster)/(len(cluster)-1)*np.sum(cluster**2)/np.sum(w*dr*dr)**2
        cluster_errors.append(abs(variance-record.variance))
        rt=np.sum(rw[index]*(yr*dr)[:,None],axis=0)/np.sum(rw[index]*(dr*dr)[:,None],axis=0)
        brr=np.sum((rt-theta)**2)/20
        brr_errors.append(abs(brr-record.brr_variance))
        folds=np.load(OUT/f'folds_{record.factor}_{record.specification}.npz')
        assert np.array_equal(index,folds['source_row'])
        membership=pd.DataFrame({'school':data.school_key.iloc[index].to_numpy(),'fold':folds['fold']})
        assert membership.groupby('school').fold.nunique().max()==1
    assert max(coefficient_errors)<1e-8 and max(cluster_errors)<1e-8 and max(brr_errors)<1e-8
    audit={'status':'passed','unique_jobs':480,'main_jobs':240,'sensitivity_jobs':240,'common_n':5112,'schools':182,'checkpoints':480,'signature_and_source_checks':True,'max_pool_arithmetic_error':max(errors),'max_residual_coefficient_error':max(coefficient_errors),'max_cluster_variance_error':max(cluster_errors),'max_fixed_score_brr_variance_error':max(brr_errors),'school_overlap':0,'grade_unique_values':int(data.GRADE.nunique()),'grade_sensitivity_adds_information':False,'fixed_score_BRR_not_full_nuisance_refit':True,'causal_identification_verified':False}
    (OUT/'audit_report.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    main_results=pooled[pooled.specification.isin(['single','mutual'])].copy()
    main_results['brr_bh_q_value']=np.nan
    for spec,indices in main_results.groupby('specification').groups.items():
        ids=np.asarray(list(indices)); order=ids[np.argsort(main_results.loc[ids,'brr_p_value'].to_numpy())]
        p=main_results.loc[order,'brr_p_value'].to_numpy()
        main_results.loc[order,'brr_bh_q_value']=np.minimum(1,np.minimum.accumulate((p*12/np.arange(1,13))[::-1])[::-1])
    main_results.to_csv(OUT/'main_results_audited.csv',index=False,encoding='utf-8-sig')
    exports=[]
    for factor in c.FACTORS:
        one=main_results[(main_results.factor==factor)&main_results.specification.eq('single')].iloc[0]
        mutual=main_results[(main_results.factor==factor)&main_results.specification.eq('mutual')].iloc[0]
        if factor in ['MATHEFF','DISCLIM','ESCS','HOMEPOS']:
            category='positive_association_in_both_background_and_mutual_specifications'
        elif factor in ['BELONG','ICTSCH']:
            category='negative_conditional_association_requires_contextual_review'
        elif factor=='BULLIED':
            category='imprecise_association_not_evidence_of_absence_or_safety'
        else:
            category='adjustment_sensitive_or_mutually_imprecise'
        exports.append({'variable_code':factor,'variable_name_zh':NAMES[factor],'education_system':'JPN','sample_n':5112,'category':category,'background_adjusted_coefficient':float(one.coefficient),'mutually_adjusted_coefficient':float(mutual.coefficient),'confidence_interval':[float(mutual.ci_low),float(mutual.ci_high)],'bh_q_value':float(mutual.bh_q_value),'prohibited_interpretation':'Do not turn population associations into individual causes or intervention rankings. Non-significant bullying association does not suspend safeguarding.','source':'main_results_audited.csv','deployment_status':'candidate_not_integrated_or_evaluated'})
    (OUT/'grade_agent_japan_candidate_factors.json').write_text(json.dumps({'status':'candidate_only_not_deployed','causal_identification_verified':False,'records':exports},ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 日本样本重分析结果与解释边界','','## 完成范围','','已完成480项：两套主模型240项；四个预定目标因素的样本、种子、学习器及年级检查160项；8套定向控制集检查80项。全部使用十个数学合理值。另对240项主模型计算固定辅助预测的80重复权重方差敏感性。','', '原日本样本5760人、182所学校；共同完整样本5112人，保留88.75%的学生与约88.96%的原始最终权重。原日本工程和多国结果没有覆盖。','','## 两套主模型','','系数单位为目标指标一个原始单位对应的数学成绩调整差异。不可跨指标直接按原始系数排列因果重要性。','','| 因素 | 背景调整 | 多因素调整 | 多因素95%区间 | 多因素BH q |','|---|---:|---:|---|---:|']
    for factor in c.FACTORS:
        one=main_results[(main_results.factor==factor)&main_results.specification.eq('single')].iloc[0]
        m=main_results[(main_results.factor==factor)&main_results.specification.eq('mutual')].iloc[0]
        lines.append(f'| {NAMES[factor]} ({factor}) | {one.coefficient:.2f} | {m.coefficient:.2f} | [{m.ci_low:.2f}, {m.ci_high:.2f}] | {m.bh_q_value:.4g} |')
    lines += ['', '## 可支持的实质结论','','数学自我效能、纪律氛围、社会经济文化地位及家庭资源在两套模型中保留正向关联。这是所检查规格下的结果，不是干预效果排序。ESCS与HOMEPOS在不同的目标模型中处理，不能将两项效应简单相加。','','MATHEF21与数学焦虑在仅调整背景条件时关联明显，在相互调整后不精确。MATHEF21移除MATHEFF后保留正向关联，符合两类自我效能共享信息这一解释，但不证明中介作用或确定因果路径。','','教师支持由背景调整的正向关联转为多因素条件负向估计。多因素主模型未通过BH校正，扩大可用样本、更换种子或ExtraTrees后区间也跨零。其主要结论是规格敏感和不确定性，不是教师支持有害。','','归属感在多因素模型、替代样本和替代学习器中为负，但背景调整和移除心理组后区间跨零。因此，负向条件关联存在于特定调整问题，不能推广为学校归属感的负面教育价值。','','学校ICT可用性的负向关联在两套主模型中出现。没有从本研究证明减少ICT资源可以改善成绩。欺凌系数不精确，不等于欺凌无害，不能影响智能体安全处理。','','## 技术审计与边界','','480个唯一任务、每组10个合理值、所有数值有限；主模型残差回归、学校聚类方差、PV合并和固定预测BRR均经独立数值复算。学校在训练/验证折间零重叠。','','年级指标在5760名日本学生中全部为0；加入年级与原模型相同，不计作独立稳健性支持。','','重复权重检查保持辅助模型固定，并未对80个重复样本重拟合机器学习辅助函数。因此不能称完整PISA-DML设计推断。样本敏感性仅覆盖事先列出的4个目标因素，不能宣称全部因素对缺失处理均稳健。额外规格的区间为探索性点区间，未进行配对系数差检验或全体探索性检验的联合校正。','','## 与既有结果的关系','','日本与多国的心理构念相互调整结果并不完全相同。两者的目标总体与模型拟合不同，尚未完成正式国别异质性检验。原日本版本还改变了学校分折、调整变量和样本，不能将新旧系数差异全归于某一项修正。','','## 论文与智能体处理建议','','将日本限定为主研究情境，多国结果作为扩展，透明保留不一致发现。两套调整规格分别回答背景调整关联与进一步条件关联，不按显著性选模型。不得把合成案例中的规则一致性改称真实学生因果诊断准确率。候选智能体数据已导出，但未替换部署证据，也未重跑原智能体评价。','','## 官方背景核实','','OECD日本国别说明明确表示日本数据达到PISA质量标准；这支持数据适用性，不自动证明本研究完整案例样本无偏，也不构成唯一选择日本的充分理由。','','https://www.oecd.org/en/publications/pisa-2022-results-volume-i-and-ii-country-notes_ed6fbcc5-en/japan_f7d7daad-en.html','','https://www.oecd.org/en/about/programmes/pisa/how-to-prepare-and-analyse-the-pisa-database.html','']
    (OUT/'日本重分析_结果与解释.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(audit,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
