"""Matched-information 2x2x2 prompt-factor pilot; no website/manuscript mutations.

P=prediction/SHAP information bundle; D=DML information bundle;
C=same-call self-check instruction (NOT an independently invoked reviewer).
"""
import argparse,csv,hashlib,itertools,json,os,random,re,sys,time,uuid
from pathlib import Path
from datetime import datetime,timezone
from urllib.request import Request,urlopen
from urllib.error import HTTPError

ROOT=Path('D:/pisa2022/outputs_grade_agent_factorial8_matched_pilot_20261026')
MODEL='glm-4.5-flash'
API='https://open.bigmodel.cn/api/paas/v4/chat/completions'
CASE_SOURCE=Path('D:/pisa2022/outputs_grade_agent_glm_illustration_20261026/protocol_lock.json')
METRICS=Path('D:/pisa2022/outputs_five_models_tuned_42_features/tuned_five_model_metrics_summary.csv')
SHAP=Path('D:/pisa2022/outputs_final_shap_42_features/shap_importance_pooled.csv')
DML=Path('D:/pisa2022/outputs_grade_agent_formal/table_4_dml_pooled_results.csv')
COMMON=("You are an educational assistant preparing a provisional mathematics learning-support report. "
    "Use the supplied case records. Distinguish reported observations from interpretations that need checking. "
    "Do not invent case facts or present an individual cause as established. "
    "Do not ask additional questions in this task: every configuration receives the same complete record. "
    "State unresolved information in the final report. Write in English, below 450 words, using exactly these headings:\n"
    "CASE SUMMARY\nPRIORITY ISSUES\nINFORMATION STILL NEEDED\nLEARNING-SUPPORT PLAN\nINTERPRETATION LIMITS\n"
    "In LEARNING-SUPPORT PLAN, give actions for teacher, family and student. State the relevant case issue, action, "
    "time window and observable review indicator. Return the final report only, without a JSON wrapper or internal reasoning.")
CHECK=("<SELF_CHECK_INSTRUCTION>\nBefore returning your final report, check your draft against the supplied case records "
    "and any supplied research findings. Check that each priority has a supporting case fact; that temporal order "
    "has not been reversed; that a stable or unknown background condition has not been asserted to be a demonstrated "
    "problem; that no population result has been treated as proof of this student's cause; and that each action "
    "matches the stated issue and the available time and resources. Check for contradictions and unsupported conclusions. "
    "Revise any violations before returning the report. Do not output the checking process.\n</SELF_CHECK_INSTRUCTION>")

def now():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,obj):
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_suffix(path.suffix+'.tmp');temp.write_text(json.dumps(obj,ensure_ascii=False,indent=2),encoding='utf-8');temp.replace(path)
def rows(path):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))

def prepare():
    old=json.loads(CASE_SOURCE.read_text(encoding='utf-8'))
    case='INITIAL ACCOUNT\n'+old['case_opening']+'\n\nADDITIONAL FIXED RECORDS\nThese records fill the information gaps noted in the initial account.\n'
    case+='\n\n'.join(domain+': '+fact for domain,fact in old['fixed_followup_records'].items())
    metrics=rows(METRICS);shap=rows(SHAP);dml=rows(DML)
    best=next(r for r in metrics if r['model']=='LightGBM')
    predictive=['<PREDICTIVE_SHAP_INFORMATION>',
      'Population-level predictive analysis from the original Japan PISA 2022 study.',
      f"LightGBM mean weighted test R2={float(best['weighted_r2_mean']):.6f}, RMSE={float(best['weighted_rmse_mean']):.6f}.",
      'Top ten features by pooled mean absolute SHAP contribution:']
    for r in shap[:10]:predictive.append(f"{r['feature']}: mean absolute SHAP={float(r['mean_abs_shap']):.6f}.")
    predictive+=['SHAP contributions describe fitted predictions, not causal effects or established individual explanations.', '</PREDICTIVE_SHAP_INFORMATION>']
    predictive='\n'.join(predictive)
    adjusted=['<DML_INFORMATION>',
      'Cross-fitted DML findings from the original Japan PISA 2022 study, pooled over ten mathematics plausible values.',
      'Variable definitions: MATHEFF=mathematics self-efficacy; DISCLIM=disciplinary climate; BELONG=school belonging; '
      'ICTSCH=school ICT resources; TEACHSUP=teacher support; ICTQUAL=digital-resource quality; HOMEPOS=home possessions; '
      'ESCS=economic, social and cultural status; ICTENQ=ICT inquiry/use; BULLIED=being bullied; '
      'ANXMAT=mathematics anxiety; MATHEF21=21st-century mathematics self-efficacy.',
      'Each row gives the adjusted coefficient, pooled school-clustered standard error, pooled p value and direction consistency.']
    for r in dml:
        pv=float(r['p_value_pooled']);ptext='<0.000001' if pv<1e-6 else f'{pv:.6f}'
        adjusted.append(f"{r['treatment']}: coefficient={float(r['coef_pooled']):.6f}; SE={float(r['std_error_pooled']):.6f}; "
            f"p={ptext}; direction consistent across plausible values={r['direction_consistent']}.")
    adjusted+=['These are population adjusted associations under the implemented observational specification. '
      'Raw coefficients use different index scales and must not be ranked as directly comparable effect magnitudes. '
      'The estimates do not establish an individual student cause.', '</DML_INFORMATION>']
    adjusted='\n'.join(adjusted)
    blocks={'P':predictive,'D':adjusted,'C':CHECK}
    configs=[]
    for p,d,c in itertools.product([0,1],repeat=3):
        flags={'P':p,'D':d,'C':c};name=f'P{p}_D{d}_C{c}'
        prompt=COMMON+'\n\n'+'\n\n'.join(blocks[k] for k in ['P','D','C'] if flags[k])
        # Strip optional blocks: every configuration must reduce to the same base.
        stripped=prompt
        for b in blocks.values():stripped=stripped.replace(b,'')
        assert stripped.strip()==COMMON
        for k,b in blocks.items():assert (b in prompt)==bool(flags[k])
        if not p:assert '<PREDICTIVE_SHAP_INFORMATION>' not in prompt and 'mean absolute SHAP=' not in prompt
        if not d:assert '<DML_INFORMATION>' not in prompt and 'coefficient=' not in prompt
        if not c:assert '<SELF_CHECK_INSTRUCTION>' not in prompt and 'check your draft' not in prompt
        configs.append({'configuration':name,'flags':flags,'system_prompt':prompt})
    for a in configs:
        for b in configs:
            diffs=[k for k in blocks if a['flags'][k]!=b['flags'][k]]
            if len(diffs)==1:
                k=diffs[0]
                normalize=lambda s:re.sub(r'\n{3,}','\n\n',s.replace(blocks[k],'')).strip()
                assert normalize(a['system_prompt'])==normalize(b['system_prompt'])
    lock={'created_utc':now(),'scope':'single_case_matched_information_prompt_factorial_pilot_not_original600',
      'model':MODEL,'api_endpoint':API,'language':'English','case_id':'ILLUSTRATIVE_EN_001_COMPLETE_RECORD',
      'case_record':case,'common_instruction':COMMON,'optional_blocks':blocks,'configurations':configs,
      'temperature':.4,'max_tokens':2200,'thinking':'disabled','repeats':1,'planned_calls':8,
      'randomized_order_seed':20261026,'input_hashes':{str(p):sha(p) for p in [CASE_SOURCE,METRICS,SHAP,DML]},
      'runner_sha256':sha(Path(__file__)),
      'limits':['P bundles prediction and SHAP information; their individual effects are not separated.',
         'C is a same-call self-check instruction, not an independent reviewer invocation.',
         'All conditions receive the same complete case record, format, action requirements and generation parameters.',
         'No adaptive follow-up, special priority-routing rules or evidence-derived classification rules are shared.',
         'Optional information content and prompt length necessarily differ; no total-token matched placebo is provided.',
         'One exposed synthetic case and one run per cell; no general superiority, significance or consistency estimate.',
         'No output-based retries, selection of best answers or fabricated expert ratings.']}
    stable={k:v for k,v in lock.items() if k!='created_utc'}
    lock['signature']=hashlib.sha256(json.dumps(stable,ensure_ascii=False,sort_keys=True).encode()).hexdigest()
    path=ROOT/'protocol_lock.json'
    if path.exists():
        previous=json.loads(path.read_text(encoding='utf-8'));assert previous['signature']==lock['signature'];lock=previous
    else:save(path,lock)
    save(ROOT/'pre_run_contract_checks.json',{'eight_unique_cells':len({r['configuration'] for r in configs})==8,
       'all_case_records_identical':True,'optional_blocks_exactly_toggle':True,'one_factor_pairwise_differences_only':True,
       'no_DML_payload_in_D0':True,'no_predictive_SHAP_payload_in_P0':True,'no_self_check_instruction_in_C0':True,
       'original_data_unchanged':True,'signature':lock['signature']})
    return lock

def generate(config,lock,key):
    target=ROOT/'responses'/(config['configuration']+'.json')
    if target.exists():
        row=json.loads(target.read_text(encoding='utf-8'));assert row['signature']==lock['signature'];return row
    body={'model':MODEL,'messages':[{'role':'system','content':config['system_prompt']},
         {'role':'user','content':lock['case_record']}],'temperature':.4,'max_tokens':2200,'thinking':{'type':'disabled'},'stream':False}
    for attempt in range(3):
        started=time.monotonic()
        request=Request(API,data=json.dumps(body).encode(),headers={'Authorization':'Bearer '+key,'Content-Type':'application/json'})
        try:
            with urlopen(request,timeout=150) as response:payload=json.loads(response.read().decode())
            choice=payload['choices'][0]
            row={'configuration':config['configuration'],'flags':config['flags'],'signature':lock['signature'],
              'request_body':body,'response_id':payload.get('id'),'model_returned':payload.get('model'),
              'finish_reason':choice.get('finish_reason'),'report':choice['message'].get('content',''),
              'usage':payload.get('usage'),'generated_utc':now(),'elapsed_seconds':time.monotonic()-started,
              'transport_attempt':attempt+1}
            row['status']='completed' if row['report'] and row['finish_reason']=='stop' else 'incomplete'
            save(target,row);return row
        except HTTPError as exc:
            try:err=json.loads(exc.read().decode()).get('error',{})
            except Exception:err={}
            save(ROOT/'transport_events'/(uuid.uuid4().hex+'.json'),{'configuration':config['configuration'],
              'http_status':exc.code,'provider_code':err.get('code'),'message':str(err.get('message','')).replace(key,'[REDACTED]'),
              'time':now(),'attempt':attempt+1})
            if exc.code!=429 or str(err.get('code'))=='1113' or attempt==2:raise RuntimeError(f'HTTP {exc.code}; provider code {err.get("code")}') from None
            time.sleep(20*(attempt+1))

def export(lock):
    result=[]
    for config in lock['configurations']:
        path=ROOT/'responses'/(config['configuration']+'.json')
        if path.exists():result.append(json.loads(path.read_text(encoding='utf-8')))
    save(ROOT/'raw_reports.json',result)
    lines=['# Matched-information eight-condition pilot','',
      'Model: GLM-4.5-Flash. One run per cell. P=prediction/SHAP information; D=DML information; C=same-call self-check instruction.',
      'All conditions receive identical complete case facts and report requirements. This is a prompt-component factorial pilot, not an independent-reviewer system test.',
      'Previous multi-turn illustrations and the original 600-report experiment are unchanged.','',
      '## Common complete case record','',lock['case_record'],'','## Configuration matrix','',
      '| Configuration | Prediction/SHAP | DML | Self-check | Status |','|---|---:|---:|---:|---|']
    for cfg in lock['configurations']:
        row=next((r for r in result if r['configuration']==cfg['configuration']),{})
        lines.append('| '+cfg['configuration']+' | '+' | '.join(str(cfg['flags'][k]) for k in ['P','D','C'])+' | '+row.get('status','not_generated')+' |')
    for row in result:lines.extend(['','## '+row['configuration'],'',row['report'],''])
    lines.extend(['','## Interpretation limits','']+['- '+s for s in lock['limits']])
    (ROOT/'Eight_Condition_English_Reports.md').write_text('\n'.join(lines),encoding='utf-8')
    save(ROOT/'status.json',{'status':'completed' if len(result)==8 and all(r['status']=='completed' for r in result) else 'incomplete',
        'saved_reports':len(result),'planned_reports':8,'signature':lock['signature'],'updated_utc':now()})

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--run',action='store_true');args=parser.parse_args();lock=prepare()
    if not args.run:print('PREPARED '+lock['signature']);return
    key=os.environ.get('ZHIPU_API_KEY') or sys.stdin.readline().strip()
    if not key:raise RuntimeError('Credential missing')
    order=lock['configurations'].copy();random.Random(20261026).shuffle(order)
    save(ROOT/'execution_order.json',[r['configuration'] for r in order])
    for config in order:
        try:
            row=generate(config,lock,key);print(config['configuration']+' '+row['status'],flush=True)
        except Exception as exc:
            save(ROOT/'failures'/(config['configuration']+'.json'),{'error':str(exc),'time':now()})
            print(config['configuration']+' failed '+str(exc),flush=True)
        export(lock)
        time.sleep(2)
    key=None;print('EXPORT_COMPLETE',flush=True)

if __name__=='__main__':main()
