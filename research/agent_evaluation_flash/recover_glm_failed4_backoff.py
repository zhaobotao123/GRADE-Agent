"""Bounded slow transport recovery; only the four explicitly authorized failed slots."""
import json,os,time,hashlib
from pathlib import Path
from datetime import datetime,timezone,timedelta
from urllib.error import HTTPError,URLError
import run_glm600_locked as core

def main():
    # Never overlap the first recovery worker or the main experiment.
    guard=core.ROOT/'worker.lock'
    wait_start=time.monotonic()
    while guard.exists():
        if time.monotonic()-wait_start>600:raise RuntimeError('Previous worker still owns the lock; no duplicate started.')
        time.sleep(10)
    lock,scorer=core.prepare()
    original=json.loads((core.ROOT/'recovery_failed4/transport_recovery_amendment.json').read_text(encoding='utf-8'))
    selected=original['jobs'];assert len(selected)==4
    folder=core.ROOT/'recovery_failed4_slow';folder.mkdir(exist_ok=True)
    amendment={'created_utc':core.now(),'original_signature':lock['signature'],'authorized_scope':'Original four connection-failed slots only; no other jobs.',
        'reason':'Temporary provider429 capacity responses and intermittent transport disconnects during initial recovery.',
        'policy':'Serial transport-only attempts, at most8 rounds and30minutes total. Initial120s cooldown; later exponential cooldown capped600s. No content-based retry.',
        'original_failures_and_all_attempts_retained':True,'unchanged_model_prompts_case_data_parameters_scorer':True,
        'endpoint':core.ENDPOINT,'jobs':[x['job_id'] for x in selected],'runner_sha256':core.sha(Path(__file__))}
    assert not (folder/'amendment.json').exists(),'Do not restart without inspecting prior slow-recovery outcome.'
    core.save(folder/'amendment.json',amendment)
    with guard.open('x',encoding='utf-8') as f:f.write(str(os.getpid()))
    initial={p.name:core.sha(p) for p in (core.ROOT/'responses').glob('*.json') if json.loads(p.read_text(encoding='utf-8'))['status']=='completed'}
    events=[];started=time.monotonic();stop_reason='retry_budget_exhausted'
    def pending():
        return [x for x in selected if json.loads((core.ROOT/'responses'/(x['job_id']+'.json')).read_text(encoding='utf-8'))['status']!='completed']
    def status(state,**extra):
        s,_=core.summarize(lock,scorer);s.update(status=state,worker_pid=os.getpid(),recovery_only=True,**extra);core.save(core.ROOT/'status.json',s)
    def cooldown(seconds):
        end=time.monotonic()+seconds;stamp=(datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat()
        while time.monotonic()<end:
            status('waiting_model_capacity',retry_after_utc=stamp,last_transport_error='Model busy or transport interrupted; scheduled slow retry.')
            time.sleep(min(15,max(0,end-time.monotonic())))
    try:
        for round_id in range(8):
            outstanding=pending()
            if not outstanding:stop_reason='all_four_recovered';break
            if time.monotonic()-started>=1800:stop_reason='30minute_limit';break
            delay=min(120*(2**round_id),600)
            delay=min(delay,max(0,1800-(time.monotonic()-started)))
            print('COOLDOWN '+str(int(delay))+'s; outstanding='+str(len(outstanding)),flush=True);cooldown(delay)
            if time.monotonic()-started>=1800:stop_reason='30minute_limit';break
            # Rotate starting slot between rounds, avoiding repeated load on one failed slot.
            offset=round_id%len(outstanding);outstanding=outstanding[offset:]+outstanding[:offset]
            permanent=False
            for frozen in outstanding:
                job=frozen['job'];name=frozen['job_id'];target=core.ROOT/'responses'/(name+'.json')
                first=json.loads((core.ROOT/'attempts'/name/'attempt01.json').read_text(encoding='utf-8'))
                body={k:job[k] for k in ['caseId','system','repeat','answers']};assert body==first['http_request_body']
                old_attempts=list((core.ROOT/'attempts'/name).glob('attempt*.json'))
                attempt=max(int(p.stem.replace('attempt','')) for p in old_attempts)+1
                path=core.ROOT/'attempts'/name/f'attempt{attempt:02d}.json';assert not path.exists()
                rec={**{k:first[k] for k in ['signature','endpoint','http_request_body','expected_upstream_request_not_independently_observed']},
                    'job_id':name,'attempt':attempt,'started_utc':core.now(),'recovery_amendment':'recovery_failed4_slow/amendment.json'}
                core.save(path,rec);status('recovering_failed4',active_job=name)
                try:
                    code,result=core.call_api(body)
                    core.save(path,{**rec,'http_status':code,'response':result,'finished_utc':core.now()})
                    valid=bool(isinstance(result.get('report'),str) and result['report'].strip()) and result.get('model')=='glm-4.5-flash' and result.get('provider')=='zhipu'
                    valid=valid and result.get('system')==job['system'] and result.get('caseId')==job['caseId']
                    if not valid:stop_reason='invalid_response_no_content_retry';permanent=True;break
                    current=json.loads(target.read_text(encoding='utf-8'));assert current['status']=='transport_failed'
                    archived=folder/'failure_history'/(name+'.json');core.save(archived,current)
                    success={**body,'signature':lock['signature'],'status':'completed','report':result['report'],
                        'model':result['model'],'provider':result['provider'],'generatedAt':result.get('generatedAt'),
                        'finished_utc':core.now(),'transport_attempt':attempt,'full_server_response':result,
                        'upstream_finish_reason':'not_exposed_by_endpoint','recovered_after_transport_failure':True,
                        'original_failure_record':str(archived),'transport_recovery_amendment':'recovery_failed4_slow/amendment.json'}
                    core.save(target,success);events.append({'job_id':name,'attempt':attempt,'status':'recovered'})
                    print('RECOVERED '+name+' attempt'+str(attempt),flush=True);status('recovering_failed4')
                except Exception as exc:
                    code=None;details='';retry=isinstance(exc,(URLError,TimeoutError,ConnectionError))
                    if isinstance(exc,HTTPError):code=exc.code;details=exc.read(4000).decode(errors='replace');retry=code==429 or code>=500
                    core.save(path,{**rec,'http_status':code,'error_type':type(exc).__name__,'error_message':str(exc),
                        'provider_error_body':details,'transport_retry_eligible':retry,'finished_utc':core.now()})
                    events.append({'job_id':name,'attempt':attempt,'status':'transport_failed','http_status':code})
                    print('TRANSPORT_FAILURE '+name+' '+str(code),flush=True)
                    if not retry:stop_reason='nonretryable_transport_error';permanent=True
                    break
                if time.monotonic()-started>=1800:break
            if permanent:break
        if not pending():stop_reason='all_four_recovered'
        final,_=core.summarize(lock,scorer);final['status']='awaiting_remaining71' if not pending() else 'recovery_incomplete'
        final['recovery_stop_reason']=stop_reason;final['recovery_failed4_completed']=not pending();core.save(core.ROOT/'status.json',final)
        assert all(core.sha(core.ROOT/'responses'/name)==h for name,h in initial.items())
        core.save(folder/'audit.json',{'events':events,'initial_successful_reports_byte_unchanged':True,'remaining71_not_requested':True,
            'all_original_attempts_preserved':True,'final_status':final,'finished_utc':core.now()})
        print(json.dumps(final,ensure_ascii=False),flush=True)
    finally:
        if guard.exists():guard.unlink()

if __name__=='__main__':main()
