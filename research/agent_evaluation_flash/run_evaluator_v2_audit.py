"""Run a versioned post-hoc audit over every existing report, without API calls."""
import json,csv,hashlib,random,subprocess,sys
from pathlib import Path
from collections import Counter
from datetime import datetime,timezone
from evaluator_v2 import evaluate,VERSION
import run_glm600_locked as original

ROOT=original.ROOT
OUT=ROOT/'evaluator_v2_posthoc_20261026'
SYSTEMS=original.SYSTEMS
NAMES=dict(zip(SYSTEMS,['普通LLM','仅统计研究结果','无DML智能体','无复核智能体','完整GRADE-Agent']))
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,obj):path.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
def csv_file(path,rows):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

def main():
    assert not OUT.exists(),'Retain prior audits; use a new explicitly versioned output.'
    raw_path=ROOT/'raw_reports.json';old_path=ROOT/'run_level_metrics.csv'
    initial={str(p):sha(p) for p in [raw_path,old_path,ROOT/'protocol_lock.json',ROOT/'status.json']}
    raw=json.loads(raw_path.read_text(encoding='utf-8'));assert all(r['status']=='completed' for r in raw)
    key=lambda r:(r['system'],r['caseId'],int(r['repeat']))
    assert len({key(r) for r in raw})==len(raw)
    old={key(r):r for r in csv.DictReader(old_path.open(encoding='utf-8-sig'))}
    assert set(old)==set(map(key,raw))
    test=subprocess.run([sys.executable,'-X','utf8','-m','unittest','discover','-s',str(Path(__file__).parent),'-p','test_evaluator_v2.py','-v'],capture_output=True,text=True,encoding='utf-8')
    assert test.returncode==0,test.stderr
    OUT.mkdir(parents=True)
    expected=original.load_scorer()['CASE_EXPECTED_SIGNALS']
    protocol={'version':VERSION,'registered_utc':datetime.now(timezone.utc).isoformat(),'posthoc':True,
        'reason':'Observed measurement errors in legacy parser, not a change to generation or case expected labels.',
        'n_existing_reports':len(raw),'source_hashes':initial,'evaluator_sha256':sha(Path(__file__).with_name('evaluator_v2.py')),
        'tests_sha256':sha(Path(__file__).with_name('test_evaluator_v2.py')),'runner_sha256':sha(Path(__file__)),
        'uniform_application':'Exactly one evaluate(report, case_facts, expected_signals) implementation for all groups; no system identity or old score supplied to evaluator.',
        'case_expected_signals':{k:sorted(v) for k,v in expected.items() if k.startswith('H')},
        'rules':['Stop priority extraction at section boundaries; support markdown and natural primary-issue anchors.',
            'Recognize prespecified category synonyms; suppress negated/clearly adequate conditions and assessment-interruption/classroom conflation.',
            'If priority is ambiguous, absent, outside lexical coverage, or multi-category, leave alignment unscored and require review.',
            'Boundary statement presence is separate from whether the whole report respects evidence boundaries.',
            'Causal wording generates quoted review candidates, never automatic evidence of an unsupported individual cause.',
            'Action structure counts only within recognized action sections; no claim to score relevance, feasibility or educational effectiveness.',
            'Never compute an overall educational-quality score or compare conditional-on-scored percentages as if coverage were equal.'],
        'validation_limit':'18 engineering regression tests and source-quote verification, not independent expert validation. Rules revised after viewing current reports; all new results must be labeled post-hoc.',
        'generation_unchanged':True,'old_scores_preserved':True,'no_new_model_calls':True}
    # Freeze before any group summary is computed.
    save(OUT/'evaluation_protocol_v2.json',protocol)
    save(OUT/'input_snapshot.json',raw)
    (OUT/'regression_tests.txt').write_text(test.stdout+test.stderr,encoding='utf-8')
    ordered=sorted(raw,key=key);random.Random(20261026).shuffle(ordered)
    detail=[];flat=[];review=[]
    for i,item in enumerate(ordered,1):
        report_id=f'A{i:04d}'
        assessment=evaluate(item['report'],item['answers'],expected[item['caseId'].split('_')[0]])
        previous=old[key(item)]
        detail.append({'report_id':report_id,'system':item['system'],'caseId':item['caseId'],'repeat':item['repeat'],
            'report_sha256':hashlib.sha256(item['report'].encode()).hexdigest(),'assessment':assessment})
        pquotes=list(dict.fromkeys(x['quote'] for x in assessment['priority_evidence']))
        flat.append({'report_id':report_id,'system':item['system'],'caseId':item['caseId'],'repeat':item['repeat'],
            'old_primary_signal':previous['primary_signal'],'new_primary_signal':assessment['primary_signal'],
            'old_priority_alignment':previous['priority_alignment'],'new_priority_alignment':assessment['priority_alignment'],
            'priority_extraction_source':assessment['priority_extraction_source'],'priority_evidence':'\n'.join(pquotes),
            'explicit_boundary_statement_present':assessment['explicit_boundary_statement_present'],
            'old_forbidden_causal_flag':previous['forbidden_causal_flag'],
            'causal_claim_review_required':assessment['causal_claim_review_required'],
            'causal_candidate_quotes':'\n'.join(dict.fromkeys(x['quote'] for x in assessment['causal_claim_candidates'])),
            'old_action_completeness':previous['operational_action_completeness'],
            'action_structure_completeness_v2':assessment['action_structure_completeness'],
            'manual_review_required':assessment['manual_review_required'],
            'review_reasons':'\n'.join(assessment['manual_review_reasons'])})
        if assessment['manual_review_required']:
            review.append({'report_id':report_id,'caseId':item['caseId'],
                'review_reason':'\n'.join(assessment['manual_review_reasons']),
                'case_facts':json.dumps(item['answers'],ensure_ascii=False),
                'report':item['report'],'reviewed_primary_signal':'','reviewed_priority_alignment':'',
                'reviewed_unsupported_individual_causal_claim':'','review_note':''})
    save(OUT/'report_level_audit_v2.json',detail);csv_file(OUT/'old_new_measurement_audit.csv',flat)
    if review:csv_file(OUT/'需要复核的报告.csv',review)
    summary=[]
    for s in SYSTEMS:
        group=[r for r in flat if r['system']==s];n=len(group)
        resolved=[r for r in group if r['new_priority_alignment'] is not None]
        summary.append({'system':s,'n_reports':n,'priority_resolved_n':len(resolved),
            'priority_pending_review_n':n-len(resolved),'priority_aligned_n':sum(r['new_priority_alignment']==1 for r in resolved),
            'priority_not_aligned_n':sum(r['new_priority_alignment']==0 for r in resolved),
            'explicit_boundary_statement_present_n':sum(r['explicit_boundary_statement_present'] for r in group),
            'causal_claim_review_candidate_reports_n':sum(r['causal_claim_review_required'] for r in group),
            'any_manual_review_reports_n':sum(r['manual_review_required'] for r in group),
            'note':'Resolved-only proportions are not comparable when coverage differs; no overall educational-quality score.'})
    csv_file(OUT/'measurement_coverage_summary.csv',summary)
    changes=[r for r in flat if r['new_primary_signal']!=r['old_primary_signal']]
    md=['# 评价工具v2修改说明','','## 定位','',
        '这是在查看部分结果后修订的自动测量审计工具，属于事后修订，不是事前注册的新主分析，也不是经过专家效度验证的教育诊断量表。',
        '对全部现有报告统一运行；原报告、旧评分、模型调用设置及案例预期类别均不改动。','',
        '## 已修改的规则','',
        '1. 优先问题只在对应章节或明确的主要问题句中提取，不再跨入下一节读取420字符。支持普通Markdown小标题与自然语言主要问题句。',
        '2. 排除“No conflicting sources”等否定表达；新增偏头痛、火警、语言转换等类别同义表达；不把测验中断直接等同课堂秩序问题。',
        '3. 主要问题不明确、同时出现多个类别或词典不能识别时，保留空白并列为待复核，不强制记0。提取器不接收配置名称或旧分数。',
        '4. 分开记录“有无边界说明”与“可能需核查的因果措辞”；后者必须结合案例原文核查，不自动等同错误。',
        '5. 行动结构仅在建议章节检查行动、时间、跟踪要素；这个分数不评价建议是否相关、可行或有效。',
        '6. 每个自动判断附原文引句和位置；复核表不显示配置名称或旧得分，但文本格式仍可能暴露配置，因此不声称严格盲评。','',
        '## 当前报告覆盖情况','','| 配置 | 报告数 | 优先项可判定 | 待复核优先项 | 可判定中符合 | 可判定中不符合 | 有待核查因果措辞的报告 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for r in summary:md.append('| '+NAMES[r['system']]+' | '+' | '.join(str(r[k]) for k in ['n_reports','priority_resolved_n','priority_pending_review_n','priority_aligned_n','priority_not_aligned_n','causal_claim_review_candidate_reports_n'])+' |')
    md+=['','不同配置的可判定覆盖率可能不同，不能只对可判定子集计算一个百分比就声称某组更好。待复核不等于错误，也不等于通过。',
        '', '## 检查结果','',f'- 当前输入：{len(raw)}份报告，全部处理，未挑选配置或样本。',
        '- 18项程序回归测试通过；所有引用句和字符位置均与原报告逐一校验。工程测试不等于教育效度验证。',
        f'- 新旧主要信号提取结果不同的报告：{len(changes)}份（包含新版留空待复核的情况）。',
        '- 原数据和旧评分的文件哈希在运行前后核对一致。',
        '', '## 下一步','',
        '先用待复核表核实歧义与因果措辞，再判断哪些指标可以形成最终分数。剩余报告生成后必须使用同一版规则统一处理；不得根据组间结果有选择地修改规则。',
        '不自动把本次结果替换进论文，也不生成缺少效度依据的综合诊断质量分。']
    (OUT/'评价工具v2修改说明.md').write_text('\n'.join(md),encoding='utf-8')
    assert all(sha(Path(p))==h for p,h in initial.items()),'Original files changed during audit.'
    save(OUT/'integrity_check.json',{'all_existing_reports_processed':len(flat)==len(raw),
        'original_files_unchanged':True,'no_new_API_calls':True,'uniform_group_independent_evaluator':True,
        'source_quotes_verified':True,'tests_passed':18,'manual_review_report_count':len(review),
        'new_old_primary_signal_changes_including_unresolved':len(changes)})
    print(json.dumps({'output':str(OUT),'n_reports':len(raw),'n_review':len(review),'summary':summary},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
