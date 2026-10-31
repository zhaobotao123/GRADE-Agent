"""Latest teacher2 file, separately versioned; no source scores edited."""
from collections import defaultdict
from datetime import datetime,timezone
import json
from pathlib import Path
import warnings

from analyze_human_ratings import read_xlsx,read_second,reliability,hashfile,FIELDS,LABELS,ROOT,BASE,np

FIRST=Path('C:/Users/84130/Documents/评分表_评分者1_复核说明补充版.xlsx')
SECOND=Path('C:/Users/84130/Documents/deepseek_csv_20261025_3e2045.txt')
PREVIOUS=BASE/'human_rating_review2/评分者2_用户提供复核文本.csv'
OUT=BASE/'human_rating_review3'


def load(path):return json.loads(path.read_text(encoding='utf-8'))
def show(value):return '不可计算' if value is None else f'{value:.3f}'


def main():
    hashes={str(p):hashfile(p) for p in [FIRST,SECOND,PREVIOUS]}
    a=read_xlsx(FIRST);b=read_second(SECOND);old=read_second(PREVIOUS)
    slots={r['report_id']:r for r in load(ROOT/'restricted_human_sample_plan.json')['slots']}
    index={r['report_id']:r for r in load(BASE/'packet_index.json')}
    assert set(a)==set(b)==set(old)==set(slots)==set(index)
    ids=sorted(i for i in index if index[i]['status']=='completed')
    assert len(ids)==29
    for records in [a,b]:
        assert all(all(x is not None for x in records[i]['scores']) for i in ids)
        assert records['R026']['scores']==[None,None,None]
    changes=[{'report_id':i,'dimension':field,'previous':old[i]['scores'][j],'current':b[i]['scores'][j]}
        for i in sorted(b) for j,field in enumerate(FIELDS) if old[i]['scores'][j]!=b[i]['scores'][j]]
    with warnings.catch_warnings():
        warnings.simplefilter('ignore',RuntimeWarning)
        agreement=reliability(a,b,ids)
    groups=defaultdict(list);paired=defaultdict(dict)
    for i in ids:
        scores=[(x+y)/2 for x,y in zip(a[i]['scores'],b[i]['scores'])]
        groups[slots[i]['system']].append(scores)
        paired[slots[i]['case_id']][slots[i]['system']]=scores
    means=[]
    for system,label in LABELS.items():
        arr=np.asarray(groups[system])
        means.append({'system':system,'label':label,'reports':len(arr),
            'scores':{f:float(arr[:,j].mean()) for j,f in enumerate(FIELDS)}})
    rng=np.random.default_rng(20261025);contrasts=[]
    for other in ['llm_baseline','agent_critic_only']:
        cases=sorted(c for c,v in paired.items() if 'agent_full' in v and other in v)
        for j,field in enumerate(FIELDS):
            delta=np.array([paired[c]['agent_full'][j]-paired[c][other][j] for c in cases])
            bs=delta[rng.integers(0,len(delta),(10000,len(delta)))].mean(axis=1)
            lo,hi=np.quantile(bs,[.025,.975])
            contrasts.append({'comparison':'完整智能体减'+LABELS[other],'dimension':field,'paired_cases':len(cases),
                'difference':float(delta.mean()),'exploratory_CI':[float(lo),float(hi)]})
    result={'stage':'latest_postclarification_teacher2_review_not_initial_independent_reliability',
        'created':datetime.now(timezone.utc).isoformat(),'source_hashes':hashes,'score_changes_vs_previous':changes,
        'agreement':agreement,'system_means':means,'case_paired_contrasts':contrasts,
        'rated_reports':29,'sampled_cases':10,'not_rated':['R026'],
        'inputs_unchanged':all(hashfile(Path(p))==h for p,h in hashes.items()),
        'earlier_analyses_preserved':True,
        'records':[{'report_id':i,'case_id':slots[i]['case_id'],'system':slots[i]['system'],
                    'teacher1':a[i],'teacher2':b[i]} for i in sorted(index)]}
    OUT.mkdir(exist_ok=True)
    (OUT/'最新评分者2_复核分析.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# 最新评分者2文件：更新后的复核汇总','',
        f'本次使用用户新指定文件“{SECOND.name}”，不再沿用上一条消息粘贴的老师2评分。第一位教师仍使用复核说明补充版。输入文件及早期分析均未修改。','',
        '30个编号齐全；29份有效报告双方各有三个合法分数，R026双方留空。','',
        '## 与上一版老师2评分的数值差异','']
    for c in changes:lines.append(f"- {c['report_id']}，{c['dimension']}：{c['previous']} → {c['current']}。")
    lines+=['','这次是数值确有变化的新版本，并非前一轮汇总算错。应保留评分修订理由；不要求为提高一致性或系统分数而再次改分。','',
        '## 当前版本的系统均分（两位教师平均，每项满分2）','',
        '| 系统 | 有效报告数 | 因素合理性 | 建议适用性 | 不确定处理 |','|---|---:|---:|---:|---:|']
    for row in means:lines.append(f"| {row['label']} | {row['reports']} | "+' | '.join(f"{row['scores'][f]:.3f}" for f in FIELDS)+' |')
    lines+=['','无DML版本有9份有效报告，其他各10份；失败报告不填0，比较另按同一案例配对。','',
        '## 当前复核版本的一致性','',
        '| 维度 | 完全一致率 | 线性加权κ |','|---|---:|---:|']
    for row in agreement:lines.append(f"| {row['dimension']} | {row['exact_agreement']:.1%} | {show(row['linear_weighted_kappa'])} |")
    lines+=['','建议适用性双方对所有有效报告都给2分，完全一致率为100%，但κ的分母为0，不能计算。不能把它记作κ=1或κ=0。不确定处理仍因一位教师恒给2分而呈现κ=0。两项均存在严重天花板效应。',
        '这些都是多次口径澄清后的复核指标，不应替换最初独立评分一致性。初始及中间版本继续保留。','',
        '## 案例配对比较（探索性）','']
    for c in contrasts:lines.append(f"- {c['comparison']}，{c['dimension']}：{c['difference']:+.3f}，95%探索性区间[{c['exploratory_CI'][0]:+.3f}, {c['exploratory_CI'][1]:+.3f}]，{c['paired_cases']}对案例。")
    lines+=['','## 解释限制','',
        '- 仅10个抽样合成案例、29份有效报告。高绝对均分和很少的评分档位变化不等于真实学生诊断能力或教学效益已获验证。',
        '- 本轮没有建立完整系统相对普通LLM或无DML版本的稳定比较优势。微小均分差不能作为稳定改进，也不能据此证明等效或DML有害。',
        '- R009仍有“建议较笼统”的评语，但建议适用性已从1改2；R002、R011等此前明确指出标签错配的评分也上调且未保留解释。建议记录这些改动的准则依据，而不是继续追求更高分或更高κ。',
        '- 不新增或代填任何教师评分；不改变系统输出、抽样案例或初始实验标签。']
    (OUT/'最新评分者2_复核汇总.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['records','source_hashes']},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
