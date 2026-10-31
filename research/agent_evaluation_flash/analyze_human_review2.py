"""Analyze post-clarification reviews separately from initial independent ratings."""
from collections import defaultdict
from datetime import datetime,timezone
import json
from pathlib import Path

from analyze_human_ratings import read_xlsx,read_second,reliability,hashfile,FIELDS,LABELS,ROOT,BASE,np

FIRST=Path('C:/Users/84130/Documents/评分表_评分者1_复核说明补充版.xlsx')
FIRST_PRIOR=Path('C:/Users/84130/Documents/评分表_评分者1_复核修订版.xlsx')
SECOND_PRIOR=Path('C:/Users/84130/Documents/评分表2.txt')
OUT=BASE/'human_rating_review2'
SECOND=OUT/'评分者2_用户提供复核文本.csv'


def load(path):return json.loads(path.read_text(encoding='utf-8'))


def main():
    paths=[FIRST,FIRST_PRIOR,SECOND,SECOND_PRIOR]
    before={str(p):hashfile(p) for p in paths}
    first=read_xlsx(FIRST);oldfirst=read_xlsx(FIRST_PRIOR)
    second=read_second(SECOND);oldsecond=read_second(SECOND_PRIOR)
    slots={r['report_id']:r for r in load(ROOT/'restricted_human_sample_plan.json')['slots']}
    index={r['report_id']:r for r in load(BASE/'packet_index.json')}
    assert set(first)==set(oldfirst)==set(second)==set(oldsecond)==set(slots)==set(index)
    valid=sorted(i for i in index if index[i]['status']=='completed')
    assert len(valid)==29
    for records in [first,second]:
        assert all(all(v is not None for v in records[i]['scores']) for i in valid)
        assert records['R026']['scores']==[None,None,None]
    assert all(first[i]['scores']==oldfirst[i]['scores'] for i in first)
    firstchanges=[{'report_id':i,'old':oldfirst[i],'new':first[i]} for i in sorted(first) if first[i]!=oldfirst[i]]
    secondchanges=[{'report_id':i,'old':oldsecond[i],'new':second[i]} for i in sorted(second) if second[i]!=oldsecond[i]]
    agreement=reliability(first,second,valid)
    groups=defaultdict(list);paired=defaultdict(dict)
    for i in valid:
        slot=slots[i]
        scores=[(a+b)/2 for a,b in zip(first[i]['scores'],second[i]['scores'])]
        groups[slot['system']].append(scores)
        paired[slot['case_id']][slot['system']]=scores
    means=[]
    for system,label in LABELS.items():
        arr=np.array(groups[system])
        means.append({'system':system,'label':label,'n_reports':len(arr),
            'mean_scores':{field:float(arr[:,j].mean()) for j,field in enumerate(FIELDS)}})
    rng=np.random.default_rng(20261025)
    differences=[]
    for comparator in ['llm_baseline','agent_critic_only']:
        case_ids=sorted(c for c,x in paired.items() if 'agent_full' in x and comparator in x)
        for j,field in enumerate(FIELDS):
            v=np.array([paired[c]['agent_full'][j]-paired[c][comparator][j] for c in case_ids])
            boot=v[rng.integers(0,len(v),(10000,len(v)))].mean(axis=1)
            low,high=np.quantile(boot,[.025,.975])
            differences.append({'dimension':field,'contrast':'完整智能体减'+LABELS[comparator],
                'paired_cases':len(case_ids),'difference':float(v.mean()),'exploratory_CI_low':float(low),
                'exploratory_CI_high':float(high),'case_ids':case_ids})
    prior=load(BASE/'human_rating_analysis/两位教师评分分析.json')
    result={'stage':'post_rubric_clarification_review_not_initial_independent_reliability',
        'time':datetime.now(timezone.utc).isoformat(),'source_hashes':before,
        'source_of_second_review':'User pasted CSV in current message; preserved verbatim as local CSV intermediate.',
        'first_review_score_changes':0,'first_review_note_changes':firstchanges,
        'second_review_changes':secondchanges,'current_reviewed_agreement':agreement,
        'initial_independent_agreement_preserved':prior['sensitivity_initial_vs_rater2_reliability'],
        'previous_first_review_vs_second_initial_preserved':prior['primary_reviewed_vs_rater2_reliability'],
        'system_descriptive_means':means,'exploratory_paired_contrasts':differences,
        'rated_reports':29,'sampled_cases':10,'generation_failure_not_rated':['R026'],
        'source_files_unchanged':all(hashfile(p)==before[str(p)] for p in paths),
        'interpretation_limits':['These are post-clarification reviews, not baseline independent inter-rater reliability.',
            'Shared criteria clarification can increase agreement; preserve all original scores and version history.',
            'No teacher scores were changed by this script; remaining disagreements are retained.',
            'Ceiling effects and ten synthetic cases limit comparative sensitivity; no superiority or equivalence established.'],
        'records':[{'report_id':i,'case_id':slots[i]['case_id'],'system':slots[i]['system'],
            'generation_status':index[i]['status'],'rater1':first[i],'rater2':second[i]} for i in sorted(index)]}
    OUT.mkdir(exist_ok=True)
    (OUT/'两位教师_口径澄清后复核分析.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 两位教师评分：口径澄清后的复核结果','',
        '第一位教师使用“复核说明补充版”，数值与上一复核版一致，仅补充R005、R020、R022、R023的说明。第二位教师使用本轮用户粘贴文本；R005、R022、R023因素合理性由1改2，R020建议适用性和不确定处理由1改2，因素合理性仍为1。原始版本均保留。','',
        '30个报告编号齐全；29份有效报告每名教师均有三个合法分数，R026双方仍留空。没有用0填补失败报告，也没有替换其他次生成。','',
        '## 当前复核后的一致性','',
        '| 维度 | 完全一致比例 | 线性加权κ |','|---|---:|---:|']
    for row in agreement:lines.append(f"| {row['dimension']} | {row['exact_agreement']:.1%} | {row['linear_weighted_kappa']:.3f} |")
    lines+=['','上述指标是评分标准澄清后的复核一致性，不能替代初始独立一致性。最初两份原始评分的因素合理性一致率68.97%、κ=0.371；第一位独立复核、第二位尚未复核时为65.52%、κ=0.300。三个阶段均保留，不选择最高值充当初始信度。','',
        '建议适用性和不确定性处理仍有明显天花板效应：第一位全部为2，第二位只有R009为1。原始一致比例虽高，κ仍为0，不应宣称两个维度具有很高的校正偶然一致信度。','',
        '因素合理性剩余分歧：'+ '、'.join(agreement[0]['disagreement_ids'])+'。保留各自判断，无需为了提高一致性而强行调分。','',
        '## 系统描述性均分（两位教师平均，每项满分2）','',
        '| 系统 | 有效报告数 | 因素合理性 | 建议适用性 | 不确定处理 |','|---|---:|---:|---:|---:|']
    for row in means:
        lines.append(f"| {row['label']} | {row['n_reports']} | "+' | '.join(f"{row['mean_scores'][f]:.3f}" for f in FIELDS)+' |')
    lines+=['','无DML版本因R026失败只有9份有效内容评分，其余各10份。系统差异另按相同案例配对，不能将29份×2教师当作58个独立案例。','',
        '## 按案例配对的探索性差异','']
    for row in differences:
        lines.append(f"- {row['contrast']}，{row['dimension']}：{row['difference']:+.3f}，95%探索性重抽样区间[{row['exploratory_CI_low']:+.3f}, {row['exploratory_CI_high']:+.3f}]，{row['paired_cases']}对案例。")
    lines+=['','## 可以和不能得出的结论','',
        '- 本轮受控案例中，教师对建议与不确定性处理的评分普遍较高；因素清单仍存在背景项过宽、标签与证据不匹配和遗漏等问题。',
        '- 尚未建立完整智能体相对普通LLM或无DML版本的稳定优势。较高绝对分数不等于比较优势；当前小样本也不能证明系统等效或DML有害。',
        '- 不再因分数未支持研究预期而反复要求老师改分。可将当前复核记录收束，保存初始与复核两套结果及过程说明。',
        '- 如继续改进，应先定位模型的因素分类和事实支持问题，改动只用于开发；新的有效性检验需要新的独立测试材料，不能继续在这批已暴露案例上追求更高分。',
        '- 评分口径澄清后两位教师是否仍分别盲评，应按真实过程记录；本分析不假定再次证明了独立性。',
        '- 原工作簿、旧文本和原始实验输出未修改。']
    (OUT/'两位教师_口径澄清后复核汇总.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k in ['first_review_score_changes','current_reviewed_agreement',
        'system_descriptive_means','exploratory_paired_contrasts','rated_reports','source_files_unchanged']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
