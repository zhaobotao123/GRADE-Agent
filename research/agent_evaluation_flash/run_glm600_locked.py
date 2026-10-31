"""Independent GLM replication of the five-condition report benchmark.

No credentials, deployment, original reports, or manuscript are modified.
The immutable deployment supplies server-side authentication. Expected messages
are archived locally; the server API does not expose its upstream finish reason.
"""
import argparse,ast,csv,hashlib,json,os,random,subprocess,sys,time,uuid
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter,defaultdict
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from urllib.request import Request,urlopen
from urllib.error import HTTPError,URLError
import numpy as np

ROOT=Path('D:/pisa2022/outputs_grade_agent_glm600_20261026')
PACKAGE=Path('C:/Users/84130/Documents/Codex/2026-07-03/zhe/outputs/Supplementary_Software_1')
CASES=PACKAGE/'protocol/heldout_cases_v1.json'
SCORER=PACKAGE/'scripts/rescore_v6_transparent.py'
WEBSITE=Path('C:/Users/84130/Documents/Codex/2026-07-03/zhe/gradeagent')
NODE=Path('C:/Users/84130/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe')
ENDPOINT='https://197e9dd7.gradeagent.pages.dev/api/ablation'
SYSTEMS=['single_turn_llm','evidence_only_llm','grade_agent_no_dml','grade_agent_no_critic','full_grade_agent']
METRICS=['causal_boundary_compliance','missing_information_compliance','priority_alignment','operational_action_completeness','primary_signal_consistency']
LABELS=['解释边界符合率','缺失信息处理','主要问题识别符合率','行动要素完整性','重复生成一致性']
SEED=20261026
NBOOT=200000

def now():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def signature(value):return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False).encode()).hexdigest()
def save(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+'.'+uuid.uuid4().hex+'.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    for attempt in range(20):
        try:temp.replace(path);return
        except PermissionError:
            if attempt==19:raise
            time.sleep(.2)

def write_csv(path,rows):
    assert rows
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)

def load_scorer():
    # Preserve the archived v6 definitions exactly; omit historical top-level I/O.
    tree=ast.parse(SCORER.read_text(encoding='utf-8'));skip={'RAW','OUT','OLD_SUMMARY'}
    nodes=[n for n in tree.body if isinstance(n,(ast.Import,ast.ImportFrom,ast.FunctionDef)) or
        (isinstance(n,ast.Assign) and all(not isinstance(t,ast.Name) or t.id not in skip for t in n.targets))]
    namespace={};exec(compile(ast.Module(body=nodes,type_ignores=[]),str(SCORER),'exec'),namespace)
    return namespace

def prepare():
    ROOT.mkdir(parents=True,exist_ok=True)
    assert sha(CASES)=='c01face3e08421b264e54841c3421651d88dc28a1a9e84457b1dc994d0763491'
    assert sha(SCORER)=='e556f89b1e7d7d4e9288162cae6d3584313bf088e599c760ab080def829dfe73'
    js="import {SYSTEM_PROMPTS,DML_BLOCK,CRITIC_BLOCK} from '"+(WEBSITE/'functions/api/ablation.js').as_uri()+"'; console.log(JSON.stringify({SYSTEM_PROMPTS,DML_BLOCK,CRITIC_BLOCK}));"
    exported=json.loads(subprocess.run([str(NODE),'--input-type=module','-e',js],capture_output=True,text=True,encoding='utf-8',check=True).stdout)
    prompts={s:exported['SYSTEM_PROMPTS'][s] for s in SYSTEMS}
    norm=lambda x:'\n\n'.join(p.strip() for p in x.split('\n\n') if p.strip())
    assert norm(prompts['full_grade_agent'].replace(exported['DML_BLOCK'],''))==norm(prompts['grade_agent_no_dml'])
    assert norm(prompts['full_grade_agent'].replace(exported['CRITIC_BLOCK'],''))==norm(prompts['grade_agent_no_critic'])
    assert exported['DML_BLOCK'] not in prompts['grade_agent_no_dml']
    assert exported['CRITIC_BLOCK'] not in prompts['grade_agent_no_critic']
    assert 'pooled estimate' not in prompts['grade_agent_no_dml']
    assert 'SHAP' not in prompts['single_turn_llm'] and 'SHAP' not in prompts['evidence_only_llm']
    cases=json.loads(CASES.read_text(encoding='utf-8-sig'))
    assert len(cases)==12 and len({c['caseId'] for c in cases})==12
    scorer=load_scorer()
    # Reproduction test against the archived run-level scores before new calls.
    original=json.loads((PACKAGE/'evaluation/raw_reports.json').read_text(encoding='utf-8-sig'))
    previous=list(csv.DictReader((PACKAGE/'evaluation/run_level_metrics.csv').open(encoding='utf-8-sig')))
    key=lambda r:(r['system'],r['caseId'],int(r['repeat']))
    prev={key(r):r for r in previous}
    assert len(original)==len(prev)==600
    assert all(all(('' if v is None else str(v))==prev[key(item)][f] for f,v in scorer['audit'](item).items()) for item in original)
    plan={'model':'glm-4.5-flash','provider':'zhipu','endpoint':ENDPOINT,'cases':cases,'systems':SYSTEMS,'prompts':prompts,
        'repeats':10,'planned_reports':600,'temperature':.4,'max_tokens':1500,'thinking':'disabled','stream':False,
        'concurrency':2,'execution_order_seed':SEED,'bootstrap_reps':NBOOT,'bootstrap_seed':SEED,
        'bootstrap_method':'paired case-cluster percentile, pointwise 95%; no multiplicity correction or p-values',
        'missing_information_bootstrap':'conditional on the three applicable cases H02,H08,H09; resample three case clusters, retain ten outputs per cluster',
        'consistency_definition':'per case most frequent extracted primary-signal count divided by ten, then average across twelve cases',
        'case_information_policy':'All conditions receive identical fixed answer records. Expected scoring constraints are never sent to the model.',
        'review_definition':'same-call prompt self-check instruction, not an independent reviewer invocation',
        'evaluation_scope':'controlled report-generation/rule-adherence benchmark, not multi-turn workflow or real-student diagnostic validity',
        'retry_policy':'at most three attempts for HTTP429/5xx/transport failure only; retain every attempt. Never retry on content, score, or missing headings.',
        'failure_policy':'preserve failures and stop after three failed scheduled jobs; no silent replacement. Full inferential export requires all600 successful responses.',
        'sources':{str(p):sha(p) for p in [CASES,SCORER,WEBSITE/'functions/api/ablation.js',WEBSITE/'functions/lib/llm.js',Path(__file__)]},
        'traceability_limit':'API returns model, provider, report and server timestamp, but not upstream request ID, usage or finish_reason. Expected upstream messages come from the archived local deployment source, not independent server-side traces.',
        'statistical_limits':['Cases are researcher constructed, not a probability sample of educational practice.',
            'Only12 case clusters, and only3 applicable missing-information cases; intervals are exploratory empirical case-resampling summaries.',
            'Ceiling or constant scores can yield zero-width bootstrap intervals; these do not establish zero uncertainty or perfect external performance.',
            'No within-case generation resampling: consistency intervals summarize variation across the observed ten-output case batches.',
            'Automated lexical criteria measure reporting-rule adherence, not full educational quality.',
            'Baselines and agent conditions differ in prompt structure and instructions as well as evidence; only the two component contrasts isolate exact prompt-block removal.']}
    sig=signature(plan);lock={'created_utc':now(),'signature':sig,'plan':plan}
    path=ROOT/'protocol_lock.json'
    if path.exists():
        old=json.loads(path.read_text(encoding='utf-8'));assert old['signature']==sig,'Protocol changed; use a new experiment directory.';lock=old
    else:save(path,lock)
    save(ROOT/'pre_run_checks.json',{'signature':sig,'case_count':12,'systems':5,'expected_reports':600,
        'exact_DML_block_removal':True,'exact_review_block_removal':True,'same_case_information':True,
        'no_expected_labels_sent':True,'original_v6_scorer_reproduces_archived600':True,
        'scorer_version':'frozen original v6; not the different benchmark_audit.py variant'})
    return lock,scorer

def call_api(payload):
    request=Request(ENDPOINT,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','User-Agent':'GRADE-Agent-GLM-Replication/1.0'})
    with urlopen(request,timeout=160) as response:return response.status,json.loads(response.read().decode())

def smoke(lock):
    path=ROOT/'diagnostics/model_smoke.json'
    if path.exists():obj=json.loads(path.read_text(encoding='utf-8'))
    else:
        body={'system':'single_turn_llm','caseId':'TRANSPORT_MODEL_CHECK_NOT_EXPERIMENT','answers':{'instruction':'Reply in English with a single sentence saying this is a model connection check. Do not assess any student.'}}
        code,result=call_api(body);obj={'request':body,'http_status':code,'response':result,'signature':lock['signature'],'timestamp':now(),'excluded_from600':True};save(path,obj)
    assert obj['response'].get('model')=='glm-4.5-flash' and obj['response'].get('provider')=='zhipu',obj['response'].get('model')

def job_name(job):return f"{job['caseId']}__{job['system']}__r{job['repeat']:02d}"
def generate(job,lock):
    name=job_name(job);target=ROOT/'responses'/(name+'.json')
    if target.exists():
        row=json.loads(target.read_text(encoding='utf-8'));assert row['signature']==lock['signature'];return row
    body={k:job[k] for k in ['caseId','system','repeat','answers']}
    expected_user='Assess '+job['caseId']+'.\n\nCASE INFORMATION\n'+json.dumps(job['answers'],ensure_ascii=False,indent=2)
    # JSON pretty-print differs between JS and Python only for non-ASCII; all case records are English.
    expected_request={'model':'glm-4.5-flash','messages':[{'role':'system','content':lock['plan']['prompts'][job['system']]},{'role':'user','content':expected_user}],
        'temperature':.4,'max_tokens':1500,'thinking':{'type':'disabled'},'stream':False}
    for attempt in range(1,4):
        attempt_path=ROOT/'attempts'/name/f'attempt{attempt:02d}.json'
        assert not attempt_path.exists(),'A previous attempt is unresolved; inspect before resuming.'
        started=now();request_record={'signature':lock['signature'],'job_id':name,'attempt':attempt,'started_utc':started,
            'endpoint':ENDPOINT,'http_request_body':body,'expected_upstream_request_not_independently_observed':expected_request}
        save(attempt_path,request_record)
        try:
            code,result=call_api(body)
            record={**request_record,'http_status':code,'response':result,'finished_utc':now()};save(attempt_path,record)
            report=result.get('report','');valid=isinstance(report,str) and bool(report.strip())
            valid=valid and result.get('model')=='glm-4.5-flash' and result.get('provider')=='zhipu'
            valid=valid and result.get('system')==job['system'] and result.get('caseId')==job['caseId']
            row={**body,'signature':lock['signature'],'status':'completed' if valid else 'invalid_response',
                'report':report,'model':result.get('model'),'provider':result.get('provider'),'generatedAt':result.get('generatedAt'),
                'finished_utc':now(),'transport_attempt':attempt,'full_server_response':result,
                'upstream_finish_reason':'not_exposed_by_endpoint'}
            save(target,row);return row
        except Exception as exc:
            retry=False;code=None;error_body=''
            if isinstance(exc,HTTPError):
                code=exc.code;error_body=exc.read(4000).decode(errors='replace');retry=code==429 or code>=500
            elif isinstance(exc,(URLError,TimeoutError,ConnectionError)):retry=True
            save(attempt_path,{**request_record,'http_status':code,'error_type':type(exc).__name__,
                'error_message':str(exc),'provider_error_body':error_body,'finished_utc':now(),'transport_retry_eligible':retry})
            if retry and attempt<3:time.sleep(15*attempt);continue
            row={**body,'signature':lock['signature'],'status':'transport_failed','error_type':type(exc).__name__,
                'http_status':code,'finished_utc':now(),'transport_attempt':attempt}
            save(target,row);return row

def summarize(lock,scorer):
    outputs=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'responses').glob('*.json'))]
    assert all(r['signature']==lock['signature'] for r in outputs)
    completed=[r for r in outputs if r['status']=='completed'];failed=[r for r in outputs if r['status']!='completed']
    save(ROOT/'raw_reports.json',outputs)
    scored=[scorer['audit'](r) for r in completed]
    if scored:write_csv(ROOT/'run_level_metrics.csv',scored)
    status={'status':'completed' if len(completed)==600 else 'incomplete','planned_reports':600,'saved_jobs':len(outputs),
        'completed_reports':len(completed),'failed_jobs':len(failed),'remaining_jobs':600-len(outputs),'model':'glm-4.5-flash',
        'signature':lock['signature'],'updated_utc':now()}
    save(ROOT/'status.json',status)
    return status,scored

def bootstrap(lock,scored):
    assert len(scored)==600
    keyed={(r['system'],r['caseId'],int(r['repeat'])) for r in scored};assert len(keyed)==600
    cases=sorted({r['caseId'] for r in scored});assert len(cases)==12
    cube=defaultdict(list)
    for r in scored:cube[r['system'],r['caseId']].append(r)
    assert all(len(g)==10 and {int(r['repeat']) for r in g}==set(range(1,11)) for g in cube.values())
    summary=[];case_rows=[]
    score_fields=[k for k in scored[0] if k not in ['system','caseId','repeat','model','primary_signal','priority_extraction_source']]
    for s in SYSTEMS:
        group=[r for r in scored if r['system']==s];entry={'system':s,'model':'glm-4.5-flash','n_reports':120}
        for f in score_fields:
            vals=[r[f] for r in group if r[f] is not None];entry[f]=sum(vals)/len(vals) if vals else '';entry[f+'_n']=len(vals)
        consistency=[]
        for case in cases:
            g=cube[s,case];modal=Counter(r['primary_signal'] for r in g).most_common(1)[0][1]/10;consistency.append(modal)
            row={'system':s,'caseId':case,'n_reports':10,'primary_signal_consistency':modal}
            for f in METRICS[:-1]:
                vals=[r[f] for r in g if r[f] is not None];row[f]=sum(vals)/len(vals) if vals else ''
            case_rows.append(row)
        entry['primary_signal_consistency']=sum(consistency)/12;entry['primary_signal_consistency_n_cases']=12;summary.append(entry)
    write_csv(ROOT/'system_summary.csv',summary);write_csv(ROOT/'case_level_metrics.csv',case_rows)
    by_case={(r['system'],r['caseId']):r for r in case_rows};rng=np.random.default_rng(SEED)
    indices12=rng.integers(0,12,size=(NBOOT,12));indices3=rng.integers(0,3,size=(NBOOT,3))
    save(ROOT/'bootstrap_sampling_metadata.json',{'seed':SEED,'n_bootstrap':NBOOT,'case_ids':cases,
        'same_indices_across_systems':True,'applicability_conditioned_for_missing_information':True,
        'indices12_sha256':hashlib.sha256(indices12.tobytes()).hexdigest(),'indices3_sha256':hashlib.sha256(indices3.tobytes()).hexdigest()})
    intervals=[];contrasts=[];draw_archive={}
    for f in METRICS:
        eligible=[c for c in cases if all(by_case[s,c][f]!='' for s in SYSTEMS)]
        assert len(eligible)==(3 if f=='missing_information_compliance' else 12)
        mat=np.array([[by_case[s,c][f] for c in eligible] for s in SYSTEMS],dtype=float)
        indices=indices3 if len(eligible)==3 else indices12
        draws=mat[:,indices].mean(axis=2);points=mat.mean(axis=1)
        assert np.isfinite(draws).all();draw_archive[f]=draws
        for i,s in enumerate(SYSTEMS):
            lo,hi=np.quantile(draws[i],[.025,.975],method='linear');degenerate=bool(np.ptp(draws[i])<1e-12)
            intervals.append({'system':s,'metric':f,'estimate_percent':100*points[i],
                'ci_low_percent':100*lo,'ci_high_percent':100*hi,'n_case_clusters':len(eligible),
                'n_reports':10*len(eligible),'bootstrap_reps':NBOOT,'seed':SEED,
                'degenerate_empirical_bootstrap':degenerate,'method':'paired case-cluster percentile; pointwise95%'})
        for comparator in ['grade_agent_no_dml','grade_agent_no_critic']:
            j=SYSTEMS.index(comparator);diff=draws[4]-draws[j];lo,hi=np.quantile(diff,[.025,.975],method='linear')
            contrasts.append({'contrast':'full_grade_agent_minus_'+comparator,'metric':f,
                'estimate_percentage_points':100*(points[4]-points[j]),'ci_low_percentage_points':100*lo,
                'ci_high_percentage_points':100*hi,'n_case_clusters':len(eligible),
                'bootstrap_reps':NBOOT,'seed':SEED,'interval_includes_zero':bool(lo<=0<=hi),
                'degenerate_empirical_bootstrap':bool(np.ptp(diff)<1e-12),'method':'paired case-cluster percentile; pointwise95%; unadjusted'})
    write_csv(ROOT/'system_metrics_with_ci.csv',intervals);write_csv(ROOT/'paired_component_contrasts_with_ci.csv',contrasts)
    np.savez_compressed(ROOT/'bootstrap_draws.npz',**draw_archive)
    lines=['# GLM五配置独立重跑结果','', '模型：GLM-4.5-Flash。12个固定合成案例×5配置×10次生成，共600份报告。',
        '所有结果由本轮原始回复按冻结v6规则统一计算；没有挑选最好回复，也未修改旧实验或论文。','',
        '## 系统结果：点估计（95%案例聚类Bootstrap区间）','',
        '| 配置 | '+' | '.join(LABELS)+' |','|---|'+'---|'*5]
    for s in SYSTEMS:
        vals=[next(r for r in intervals if r['system']==s and r['metric']==f) for f in METRICS]
        lines.append('| '+s+' | '+' | '.join(f"{r['estimate_percent']:.1f}% ({r['ci_low_percent']:.1f}–{r['ci_high_percent']:.1f})" for r in vals)+' |')
    lines+=['','## 完整系统减去消融配置：百分点差值与95%配对区间','','| 对照 | 指标 | 差值 | 95%区间 |','|---|---|---:|---|']
    for r in contrasts:lines.append(f"| {r['contrast']} | {LABELS[METRICS.index(r['metric'])]} | {r['estimate_percentage_points']:+.1f} | {r['ci_low_percentage_points']:+.1f}–{r['ci_high_percentage_points']:+.1f} |")
    lines+=['','## 必须保留的解释边界','',
        '- 缺失信息指标仅适用于H02、H08、H09，共3个案例、每配置30份报告；不适用不记0，不产生nan。其区间仅在这3个适用案例内重抽样。',
        '- 100–100或0–0的零宽区间来自已观察案例全部同分，不代表没有不确定性或总体表现完美。',
        '- 其他指标用12个案例聚类重抽样；每次保留所抽案例的全部10次生成，各配置使用相同案例索引。没有把120次生成当作120个独立案例。',
        '- 一致性按每个案例10次输出的主要信号众数比例计算，再跨案例平均；区间描述已观察批次间的案例差异。',
        '- 区间是20万次百分位法的探索性逐项95%区间，未作多重比较校正；不由区间重叠与否推断两个配置的差异。',
        '- 合成案例不是教育实践的概率样本；这些区间不能直接外推到真实学生诊断或教学效果。',
        '- 复核仅指同一次调用中的自我检查指令；本轮不是独立审阅模型或多轮交互效果实验。',
        '- 服务端没有返回上游finish_reason与用量；原始接口回复完整保留，不能声称已验证全部模型输出未因token限制截断。',
        '', '## 方法参考','',
        '[Grouped resampling documentation](https://rsample.tidymodels.org/reference/group_bootstraps.html)',
        '[Paired resampling and percentile intervals](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.bootstrap.html)']
    (ROOT/'结果说明_中文.md').write_text('\n'.join(lines),encoding='utf-8')
    save(ROOT/'analysis_audit.json',{'signature':lock['signature'],'n_reports':600,'unique_job_keys':600,
        'scorer_hash':sha(SCORER),'all_labels_and_priority_scores_recomputed_together':True,
        'no_nan_in_reported_estimates_or_intervals':all(np.isfinite(float(r[k])) for r in intervals for k in ['estimate_percent','ci_low_percent','ci_high_percent']),
        'sources_unchanged':all(sha(Path(p))==h for p,h in lock['plan']['sources'].items()),
        'finished_utc':now(),'result_files':{p.name:sha(p) for p in ROOT.glob('*.csv')}})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');args=parser.parse_args()
    lock,scorer=prepare();print('PROTOCOL_LOCKED '+lock['signature'],flush=True)
    if not args.run:return
    guard=ROOT/'worker.lock'
    with guard.open('x',encoding='utf-8') as f:f.write(str(os.getpid()))
    try:
        smoke(lock);print('MODEL_VERIFIED glm-4.5-flash zhipu',flush=True)
        jobs=[{'caseId':c['caseId'],'answers':c['answers'],'system':s,'repeat':r} for c in lock['plan']['cases'] for s in SYSTEMS for r in range(1,11)]
        random.Random(SEED).shuffle(jobs);save(ROOT/'execution_order.json',[job_name(j) for j in jobs])
        todo=[j for j in jobs if not (ROOT/'responses'/(job_name(j)+'.json')).exists()]
        status,_=summarize(lock,scorer);status['status']='running';status['worker_pid']=os.getpid();save(ROOT/'status.json',status)
        failures=0;iterator=iter(todo)
        with ThreadPoolExecutor(max_workers=2) as executor:
            pending={executor.submit(generate,j,lock):j for j in [next(iterator,None),next(iterator,None)] if j is not None}
            while pending:
                done,_=wait(pending,return_when=FIRST_COMPLETED)
                for future in done:
                    job=pending.pop(future);result=future.result();failures+=int(result['status']!='completed')
                    status,_=summarize(lock,scorer);status['status']='running';status['worker_pid']=os.getpid();save(ROOT/'status.json',status)
                    print(f"{status['saved_jobs']}/600 {job_name(job)} {result['status']}",flush=True)
                    if failures<3:
                        following=next(iterator,None)
                        if following is not None:pending[executor.submit(generate,following,lock)]=following
        status,scored=summarize(lock,scorer)
        if status['completed_reports']==600:
            bootstrap(lock,scored);status['analysis_completed']=True;status['updated_utc']=now();save(ROOT/'status.json',status)
            print('ALL600_AND_BOOTSTRAP_COMPLETED',flush=True)
        else:print('INCOMPLETE_RETAINED_NO_FULL_INFERENCE',flush=True)
    except Exception as exc:
        save(ROOT/'worker_failure.json',{'error_type':type(exc).__name__,'error_message':str(exc),'time':now()});raise
    finally:
        if guard.exists():guard.unlink()

if __name__=='__main__':main()
