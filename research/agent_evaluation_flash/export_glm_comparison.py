"""Audit raw GLM sessions and export exact excerpts, without calls or ratings."""
from pathlib import Path
import json,hashlib

root=Path('D:/pisa2022/outputs_grade_agent_glm_illustration_20261026')
rows=json.loads((root/'raw_sessions.json').read_text(encoding='utf-8'))
lock=json.loads((root/'protocol_lock.json').read_text(encoding='utf-8'))
assert len(rows)==5 and all(r['status']=='completed' for r in rows)
assert all(r['signature']==lock['signature'] for r in rows)
quotes={
 'single_turn_llm':'The extra help, while well-intentioned, may not be addressing the core issue of independent application.',
 'evidence_only_llm':'DISCLIM: Strong positive conditional-effect signal (13.74) suggests classroom climate may be contributing to the issue.',
 'grade_agent_no_dml':'No causal claims can be made about the relationship between extra help and performance.',
 'grade_agent_no_critic':'Support timing - extra help began after initial decline but did not prevent further decline.',
 'full_grade_agent':'Support timing: Extra help began after initial decline but before the second lower score, suggesting the current support may not be addressing the core difficulty.'}
notes={
 'single_turn_llm':'Recognized independent-work difficulty and requested chronology/home information. Its support-format explanation remains a hypothesis.',
 'evidence_only_llm':'Used the population classroom-climate estimate to suggest a case problem despite the initial statement that classroom order was stable. It also assigned a home-study action to DISCLIM.',
 'grade_agent_no_dml':'Kept causal interpretation cautious and identified independent-work difficulty. The connection between its family action and support-timing target is weak.',
 'grade_agent_no_critic':'Identified independent-work difficulty but described support as not preventing further decline, without a controlled comparison. Its proposed 30-minute home slot exceeds the reported available 20 minutes.',
 'full_grade_agent':'Identified independent-work difficulty and proposed prompt fading. It still speculated about support not addressing the core difficulty; this requires checking and is not an established mechanism.'}
lines=['# GLM-4.5-Flash: actual five-configuration comparison','',
 'One newly constructed English case, one run per configuration. Not part of the original 600-report experiment.',
 'Actual outputs, not illustrative invented answers. Descriptive readings below are analyst observations, not teacher ratings or validated scores.',
 'The baseline receives only the opening; interactive configurations can retrieve fixed follow-up records. This is not an information-matched ablation.','',
 '## Initial case','',lock['case_opening'],'',
 '## Actual report excerpts','',
 '| Configuration | Follow-up questions | Verbatim excerpt | Descriptive reading |','|---|---:|---|---|']
for r in rows:
    assert quotes[r['system']] in r['final_report']
    lines.append('| '+r['label']+' | '+str(r['question_count'])+' | '+quotes[r['system']]+' | '+notes[r['system']]+' |')
lines.extend(['','## What this example shows','',
 '- The evidence-only configuration illustrates a risk of applying population results without a case-supported connection.',
 '- Removing or retaining DML/critic instructions did not produce a simple monotonic improvement across the responses.',
 '- The full system also produced an interpretation that needs checking; its final disclaimer does not independently validate earlier statements.',
 '- Interactive runs did not all request the same domains. No run queried other_context; classroom was queried only by the no-DML configuration.',
 '- Domain records do not answer every subquestion. This is a controlled domain-record interview, not a real teacher/student conversation.',
 '- All five final reports passed the strict JSON schema (the baseline is plain text). All 21 experimental responses returned glm-4.5-flash with finish_reason=stop.',
 '- Earlier HTTP429 failures were retained. Only missing transport-failed turns were resumed; completed reports were reused, not regenerated or selected by quality.',
 '- A separate successful full-prompt transport probe is preserved under diagnostics/ and excluded from this comparison.',
 '- These single-case observations do not establish component superiority, diagnostic validity, or real educational benefit.',''])
(root/'GLM_English_Comparison_Table.md').write_text('\n'.join(lines),encoding='utf-8')
calls=[json.loads(p.read_text(encoding='utf-8')) for p in root.glob('sessions/*/call_*.json')]
assert len(calls)==21 and {c['model_returned'] for c in calls}=={'glm-4.5-flash'}
assert all(c['finish_reason']=='stop' for c in calls)
audit={'sessions':5,'reports':5,'experimental_calls':21,'returned_model':'glm-4.5-flash',
       'quotes_verified_verbatim':True,'original_reports_reused':True,'new_case_not_original600':True,
       'prior_deepseek_results_unchanged':True,'usage':{k:sum(c['usage'].get(k,0) for c in calls) for k in ['prompt_tokens','completion_tokens','total_tokens']},
       'input_signature':lock['signature'],
       'raw_hashes':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in root.glob('sessions/*/*.json')}}
(root/'comparison_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in audit.items() if k!='raw_hashes'},ensure_ascii=False,indent=2))
