"""Read-only audit and readable export; no model calls, no raw output changes."""
from pathlib import Path
import hashlib, json

ROOT=Path('D:/pisa2022/outputs_grade_agent_english_illustration_20261026')
design=json.loads((ROOT/'protocol_lock.json').read_text(encoding='utf-8'))
rows=[json.loads((ROOT/'sessions'/s/'session.json').read_text(encoding='utf-8')) for s in design['systems']]
source=Path(design['source_prompt_path'])
assert hashlib.sha256(source.read_bytes()).hexdigest()==design['source_sha256']
assert all(r['signature']==design['signature'] for r in rows)
source_hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in ROOT.glob('sessions/*/*.json')}
readable=[];recovered=[]
for r in rows:
    report=r['final_report'];note='Strictly parsed report.'
    if report is None:
        raw=r['turns'][-1]['response']['content']
        assert r['error']=='invalid_JSON'
        parsed=json.loads(raw,strict=False)
        assert parsed['phase']=='report' and isinstance(parsed['report'],str)
        report=parsed['report'];recovered.append(r['system'])
        note='Strict JSON validation failed because the report string contains literal line breaks. Extracted with json.loads(strict=False); report wording unchanged. Original failure retained.'
    readable.append({'system':r['system'],'label':r['label'],'report':report,'note':note})
quotes={
 'single_turn_llm':'If after, it may be a response to the problem rather than a cause; if before, check whether the support format is actually building independence.',
 'evidence_only_llm':'support began after the first decline; the second decline followed only two weeks of support, too short to judge effectiveness.',
 'grade_agent_no_dml':'This is a documented, case-supported timing signal, not proof the support caused the decline.',
 'grade_agent_no_critic':'The first decline predates support, so support did not cause it; the second decline after two weeks is an isolated, uncontrolled result, not evidence that support failed.',
 'full_grade_agent':'Extra help began after the first decline, so it cannot explain that decline; the second decline followed support without a controlled comparison, so support effectiveness is unverified.'}
for r in readable:assert quotes[r['system']] in r['report']
calls=[json.loads(p.read_text(encoding='utf-8')) for p in ROOT.glob('sessions/*/call_*.json')]
assert len(calls)==25 and all(r['finish_reason']=='stop' for r in calls)
assert {r['model_returned'] for r in calls}=={'deepseek-flash'}
assert all(set(r['revealed_domains'])=={'support_timing','independent_work','confidence','home_resources','classroom'} for r in rows[1:])
notes={
 'single_turn_llm':'Recognized prompt dependence, proposed checking support chronology, and suggested fading prompts without an external evidence map.',
 'evidence_only_llm':'Identified prompt dependence and confidence concerns. The categorical claim that two weeks is too short is stronger than the case alone establishes.',
 'grade_agent_no_dml':'Made chronology the primary signal and proposed tracking independent starts. Chronology clarifies interpretation but is not itself a demonstrated cause of difficulty.',
 'grade_agent_no_critic':'Separated pre-support decline from the uncontrolled post-support observation and proposed a diagnostic task and prompt fading.',
 'full_grade_agent':'Integrated chronology and independent work, while preserving uncertainty. No distinctive DML-related advantage is established by this single response.'}
summary=['# Actual English responses: one illustrative case, five configurations','',
 'All quotations below are verbatim excerpts from actual DeepSeek Flash outputs. They are not the earlier hypothetical examples.',
 'One run per configuration. This new case is separate from the original 600-report study and used Flash rather than the original Pro model.',
 'The baseline received only the initial case. Four interactive configurations each asked five follow-up questions and received the same five domain records, in different orders.',
 'The interactive protocol is an adaptation of the original prompts. This is an exploratory workflow demonstration, not an information-matched ablation or a test of real-student diagnosis.','',
 '## Initial case','',design['case_opening'],'',
 '## Actual response comparison','',
 '| Configuration | Follow-up questions | Verbatim report excerpt | Descriptive reading (not an expert score) |',
 '|---|---:|---|---|']
for row,r in zip(rows,readable):
    summary.append('| '+r['label']+' | '+str(row['question_count'])+' | '+quotes[r['system']]+' | '+notes[r['system']]+' |')
summary.extend(['','## Findings and limitations','',
 '- Every configuration treated support chronology cautiously; the general LLM also raised the possibility that help followed pre-existing difficulty.',
 '- The four interactive runs obtained the same set of additional domain facts. Their proposed supports overlapped: independent first steps, gradual prompt fading, and monitoring.',
 '- No configuration queried the other_context domain, leaving test comparability, attendance, language, health and safety records unrequested.',
 '- Several classroom-domain questions actually concerned prompt timing or classroom participation. The fixed domain record did not answer all subquestions. The protocol tests domain-record retrieval, not unconstrained human conversation.',
 '- The complete configuration produced readable report content but failed strict JSON validation. Its original failed session remains unchanged; the displayed report was extracted deterministically with strict=False, without a new model call.',
 '- Four sessions passed the strict report schema; one additional report is readable after format-tolerant extraction. All 25 saved responses ended with finish_reason=stop.',
 '- This single-run example does not establish a DML contribution, full-system superiority, repeated-run consistency, or educational effectiveness.',''])
(ROOT/'English_Case_Comparison_Table.md').write_text('\n'.join(summary),encoding='utf-8')
full=summary[:]
full.extend(['','## Fixed records prepared before generation',''])
for domain,fact in design['fixed_followup_records'].items():full.extend(['### '+domain,'',fact,''])
for row,r in zip(rows,readable):
    full.extend(['','## Complete transcript: '+r['label'],'',r['note'],''])
    for t in row['turns']:
        p=t.get('parsed',{})
        if p.get('phase')=='question':
            full.extend(['**Question ('+p['domain']+'):** '+p['question'],'','**Fixed response:** '+t.get('interviewer_reply','[No reply]'),''])
    if row['question_count']==0:full.extend(['No follow-up questions.',''])
    full.extend(['### Final report (verbatim)','',r['report'],''])
(ROOT/'English_Case_Comparison_Readable.md').write_text('\n'.join(full),encoding='utf-8')
audit={'planned_sessions':5,'saved_calls':25,'strictly_valid_reports':4,'format_tolerant_recovered_reports':recovered,
    'model_returned':'deepseek-flash','all_finish_reasons_stop':True,
    'all_four_interactive_runs_received_same_domain_set':True,
    'raw_files_unchanged':True,'raw_source_sha256':source_hashes,
    'usage':{k:sum(r.get('usage',{}).get(k,0) for r in calls) for k in ['prompt_tokens','completion_tokens','total_tokens']},
    'no_additional_model_calls':True,'no_expert_ratings_or_success_scores':True,'signature':design['signature']}
for name,sha in source_hashes.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha
(ROOT/'readable_export_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in audit.items() if k!='raw_source_sha256'},ensure_ascii=False,indent=2))
