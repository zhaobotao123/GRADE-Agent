"""Provider replication of the fixed English workflow case; original outputs untouched."""
from pathlib import Path
import hashlib,json,os,sys
import run_english_illustrative_case as core

core.ROOT=Path('D:/pisa2022/outputs_grade_agent_glm_illustration_20261026')
core.MODEL='glm-4.5-flash'
core.API='https://open.bigmodel.cn/api/paas/v4'

def main():
    design=core.prepare()
    previous=json.loads(Path('D:/pisa2022/outputs_grade_agent_english_illustration_20261026/protocol_lock.json').read_text(encoding='utf-8'))
    for name in ['case_opening','fixed_followup_records','systems','prompts','temperature','max_tokens','repeats_per_configuration','max_questions_per_interactive_configuration']:
        assert design[name]==previous[name],name
    core.save(core.ROOT/'provider_replication.json',{'provider':'Zhipu','api_base':core.API,'model_requested':core.MODEL,
        'wrapper_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'same_case_prompts_settings_as_deepseek_flash':True,'prior_signature':previous['signature']})
    key=os.environ.get('ZHIPU_API_KEY') or sys.stdin.readline().strip()
    if not key:raise RuntimeError('Credential missing')
    smoke=core.api('/chat/completions',key,{'model':core.MODEL,'messages':[{'role':'user','content':'Return JSON only: {"ok":true}'}],
        'thinking':{'type':'disabled'},'temperature':.4,'max_tokens':64,'response_format':{'type':'json_object'},'stream':False})
    core.save(core.ROOT/'model_smoke_response.json',smoke)
    assert smoke.get('model')==core.MODEL
    core.save(core.ROOT/'status.json',{'status':'running','model':core.MODEL,'planned_sessions':5})
    results=[]
    for system in core.SYSTEMS:
        try:results.append(core.session(system,design,key))
        except Exception as exc:
            core.save(core.ROOT/'failures'/f'{system}.json',{'system':system,'error':str(exc),'timestamp':core.now()})
            results.append({'system':system,'label':core.LABELS[system],'status':'failed','error':str(exc),'turns':[],
                'revealed_domains':[],'question_count':0,'final_report':None,'signature':design['signature']})
            print(system+' failed '+str(exc),flush=True)
        core.save(core.ROOT/'status.json',{'status':'running','model':core.MODEL,'planned_sessions':5,'saved_sessions':len(results)})
    key=None;core.save(core.ROOT/'raw_sessions.json',results)
    core.save(core.ROOT/'status.json',{'status':'completed' if all(r['status']=='completed' for r in results) else 'completed_with_failures',
        'model':core.MODEL,'saved_sessions':len(results),'strictly_valid_reports':sum(r['status']=='completed' for r in results),'updated_utc':core.now()})
    lines=['# GLM-4.5-Flash: actual English case comparison','',
        'One exploratory run per configuration; not part of the original 600 reports. The baseline has less case information than the interactive configurations.',
        'Identical initial case, fixed answer records, system prompts and generation settings to the previous DeepSeek Flash illustration.','',
        '## Initial case','',design['case_opening'],'']
    for r in results:
        lines.extend(['## '+r['label'],'','Strict status: '+r['status'],''])
        for t in r['turns']:
            p=t.get('parsed',{})
            if p.get('phase')=='question':lines.extend(['**Question:** '+p.get('question',''),'','**Fixed response:** '+t.get('interviewer_reply','[No answer]'),''])
        report=r.get('final_report')
        if not report and r['turns']:
            try:
                p=json.loads(r['turns'][-1]['response']['content'],strict=False)
                if p.get('phase')=='report' and isinstance(p.get('report'),str):
                    report=p['report'];lines.extend(['Format-tolerant extraction only; strict failure retained.',''])
            except (ValueError,TypeError,AttributeError):pass
        lines.extend(['### Final report','',report or '[No valid final report. See preserved raw output.]',''])
    (core.ROOT/'GLM_English_Case_Full.md').write_text('\n'.join(lines),encoding='utf-8')
    print('EXPORT_COMPLETE',flush=True)

if __name__=='__main__':main()
