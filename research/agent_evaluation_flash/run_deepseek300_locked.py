"""Independent 12 x 5 x 5 DeepSeek-Flash replication, key from process stdin only."""
import argparse,csv,hashlib,json,os,random,sys,time,uuid
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,build_opener,HTTPRedirectHandler
from urllib.error import HTTPError,URLError
from urllib.parse import urlparse
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from collections import Counter
import evaluator_v2
import run_glm600_locked as old

ROOT=Path('D:/pisa2022/outputs_grade_agent_deepseek41flash300_20261026')
MODEL='deepseek-flash'
API='https://api.deepseek.com'
SEED=20261026
SYSTEMS=old.SYSTEMS
def now():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):old.save(path,value)
def write_csv(path,rows):
    if not rows:return
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)

class SameProviderRedirect(HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        if urlparse(newurl).scheme!='https' or urlparse(newurl).hostname!='api.deepseek.com':
            raise RuntimeError('Cross-origin authentication redirect refused.')
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def request_api(path,key,body=None):
    assert path in ['/models','/chat/completions']
    req=Request(API+path,data=None if body is None else json.dumps(body).encode('utf-8'),
        headers={'Authorization':'Bearer '+key,'Content-Type':'application/json','User-Agent':'GRADE-Agent-Research-Replication/1.0'})
    with build_opener(SameProviderRedirect()).open(req,timeout=180) as response:return json.loads(response.read().decode('utf-8'))

def prepare():
    ROOT.mkdir(exist_ok=True,parents=True)
    previous_path=old.ROOT/'protocol_lock.json'
    previous=json.loads(previous_path.read_text(encoding='utf-8'))
    assert previous['signature']=='61e4bf92b9d81ef53868cf9672042c21c9deca6e75538b7c0bc1bf3da3dd284e'
    previous=previous['plan'];prompts=previous['prompts'];cases=previous['cases']
    assert len(cases)==12 and list(prompts)==SYSTEMS
    frozen_files=[Path(__file__),Path(evaluator_v2.__file__),Path(old.__file__),old.SCORER,previous_path]
    plan={'model_requested':MODEL,'model_family_intended':'DeepSeek-V4.1-Flash','provider':'DeepSeek official API',
        'api_base':API,'n_cases':12,'n_configurations':5,'repeats_per_case_configuration':5,'planned_reports':300,
        'cases':cases,'systems':SYSTEMS,'system_prompts':prompts,'temperature':.4,'max_tokens':1500,
        'thinking':{'type':'disabled'},'stream':False,'concurrency':2,'randomized_order_seed':SEED,
        'case_information':'Same fixed case answers for all groups; expectedConstraints never sent to model.',
        'component_definition':'NoDML removes exactly DML evidence block; noReview removes exactly same-call self-check block. This is not a multi-turn or independent-reviewer experiment.',
        'retry_policy':'At most5 transport attempts per scheduled job, backoff15/30/60/120s; HTTP429,5xx and connection failures only. Retain all attempts. No score, format or content-based retry.',
        'incomplete_output_policy':'Retain length-truncated/empty/refused responses and finish_reason; no hidden regeneration. Report separately before any inference.',
        'evaluation':'Frozen v2 measurement audit; unresolved priority left blank, causal wording sent for review not automatic errors. No validated overall diagnostic-quality score.',
        'statistical_reporting':'No automatic confidence interval for unvalidated semantic accuracy; final comparative inference waits for explicit handling of pending review and incomplete generations.',
        'limits':['The twelve synthetic cases have been inspected during earlier development; this is not a new unseen test set.',
            'Baseline vs agent prompts differ in structure and rules; interpret baseline comparisons as full-configuration comparisons.',
            'Do not mix new DeepSeek outputs with original Pro or GLM runs.',
            'API alias may change its backend version; preserve model inventory, response model, fingerprint, request ID, timestamp and usage.',
            'No model-based judge or teacher ratings have been fabricated.'],
        'source_hashes':{str(p):sha(p) for p in frozen_files},'credential_storage':'Runtime process memory only, never in source, logs, manifest or result files.'}
    signature=hashlib.sha256(json.dumps(plan,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    path=ROOT/'protocol_lock.json'
    if path.exists():
        lock=json.loads(path.read_text(encoding='utf-8'));assert lock['signature']==signature,'Protocol changed; use a new output directory.'
    else:
        lock={'created_utc':now(),'signature':signature,'plan':plan};save(path,lock)
    status=ROOT/'status.json'
    if not status.exists():save(status,{'status':'prepared_waiting_for_authentication','planned_reports':300,'completed_reports':0,
        'saved_jobs':0,'failed_jobs':0,'remaining_jobs':300,'model':MODEL,'updated_utc':now(),'signature':signature,
        'next_stage_description':'生成后统一保存v2审计结果；待复核不强行计分，暂不生成诊断准确率区间。'})
    return lock

def verify_model(lock,key):
    inventory=request_api('/models',key)
    choice=next((r for r in inventory.get('data',[]) if r.get('id')==MODEL),None)
    if choice is None:raise RuntimeError('Requested deepseek-flash is absent from the model inventory; no fallback used.')
    save(ROOT/'model_inventory.json',{'checked_utc':now(),'response':inventory})
    body={'model':MODEL,'messages':[{'role':'user','content':'Reply with the single word READY. This is a connection check, not an experimental case.'}],
        'thinking':{'type':'disabled'},'temperature':.4,'max_tokens':32,'stream':False}
    result=request_api('/chat/completions',key,body)
    returned=result.get('model','')
    if not isinstance(returned,str) or not ('flash' in returned.lower()):raise RuntimeError('Returned model is not identified as Flash; no experimental generation started.')
    save(ROOT/'model_verification.json',{'verified_utc':now(),'signature':lock['signature'],'requested_model':MODEL,
        'inventory_entry':choice,'smoke_request':body,'smoke_response':result,'excluded_from300':True})
    print('MODEL_VERIFIED '+returned,flush=True)

def job_id(job):return job['caseId']+'__'+job['system']+'__r'+str(job['repeat']).zfill(2)

def generate(job,lock,key):
    name=job_id(job);target=ROOT/'responses'/(name+'.json')
    if target.exists():return json.loads(target.read_text(encoding='utf-8'))
    case_text='Assess '+job['caseId']+'.\n\nCASE INFORMATION\n'+json.dumps(job['answers'],ensure_ascii=False,indent=2)
    body={'model':MODEL,'messages':[{'role':'system','content':lock['plan']['system_prompts'][job['system']]},{'role':'user','content':case_text}],
        'temperature':.4,'max_tokens':1500,'thinking':{'type':'disabled'},'stream':False}
    for attempt in range(1,6):
        path=ROOT/'attempts'/name/f'attempt{attempt:02d}.json';assert not path.exists(),'Unresolved prior attempt: inspect before resuming.'
        record={'signature':lock['signature'],'job_id':name,'attempt':attempt,'started_utc':now(),'endpoint':API+'/chat/completions','request_body':body}
        save(path,record)
        try:
            response=request_api('/chat/completions',key,body);save(path,{**record,'finished_utc':now(),'response':response})
            choices=response.get('choices',[]);choice=choices[0] if choices else {};report=choice.get('message',{}).get('content','') or ''
            finish=choice.get('finish_reason');returned=response.get('model','')
            status='completed' if report.strip() and finish=='stop' else 'generated_incomplete'
            if 'flash' not in str(returned).lower():status='unexpected_model'
            row={**job,'signature':lock['signature'],'status':status,'report':report,'model':returned,'model_requested':MODEL,
                'finish_reason':finish,'response_id':response.get('id'),'system_fingerprint':response.get('system_fingerprint'),
                'usage':response.get('usage'),'generatedAt':now(),'transport_attempt':attempt,'full_api_response':response}
            save(target,row);return row
        except Exception as exc:
            code=None;error_body='';retry=isinstance(exc,(URLError,TimeoutError,ConnectionError))
            if isinstance(exc,HTTPError):
                code=exc.code;error_body=exc.read(4000).decode(errors='replace').replace(key,'[REDACTED]');retry=code==429 or code>=500
            save(path,{**record,'error_type':type(exc).__name__,'http_status':code,'error_message':str(exc).replace(key,'[REDACTED]'),
                'provider_error_body':error_body,'finished_utc':now(),'transport_retry_eligible':retry})
            if retry and attempt<5:time.sleep(15*2**(attempt-1));continue
            row={**job,'signature':lock['signature'],'status':'transport_failed','error_type':type(exc).__name__,'http_status':code,
                'finished_utc':now(),'transport_attempt':attempt};save(target,row);return row

def export(lock,worker_running=True):
    rows=[json.loads(p.read_text(encoding='utf-8')) for p in sorted((ROOT/'responses').glob('*.json'))]
    save(ROOT/'raw_reports.json',rows)
    report_rows=[r for r in rows if r.get('report') and r['status'] in ['completed','generated_incomplete']]
    expected=old.load_scorer()['CASE_EXPECTED_SIGNALS'];audit=[]
    for r in report_rows:
        a=evaluator_v2.evaluate(r['report'],r['answers'],expected[r['caseId'].split('_')[0]])
        audit.append({'system':r['system'],'caseId':r['caseId'],'repeat':r['repeat'],'model':r['model'],'generation_status':r['status'],
            'primary_signal':a['primary_signal'],'priority_alignment':a['priority_alignment'],
            'explicit_boundary_statement_present':a['explicit_boundary_statement_present'],
            'causal_claim_review_required':a['causal_claim_review_required'],
            'action_structure_completeness':a['action_structure_completeness'],'manual_review_required':a['manual_review_required'],
            'review_reasons':'\n'.join(a['manual_review_reasons']),
            'audit_json':json.dumps(a,ensure_ascii=False)})
    if audit:write_csv(ROOT/'run_level_metrics.csv',audit)
    complete=sum(r['status']=='completed' for r in rows)
    incomplete=sum(r['status']=='generated_incomplete' for r in rows)
    failed=sum(r['status'] not in ['completed','generated_incomplete'] for r in rows)
    by_system={s:sum(r['system']==s and r['status']=='completed' for r in rows) for s in SYSTEMS}
    state={'status':'running' if worker_running else ('generation_completed_review_pending' if len(rows)==300 else 'incomplete'),
        'planned_reports':300,'saved_jobs':len(rows),'completed_reports':complete,'generated_incomplete_reports':incomplete,
        'failed_jobs':failed,'remaining_jobs':300-len(rows),'model':MODEL,'model_display_name':'DeepSeek-V4.1-Flash',
        'by_system':by_system,'signature':lock['signature'],'updated_utc':now(),
        'next_stage_description':'本轮输出按v2审计规则处理；待复核报告保留空白，不计算未经验证的诊断准确率。'}
    if worker_running:state['worker_pid']=os.getpid()
    save(ROOT/'status.json',state)
    if not worker_running:
        coverage=[]
        for s in SYSTEMS:
            g=[r for r in audit if r['system']==s]
            coverage.append({'system':s,'planned_reports':60,'reports_with_text':len(g),'completed_reports':by_system[s],
                'priority_aligned_n':sum(r['priority_alignment']==1 for r in g),'priority_not_aligned_n':sum(r['priority_alignment']==0 for r in g),
                'priority_pending_review_n':sum(r['priority_alignment'] is None for r in g),
                'causal_claim_review_reports_n':sum(r['causal_claim_review_required'] for r in g)})
        write_csv(ROOT/'measurement_coverage_summary.csv',coverage)
    return state

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');args=parser.parse_args();lock=prepare()
    print('PROTOCOL_LOCKED '+lock['signature'],flush=True)
    if not args.run:return
    key=sys.stdin.readline().strip()
    if not key:raise RuntimeError('No runtime credential supplied; no API calls made.')
    guard=ROOT/'worker.lock'
    with guard.open('x',encoding='utf-8') as f:f.write(str(os.getpid()))
    try:
        verify_model(lock,key)
        jobs=[{'system':s,'caseId':c['caseId'],'answers':c['answers'],'repeat':i} for c in lock['plan']['cases'] for s in SYSTEMS for i in range(1,6)]
        random.Random(SEED).shuffle(jobs);save(ROOT/'execution_order.json',[job_id(j) for j in jobs])
        todo=[j for j in jobs if not (ROOT/'responses'/(job_id(j)+'.json')).exists()]
        iterator=iter(todo);export(lock);fatal=False
        with ThreadPoolExecutor(max_workers=2) as pool:
            pending={pool.submit(generate,j,lock,key):j for j in [next(iterator,None),next(iterator,None)] if j is not None}
            while pending:
                done,_=wait(pending,return_when=FIRST_COMPLETED)
                for future in done:
                    job=pending.pop(future);row=future.result();state=export(lock)
                    print(f"{state['saved_jobs']}/300 {job_id(job)} {row['status']}",flush=True)
                    if row.get('http_status') in [400,401,402,403] or row['status']=='unexpected_model':fatal=True
                    if not fatal:
                        following=next(iterator,None)
                        if following is not None:pending[pool.submit(generate,following,lock,key)]=following
        final=export(lock,False);print(json.dumps(final,ensure_ascii=False),flush=True)
        save(ROOT/'integrity_check.json',{'signature':lock['signature'],'source_files_unchanged':all(sha(Path(p))==h for p,h in lock['plan']['source_hashes'].items()),
            'key_not_persisted':True,'all_attempts_retained':True,'no_content_based_regeneration':True,'finished_utc':now()})
    except Exception as exc:
        code=exc.code if isinstance(exc,HTTPError) else None
        message=str(exc).replace(key,'[REDACTED]')
        save(ROOT/'worker_failure.json',{'error_type':type(exc).__name__,'http_status':code,'error_message':message,'time':now()})
        state=export(lock,False);state['status']='blocked_authentication_or_connection';save(ROOT/'status.json',state)
        print('WORKER_STOPPED '+type(exc).__name__+' '+str(code),flush=True)
    finally:
        key=None
        if guard.exists():guard.unlink()

if __name__=='__main__':main()
