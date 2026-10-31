"""Transport-only recovery of four failed GLM jobs; no successful job is rerun."""
from pathlib import Path
import json,hashlib,os,time
from urllib.error import HTTPError,URLError
import run_glm600_locked as core

RECOVERY=core.ROOT/'recovery_failed4'

def main():
    lock,scorer=core.prepare()
    RECOVERY.mkdir(exist_ok=True)
    amend_path=RECOVERY/'transport_recovery_amendment.json'
    if amend_path.exists():amend=json.loads(amend_path.read_text(encoding='utf-8'))
    else:
        failed=[]
        for p in sorted((core.ROOT/'responses').glob('*.json')):
            r=json.loads(p.read_text(encoding='utf-8'))
            if r['status']!='completed':
                assert r['status']=='transport_failed' and r['error_type']=='URLError'
                failed.append({'job_id':p.stem,'original_response_sha256':core.sha(p),'job':r})
        assert len(failed)==4
        amend={'created_utc':core.now(),'original_signature':lock['signature'],
            'authorization':'User explicitly authorized rerunning the four transport-failed jobs; remaining71 unrequested jobs are NOT scheduled.',
            'operational_change':'At most3 additional transport attempts, serial execution. All original attempts1–3 retained; new attempts4–6 appended.',
            'generation_settings_unchanged':True,'same_endpoint':core.ENDPOINT,'same_prompts_cases_model_and_scoring':True,
            'no_content_based_retries':True,'jobs':failed,'recovery_runner_sha256':core.sha(Path(__file__))}
        core.save(amend_path,amend)
    assert amend['original_signature']==lock['signature']
    guard=core.ROOT/'worker.lock'
    with guard.open('x',encoding='utf-8') as f:f.write(str(os.getpid()))
    initial={p.name:core.sha(p) for p in (core.ROOT/'responses').glob('*.json') if json.loads(p.read_text(encoding='utf-8'))['status']=='completed'}
    assert len(initial)==525
    outcome=[]
    try:
        for frozen in amend['jobs']:
            job=frozen['job'];name=frozen['job_id'];target=core.ROOT/'responses'/(name+'.json')
            archived=RECOVERY/'original_failures'/(name+'.json')
            if not archived.exists():
                assert core.sha(target)==frozen['original_response_sha256'];core.save(archived,job)
            current=json.loads(target.read_text(encoding='utf-8'))
            if current['status']=='completed':outcome.append({'job_id':name,'status':'already_recovered'});continue
            body={k:job[k] for k in ['caseId','system','repeat','answers']}
            expected_original=json.loads((core.ROOT/'attempts'/name/'attempt01.json').read_text(encoding='utf-8'))
            assert body==expected_original['http_request_body']
            status,_=core.summarize(lock,scorer);status.update(status='recovering_failed4',worker_pid=os.getpid(),active_job=name)
            core.save(core.ROOT/'status.json',status)
            recovered=False
            for attempt in range(4,7):
                path=core.ROOT/'attempts'/name/f'attempt{attempt:02d}.json'
                assert not path.exists(),'Recovery attempt already exists; inspect it before another recovery.'
                record={**{k:expected_original[k] for k in ['signature','endpoint','http_request_body','expected_upstream_request_not_independently_observed']},
                    'job_id':name,'attempt':attempt,'started_utc':core.now(),'transport_recovery_amendment':'recovery_failed4/transport_recovery_amendment.json'}
                core.save(path,record)
                try:
                    code,result=core.call_api(body)
                    core.save(path,{**record,'http_status':code,'response':result,'finished_utc':core.now()})
                    valid=bool(isinstance(result.get('report'),str) and result['report'].strip())
                    valid=valid and result.get('model')=='glm-4.5-flash' and result.get('provider')=='zhipu'
                    valid=valid and result.get('system')==job['system'] and result.get('caseId')==job['caseId']
                    if not valid:
                        outcome.append({'job_id':name,'status':'invalid_response_retained_without_content_retry'});break
                    success={**body,'signature':lock['signature'],'status':'completed','report':result['report'],
                        'model':result['model'],'provider':result['provider'],'generatedAt':result.get('generatedAt'),
                        'finished_utc':core.now(),'transport_attempt':attempt,'full_server_response':result,
                        'upstream_finish_reason':'not_exposed_by_endpoint','recovered_after_transport_failure':True,
                        'original_failure_record':str(archived),'original_failure_sha256':frozen['original_response_sha256']}
                    core.save(target,success);outcome.append({'job_id':name,'status':'recovered','attempt':attempt});recovered=True
                    print('RECOVERED '+name+' attempt'+str(attempt),flush=True);break
                except Exception as exc:
                    code=None;details='';retry=isinstance(exc,(URLError,TimeoutError,ConnectionError))
                    if isinstance(exc,HTTPError):code=exc.code;details=exc.read(4000).decode(errors='replace');retry=code==429 or code>=500
                    core.save(path,{**record,'http_status':code,'error_type':type(exc).__name__,'error_message':str(exc),
                        'provider_error_body':details,'transport_retry_eligible':retry,'finished_utc':core.now()})
                    print('TRANSPORT_FAILURE '+name+' attempt'+str(attempt)+' '+str(code),flush=True)
                    if not retry or attempt==6:
                        outcome.append({'job_id':name,'status':'still_failed','http_status':code});break
                    time.sleep(15*(attempt-3))
            status,_=core.summarize(lock,scorer);status.update(status='recovering_failed4',worker_pid=os.getpid())
            core.save(core.ROOT/'status.json',status)
        final,_=core.summarize(lock,scorer)
        final['status']='awaiting_remaining71' if final['completed_reports']==529 and final['failed_jobs']==0 else 'recovery_incomplete'
        final['recovery_failed4_completed']=all(r['status'] in ['recovered','already_recovered'] for r in outcome)
        core.save(core.ROOT/'status.json',final)
        assert all(core.sha(core.ROOT/'responses'/name)==h for name,h in initial.items())
        core.save(RECOVERY/'recovery_audit.json',{'original_signature':lock['signature'],'outcomes':outcome,
            'original525_successful_reports_byte_unchanged':True,'original_failure_attempts_preserved':True,
            'remaining71_not_requested':True,'final_status':final,'finished_utc':core.now()})
        print(json.dumps(final,ensure_ascii=False),flush=True)
    finally:
        if guard.exists():guard.unlink()

if __name__=='__main__':main()
