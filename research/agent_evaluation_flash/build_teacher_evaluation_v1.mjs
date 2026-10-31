import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

const base='C:/Users/84130/Documents/Codex/2026-08-09/zh';
const source='D:/pisa2022/outputs_grade_agent_deepseek41flash300_20261026';
const out=path.join(base,'outputs/teacher_evaluation_20261026_v1');
const internal=path.join(out,'研究者留存_不要发给老师');
const preview=path.join(base,'work/teacher_evaluation_v1_previews');
try{await fs.access(path.join(internal,'artifact_manifest.json'));throw Error('Materials already exist. Refusing to overwrite possible teacher annotations.');}catch(e){if(e.code!=='ENOENT')throw e;}
const rawText=await fs.readFile(path.join(source,'raw_reports.json'),'utf8');
const lockText=await fs.readFile(path.join(source,'protocol_lock.json'),'utf8');
const raw=JSON.parse(rawText),cases=JSON.parse(lockText).plan.cases;
const sha=x=>crypto.createHash('sha256').update(x).digest('hex');
const systems=['single_turn_llm','evidence_only_llm','grade_agent_no_dml','grade_agent_no_critic','full_grade_agent'];
if(raw.length!==300||raw.some(r=>r.status!=='completed'||r.finish_reason!=='stop'))throw Error('Source experiment incomplete');
if(new Set(raw.map(r=>[r.system,r.caseId,r.repeat].join('|'))).size!==300)throw Error('Duplicate source keys');
const seed='teacher-evaluation-v1-20261026';
const key=r=>[r.system,r.caseId,r.repeat].join('|');
const rank=(namespace,value)=>sha(seed+'|'+namespace+'|'+value);
const selected=[];
for(const c of cases)for(const system of systems){
 const group=raw.filter(r=>r.caseId===c.caseId&&r.system===system);
 if(group.length!==5)throw Error('Unexpected group size');
 group.sort((a,b)=>rank('sample',key(a)).localeCompare(rank('sample',key(b))));
 selected.push(group[0]);
}
selected.sort((a,b)=>rank('anonymous-order',key(a)).localeCompare(rank('anonymous-order',key(b))));
const items=selected.map((r,i)=>({...r,blind_id:'B'+String(i+1).padStart(3,'0'),case_short:r.caseId.split('_')[0]}));
const translations={
 H01:['过去六周，学生的数学课堂参与和成绩下降。','学生回避在课堂上大声回答，但能够私下完成书面任务。','两名同伴在数学讨论时反复嘲笑该学生的口音。','学生说，如果这两名同伴先到教室，自己会害怕进入教室。','目前尚未将此事转介给学校的学生安全保护负责人。'],
 H02:['家长报告成绩明显下降，但成绩册显示变化不大。','学生表示有信心，辅导教师则报告其经常回避任务。','任课教师认为学生注意力持续，家长则报告学生对学校相关事情感到困扰。','私人辅导的时间和类型尚未记录。'],
 H03:['一次数学成绩明显低于此前持续两年的稳定表现。','学生仍有信心，并继续尝试难题。','未报告课堂环境变化。','学习支持安排没有变化。','学生因急性偏头痛提前离开本次测评。'],
 H04:['数学表现持续低于预期，尤其在文字应用题上。','学生能坚持尝试；说明被澄清后，可以解答等价任务。','课堂秩序良好。','学生最近从一所使用另一种教学语言的学校转来。','尚未评估任务对学术语言能力的要求。'],
 H05:['学生的低表现出现在近期增加辅导和教师跟进之前。','学生对不同数学主题的信心不一。','课堂整体比较专注。','学习困难显现后，辅导和数字练习才被加强。','学生在提示下能成功，但很少独立开始解题。'],
 H06:['三次测评的成绩逐步下降。','学生认为数学能力无法改善，第一次出错后便停止尝试。','未报告持续的课堂干扰。','教师支持保持稳定。','学习材料充足。'],
 H07:['成绩下降主要出现在与同一班级群体一起上的课中。','学生仍愿意尝试数学任务。','频繁的课堂中断和与任务无关的噪声，使学生无法完成例题学习。','教师定期提供反馈。','家庭学习资源充足。'],
 H08:['一位监护人表示，数学学习最近成了一个担忧。','信心情况未知。','课堂情况未知。','支持情况未知。','未提供成绩、日期、作业样本或学生本人的说法。'],
 H09:['此前成绩稳定，但本学期表现下降。','学生自报信心中等。','未报告持续的课堂干扰。','支持和资源没有变化。','尚未核查出勤、睡眠、健康、课表变化和课程衔接情况。'],
 H10:['四次测评的表现持续下降。','学生报告自己出错后很快放弃。','学生还报告课堂经常被打断。','学习支持保持稳定。','数字资源可用，且学生有使用。'],
 H11:['学习表现较低，但保持稳定。','学习有指导的例题时信心较高，独立任务时信心较低。','课堂秩序良好。','强化支持开始于第一次低分测评之后。','学生会等待提示后再选择解题策略。'],
 H12:['在课堂作业和测评结果一直稳定之后，一次数学小测出现低分。','学生仍积极参与并有信心。','课堂环境专注。','支持安排没有变化。','火警打断了这次小测，并缩短了可用于作答的时间。']
};
const fieldNames={trajectory:'学习表现',confidence:'学习信心',classroom:'课堂情况',safety:'安全情况',support:'支持安排',recentEvent:'近期事件',language:'教学语言',followThrough:'独立完成情况',resources:'学习资源',records:'现有记录',recentChange:'尚待核查的变化'};
for(const c of cases)if(translations[c.caseId.split('_')[0]].length!==Object.keys(c.answers).length)throw Error('Translation mismatch');
const taxonomy=[
 ['safeguarding','学生安全与保护','需要优先关注同伴侵害、恐惧或其他安全保护事项。'],
 ['conflicting_sources','不同信息来源相互冲突','家长、教师、学生或记录不一致，需要先核实与协调。'],
 ['isolated_event','单次测评或特殊事件','需要先核实一次结果、测评中断或结果可比性。'],
 ['language_context','教学语言或题目语言情境','需关注语言理解及教学、测评语言要求。'],
 ['support_timing','支持安排及其时间顺序','需核实支持发生在困难之前还是之后，并审视支持安排。'],
 ['learning_confidence','学习信心与遇错坚持','需关注学习信心、能力信念及出错后的坚持。'],
 ['classroom_conditions','课堂环境与干扰','需关注中断、噪声及课堂条件。'],
 ['insufficient_information','关键信息不足','当前材料不足，需先补充成绩、时间、作品或其他来源的信息。'],
 ['health_or_context','出勤、健康及近期生活情境','需关注或核实出勤、睡眠、健康、课表或课程变化等；不表示已确诊。'],
 ['independent_problem_solving','独立解题与提示依赖','需关注能否独立起步、选策略及从例题迁移。'],
 ['mathematics_knowledge_gap','数学知识或先备技能','有材料支持时，关注具体知识、概念或先备技能。'],
 ['learning_strategy','学习或解题策略','有材料支持时，关注计划、检查、组织及策略使用。'],
 ['motivation','学习动机与参与','有材料支持时，关注兴趣、投入或参与；不自动等同于低信心。'],
 ['family_resources','家庭资源与练习条件','有材料支持时，关注材料、空间、时间与练习条件。'],
 ['math_anxiety','数学焦虑或考试担忧','有材料支持时，关注数学情境中的担忧；不作临床诊断。'],
 ['other','其他（须写明）','如上述类别不能表达，请在备注补充具体问题，待共同确认后再归类。']
];
const refs=[
 ['MRBench','Maurya et al. (2025). Unifying AI Tutor Evaluation: An Evaluation Taxonomy for Pedagogical Ability Assessment of LLM-Powered AI Tutors.','https://aclanthology.org/2025.naacl-long.57/'],
 ['BEA 2025','Kochmar et al. (2025). Findings of the BEA 2025 Shared Task on Pedagogical Ability Assessment of AI-powered Tutors.','https://aclanthology.org/2025.bea-1.77/']
];
const h=x=>String(x).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
function facts(c){const cn=translations[c.caseId.split('_')[0]];return '<dl>'+Object.entries(c.answers).map(([k,v],i)=>`<dt>${h(fieldNames[k]||k)}</dt><dd>${h(cn[i])}<small lang="en">${h(v)}</small></dd>`).join('')+'</dl>';}
const css=`body{font:16px/1.7 'Microsoft YaHei',Arial,sans-serif;color:#20252b;background:#f5f6f8;margin:0}main{max-width:1020px;margin:32px auto;padding:0 24px}header,article,section{background:white;padding:24px 30px;margin:20px 0;border:1px solid #dce1e6;border-radius:8px}h1{font-size:25px;margin:0 0 12px}h2{font-size:20px}h3{font-size:17px}small{display:block;color:#58616b;margin:4px 0 10px;font-family:Arial,sans-serif}dt{font-weight:600}dd{margin:0 0 14px}select{font:inherit;padding:8px;max-width:100%}.report{font:16px/1.7 'Times New Roman',serif;white-space:pre-wrap;overflow-wrap:anywhere;border-top:1px solid #ddd;padding-top:20px}.muted{color:#58616b}a{color:#235b8d}article[hidden]{display:none}@media print{body{background:white}header,article,section{border:0;padding:0}article[hidden]{display:block}.controls{display:none}article{break-before:page}small{color:#333}}`;
function htmlPage(title,body,script=''){return `<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${h(title)}</title><style>${css}</style></head><body><main>${body}</main>${script}</body></html>`;}

await fs.mkdir(internal,{recursive:true});await fs.mkdir(preview,{recursive:true});
const plan={version:'teacher_evaluation_v1',prepared_utc:new Date().toISOString(),seed,
 source_raw_sha256:sha(rawText),generation_protocol_sha256:sha(lockText),source_n:300,
 status:'materials_prepared_awaiting_independent_teacher_annotations',
 design:'Post-hoc supplementary evaluation designed after aggregate AI results were inspected. Not a prospective registration or independent new test set.',
 sample:'One of five reports in each case x configuration stratum, selected by lowest SHA256 of fixed seed and source key; no score-based selection. 60 reports; same sampled reports for both teachers, independently shuffled presentation order.',
 anonymity:'Configuration metadata and old scores omitted. Raw report text remains unchanged and can reveal system identity/style; partial label masking, not guaranteed full blinding.',
 sequence:['Stage A: each teacher independently annotates twelve case-only reference priority sets, without reports or author expectedConstraints.',
 'Preserve both independent files; reconcile differences without inspecting model outputs. Resolve new labels and freeze final reference/codebook before F1 extraction/comparison.',
 'Stage B: independently rate the sixty unchanged original reports; do not see the other teacher scores or configuration mapping.',
 'Preserve first independent ratings for agreement, then resolve disagreements if consensus ratings are needed.'],
 planned_metrics:{problem_identification:'Report-level multilabel priority issue precision/recall/F1 versus teacher-confirmed reference sets. Primary micro-F1; secondary sample-averaged F1 and class-wise counts. Fixed mapping; do not infer true individual causation. Report extraction must be checked against human labels; existing 1-2-label AI sets are not automatically substituted.',
 guidance:'Adapted MRBench Providing Guidance: Yes / To some extent / No; DAMR=Yes / scorable reports, by configuration. Not the original validated tutoring task.',
 actionability:'Adapted MRBench Actionability: Yes / To some extent / No; report DAMR separately, no correctness double counting.',
 boundaries:'Study-specific supplemental interpretation-boundary dimension; not a published standardized scale.',
 reliability:'Linear-weighted Cohen kappa on the two original independent ordinal ratings, separately by dimension; also raw agreement and label frequencies. Undefined kappa reported as unavailable, not 1.',
 uncertainty:'Paired case-cluster percentile bootstrap, retain within-case repeated reports; 12 constructed case clusters. Exploratory pointwise95% intervals, unadjusted; no arbitrary overall weighted ranking.'},
 score_missingness:'Blank is not zero. Unable to judge remains unscored, with reason and denominator disclosed; no replacement sampling based on scores.',
 optional_future_faithfulness:'Not run or renamed as RAGAS. Would require a separately defined evidence context and statement-level grounding protocol; not silently applied only to evidence-using groups.',
 no_model_calls:true,no_teacher_scores_fabricated:true,no_existing_data_changed:true,
 taxonomy,refs};
await fs.writeFile(path.join(internal,'evaluation_plan.json'),JSON.stringify(plan,null,2));
await fs.writeFile(path.join(internal,'anonymous_mapping_DO_NOT_SHARE.json'),JSON.stringify(items.map(r=>({blind_id:r.blind_id,caseId:r.caseId,system:r.system,repeat:r.repeat,source_report_sha256:sha(r.report)})),null,2));

function basicSheet(wb,name,cols,lastRow){const s=wb.worksheets.add(name);s.showGridLines=false;s.getRangeByIndexes(0,0,lastRow,cols).format.font={name:'Arial',size:11,color:'#20252B'};s.getRangeByIndexes(0,0,lastRow,cols).format.verticalAlignment='center';return s;}
function title(s,text){s.getRange('A2').values=[[text]];s.getRange('A2').format.font={name:'Arial',size:15,bold:true,color:'#20252B'};s.getRange('A2').format.rowHeight=28;}
function head(s,range){s.getRange(range).format={fill:'#304B67',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:34};}
function validation(s,range,values){s.getRange(range).dataValidation={rule:{type:'list',values}};}
function notesSheet(wb,stage){
 const s=basicSheet(wb,'填写说明',3,45);title(s,stage==='A'?'参考问题标注说明':'匿名报告评分说明');
 s.getRange('A1:A45').format.columnWidthPx=220;s.getRange('B1:B45').format.columnWidthPx=650;s.getRange('C1:C45').format.columnWidthPx=12;
 const rows=stage==='A'?[
 ['先后顺序','先完成本阶段并提交，再查看阶段B报告；请独立填写，不参考另一位教师或模型答案。'],
 ['看什么','打开同文件夹中的“12案例材料.html”。中文为辅助翻译，英文为原始事实；发现翻译差异请指出。'],
 ['标注对象','选择当前事实支持、需要优先核实或处理的问题，不是判断学生的真实致因；不要把所有可能性都列入。'],
 ['怎么填','在“优先问题代码”填一个或多个代码，用英文分号分隔；不限制只能选两个。在依据栏简述对应事实。'],
 ['稳定背景与未知','稳定、保护性或未知信息不自动成为问题；是否优先核实，由案例事实决定。'],
 ['无法确定','保留空白并选“待讨论”或“无法判断”，说明原因；不要勉强填一个代码。'],
 ['新增类别','代码表为本研究整理，不是通用量表。可用other并写明；须在计算F1前确认类别与映射。'],
 ['代码','名称及适用含义'],...taxonomy.map(([code,name,meaning])=>[code,name+'：'+meaning])
 ]:[
 ['独立评分','确认阶段A参考标注已提交后，再打开“60匿名报告.html”；不要与另一位教师商量分数。'],
 ['评分对象','依据同页案例事实评价英文原始报告；不因格式、长度、条目数量、统计术语或引用数量加减分。'],
 ['指导质量：是','建议正确且贴合当前案例，解释合理；先补充信息或优先安全转介也可以是充分的指导。'],
 ['指导质量：部分','有指导，但部分不正确、不贴合案例，或缺少重要内容。'],
 ['指导质量：否','没有提供指导；或所给指导整体明显错误、不相关。'],
 ['可操作性：是','用户能明白下一步该做什么，行动具体到足以执行；不强制三类主体或数字化期限。'],
 ['可操作性：部分','有行动方向，但仍较笼统或不够清楚。'],
 ['可操作性：否','无法从报告中确定可执行的下一步。'],
 ['分别判断','指导的正确性与行动的清晰度分开评分；一个建议可以可执行但不正确，不能自动连带打分。'],
 ['解释边界：是','区分事实与假设，不把群体统计关系当作这个学生的确定原因；无需固定免责声明措辞。'],
 ['解释边界：部分','有局部未经充分限定的推测或过度解释，但未形成明确、决定性的无依据因果判断。'],
 ['解释边界：否','明确作出无依据的个体因果、临床或敏感身份判断，或误把困难之后的支持说成致因。'],
 ['无法判断','选择“无法判断”并说明原因；不是“否”，也不记0分。'],
 ['主要问题代码','可选：填写报告实际上着重讨论的问题代码，供核查自动标签抽取；不是替报告填写正确答案。'],
 ['简要依据','给“部分”“否”或“无法判断”时，请指出具体问题；可摘录一处短句。'],
 ['填写状态','三项都评完且需说明的问题已写清后，再选“已完成”；评分不计算加权总分。'],
 ['文献与改编','指导质量、可操作性参考MRBench；本研究改为教师支持报告情境。解释边界是研究自定义补充维度。'],
 ['统计数字','本表不独立核验统计引用数字真伪，数字准确性需另与研究源结果核对；不要因技术表达本身加减分。'],
 ['评分标记','三项使用“是/部分/否/无法判断”。不查看任何旧AI分数或配置映射。'],
 ['代码表','主要问题代码与阶段A相同；如需新增类别，请写备注，不自行改变原有含义。']
 ];
 s.getRangeByIndexes(3,0,rows.length,2).values=rows;
 s.getRangeByIndexes(3,0,rows.length,2).format.wrapText=true;
 s.getRangeByIndexes(3,0,rows.length,2).format.verticalAlignment='top';
 s.getRangeByIndexes(3,0,rows.length,1).format.font={name:'Arial',size:11,bold:true};
 for(let i=0;i<rows.length;i++)s.getRangeByIndexes(i+3,0,1,2).format.rowHeight=rows[i][1].length>67?52:38;
 if(stage==='A')head(s,'A11:B11');
 const refStart=4+rows.length+2;
 s.getRangeByIndexes(refStart,0,1,2).values=[['文献来源','指导质量、可操作性及DAMR的依据；本表为情境改编，不是直接使用原量表。']];
 s.getRangeByIndexes(refStart,0,1,2).format.wrapText=true;s.getRangeByIndexes(refStart,0,1,2).format.rowHeight=38;
 refs.forEach((r,i)=>{s.getRangeByIndexes(refStart+1+i,0,1,2).values=[[r[0],r[2]]];s.getRangeByIndexes(refStart+1+i,0,1,2).format.rowHeight=25;});
 return s;
}
const created=[];
for(const teacher of [1,2]){
 const aDir=path.join(out,'先发_阶段A',`教师${teacher}`),bDir=path.join(out,'确认A后再发_阶段B',`教师${teacher}`);
 await fs.mkdir(aDir,{recursive:true});await fs.mkdir(bDir,{recursive:true});
 const a=Workbook.create(),s=basicSheet(a,'参考标注',5,23);title(s,`12案例参考标注（教师${teacher}）`);
 s.getRange('A4').values=[['先阅读“12案例材料.html”，再独立填写；黄色区域为填写栏。']];s.getRange('A4').format.rowHeight=26;
 s.getRange('A6:E6').values=[['案例编号','优先问题代码（可多选）','对应事实与判断依据','补充说明/其他问题（选填）','填写状态']];head(s,'A6:E6');
 s.getRange('A7:E18').values=cases.map(c=>[c.caseId.split('_')[0],null,null,null,null]);
 s.getRange('A7:E18').format.rowHeight=76;s.getRange('B7:E18').format.fill='#FFF6D8';s.getRange('A7:E18').format.wrapText=true;s.getRange('A7:E18').format.verticalAlignment='top';
 [90,230,400,300,110].forEach((w,i)=>s.getRangeByIndexes(0,i,23,1).format.columnWidthPx=w);
 validation(s,'E7:E18',['已完成','待讨论','无法判断']);s.freezePanes.freezeRows(6);s.freezePanes.freezeColumns(1);
 const ag=notesSheet(a,'A');a.recalculate();
 const aFile=path.join(aDir,`阶段A_参考标注_教师${teacher}.xlsx`);await (await SpreadsheetFile.exportXlsx(a)).save(aFile);created.push(aFile);
 for(const [sheet,range,suffix] of [[s,'A1:E10','A填写'],[ag,'A1:B29','A说明']]){
  const blob=await a.render({sheetName:sheet.name,range,scale:1,format:'png'});await fs.writeFile(path.join(preview,`教师${teacher}_${suffix}.png`),new Uint8Array(await blob.arrayBuffer()));
 }
 const aHtml=htmlPage('12案例材料',`<header><h1>12案例材料 · 教师${teacher}</h1><p>请先独立完成阶段A，不查看模型报告、另一位教师标注或研究者原先的预期标签。</p><p>下列仅含案例事实。中文为辅助翻译，英文为原始材料；如发现含义不一致，请以英文为准并注明。</p></header>`+cases.map(c=>`<article><h2>${h(c.caseId.split('_')[0])}</h2>${facts(c)}</article>`).join(''));
 await fs.writeFile(path.join(aDir,'12案例材料.html'),aHtml);

 const order=[...items].sort((x,y)=>rank('teacher-order-'+teacher,x.blind_id).localeCompare(rank('teacher-order-'+teacher,y.blind_id)));
 const b=Workbook.create(),bs=basicSheet(b,'报告评分',8,68);title(bs,`60份匿名报告评分（教师${teacher}）`);
 bs.getRange('A4').values=[['确认阶段A已提交后，再打开“60匿名报告.html”。三项分别评分，不计算总分。']];bs.getRange('A4').format.rowHeight=26;
 bs.getRange('A6:H6').values=[['报告编号','案例编号','指导质量','可操作性','解释边界（补充）','报告主要问题代码（选填）','简要依据或问题说明','填写状态']];head(bs,'A6:H6');
 bs.getRange('A7:H66').values=order.map(r=>[r.blind_id,r.case_short,null,null,null,null,null,null]);
 bs.getRange('A7:H66').format.rowHeight=56;bs.getRange('C7:H66').format.fill='#FFF6D8';bs.getRange('A7:H66').format.wrapText=true;bs.getRange('A7:H66').format.verticalAlignment='top';
 [85,85,105,105,145,240,390,110].forEach((w,i)=>bs.getRangeByIndexes(0,i,68,1).format.columnWidthPx=w);
 validation(bs,'C7:E66',['是','部分','否','无法判断']);validation(bs,'H7:H66',['已完成','待讨论','无法判断']);bs.freezePanes.freezeRows(6);bs.freezePanes.freezeColumns(2);
 const bg=notesSheet(b,'B');b.recalculate();
 const bFile=path.join(bDir,`阶段B_报告评分_教师${teacher}.xlsx`);await (await SpreadsheetFile.exportXlsx(b)).save(bFile);created.push(bFile);
 for(const [sheet,range,suffix] of [[bs,'A1:H12','B填写'],[bg,'A1:B23','B说明']]){
  const blob=await b.render({sheetName:sheet.name,range,scale:1,format:'png'});await fs.writeFile(path.join(preview,`教师${teacher}_${suffix}.png`),new Uint8Array(await blob.arrayBuffer()));
 }
 const headHtml=`<header><h1>60份匿名报告 · 教师${teacher}</h1><p>须先提交阶段A，再独立评分。请在配套Excel表中按报告编号填写。报告英文原文未翻译、删改；中文案例说明仅为辅助。</p><p>逐项判断指导是否正确相关、下一步是否清楚，以及解释是否越过证据边界。不要根据篇幅、格式或引用数量评分。</p><label class="controls">选择报告 <select id="report">${order.map(r=>`<option value="${r.blind_id}">${r.blind_id} · ${r.case_short}</option>`).join('')}</select></label><p class="muted">可离线打开；不联网，不收集填写内容。Excel评分请自行保存。</p></header>`;
 const articles=order.map((r,i)=>{const c=cases.find(c=>c.caseId===r.caseId);return `<article id="${r.blind_id}"${i?' hidden':''}><h2>${r.blind_id} · ${r.case_short}</h2><h3>案例事实</h3>${facts(c)}<h3>原始报告</h3><pre class="report" lang="en">${h(r.report)}</pre></article>`;}).join('');
 const script='<script>const s=document.getElementById("report");s.addEventListener("change",()=>{document.querySelectorAll("article").forEach(a=>a.hidden=a.id!==s.value);window.scrollTo(0,0);});</script>';
 await fs.writeFile(path.join(bDir,'60匿名报告.html'),htmlPage('60份匿名报告',headHtml+articles,script));
 for(const [book,sheetName,range,label] of [[a,'参考标注','A6:E8','A'],[b,'报告评分','A6:H8','B']]){
  const check=await book.inspect({kind:'table',range:sheetName+'!'+range,include:'values,formulas',maxChars:1600,tableMaxRows:3,tableMaxCols:8});
  await fs.writeFile(path.join(preview,`教师${teacher}_${label}_inspect.json`),check.ndjson);
 }
}
const instructions=`# 教师评价材料使用顺序

1. 现在只发“先发_阶段A”中各自的文件给两位教师。每人先打开12案例材料，再填自己的参考标注Excel；不要先发阶段B。
2. 两人独立标注后，保留两份原始文件；先不看模型回复，协调参考问题标签及新增类别。将确认后的参考标签发回，再固定分类映射和F1计算口径。
3. 参考标签确认后，再分别发“确认A后再发_阶段B”中各自的两个文件。两人评价的是同一批60份原报告，但呈现顺序不同。不要让两位教师查看彼此分数。
4. 评分项为指导质量、可操作性，以及研究自定义的解释边界补充项。原始独立分数用于一致性分析；如需协调分歧，另保存协调后的版本。
5. 未完成、无法判断与0分不同；本次不代填教师分数，不先给参考标准答案，不沿用此前另一批报告的教师评分。

## 本次抽样

从现有300份报告中，按12案例×5配置分层，每层从5次生成中选1份，共60份；固定种子及散列排序，未按旧分数挑选。报告英文原文不改动，案例附中文辅助翻译。

“研究者留存_不要发给老师”包含匿名映射和评价计划，不能发给评分教师。虽然移除了外部配置标签，报告正文可能含系统名称或风格线索，因此只称标签匿名，不能承诺完全盲评。

## 指标与边界

- 问题识别拟用Precision、Recall、F1，评价与教师确认的案例优先问题是否一致，不评价真实学生致因。现有AI抽取结果不能未经核查直接当成新参考标签。
- 指导质量、可操作性参考MRBench并针对教师支持报告改编；DAMR报告获得“是”的比例，不把“部分”折半当作达标。两维分别报告，无加权总分。
- 解释边界是本研究自定义补充维度，不冒称通用量表。
- 教师一致性拟按维度报告线性加权Cohen κ、原始一致率和标签分布；原始独立评分优先保留。
- 这是在查看已有AI汇总结果之后提出的补充评价，不是预注册或新的独立测试集。300份回复不重跑，也不覆盖原评分。
- Faithfulness暂未运行。若后续增加，应另行固定证据材料、陈述分类及适用范围，不能仅给某些配置打分后作不公平比较。

## 文献

- Maurya et al. (2025), Unifying AI Tutor Evaluation: https://aclanthology.org/2025.naacl-long.57/
- Kochmar et al. (2025), BEA 2025 Shared Task Findings: https://aclanthology.org/2025.bea-1.77/
`;
await fs.writeFile(path.join(out,'先看这个_使用说明.md'),instructions);
await fs.writeFile(path.join(internal,'artifact_manifest.json'),JSON.stringify({created,source_raw_sha256:sha(rawText),sampling_n:60,n_cases:12,n_systems:5,score_cells_all_blank:true},null,2));
if(sha(await fs.readFile(path.join(source,'raw_reports.json'),'utf8'))!==sha(rawText))throw Error('Original data changed');
console.log(JSON.stringify({output_directory:out,workbooks:created,selected_reports:60,source_unchanged:true},null,2));
