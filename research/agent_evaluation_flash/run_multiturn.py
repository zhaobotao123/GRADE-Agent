"""Bounded, domain-routed multi-turn pilot; credentials only in memory.

No expert ratings or independent gold labels are fabricated by this program.
"""
import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime,timezone
import hashlib
import json
import os
from pathlib import Path
import random
import sys
import threading
import time
from urllib.error import HTTPError
from urllib.request import Request,urlopen

from prepare_cases import ROOT,DOMAINS,FACTORS

WORK=Path(__file__).resolve().parent
EVIDENCE=Path('D:/pisa2022/outputs_grade_agent_japan_reanalysis_v1/grade_agent_japan_complete_candidate.json')
SYSTEMS=['llm_baseline','agent_no_dml_no_critic','agent_dml_only','agent_critic_only','agent_full']
MODEL='deepseek-flash'
API='https://api.deepseek.com'
mutex=threading.Lock()
calls=0


def now(): return datetime.now(timezone.utc).isoformat()
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix('.tmp')
    tmp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8')
    tmp.replace(path)


def prompts():
    shared=('你正与一位家长或教师进行数学学习咨询。先根据已知事实决定是否需要追问，再给出有事实依据的候选因素和下一步建议。'
        '所有输出使用中文及JSON。最多有五次追问机会；每次只能询问一个领域。'
        '可询问领域：confidence(信心与考试感受)、classroom(课堂情况)、support(帮助与时间顺序)、context(健康出勤语言与安全)、resources(家庭与学习资源)。'
        '每次询问后系统返回该领域已记录的事实；这是受控访谈，不是真实学生模拟。'
        '问题格式：{"phase":"question","domain":"上述一个领域","question":"具体问题"}。'
        '总结格式：{"phase":"assessment","decision":"provisional或insufficient_information或safety_escalation",'
        '"factors":[{"id":"因素代码","domain":"事实所在领域","case_quote":"逐字引用已收到的一段案例事实"}],'
        '"missing_information":["尚需了解的内容"],"report":"250至450字左右的中文报告，包含判断、依据及适当的下一步建议"}。'
        '因素代码只能从以下集合选取：'+','.join(FACTORS)+
        '。这些只是报告编码：confidence学习信心；anxiety数学考试担忧；classroom课堂环境；support_timing支持时序；belonging归属；'
        'school_ict学校ICT；home_resources家庭学习资源；family_engagement家庭学习安排；language教学语言；health_attendance健康出勤；'
        'assessment_event单次测验事件；independent_work独立解题；bullying同伴威胁或欺凌。'
        '仅作为待询问领域、不确定的可能性，不列作已识别因素。未知信息保留未知，不能据此推断诊断。')
    agent=('使用结构化咨询流程：区分成绩轨迹与候选解释；检查事实来源、时间顺序和信息缺口。'
        '只在案例已支持的候选中组织解释；人口分析不能证明这个学生的原因。'
        '对直接安全披露及时建议人工介入；一般未报告安全信息保留为未知。'
        '建议与案例因素对应、可行且可以复核，不凭负向人口关联减少支持。')
    evidence=json.loads(EVIDENCE.read_text(encoding='utf-8'))
    predictive=('预测分析：日本5112人共同样本，留出学校LightGBM平均加权R²=.477，RMSE=65.95；'
        'MATHEFF的预测SHAP贡献最大。SHAP描述预测，不证明因果或个体原因。')
    dml=['日本PISA2022重分析的DML人口条件关联，背景调整/多因素调整系数如下；不同量表不能按原始系数排序。']
    for row in evidence['records']:
        dml.append(f"{row['variable_code']}({row['variable_name_zh']}): "
            f"{row['background_adjusted_coefficient']:.2f}/{row['mutually_adjusted_coefficient']:.2f}; "
            f"多因素95%区间{[round(x,2) for x in row['confidence_interval']]}; BHq={row['bh_q_value']:.3g}。")
    dml.append('教师支持、归属感及焦虑等依赖调整规格；没有显著结果不代表教育上无关。DML识别假设尚未确立，不得写为这个学生的因果真值。')
    dml='\n'.join(dml)
    critic=('输出前在内部检查并修正：每个因素是否有已收到的案例事实支持，是否遗漏重要事实，'
        '支持和困难的时间先后是否说反，是否把未知当不存在，是否发生安全延误，建议是否匹配。不要输出评分或内部检查过程。')
    return {'llm_baseline':shared,
        'agent_no_dml_no_critic':shared+'\n'+agent+'\n'+predictive,
        'agent_dml_only':shared+'\n'+agent+'\n'+predictive+'\n'+dml,
        'agent_critic_only':shared+'\n'+agent+'\n'+predictive+'\n'+critic,
        'agent_full':shared+'\n'+agent+'\n'+predictive+'\n'+dml+'\n'+critic}


def prepare():
    payload=json.loads((ROOT/'cases_author_reference.json').read_text(encoding='utf-8'))
    fixed={'model':MODEL,'systems':SYSTEMS,'temperature':.4,'max_tokens':1000,'max_questions':5,
        'thinking':'disabled','prompts':prompts(),'case_sha256':sha(ROOT/'cases_author_reference.json'),
        'source_hashes':{str(p):sha(p) for p in [Path(__file__),WORK/'prepare_cases.py',EVIDENCE]},
        'pilot':{'split':'dev','repeats':1,'sessions':50,'max_logical_calls':300},
        'formal_plan':{'split':'test','repeats':2,'sessions':300,'status':'planned_not_generated'},
        'reference_validation':'author_constructed_not_expert_validated',
        'scope':'adaptive_domain_queries_with_deterministic_fact_oracle_not_free_form_student_simulation'}
    fixed['signature']=hashlib.sha256(json.dumps(fixed,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
    lock=ROOT/'protocol_lock.json'
    if lock.exists():
        old=json.loads(lock.read_text(encoding='utf-8'))
        if old['signature']!=fixed['signature']: raise RuntimeError('Protocol changed; use new run directory.')
    else: save(lock,fixed)
    # Choose one test case per family BEFORE test generations and blind the 30 report slots.
    rng=random.Random(20261025)
    selected=[]
    for family in sorted({r['family'] for r in payload['cases']}):
        selected.append(rng.choice([r for r in payload['cases'] if r['split']=='test' and r['family']==family])['case_id'])
    slots=[{'case_id':c,'system':s,'repeat':1} for c in selected for s in ['llm_baseline','agent_critic_only','agent_full']]
    rng.shuffle(slots)
    slots=[{'report_id':f'R{i:03}',**r} for i,r in enumerate(slots,1)]
    plan={'selected_test_cases':selected,'selected_repeat':1,'slots':slots,
        'selection_rule':'one seeded-random test case per scenario family, before outputs',
        'status':'reserved_slots_reports_not_generated','signature':fixed['signature']}
    path=ROOT/'restricted_human_sample_plan.json'
    if not path.exists(): save(path,plan)
    else: assert json.loads(path.read_text(encoding='utf-8'))==plan
    return fixed,payload['cases']


def api(path,key,body=None):
    req=Request(API+path,data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    with urlopen(req,timeout=120) as response: return json.loads(response.read().decode())


def call_model(body,key,target,signature,max_calls):
    global calls
    if target.exists():
        row=json.loads(target.read_text(encoding='utf-8'))
        assert row['signature']==signature
        return row
    for attempt in range(2):
        with mutex:
            if calls>=max_calls: raise RuntimeError('Invocation call budget reached; checkpoints preserved.')
            calls+=1
        start=time.monotonic()
        try:
            response=api('/chat/completions',key,body)
            choice=response['choices'][0]
            content=choice['message'].get('content','')
            row={'signature':signature,'model_returned':response.get('model'),'response_id':response.get('id'),
                'usage':response.get('usage',{}),'finish_reason':choice.get('finish_reason'),
                'content':content,'timestamp':now(),'elapsed_seconds':time.monotonic()-start,'attempt':attempt+1}
            save(target,row)
            return row
        except HTTPError as exc:
            if exc.code in [400,401,402,403,404] or attempt==1:
                raise RuntimeError(f'API HTTP {exc.code}; no model substitution') from None
        except Exception as exc:
            if attempt==1: raise RuntimeError('Request failed: '+type(exc).__name__) from None
        time.sleep(2)


def session(case,system,repeat,lock,key,stage,max_calls):
    folder=ROOT/stage/'sessions'/f"{case['case_id']}_{system}_{repeat}"
    complete=folder/'session.json'
    if complete.exists():
        row=json.loads(complete.read_text(encoding='utf-8')); assert row['signature']==lock['signature']; return row
    messages=[{'role':'system','content':lock['prompts'][system]},
        {'role':'user','content':'已知情况：'+case['opening']+'\n请开始咨询。'}]
    revealed=[]; turns=[]; assessment=None
    for index in range(6):
        if index==5:
            messages.append({'role':'user','content':'追问机会已用完，请仅基于已收到事实给出assessment格式总结；不足之处保留未知。'})
        body={'model':MODEL,'messages':messages,'temperature':.4,'max_tokens':1000,
            'thinking':{'type':'disabled'},'response_format':{'type':'json_object'},'stream':False}
        raw=call_model(body,key,folder/f'call_{index+1}.json',lock['signature'],max_calls)
        try:
            parsed=json.loads(raw['content'])
            if not isinstance(parsed,dict): raise ValueError('not object')
        except (ValueError,TypeError):
            turns.append({'turn':index+1,'raw':raw,'error':'invalid_JSON'}); break
        turns.append({'turn':index+1,'raw':raw,'parsed':parsed,'revealed_before':revealed.copy()})
        messages.append({'role':'assistant','content':raw['content']})
        if parsed.get('phase')=='assessment': assessment=parsed; break
        domain=parsed.get('domain')
        if parsed.get('phase')!='question' or domain not in DOMAINS or index==5:
            turns[-1]['error']='invalid_phase_or_domain'; break
        if domain in revealed:
            reply='这个领域的信息已经提供，没有额外记录；请根据既有内容决定下一步。'
            turns[-1]['duplicate_domain']=True
        else:
            revealed.append(domain)
            reply=f"{domain}领域已记录事实：{case['facts'][domain]}"
        messages.append({'role':'user','content':reply})
    row={'case_id':case['case_id'],'family':case['family'],'split':case['split'],'system':system,'repeat':repeat,
        'signature':lock['signature'],'revealed_domains':revealed,'turns':turns,'assessment':assessment,
        'status':'completed' if assessment is not None else 'invalid_output',
        'scope':'controlled_case_candidate_identification_not_real_student_causal_diagnosis'}
    save(complete,row)
    return row


def score(row,case):
    assessment=row['assessment'] or {}
    entries=assessment.get('factors',[])
    if not isinstance(entries,list): entries=[]
    pred={str(x.get('id','INVALID')) for x in entries if isinstance(x,dict)}
    truth=set(sum(case['author_reference_factors_by_domain'].values(),[]))
    observed=set(sum([case['author_reference_factors_by_domain'].get(d,[]) for d in row['revealed_domains']],[]))
    tp,fp,fn=len(pred&truth),len(pred-truth),len(truth-pred)
    quote_checks=[]
    for entry in entries:
        if isinstance(entry,dict):
            domain=entry.get('domain'); quote=entry.get('case_quote')
            quote_checks.append(bool(domain in row['revealed_domains'] and isinstance(quote,str) and len(quote)>=4 and quote in case['facts'].get(domain,'')))
    required=set(case['required_inquiry_domains'])
    return {'case_id':row['case_id'],'family':row['family'],'system':row['system'],'repeat':row['repeat'],
        'valid_final':row['assessment'] is not None,'tp':tp,'fp':fp,'fn':fn,
        'reference_nonempty':bool(truth), 'precision':tp/(tp+fp) if tp+fp else None,
        'recall':tp/(tp+fn) if tp+fn else None,
        'f1':2*tp/(2*tp+fp+fn) if truth else None,
        'reference_empty_no_factor_assertion':not pred if not truth else None,
        'reference_empty_correct_abstention':bool(not pred and assessment.get('decision')=='insufficient_information') if not truth else None,
        'predicted_factors':sorted(pred),'author_reference_factors':sorted(truth),
        'unrevealed_reference_factor_assertions':len((pred&truth)-observed),
        'unknown_factor_codes':len(pred-set(FACTORS)),
        'required_domain_coverage':len(required&set(row['revealed_domains']))/len(required),
        'question_count':sum(t.get('parsed',{}).get('phase')=='question' for t in row['turns']),
        'duplicate_questions':sum(t.get('duplicate_domain',False) for t in row['turns']),
        'assessment_before_required_domains':row['assessment'] is not None and not required<=set(row['revealed_domains']),
        'safety_escalation':assessment.get('decision')=='safety_escalation' if 'bullying' in truth else None,
        'exact_case_quote_rate':sum(quote_checks)/len(quote_checks) if quote_checks else None}


def summarize(lock,cases,stage,repeats):
    selected={r['case_id']:r for r in cases if r['split']==('dev' if stage=='pilot' else 'test')}
    rows=[]
    for path in sorted((ROOT/stage/'sessions').glob('*/session.json')):
        row=json.loads(path.read_text(encoding='utf-8')); assert row['signature']==lock['signature']; rows.append(row)
    metrics=[score(r,selected[r['case_id']]) for r in rows]
    save(ROOT/stage/'session_metrics.json',metrics)
    summary=[]
    for system in SYSTEMS:
        group=[r for r in metrics if r['system']==system]
        def mean(field):
            vals=[r[field] for r in group if r[field] is not None]
            return sum(vals)/len(vals) if vals else None
        summary.append({'system':system,'sessions':len(group),'valid_final_rate':mean('valid_final'),
            'mean_nonempty_reference_F1':mean('f1'),'required_domain_coverage':mean('required_domain_coverage'),
            'empty_reference_correct_abstention':mean('reference_empty_correct_abstention'),
            'early_assessment_proxy_rate':mean('assessment_before_required_domains'),
            'exact_case_quote_rate':mean('exact_case_quote_rate')})
    save(ROOT/stage/'automatic_summary.json',summary)
    callsaved=[]
    for path in (ROOT/stage/'sessions').glob('*/call_*.json'):
        callsaved.append(json.loads(path.read_text(encoding='utf-8')))
    usage={'prompt_tokens':sum(r['usage'].get('prompt_tokens',0) for r in callsaved),
        'completion_tokens':sum(r['usage'].get('completion_tokens',0) for r in callsaved)}
    usage['estimated_USD_off_peak_no_cache']=usage['prompt_tokens']*.15/1e6+usage['completion_tokens']*.6/1e6
    usage['estimated_USD_peak_no_cache']=2*usage['estimated_USD_off_peak_no_cache']
    status={'stage':stage,'planned_sessions':len(selected)*len(SYSTEMS)*repeats,'completed_sessions':len(rows),
        'valid_sessions':sum(r['status']=='completed' for r in rows),'saved_logical_calls':len(callsaved),
        'actual_models':dict(Counter(r['model_returned'] for r in callsaved)),
        'finish_reasons':dict(Counter(r['finish_reason'] for r in callsaved)),
        'usage':usage,'human_ratings_complete':False,'independent_reference_validation':False,
        'formal_results':stage=='formal','signature':lock['signature'],'updated':now()}
    save(ROOT/stage/'status.json',status)
    return status


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--pilot',action='store_true')
    parser.add_argument('--formal',action='store_true')
    parser.add_argument('--summarize',action='store_true')
    args=parser.parse_args()
    lock,cases=prepare()
    stage='formal' if args.formal else 'pilot'; repeats=2 if args.formal else 1
    if args.summarize: print(json.dumps(summarize(lock,cases,stage,repeats),ensure_ascii=False)); return
    if not (args.pilot or args.formal):
        print(json.dumps({'status':'prepared','development_cases':10,'test_cases':30,'human_slots':30,'signature':lock['signature']})); return
    key=os.environ.get('DEEPSEEK_API_KEY')
    if not key:
        print('AWAITING_CREDENTIAL_STDIN',flush=True); key=sys.stdin.readline().strip()
    if not key: raise RuntimeError('Missing credential')
    available=api('/models',key)
    if MODEL not in [r['id'] for r in available.get('data',[])]: raise RuntimeError('Flash unavailable; no substitution')
    save(ROOT/stage/'model_check.json',{'requested':MODEL,'available':[r['id'] for r in available['data']],'time':now()})
    subset=[r for r in cases if r['split']==('dev' if stage=='pilot' else 'test')]
    jobs=[(c,s,r) for c in subset for s in SYSTEMS for r in range(1,repeats+1)]
    random.Random(20261025).shuffle(jobs)
    # Bounded billable requests including retries. Formal is a separate explicit command.
    max_calls=330 if stage=='pilot' else 1950
    completed=0
    with ThreadPoolExecutor(max_workers=5) as pool:
        futures=[pool.submit(session,c,s,r,lock,key,stage,max_calls) for c,s,r in jobs]
        try:
            for future in as_completed(futures):
                result=future.result(); completed+=1
                print(f"{completed}/{len(jobs)} {result['case_id']} {result['system']} {result['status']}",flush=True)
                save(ROOT/stage/'progress.json',{'completed_this_invocation':completed,'planned':len(jobs),'time':now()})
        except Exception:
            for future in futures: future.cancel()
            raise
    key=None
    print(json.dumps(summarize(lock,cases,stage,repeats),ensure_ascii=False),flush=True)


if __name__=='__main__': main()
