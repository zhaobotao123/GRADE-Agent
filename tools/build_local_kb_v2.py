"""Build an additive, offline evidence library. Never import or modify app runtime."""
from pathlib import Path
import csv,json,hashlib,math,shutil,zipfile

PROJECT=Path('C:/Users/84130/Documents/Codex/2026-07-03/zhe/gradeagent')
RESEARCH=Path('C:/Users/84130/Documents/Codex/2026-08-09/zh/robustness_checks')
FOLLOW=RESEARCH/'followup_20261028'
OUT=PROJECT/'knowledge/pisa-jpn-2022-v2'
DELIVERY=Path(__file__).resolve().parents[1]/'outputs'
def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
runtime=[p for folder in ['functions','src'] for p in (PROJECT/folder).rglob('*') if p.is_file()]
before={str(p):digest(p) for p in runtime}
assert not OUT.exists(), 'Version already exists; do not overwrite.'
sources={
 'shap':Path('D:/pisa2022/outputs_final_shap_42_features/shap_importance_pooled.csv'),
 'dml':Path('D:/pisa2022/outputs_grade_agent_formal/dml_results_pooled.csv'),
 'pv_stability':Path('D:/pisa2022/outputs_grade_agent_formal/dml_stability_check.csv'),
 'legacy_rules':Path('D:/pisa2022/outputs_grade_agent_formal/agent_rule_mapping_formal.csv'),
 'extra_trees':RESEARCH/'dml_sensitivity_results.csv',
 'random_forest':FOLLOW/'random_forest_pooled.csv',
 'brr':FOLLOW/'BRR_pooled_available_factors.csv',
 'brr_audit':FOLLOW/'independent_audit_status.json',
 'split_shap':RESEARCH/'shap_rank_stability.csv',
 'split_metrics':RESEARCH/'predictive_stability_summary.csv',
 'model_metrics':Path('D:/pisa2022/outputs_five_models_tuned_42_features/tuned_five_model_metrics_summary.csv'),
}
source_hashes={k:digest(p) for k,p in sources.items()}
def read(key):
 with sources[key].open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f))
def cast(v):
 if v in ['True','False']:return v=='True'
 try:return float(v) if any(c in v for c in '.eE') else int(v)
 except (ValueError,TypeError):return v
def convert(r):return {k:cast(v) for k,v in r.items()}
shap=read('shap');dml={r['treatment']:r for r in read('dml')}
split={r['feature']:r for r in read('split_shap')}
alternatives={}
for k in ['extra_trees','random_forest','brr']:
 rows=read(k)
 if k=='extra_trees':rows=[r for r in rows if r.get('model')=='ExtraTrees']
 assert len(rows)==5 and len({r['treatment'] for r in rows})==5, k
 alternatives[k]={r['treatment']:r for r in rows}
assert float(alternatives['extra_trees']['TEACHSUP']['p_value_pooled'])>.05

audit=json.loads(sources['brr_audit'].read_text(encoding='utf-8'))
assert audit['entire_plan_complete'] and audit['all_completed_checkpoints_passed']
# These descriptions are editorial drafts, not measurements or validated intervention rules.
definitions={
 'MATHEFF':('数学自我效能感','mathematics self-efficacy','beliefs','学生对数学任务能力的自我判断','遇到不会的题时，学生通常如何判断自己能否完成？','可与教师一起选择适当难度的任务，观察尝试过程和反馈。'),
 'DISCLIM':('课堂纪律氛围','disciplinary climate','classroom','学生报告的课堂秩序与学习环境','学生描述的课堂秩序或干扰具体是什么？','可先记录具体课堂干扰，再与教师商量适合该课堂的调整。'),
 'TEACHSUP':('教师支持','teacher support','support','学生报告获得的教师支持','额外帮助是在困难出现之前还是之后开始的？','可了解当前支持的内容和时机，与教师共同讨论需要调整的地方。'),
 'BELONG':('学校归属感','school belonging','school_experience','学生对学校成员身份和被接纳感的报告','学生最近在学校的人际体验和归属感有何变化？','可先听取学生具体经历，再与可信赖的学校人员讨论支持。'),
 'ICTSCH':('学校ICT资源','school ICT resources','resources','学校相关的信息通信技术资源','学生实际能使用哪些资源，如何使用，有什么困难？','可核实实际可用性和用途；负向估计不能作为减少资源的理由。'),
 'ICTQUAL':('数字资源质量','digital-resource quality','resources','学生报告的数字资源质量','数字资源是否满足当前任务，需要改进的具体方面是什么？','可先核实资源使用障碍，再考虑适合学习任务的支持。'),
 'ESCS':('经济社会文化地位','economic social and cultural status','background','家庭经济社会文化背景指数','当前学习机会或资源是否存在具体障碍？','可关注能够提供的支持机会，避免按背景给学生贴标签。'),
 'HOMEPOS':('家庭物质资源','home possessions','resources','家庭拥有的相关资源指数','家庭中哪些实际资源有助于或限制当前任务？','可根据已确认的资源障碍寻找可行支持，避免推断家庭能力或意愿。'),
 'ICTENQ':('ICT探究与使用','ICT inquiry/use','digital_learning','与ICT探究使用相关的问卷指标','学生在什么任务中怎样使用数字工具？','可围绕具体任务讨论工具使用方式，不按统计方向增加或减少使用。'),
 'BULLIED':('遭受欺凌','being bullied','safety','学生报告的欺凌经历','如果学生愿意说明，具体发生了什么，目前是否安全？','若已报告欺凌或不安全，应优先联系可信赖成人及学校学生保护人员；不能因统计不显著而忽视。'),
 'ANXMAT':('数学焦虑','mathematics anxiety','beliefs','数学相关焦虑的学生自我报告','哪些数学情境让学生感到紧张，何时开始？','可先了解具体情境和可获得的支持，不据此诊断心理障碍。'),
 'MATHEF21':('21世纪数学自我效能感','21st-century mathematics efficacy','beliefs','与21世纪数学任务相关的自我效能问卷构念','哪些类型的数学任务让学生缺乏把握？','可与教师核实具体任务表现和支持需求，避免从该估计推断个体原因。'),
}
boundaries=['Japan PISA 2022 observational population-level evidence; not an individual diagnosis or intervention effect.',
 'Mean absolute SHAP measures predictive contribution, not direction, adjusted association, or causal importance.',
 'Main DML inference uses school-clustered standard errors and fixed student-level cross-fitting folds.',
 'BRR is available for five factors only and remains conditional on frozen student-level folds.',
 'Unknown, unreported, and explicitly absent information must remain distinct; do not infer individual factor values from an index.',
 'Educational questions and support examples are AI-assisted editorial drafts awaiting author review, not empirical findings or validated interventions.']
records=[]
for s in shap:
 code=s['feature'];main=dml.get(code);meta=definitions.get(code)
 rec={'id':'PISA2022-JPN-'+code,'factor_code':code,
 'name_zh':meta[0] if meta else None,'name_en':meta[1] if meta else None,
 'category':meta[2] if meta else None,'educational_definition_draft':meta[3] if meta else None,
 'definition_status':'editorial_draft_author_review_required' if meta else 'not_curated',
 'prediction':{'source_id':'shap','row_key':code,**convert(s)},
 'split_shap_rank_stability':{'source_id':'split_shap',**convert(split[code])} if code in split else None,
 'dml_main':{'source_id':'dml','row_key':code,**convert(main)} if main else None,
 'sensitivity':[], 'evidence_class':'prediction_only',
 'interpretation_boundaries':list(boundaries),
 'follow_up_question_draft':meta[4] if meta else None,
 'support_example_draft':meta[5] if meta else None,
 'educational_content_provenance':'AI-assisted editorial drafting; no expert validation asserted' if meta else None}
 if main:
  value=float(main['coef_pooled']);se=float(main['std_error_pooled'])
  rec['dml_main']['derived_ci95']={'low':value-1.96*se,'high':value+1.96*se,'provenance':'derived, not present in original CSV','formula':'coef_pooled +/- 1.96 * std_error_pooled'}
  rec['dml_main']['p_value_note']='Numerical zero in source; report p < .001, not exact probability zero.' if float(main['p_value_pooled'])==0 else None
  if main['direction_consistent']=='False':cls='directionally_unstable_across_PVs'
  elif float(main['p_value_pooled'])>=.05:cls='weak_or_context_sensitive'
  elif value>0:cls='positive_association_PV_direction_consistent'
  else:cls='negative_association_requires_contextual_review'
  rec['evidence_class']=cls
 for key,table in alternatives.items():
  if code in table:rec['sensitivity'].append({'source_id':key,'row_key':code,'inference_scope':'full-refit Fay-BRR conditional on frozen folds' if key=='brr' else 'alternative nuisance learner; school-clustered inference',**convert(table[code])})
 if code=='TEACHSUP':rec['interpretation_boundaries'].append('ExtraTrees pooled interval includes zero (p approximately .0767); retain learner sensitivity despite significant RF and BRR results. Negative estimate does not show that teacher support harms achievement.')
 if code in ['BELONG','ICTSCH']:rec['interpretation_boundaries'].append('Negative association is not evidence to reduce belonging or resource provision; possible contextual explanations are hypotheses, not established mechanisms.')
 if code=='BULLIED':rec['interpretation_boundaries'].append('Safeguarding takes precedence over pooled significance; weak academic association never means bullying is safe.')
 records.append(rec)
kb={'schema_version':'1.0','knowledge_version':'pisa-jpn-2022-v2','created_date':'2026-10-30','status':'local_draft_not_connected_to_agent',
 'study':{'dataset':'PISA 2022','country':'Japan','analytic_students':5760,'schools':182,'plausible_values':10},
 'policy':{'causal_identification_claim':False,'rag_implemented':False,'runtime_integration':False,'editorial_review_status':'pending author review','missing_data_policy':'null means unavailable or not curated, never zero'},
 'global_boundaries':boundaries,'prediction_model_metrics':{'source_id':'model_metrics','rows':[convert(r) for r in read('model_metrics')]},
 'repeated_split_prediction_metrics':{'source_id':'split_metrics','scope':'ten additional LightGBM student-level splits; partition sensitivity, not population confidence intervals','rows':[convert(r) for r in read('split_metrics')]},
 'records':records}
assert len(records)==42 and sum(r['dml_main'] is not None for r in records)==12
assert all(sum(x['source_id']==k for r in records for x in r['sensitivity'])==5 for k in alternatives)
assert len({r['factor_code'] for r in records})==42
assert set(dml)<=set(r['factor_code'] for r in records)
assert all(math.isfinite(r['prediction']['mean_abs_shap']) for r in records)
OUT.mkdir(parents=True);(OUT/'sources').mkdir()
manifest=[]
for key,p in sources.items():
 target=OUT/'sources'/f'{key}{p.suffix}';shutil.copyfile(p,target)
 manifest.append({'source_id':key,'original_path':str(p),'snapshot_path':str(target.relative_to(OUT)).replace('\\','/'),'sha256':source_hashes[key]})
(OUT/'sources_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
(OUT/'knowledge.json').write_text(json.dumps(kb,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
lines=['# GRADE-Agent 本地研究证据知识库','', '版本 pisa-jpn-2022-v2｜本地草稿｜未接入智能体｜教育解释待作者审核','',
 '统计数值来自 sources_manifest.json 对应的CSV快照；问题和支持示例为AI辅助编辑草稿，不是原始统计结果。未整理的名称或建议保留为空。','',
 '## 使用边界','']+['- '+x for x in boundaries]
for r in records:
 lines+=['',f"## {r['factor_code']} {r['name_zh'] or '(名称待整理)'}",'',f"记录ID：{r['id']}",f"证据类别：{r['evidence_class']}",f"SHAP mean_abs_shap={r['prediction']['mean_abs_shap']}; rank={r['prediction']['rank']}（仅预测贡献，无正负方向）。"]
 if r['dml_main']:
  m=r['dml_main'];ci=m['derived_ci95'];lines += [f"主DML：coef={m['coef_pooled']}; SE={m['std_error_pooled']}; p={m['p_value_pooled']}; 推导95%CI=[{ci['low']}, {ci['high']}]。来源：sources/dml.csv。"]
 else:lines+=['未进行对应主DML估计；不可补造系数或调整关联。']
 for a in r['sensitivity']:lines += [f"敏感性 {a['source_id']}：coef={a.get('coef',a.get('coef_pooled'))}; p={a.get('p_value',a.get('p_value_pooled'))}; 95%CI=[{a['ci_low']}, {a['ci_high']}]。"]
 lines += ['解释边界：'+' '.join(r['interpretation_boundaries'])]
 if r['follow_up_question_draft']:lines += ['编辑草稿，待审核：'+r['educational_definition_draft'],'追问草稿：'+r['follow_up_question_draft'],'支持示例草稿：'+r['support_example_draft']]
(OUT/'knowledge.md').write_text('\n\n'.join(lines),encoding='utf-8')
with (OUT/'factor_index.csv').open('w',encoding='utf-8-sig',newline='') as f:
 fields=['id','factor_code','name_zh','category','evidence_class','shap_rank','has_dml','sensitivity_count','editorial_status'];writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
 for r in records:writer.writerow(dict(zip(fields,[r['id'],r['factor_code'],r['name_zh'],r['category'],r['evidence_class'],r['prediction']['rank'],r['dml_main'] is not None,len(r['sensitivity']),r['definition_status']])))
readme='''# GRADE-Agent 本地知识库 v1

本目录是新增的离线证据材料，未修改 functions、src、提示词或配置，未部署、未上传外部平台、未建立RAG。它不能用于重新描述历史实验的实现。

- knowledge.json：完整嵌套记录，42个SHAP变量，12个DML因素，5因素的ExtraTrees、RF和BRR结果。
- knowledge.md：同一内容的可读文本，可供后续审核或平台上传。
- factor_index.csv：因素索引，不是完整知识记录；完整统计信息见JSON。
- sources/ 与 sources_manifest.json：原始统计文件快照和SHA256来源。
- validation.json：构建及数值对应校验。

统计来源字段与新编写的教育解释、追问和支持示例分开保存。后者明确标记为待作者审核的AI辅助编辑草稿。30个仅有SHAP变量的定义和建议暂未整理，保持null。置信区间若由系数和标准误计算，明确标记derived。原始规则表仅作为历史材料保存，不直接采用其中的“风险诊断”模板。

这是一版未接入的本地知识库。对话调用、检索、来源回传和界面上传均未在本次实现。
'''
(OUT/'README.md').write_text(readme,encoding='utf-8')
# Round-trip and source-to-record assertions, without running any model or research script.
loaded=json.loads((OUT/'knowledge.json').read_text(encoding='utf-8'))
for r in loaded['records']:
 s=next(x for x in shap if x['feature']==r['factor_code'])
 assert r['prediction']['mean_abs_shap']==float(s['mean_abs_shap'])
 if r['dml_main']:assert r['dml_main']['coef_pooled']==float(dml[r['factor_code']]['coef_pooled'])
 for a in r['sensitivity']:
  raw=alternatives[a['source_id']][r['factor_code']]
  assert float(a.get('coef',a.get('coef_pooled')))==float(raw.get('coef',raw.get('coef_pooled')))
  assert float(a['ci_low'])<=float(a['ci_high'])
assert all(digest(p)==source_hashes[k] for k,p in sources.items())
assert all(digest(Path(p))==h for p,h in before.items())
validation={'passed':True,'records':42,'dml_records':12,'prediction_only':30,'sensitivity_records':15,'source_files':len(manifest),'original_source_hashes_unchanged':True,'runtime_files_checked_unchanged':len(before),'runtime_connected':False,'human_editorial_review_complete':False}
(OUT/'validation.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
DELIVERY.mkdir(exist_ok=True)
with zipfile.ZipFile(DELIVERY/'GRADE-Agent_Local_Knowledge_v2.zip','w',zipfile.ZIP_DEFLATED) as z:
 for p in OUT.rglob('*'):
  if p.is_file():z.write(p,Path(OUT.name)/p.relative_to(OUT))
shutil.copyfile(OUT/'knowledge.md',DELIVERY/'GRADE-Agent_Knowledge_v2.md')
print(json.dumps({'directory':str(OUT),**validation},ensure_ascii=False,indent=2))
