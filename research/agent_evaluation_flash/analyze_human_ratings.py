"""Read-only source ingestion. Preserve initial and independently reviewed rater1."""
import csv
from collections import Counter,defaultdict
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import sys

import openpyxl
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'work/pisa_audit_deps'))
import numpy as np
from sklearn.metrics import cohen_kappa_score

SOURCE_INITIAL=Path('C:/Users/84130/Documents/completed_scoring_sheet_rater1.xlsx')
SOURCE_REVIEW=Path('C:/Users/84130/Documents/评分表_评分者1_复核修订版.xlsx')
SOURCE_SECOND=Path('C:/Users/84130/Documents/评分表2.txt')
ROOT=Path('D:/pisa2022/outputs_grade_agent_flash_multiturn_v2')
BASE=Path(__file__).resolve().parents[1]/'outputs/grade_agent_flash_20261025'
FIELDS=['因素合理性','建议适用性','不确定处理']
LABELS={'llm_baseline':'普通LLM','agent_critic_only':'无DML、有复核','agent_full':'完整智能体'}


def hashfile(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8'))


def normalize(value):
    if value is None or value=='':return None
    if isinstance(value,bool):raise ValueError('Boolean is not a valid ordinal rating')
    val=float(value)
    if val not in [0,1,2]:raise ValueError(f'Invalid ordinal score {value!r}')
    return int(val)


def read_xlsx(path):
    wb=openpyxl.load_workbook(path,read_only=True,data_only=False)
    ws=wb.worksheets[0]; records={}
    for row in ws.iter_rows(min_row=9,max_row=38,values_only=True):
        ident=row[1]
        if ident in records:raise ValueError('Duplicate report ID')
        records[ident]={'scores':[normalize(row[i]) for i in [3,4,5]],'note':row[7] or ''}
    wb.close();return records


def read_second(path):
    with path.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    records={}
    for row in rows:
        ident=row['报告编号']
        if ident in records:raise ValueError('Duplicate second-rater report ID')
        records[ident]={'scores':[normalize(row[field]) for field in FIELDS],'note':row.get('问题说明','') or ''}
    return records


def kappa_manual(a,b,power=1):
    n=len(a)
    observed=sum(abs(x-y)**power for x,y in zip(a,b))/n
    ca,cb=Counter(a),Counter(b)
    expected=sum(abs(x-y)**power*ca[x]*cb[y] for x in [0,1,2] for y in [0,1,2])/n**2
    return None if expected==0 else 1-observed/expected


def reliability(first,second,valid):
    result=[]
    for index,field in enumerate(FIELDS):
        a=[first[i]['scores'][index] for i in valid]
        b=[second[i]['scores'][index] for i in valid]
        manual=kappa_manual(a,b)
        verified=float(cohen_kappa_score(a,b,labels=[0,1,2],weights='linear'))
        if manual is None:
            assert np.isnan(verified)
        else:
            assert abs(manual-verified)<1e-12
        result.append({'dimension':field,'n_reports':len(valid),
            'exact_agreement':sum(x==y for x,y in zip(a,b))/len(valid),
            'linear_weighted_kappa':manual,'quadratic_weighted_kappa':kappa_manual(a,b,2),
            'rater1_mean':float(np.mean(a)),'rater2_mean':float(np.mean(b)),
            'rater1_distribution':dict(Counter(a)),'rater2_distribution':dict(Counter(b)),
            'disagreement_ids':[i for i in valid if first[i]['scores'][index]!=second[i]['scores'][index]]})
    return result


def main():
    sources=[SOURCE_INITIAL,SOURCE_REVIEW,SOURCE_SECOND]
    hashes={str(p):hashfile(p) for p in sources}
    first=read_xlsx(SOURCE_INITIAL);review=read_xlsx(SOURCE_REVIEW);second=read_second(SOURCE_SECOND)
    sample=load(ROOT/'restricted_human_sample_plan.json')
    slots={r['report_id']:r for r in sample['slots']}
    packet={r['report_id']:r for r in load(BASE/'packet_index.json')}
    assert set(first)==set(review)==set(second)==set(slots)==set(packet)
    valid=sorted(i for i in packet if packet[i]['status']=='completed')
    invalid=sorted(set(packet)-set(valid))
    assert len(valid)==29 and invalid==['R026']
    for records in [first,review,second]:
        assert all(all(v is not None for v in records[i]['scores']) for i in valid)
        assert all(all(v is None for v in records[i]['scores']) for i in invalid)
    changes=[{'report_id':i,'initial_scores':first[i]['scores'],'reviewed_scores':review[i]['scores'],
        'initial_note':first[i]['note'],'reviewed_note':review[i]['note']} for i in sorted(first)
        if first[i]!=review[i]]
    primary=reliability(review,second,valid)
    initial=reliability(first,second,valid)
    grouped=defaultdict(list);paired=defaultdict(dict)
    for ident in valid:
        slot=slots[ident]
        average=[(x+y)/2 for x,y in zip(review[ident]['scores'],second[ident]['scores'])]
        grouped[slot['system']].append(average)
        paired[slot['case_id']][slot['system']]=average
    means=[]
    for system,label in LABELS.items():
        arr=np.array(grouped[system])
        means.append({'system':system,'label':label,'n_reports':len(arr),
            'mean_scores':{field:float(arr[:,i].mean()) for i,field in enumerate(FIELDS)}})
    rng=np.random.default_rng(20261025)
    differences=[]
    for comparator in ['llm_baseline','agent_critic_only']:
        case_ids=sorted(c for c,values in paired.items() if 'agent_full' in values and comparator in values)
        for j,field in enumerate(FIELDS):
            vals=np.array([paired[c]['agent_full'][j]-paired[c][comparator][j] for c in case_ids])
            bs=vals[rng.integers(0,len(vals),(10000,len(vals)))].mean(axis=1)
            low,high=np.quantile(bs,[.025,.975])
            differences.append({'dimension':field,'contrast':'完整智能体减'+LABELS[comparator],
                'paired_cases':len(case_ids),'case_ids':case_ids,'mean_difference':float(vals.mean()),
                'exploratory_bootstrap_CI_low':float(low),'exploratory_bootstrap_CI_high':float(high)})
    records=[]
    for ident in sorted(slots):
        records.append({'report_id':ident,'case_id':slots[ident]['case_id'],'system':slots[ident]['system'],
            'generation_status':packet[ident]['status'],
            'rater1_initial':first[ident],'rater1_reviewed':review[ident],'rater2':second[ident]})
    result={'created':datetime.now(timezone.utc).isoformat(),'source_hashes':hashes,
        'provenance':'User confirms both are teachers; rater1 self-reviewed without seeing rater2 scores/comments.',
        'scope':'29 rated reports from ten sampled controlled synthetic cases, not all300 outputs or real students',
        'status':'provisional_raw_ratings_not_adjudicated','rater1_review_changes':changes,
        'primary_reviewed_vs_rater2_reliability':primary,'sensitivity_initial_vs_rater2_reliability':initial,
        'system_means_raters_averaged':means,'exploratory_paired_contrasts':differences,
        'rated_reports':29,'sampled_cases':10,'excluded_generation_failure':invalid,
        'all_source_files_unchanged':all(hashfile(p)==hashes[str(p)] for p in sources),
        'method_notes':['Scores have ceiling effects; high raw agreement is not equivalent to high chance-corrected agreement.',
            'Original and reviewed ratings retained separately; no selective posthoc score changes.',
            'Case-paired contrasts average the two raters; ratings of the same report are not independent observations.',
            'No arbitrary total score or confirmatory p-values.',
            'Unresolved scoring rationale differences require clarification before manuscript claims.'],
        'records':records}
    destination=BASE/'human_rating_analysis'
    destination.mkdir(exist_ok=True)
    (destination/'两位教师评分分析.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 两位教师评分：初步核验与比较','',
        '来源为评分者1原版、评分者1本人独立复核版及评分者2文本文件。用户确认评分者1复核时未参考评分者2。使用复核版作当前汇总，原版作为敏感性记录保留；没有改动任何输入文件。','',
        '30个预定报告编号均齐全；29份报告两人均有三个合法分数，R026生成失败，双方均留空。对应10个抽样合成案例，不代表300场全部获教师验证。','',
        '## 复核记录','',
        '评分者1仅将R005因素合理性由1改为2；R020仍为1，修订了理由，不再因引用群体研究本身扣分。其他数值未变。','',
        '## 评分一致性（复核版与评分者2）','',
        '| 维度 | 完全一致比例 | 线性加权κ | 教师1均分 | 教师2均分 |','|---|---:|---:|---:|---:|']
    for row in primary:
        lines.append(f"| {row['dimension']} | {row['exact_agreement']:.1%} | {row['linear_weighted_kappa']:.3f} | {row['rater1_mean']:.3f} | {row['rater2_mean']:.3f} |")
    lines+=['','κ按0、1、2的序数差异线性加权；与scikit-learn实现交叉核验。定义参考：https://scikit-learn.org/stable/modules/generated/sklearn.metrics.cohen_kappa_score.html','',
        '建议适用性与不确定性处理两项，教师1全部给2分，教师2多数给2分。高完全一致比例主要集中在最高档，不能据此宣称校正偶然一致后的信度高；κ=0也不等于两人所有判断相反。','',
        '## 系统描述性均分（两人平均，每项满分2）','',
        '| 系统 | 有效报告数 | 因素合理性 | 建议适用性 | 不确定处理 |','|---|---:|---:|---:|---:|']
    for row in means:
        lines.append(f"| {row['label']} | {row['n_reports']} | "+' | '.join(f"{row['mean_scores'][f]:.3f}" for f in FIELDS)+' |')
    lines+=['','不同系统的有效报告数可能不同，不能只按不配对均分比较。R026保持缺失，不填0也不替换。','',
        '## 配对差异（探索性）','',
        '先对同一报告的两名教师取平均，再按相同案例配对，按案例重抽样10000次。小样本、序数评分及天花板效应限制解释；不报告确认性p值。','']
    for row in differences:
        lines.append(f"- {row['contrast']}，{row['dimension']}：{row['mean_difference']:+.3f}，探索性95%区间[{row['exploratory_bootstrap_CI_low']:+.3f}, {row['exploratory_bootstrap_CI_high']:+.3f}]，{row['paired_cases']}对案例。")
    lines+=['','## 需要澄清的评分口径（不自动改分）','',
        '- 评分者2对R005、R022、R023注明“无可用事实，未编造因素”，但因素合理性给1分。需确认是因信息不足本身扣分，还是报告确有遗漏/不当判断。正确暂缓不应仅因案例本身缺信息而受罚。',
        '- 评分者2对R020提到混入PISA/SHAP/DML元信息并三项扣分。应区分单纯引用已提供群体证据、表达过于技术化，以及实际个体归因越界；不同理由不可混用。',
        '- 正常或保护性条件被列为因素时，双方扣分尺度不完全相同。保留原始分歧，先各自说明依据，不根据哪个系统受益而统一分数。',
        '- 澄清应以统一准则覆盖全部报告，保留初始与复核版本。若双方交流后形成裁决，该裁决不能冒充初始独立一致性。','',
        '当前结果应作为未裁决的初步人工评价，不能凭高均分或少数差异宣称系统已经证明提高真实学生诊断或教学效果。']
    (destination/'两位教师评分_初步分析.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['records','source_hashes','method_notes','rater1_review_changes']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
