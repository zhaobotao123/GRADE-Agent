"""One English case, five configurations; exploratory workflow illustration.

Not the frozen 600-report benchmark. Credentials only from environment/stdin.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT=Path('D:/pisa2022/outputs_grade_agent_english_illustration_20261026')
SOURCE=Path('D:/Users/84130/Desktop/消融实验代码/ablation.js')
MODEL='deepseek-flash'
API='https://api.deepseek.com'
SYSTEMS=['single_turn_llm','evidence_only_llm','grade_agent_no_dml','grade_agent_no_critic','full_grade_agent']
LABELS={'single_turn_llm':'General LLM (single turn)', 'evidence_only_llm':'Evidence-only LLM (follow-up enabled)',
        'grade_agent_no_dml':'GRADE-Agent without DML evidence', 'grade_agent_no_critic':'GRADE-Agent without critic',
        'full_grade_agent':'Full GRADE-Agent'}
OPENING=("A 15-year-old student's scores on the two most recent mathematics tests have declined. "
    "The student says: 'My teacher has been giving me extra help recently, but I still get stuck when working alone. "
    "When I cannot solve a problem, I do not want to continue.' The teacher observes that the student can usually "
    "complete practice problems with prompts, but still needs help on a similar problem presented afterwards. "
    "Classroom order is generally stable. The initial account does not specify whether extra help began before "
    "or after the decline, and provides no information about home study conditions. "
    "Please identify issues worth investigating and suggest appropriate learning support. "
    "Distinguish judgments supported by the supplied information from information that still needs checking.")
FACTS={
 'support_timing':("Dated teacher records show that the first lower test score occurred before the additional help began. "
    "The teacher then arranged two 15-minute support sessions per week. The second lower score was recorded after "
    "approximately two weeks of this support. There is no controlled comparison of performance with and without support."),
 'independent_work':("The teacher reports that the student can follow a worked example and complete a problem with prompts, "
    "but often waits for the first step when attempting a similar problem independently. No item-level diagnostic assessment "
    "has yet established which mathematical knowledge or strategies are secure. The effectiveness of different prompt types is unknown."),
 'confidence':("The student reports wanting to improve but often stopping after the first unsuccessful step. "
    "The student says: 'When somebody starts it for me, I can usually keep going, but on my own I think I will get it wrong.' "
    "No standardized measure of self-efficacy or anxiety is available, and no psychological diagnosis has been made."),
 'classroom':("The teacher's recent classroom records describe stable order and no persistent instructional interruptions. "
    "The available case information does not identify a recent deterioration in classroom climate. "
    "This does not establish that every aspect of instruction is adequate."),
 'home_resources':("The parent reports that the required textbook and paper practice materials are available. "
    "The student usually has around 20 minutes for homework on school days, but shares a room and reports interruptions "
    "on some evenings. No observation or systematic home-study log is available."),
 'other_context':("Available attendance records show no recent absences, and the language of instruction has not changed. "
    "The teacher reports that the recent tests involved more multi-step problems, but test difficulty and marking have "
    "not been formally equated across occasions. Sleep, health, peer safety and the student's wider circumstances "
    "have not been independently assessed. Unreported information remains unknown.")
}

def now():return datetime.now(timezone.utc).isoformat()
def digest(data):return hashlib.sha256(data).hexdigest()
def save(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)

def prepare():
    source=SOURCE.read_text(encoding='utf-8')
    def template(name):
        match=re.search(r'(?:export )?const '+name+r' = `([\s\S]*?)`;',source)
        if not match:raise RuntimeError('Missing source prompt '+name)
        return match.group(1)
    evidence=template('EVIDENCE_MAP');predictive=template('PREDICTIVE_MAP')
    base=template('BASE_GRADE_AGENT');critic=template('CRITIC_BLOCK')
    dml=template('DML_BLOCK').replace('${EVIDENCE_MAP}',evidence)
    structure=template('OUTPUT_STRUCTURE')
    shared=("This is a controlled English-language interview with a teacher or parent, not a real student. "
        "Write all questions and reports in English. You may ask up to five follow-up questions before giving your final report. "
        "Ask one question at a time and choose exactly one domain from: "+', '.join(FACTS)+'. '
        "The interviewer returns the same prewritten domain record to every configuration requesting that domain. "
        "Do not invent additional case facts or simulate the interviewer's answers. "
        'Return one JSON object only. For a question use {"phase":"question","domain":"one domain code","question":"your question"}. '
        'When ready use {"phase":"report","report":"your final English report"}. '
        "You may finish early if sufficient information is available; preserve remaining uncertainty. "
        "For the final report, use the following presentation format. This shared format does not require an explicit critique step.\n"+structure)
    prompts={
      'single_turn_llm':("You are a general educational assistant. Read the supplied case and provide a concise English assessment "
        "of relevant factors and practical recommendations. Give your answer directly in one turn. "
        "No external evidence map or structured diagnostic rule system is provided. Do not invent case facts. Keep below 450 words."),
      'evidence_only_llm':"You are an educational assistant supplied with a PISA 2022 population evidence map.\n"+evidence+'\n\n'+shared,
      'grade_agent_no_dml':'\n\n'.join([base,predictive,critic,shared]),
      'grade_agent_no_critic':'\n\n'.join([base,predictive,dml,shared]),
      'full_grade_agent':'\n\n'.join([base,predictive,dml,critic,shared])}
    design={'created_utc':now(),'case_id':'ILLUSTRATIVE_EN_001','model_requested':MODEL,
        'case_opening':OPENING,'fixed_followup_records':FACTS,'systems':SYSTEMS,'labels':LABELS,
        'prompts':prompts,'temperature':0.4,'max_tokens':2200,'thinking':'disabled',
        'repeats_per_configuration':1,'max_questions_per_interactive_configuration':5,
        'source_prompt_path':str(SOURCE),'source_sha256':digest(SOURCE.read_bytes()),
        'runner_sha256':digest(Path(__file__).read_bytes()),
        'scope':'new_author_constructed_case_exploratory_workflow_illustration_not_original_600',
        'important_limits':['Single illustrative case, not an independently validated benchmark.',
           'General LLM receives opening only; interactive systems can obtain more facts. This is a workflow comparison, not an information-matched ablation.',
           'Interactive scaffold and report format are shared by four configurations; they are adaptations, not exact original prompts.',
           'Source evidence map is original manuscript evidence, not later Japan reanalysis.',
           'Critic is an instruction for internal self-review, not an independently run second model.',
           'No automatic success scoring, expert ratings, individual causal truth or superiority claims.',
           'No output-based retries or selection of best response. All successful and failed calls retained.']}
    stable={k:v for k,v in design.items() if k!='created_utc'}
    design['signature']=digest(json.dumps(stable,ensure_ascii=False,sort_keys=True).encode())
    lock=ROOT/'protocol_lock.json'
    if lock.exists():
        prior=json.loads(lock.read_text(encoding='utf-8'))
        if prior['signature']!=design['signature']:raise RuntimeError('Protocol changed; use new output folder.')
        return prior
    save(lock,design);return design

def api(path,key,body=None):
    req=Request(API+path,data=json.dumps(body).encode() if body is not None else None,
        headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
    try:
        with urlopen(req,timeout=150) as response:return json.loads(response.read().decode())
    except HTTPError as exc:raise RuntimeError(f'API HTTP {exc.code}; no model substitution') from None

def session(system,design,key):
    folder=ROOT/'sessions'/system;complete=folder/'session.json'
    if complete.exists():
        prior=json.loads(complete.read_text(encoding='utf-8'));assert prior['signature']==design['signature'];return prior
    messages=[{'role':'system','content':design['prompts'][system]},{'role':'user','content':OPENING}]
    revealed=[];turns=[];report=None;error=None
    for index in range(1 if system=='single_turn_llm' else 6):
        if index==5:
            messages.append({'role':'user','content':'The follow-up allowance is exhausted. Return your final report JSON using only the facts already provided; preserve unknown information.'})
        body={'model':MODEL,'messages':messages,'temperature':.4,'max_tokens':2200,'thinking':{'type':'disabled'},'stream':False}
        if system!='single_turn_llm':body['response_format']={'type':'json_object'}
        rawpath=folder/f'call_{index+1:02}.json'
        if rawpath.exists():
            row=json.loads(rawpath.read_text(encoding='utf-8'));assert row['signature']==design['signature']
        else:
            start=time.monotonic();payload=api('/chat/completions',key,body);choice=payload['choices'][0]
            row={'signature':design['signature'],'model_returned':payload.get('model'),'response_id':payload.get('id'),
                'usage':payload.get('usage'),'finish_reason':choice.get('finish_reason'),
                'content':choice['message'].get('content',''),'request_messages':messages.copy(),
                'elapsed_seconds':time.monotonic()-start,'generated_utc':now()}
            save(rawpath,row)
        turns.append({'turn':index+1,'response':row,'revealed_before':revealed.copy()})
        if row['finish_reason']!='stop':error='non_stop_finish_reason';break
        content=row['content'];messages.append({'role':'assistant','content':content})
        if system=='single_turn_llm':report=content;break
        try:parsed=json.loads(content)
        except (ValueError,TypeError):error='invalid_JSON';break
        turns[-1]['parsed']=parsed
        if not isinstance(parsed,dict):error='invalid_schema';break
        if parsed.get('phase')=='report' and isinstance(parsed.get('report'),str) and parsed['report'].strip():report=parsed['report'];break
        domain=parsed.get('domain')
        if parsed.get('phase')!='question' or domain not in FACTS or index==5:error='invalid_phase_or_domain';break
        if domain in revealed:reply='This domain record has already been supplied. There are no additional recorded facts for it.'
        else:revealed.append(domain);reply='Recorded facts for '+domain+': '+FACTS[domain]
        turns[-1]['interviewer_reply']=reply;messages.append({'role':'user','content':reply})
    result={'system':system,'label':LABELS[system],'signature':design['signature'],'revealed_domains':revealed,
        'question_count':sum('interviewer_reply' in t for t in turns),'turns':turns,'final_report':report,
        'status':'completed' if report else 'failed','error':error}
    save(complete,result);print(system+' '+result['status']+' questions='+str(result['question_count']),flush=True);return result

def export(design,results):
    ordered=sorted(results,key=lambda x:SYSTEMS.index(x['system']))
    save(ROOT/'raw_sessions.json',ordered)
    lines=['# English illustrative case: five system configurations','',
        'Exploratory workflow demonstration using DeepSeek Flash. Not part of the original 600-report benchmark.',
        'The general LLM receives the opening only; the other configurations can request additional fixed records. Differences therefore combine information access and workflow.',
        'One run per configuration; no best-run selection or expert scores.','', '## Initial case','',OPENING,'',
        '## Fixed follow-up records (written before generation)','']
    for domain,fact in FACTS.items():lines.extend(['### '+domain,'',fact,''])
    lines.extend(['## Session overview','','| Configuration | Follow-up questions | Domains disclosed | Status |','|---|---:|---|---|'])
    for r in ordered:lines.append('| '+r['label']+' | '+str(r['question_count'])+' | '+', '.join(r['revealed_domains'])+' | '+r['status']+' |')
    for r in ordered:
        lines.extend(['','## '+r['label'],'','### Follow-up dialogue',''])
        for turn in r['turns']:
            p=turn.get('parsed',{})
            if p.get('phase')=='question':lines.extend(['**Question:** '+str(p.get('question','')),'','**Fixed response:** '+turn.get('interviewer_reply','No response: invalid request.'),''])
        if r['question_count']==0:lines.extend(['No follow-up questions.',''])
        lines.extend(['### Final report','',r['final_report'] or '[No valid final report; see raw session.]',''])
    (ROOT/'English_Case_Comparison_Full.md').write_text('\n'.join(lines),encoding='utf-8')
    save(ROOT/'status.json',{'status':'completed' if all(r['status']=='completed' for r in ordered) else 'completed_with_failures',
         'planned_sessions':5,'saved_sessions':len(ordered),'valid_reports':sum(r['status']=='completed' for r in ordered),
         'model_requested':MODEL,'signature':design['signature'],'updated_utc':now()})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');args=parser.parse_args()
    design=prepare()
    if not args.run:print('PREPARED '+design['signature']);return
    key=os.environ.get('DEEPSEEK_API_KEY')
    if not key:key=sys.stdin.readline().strip()
    if not key:raise RuntimeError('DEEPSEEK_API_KEY missing')
    available=api('/models',key);ids=[r['id'] for r in available.get('data',[])]
    save(ROOT/'model_availability.json',{'checked_utc':now(),'requested':MODEL,'available_ids':ids})
    if MODEL not in ids:raise RuntimeError('Requested Flash model unavailable; no substitution')
    save(ROOT/'status.json',{'status':'running','planned_sessions':5,'signature':design['signature'],'updated_utc':now()})
    results=[]
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures={executor.submit(session,s,design,key):s for s in SYSTEMS}
        for future in as_completed(futures):
            try:results.append(future.result())
            except Exception as exc:
                s=futures[future];save(ROOT/'failures'/f'{s}.json',{'system':s,'error':str(exc),'timestamp':now()})
                results.append({'system':s,'label':LABELS[s],'status':'failed','error':str(exc),'turns':[],
                    'revealed_domains':[],'question_count':0,'final_report':None,'signature':design['signature']})
                print(s+' failed '+str(exc),flush=True)
    key=None;export(design,results);print('EXPORT_COMPLETE',flush=True)

if __name__=='__main__':main()
