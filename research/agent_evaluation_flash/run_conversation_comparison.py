"""Frozen English two-system multi-turn comparison; no automatic quality verdict."""
import argparse,hashlib,json,os,random,subprocess,sys,time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor,wait,FIRST_COMPLETED
from datetime import datetime,timezone
HERE=Path(__file__).resolve().parent
PROJECT=Path('C:/Users/84130/Documents/Codex/2026-07-03/zhe/gradeagent')
ROOT=Path('D:/pisa2022/outputs_grade_agent_english_comparison_20261027')
NODE='C:/Users/84130/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node.exe'
SOURCE=Path('D:/pisa2022/outputs_grade_agent_deepseek41flash300_20261026/protocol_lock.json')
BASELINE='''You are a helpful conversational assistant. A teacher or caregiver is discussing a student's mathematics learning. Respond in English, engage naturally with what they say, ask a relevant follow-up when useful, and provide helpful practical advice when asked. Do not assume that all the information is known.
For the common interface only: return JSON with phase (question, summary, or safety_escalation), reply (your actual answer), questionFocus, coverage (confirmed domain keys), and suggestedReplies (empty array). Use one focused question on question turns. Domain keys are trajectory, confidence, classroom, support_timing, context_safety. When asked for a final summary, write one natural paragraph of approximately 80-140 English words, without headings or bullets. Do not expose interface bookkeeping in the reply.'''
def now():return datetime.now(timezone.utc).isoformat()
def save(p,data):
 p.parent.mkdir(parents=True,exist_ok=True);tmp=p.with_suffix(p.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');tmp.replace(p)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def user_turns(answers):
 first='I would like help understanding a student\'s mathematics learning. '+answers['trajectory']
 if 'safety' in answers:first+=' '+answers['safety']
 second='Here is the next information available: '+' '.join(answers[k] for k in ['confidence','classroom'] if k in answers)
 rest=' '.join(v for k,v in answers.items() if k not in ['trajectory','safety','confidence','classroom'])
 third='Here is the remaining information I can provide: '+rest+' I do not have further details beyond these observations.'
 fourth='Please now write a brief final summary in English, in one natural paragraph of approximately 80-140 words: what should receive attention, and what could be tried first? Base your response on the information available.'
 return [first,second,third,fourth]
def prepare():
 ROOT.mkdir(parents=True,exist_ok=True)
 original=json.loads(SOURCE.read_text(encoding='utf-8'))['plan']['cases']
 cases=[{'case_id':c['caseId'],'facts':c['answers'],'user_turns':user_turns(c['answers'])} for c in original]
 frozen=[Path(__file__),HERE/'conversation_comparison_worker.mjs',PROJECT/'functions/api/chat.js',PROJECT/'functions/lib/conversation.js',PROJECT/'functions/lib/llm.js',SOURCE]
 plan={'name':'English conversational final-reply comparison','model':'deepseek-flash','systems':['ordinary_llm','grade_agent'],'cases':cases,'repeats':5,'planned_conversations':120,'turns_per_conversation':4,'temperature':.25,'max_tokens':1400,'thinking':'disabled','seed':20261027,'concurrency':2,'baseline_prompt':BASELINE,'source_hashes':{str(p):sha(p) for p in frozen},
 'comparison_scope':'Same base model, scripted English user updates, facts, order, turn budget, final length instruction. Compare final reply quality, not adaptive questioning skill. Agent includes actual app prompt, validation and safety middleware; baseline has neutral ordinary-assistant instructions plus the same interface schema/validator. No attribution to a single component.',
 'generation_policy':'All API attempts, finish reasons, model IDs and usage retained. At most four transport attempts per call (5/10/20-second backoff). Actual app allows one format-repair call; baseline has the same allowance. Failed conversations remain failed; no content/quality-based reruns. No automatic teacher ratings or winner.',
 'teacher_evaluation':{'dimensions':['contextual relevance','consistency with case facts','appropriateness and actionability of suggestions','clarity'],'scale':'1 very poor, 2 poor, 3 adequate, 4 good, 5 very good; dimension-specific anchors must be provided before scoring','raters':'Two independent teachers, blinded A/B, randomized order, originals unmodified','primary_outcome':'appropriateness and actionability of suggestions','secondary_outcomes':'remaining three dimensions; report all with multiplicity-aware interpretation','analysis':'Case is the cluster; repetitions are not independent students. Report paired case-level differences with case-cluster bootstrap CI; inter-rater agreement; no weighted composite ranking. Small n=12 and exploratory inference disclosed.'},
 'limitations':['These 12 synthetic cases were previously examined and used in development; not unseen validation.','Predefined staged updates may not answer the exact follow-up question; same updates for both groups isolate final-reply comparison.','Ordinary LLM does not receive the agent research prompt; this is a full-system comparison, not DML ablation.','New English conversation outputs cannot replace or relabel old report experiments.'],
 'references':{'general_evaluation_framework':'https://aclanthology.org/2023.emnlp-main.153/','groundedness_framework':'https://aclanthology.org/2024.eacl-demo.16/'},'rubric_status':'Adapted task-specific rubric, NOT a validated educational diagnostic scale. Teacher review pending.','credentials':'stdin and process memory only'}
 plan['teacher_evaluation']['dimension_anchors']={
 'contextual relevance':{'1':'Misses the central concern or is largely unrelated.','3':'Addresses the concern but includes generic or distracting material or misses an important relevant point.','5':'Focuses on the case-relevant concern and priorities without treating neutral background as a problem.'},
 'consistency with case facts':{'1':'Invents or contradicts a central fact or states an unsupported individual cause as established.','3':'Mostly consistent but contains a material unsupported inference or insufficiently qualified interpretation.','5':'Faithfully uses the supplied facts, distinguishes unknown from absent, and keeps conclusions within what those facts support.'},
 'appropriateness and actionability of suggestions':{'1':'Advice is unsuitable, unsafe, or not usable for this case.','3':'Advice is broadly suitable but insufficiently specific or poorly adapted to the available information.','5':'Proposes feasible, concrete first steps appropriate to the case and its uncertainties; requesting missing information or prioritizing safety can be fully appropriate.'},
 'clarity':{'1':'Difficult to follow or understand.','3':'Understandable overall but contains unnecessary jargon, repetition, or unclear organization.','5':'Clear, coherent, concise and accessible to a teacher or caregiver.'},
 'intermediate_scores':'2 lies between 1 and 3; 4 lies between 3 and 5. Do not reward length, statistical jargon, or agreement with a preferred system. A score of 5 does not establish diagnostic correctness or real-world educational benefit.'}
 signature=hashlib.sha256(json.dumps(plan,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
 lock={'signature':signature,'created_utc':now(),'plan':plan};target=ROOT/'protocol_lock.json'
 if target.exists():
  lock=json.loads(target.read_text(encoding='utf-8'));assert lock['signature']==signature,'Frozen source changed; stop and use a new experiment directory.'
 else:save(target,lock)
 jobs=[{'id':f"{c['case_id']}__{s}__r{r:02d}",'case_id':c['case_id'],'system':s,'repeat':r,'user_turns':c['user_turns']} for c in cases for s in plan['systems'] for r in range(1,6)]
 random.Random(20261027).shuffle(jobs);save(ROOT/'execution_order.json',[j['id'] for j in jobs])
 return lock,jobs
def execute(job,key,folder):
 cfg={'apiKey':key,'directory':str(folder),'project':str(PROJECT),'system':job['system'],'job':{k:v for k,v in job.items() if k!='user_turns'},'userTurns':job['user_turns'],'baselinePrompt':BASELINE}
 child=subprocess.run([NODE,str(HERE/'conversation_comparison_worker.mjs')],input=json.dumps(cfg),text=True,encoding='utf-8',capture_output=True,timeout=1800,creationflags=subprocess.CREATE_NO_WINDOW)
 if child.returncode!=0:save(folder/'process_failure.json',{'code':child.returncode,'error':child.stderr.replace(key,'[REDACTED]')[-2000:]})
 result=folder/'conversation.json'
 return json.loads(result.read_text(encoding='utf-8')) if result.exists() else {'status':'failed','job':job['id']}
def status(running):
 rows=[json.loads(p.read_text(encoding='utf-8')) for p in (ROOT/'conversations').glob('*/conversation.json')]
 finished=[r for r in rows if r['status']!='running'];done=sum(r['status']=='completed' for r in finished)
 data={'status':'running' if running else ('generation_completed_teacher_review_pending' if len(finished)==120 else 'incomplete'),'planned_conversations':120,'completed':done,'failed':len(finished)-done,'active':len(rows)-len(finished),'remaining':120-len(finished),'worker_pid':os.getpid(),'model':'deepseek-flash','updated_utc':now(),'by_system':{s:sum(r['status']=='completed' and r['system']==s for r in finished) for s in ['ordinary_llm','grade_agent']}}
 save(ROOT/'status.json',data);save(ROOT/'final_replies.json',[{'job':r['job'],'system':r['system'],'status':r['status'],'final_reply':r.get('final_reply')} for r in finished]);return data
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');args=parser.parse_args();lock,jobs=prepare();print('PROTOCOL '+lock['signature'],flush=True)
 if not args.run:status(False);return
 key=sys.stdin.readline().strip();assert key,'No runtime credential'
 guard=ROOT/'worker.lock';guard.open('x').write(str(os.getpid()))
 try:
  # Novel smoke case, excluded from formal 120. Both full four-turn paths must work.
  pilot_facts={'trajectory':'The last two mathematics quizzes were lower than earlier in the term.','confidence':'The student attempts fractions but confuses numerator and denominator.','classroom':'The class is orderly.','support':'The teacher recently began checking one worked example with the student.'}
  pilots=[]
  for s in ['ordinary_llm','grade_agent']:
   job={'id':'PILOT__'+s,'system':s,'case_id':'PILOT','repeat':0,'user_turns':user_turns(pilot_facts)}
   result=execute(job,key,ROOT/'pilot'/s);pilots.append(result)
   print('PILOT '+s+' '+result['status'],flush=True)
  if not all(r['status']=='completed' for r in pilots):raise RuntimeError('Pilot failed; formal experiment not started')
  save(ROOT/'pilot_check.json',{'excluded_from_formal':True,'completed':True,'time':now()})
  todo=[j for j in jobs if not (ROOT/'conversations'/j['id']/'conversation.json').exists()]
  status(True)
  with ThreadPoolExecutor(max_workers=2) as pool:
   iterator=iter(todo);pending={}
   for _ in range(2):
    j=next(iterator,None)
    if j:pending[pool.submit(execute,j,key,ROOT/'conversations'/j['id'])]=j
   while pending:
    done,_=wait(pending,return_when=FIRST_COMPLETED)
    for future in done:
     job=pending.pop(future);result=future.result();state=status(True)
     print(f"{state['completed']} complete / {state['failed']} failed /120: {job['id']} {result['status']}",flush=True)
     if any(sha(Path(p))!=h for p,h in lock['plan']['source_hashes'].items()):raise RuntimeError('Frozen source modified during experiment')
     j=next(iterator,None)
     if j:pending[pool.submit(execute,j,key,ROOT/'conversations'/j['id'])]=j
  print(json.dumps(status(False)),flush=True)
 except Exception as error:
  save(ROOT/'worker_failure.json',{'error':str(error).replace(key,'[REDACTED]'),'time':now()});status(False);raise
 finally:
  guard.unlink(missing_ok=True);key=None
if __name__=='__main__':main()
