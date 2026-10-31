"""Verify actual outgoing inputs and export unedited priority sections; no scoring."""
from pathlib import Path
import hashlib,json,re

root=Path('D:/pisa2022/outputs_grade_agent_factorial8_matched_pilot_20261026')
lock=json.loads((root/'protocol_lock.json').read_text(encoding='utf-8'))
labels={'P0_D0_C0':'基础配置（无三项）','P0_D0_C1':'仅自查','P0_D1_C0':'仅DML','P0_D1_C1':'DML＋自查（无预测/SHAP）',
        'P1_D0_C0':'仅预测/SHAP','P1_D0_C1':'预测/SHAP＋自查（无DML）','P1_D1_C0':'预测/SHAP＋DML（无自查）','P1_D1_C1':'完整配置'}
records=[]
for cfg in lock['configurations']:
    row=json.loads((root/'responses'/(cfg['configuration']+'.json')).read_text(encoding='utf-8'))
    assert row['signature']==lock['signature'] and row['status']=='completed'
    assert row['model_returned']=='glm-4.5-flash' and row['finish_reason']=='stop'
    req=row['request_body'];assert req['messages']==[{'role':'system','content':cfg['system_prompt']},{'role':'user','content':lock['case_record']}]
    assert req['temperature']==.4 and req['max_tokens']==2200 and req['thinking']=={'type':'disabled'}
    assert req['stream'] is False
    row['label_zh']=labels[cfg['configuration']]
    # Exact segment extraction, not a generated paraphrase or a rating.
    report=row['report']
    m=re.search(r'(?im)^\s*(?:\*\*)?PRIORITY ISSUES(?:\*\*)?\s*:?[ \t]*\n',report)
    n=re.search(r'(?im)^\s*(?:\*\*)?INFORMATION STILL NEEDED(?:\*\*)?\s*:?[ \t]*\n',report)
    row['priority_excerpt']=report[m.end():n.start()].strip() if m and n and n.start()>m.end() else '[Heading not located automatically; inspect complete report.]'
    records.append(row)
assert len(records)==8
for name,h in lock['input_hashes'].items():assert hashlib.sha256(Path(name).read_bytes()).hexdigest()==h
user_hashes={hashlib.sha256(r['request_body']['messages'][1]['content'].encode()).hexdigest() for r in records}
assert len(user_hashes)==1
lines=['# 八组信息匹配试跑：原始英文判断对照','',
       '模型：GLM-4.5-Flash。每组一次，单个此前已讨论的合成案例。所有组得到相同的初始描述及六类补充记录；均直接生成报告，不进行自由追问。',
       'P=预测与SHAP信息整体；D=DML统计结果；C=同一次调用内的自查指令，不是单独调用的审阅模型。',
       '下面仅摘录各组实际报告中的 PRIORITY ISSUES 段，不是教师评分，不按输出好坏重试或选择。','',
       '| 配置 | 预测/SHAP | DML | 自查 | 实际英文判断原文 |','|---|---:|---:|---:|---|']
for r in records:
    excerpt=r['priority_excerpt'].replace('|','\\|').replace('\n','<br>')
    lines.append('| '+r['label_zh']+' | '+' | '.join(str(r['flags'][k]) for k in ['P','D','C'])+' | '+excerpt+' |')
lines.extend(['','## 如何配对阅读','',
 '- DML：比较“仅预测/SHAP”和“预测/SHAP＋DML”；或比较“预测/SHAP＋自查”和“完整配置”。',
 '- 预测/SHAP：比较“仅DML”和“预测/SHAP＋DML”；或比较“DML＋自查”和“完整配置”。',
 '- 自查：比较“仅DML”和“DML＋自查”；或比较“预测/SHAP＋DML”和“完整配置”。',
 '- 也应阅读其他所有只差一个开关的配对。单案例单次输出不能估计总体优势、稳定性或交互作用的统计显著性。',
 '- 这是对信息和自查指令的严格开关控制；不是独立审阅调用的消融，也不是自由多轮流程的效果验证。',''])
(root/'八组对照_实际英文判断.md').write_text('\n'.join(lines),encoding='utf-8')
audit={'reports':8,'calls':8,'actual_models':['glm-4.5-flash'],'all_finish_stop':True,
       'actual_requests_match_locked_prompts':True,'identical_case_record_hash':next(iter(user_hashes)),
       'generation_parameters_identical':True,'all_optional_blocks_match_flags':True,
       'single_run_not_effectiveness_or_superiority_test':True,'signature':lock['signature'],
       'usage':{k:sum(r['usage'].get(k,0) for r in records) for k in ['prompt_tokens','completion_tokens','total_tokens']},
       'source_reports_sha256':{r['configuration']:hashlib.sha256((root/'responses'/(r['configuration']+'.json')).read_bytes()).hexdigest() for r in records}}
(root/'actual_request_audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in audit.items() if k!='source_reports_sha256'},ensure_ascii=False,indent=2))
