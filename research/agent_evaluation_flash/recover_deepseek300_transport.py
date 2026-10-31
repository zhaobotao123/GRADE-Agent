"""Complete the original five-attempt transport budget for interrupted HTTP reads.

Waits for the original worker; never reruns a successfully received model output.
"""
import json,os,sys,time
from pathlib import Path
from urllib.error import HTTPError,URLError
from http.client import IncompleteRead,RemoteDisconnected
import run_deepseek300_locked as core

def main():
    key=sys.stdin.readline().strip()
    if not key:raise RuntimeError('Runtime credential missing.')
    guard=core.ROOT/'worker.lock';start=time.monotonic()
    print('WAITING_FOR_GENERATION_WORKER',flush=True)
    while guard.exists():
        if time.monotonic()-start>14400:raise RuntimeError('Generation worker still active; no overlapping recovery started.')
        time.sleep(10)
    lock=core.prepare();folder=core.ROOT/'transport_recovery';folder.mkdir(exist_ok=True)
    files=sorted((core.ROOT/'responses').glob('*.json'))
    successful={p.name:core.sha(p) for p in files if json.loads(p.read_text(encoding='utf-8'))['status']!='transport_failed'}
    failed=[p for p in files if json.loads(p.read_text(encoding='utf-8'))['status']=='transport_failed']
    amendment={'created_utc':core.now(),'signature':lock['signature'],'scope':'Only network/HTTP-body-read failures; never truncate/content/format-based replacement.',
        'reason':'http.client.IncompleteRead is a transport interruption, but the original retry classifier did not recognize it.',
        'attempt_budget':'Keep original maximum5 attempts per job including all earlier attempts; no extra budget added.',
        'all_generation_parameters_unchanged':True,'original_failures_preserved':True,'failed_jobs':[p.stem for p in failed],
        'runner_sha256':core.sha(Path(__file__))}
    assert not (folder/'operational_note.json').exists()
    core.save(folder/'operational_note.json',amendment)
    with guard.open('x',encoding='utf-8') as f:f.write(str(os.getpid()))
    try:
        for target in failed:
            old=json.loads(target.read_text(encoding='utf-8'));name=target.stem
            archive=folder/'original_failures'/target.name;core.save(archive,old)
            paths=list((core.ROOT/'attempts'/name).glob('attempt*.json'))
            used=max(int(p.stem.replace('attempt','')) for p in paths)
            first=json.loads((core.ROOT/'attempts'/name/'attempt01.json').read_text(encoding='utf-8'))
            body=first['request_body'];assert body['model']==core.MODEL
            for attempt in range(used+1,6):
                path=core.ROOT/'attempts'/name/f'attempt{attempt:02d}.json';assert not path.exists()
                record={'signature':lock['signature'],'job_id':name,'attempt':attempt,'started_utc':core.now(),
                    'endpoint':core.API+'/chat/completions','request_body':body,'operational_note':'transport_recovery/operational_note.json'}
                core.save(path,record);state=core.export(lock);state['worker_pid']=os.getpid();state['status']='recovering_transport';core.save(core.ROOT/'status.json',state)
                try:
                    response=core.request_api('/chat/completions',key,body);core.save(path,{**record,'response':response,'finished_utc':core.now()})
                    choice=(response.get('choices') or [{}])[0];report=choice.get('message',{}).get('content','') or '';finish=choice.get('finish_reason')
                    status='completed' if report.strip() and finish=='stop' else 'generated_incomplete'
                    if 'flash' not in str(response.get('model','')).lower():status='unexpected_model'
                    row={**{k:old[k] for k in ['system','caseId','answers','repeat']},'signature':lock['signature'],'status':status,
                        'report':report,'model':response.get('model'),'model_requested':core.MODEL,'finish_reason':finish,
                        'response_id':response.get('id'),'system_fingerprint':response.get('system_fingerprint'),'usage':response.get('usage'),
                        'generatedAt':core.now(),'transport_attempt':attempt,'full_api_response':response,'recovered_after_transport_failure':True,
                        'original_failure_record':str(archive)}
                    core.save(target,row);print('RECOVERED '+name+' '+status,flush=True);core.export(lock);break
                except Exception as exc:
                    code=None;detail='';retry=isinstance(exc,(URLError,TimeoutError,ConnectionError,IncompleteRead,RemoteDisconnected))
                    if isinstance(exc,HTTPError):code=exc.code;detail=exc.read(4000).decode(errors='replace').replace(key,'[REDACTED]');retry=code==429 or code>=500
                    core.save(path,{**record,'error_type':type(exc).__name__,'http_status':code,'error_message':str(exc).replace(key,'[REDACTED]'),
                        'provider_error_body':detail,'transport_retry_eligible':retry,'finished_utc':core.now()})
                    if not retry or attempt==5:break
                    time.sleep(15*2**(attempt-1))
        state=core.export(lock,False)
        assert all(core.sha(core.ROOT/'responses'/name)==h for name,h in successful.items())
        core.save(folder/'integrity_check.json',{'existing_successful_or_incomplete_outputs_byte_unchanged':True,
            'original_attempts_retained':True,'generation_settings_unchanged':True,'final_status':state,'finished_utc':core.now()})
        print(json.dumps(state,ensure_ascii=False),flush=True)
    finally:
        key=None
        if guard.exists():guard.unlink()

if __name__=='__main__':main()
