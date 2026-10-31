import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';

const base='C:/Users/84130/Documents/Codex/2026-08-09/zh';
const old=path.join(base,'outputs/teacher_evaluation_20261026_v1');
const aidsRoot=path.join(base,'outputs/teacher_summary_20261026_v2/研究者留存_不要发给老师');
const root=path.join(base,'outputs/teacher_comparison_20261027_v3');
const internal=path.join(root,'研究者留存_不要发给老师');
const preview=path.join(base,'work/teacher_comparison_v3_previews');
try{await fs.access(path.join(internal,'manifest.json'));throw Error('Existing materials may contain teacher scores. Refusing overwrite.');}catch(e){if(e.code!=='ENOENT')throw e;}
const hash=s=>crypto.createHash('sha256').update(s).digest('hex');
const h=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
const decode=s=>s.replaceAll('&quot;','"').replaceAll('&#x27;',"'").replaceAll('&gt;','>').replaceAll('&lt;','<').replaceAll('&amp;','&');
const mapping=JSON.parse(await fs.readFile(path.join(old,'研究者留存_不要发给老师/anonymous_mapping_DO_NOT_SHARE.json'),'utf8'));
const raw=JSON.parse(await fs.readFile('D:/pisa2022/outputs_grade_agent_deepseek41flash300_20261026/raw_reports.json','utf8'));
const aids={};
for(const m of mapping){
 const doc=JSON.parse(await fs.readFile(path.join(aidsRoot,'summaries',m.blind_id+'.json'),'utf8'));
 if(doc.status!=='completed')throw Error('Incomplete reading aid');
 const source=raw.find(r=>r.system===m.system&&r.caseId===m.caseId&&r.repeat===m.repeat);
 if(!source||hash(source.report)!==m.source_report_sha256)throw Error('Source report mismatch');
 for(const section of ['main','advice','boundary'])for(const q of doc.reading_aid[section].verified_quotes){
  // Python offsets count Unicode code points, not JavaScript UTF-16 units.
  if(Array.from(source.report).slice(q.start,q.end).join('')!==q.text)throw Error('Quote span mismatch');
 }
 aids[m.blind_id]={...doc,report:source.report};
}
const casePage=await fs.readFile(path.join(old,'先发_阶段A/教师1/12案例材料.html'),'utf8');
const cases=[...casePage.matchAll(/<article><h2>(H\d{2})<\/h2>(.*?)<\/article>/gs)].map(m=>({id:m[1],html:m[2]}));
if(cases.length!==12||mapping.length!==60)throw Error('Wrong case/sample count');
for(const c of cases){
 const group=mapping.filter(m=>m.caseId.split('_')[0]===c.id);
 if(group.length!==5||new Set(group.map(m=>m.system)).size!==5)throw Error('Not five configurations per case');
 c.text=[...c.html.matchAll(/<dt>(.*?)<\/dt><dd>(.*?)<small/gs)].map(m=>decode(m[1])+': '+decode(m[2])).join('\n');
}
await fs.mkdir(internal,{recursive:true});await fs.mkdir(preview,{recursive:true});
const descriptions=[
 ['评价对象','评价同一案例下的五份原始回复，不给案例本身打分。中文摘要是AI辅助阅读材料，不是模型原始输出。'],
 ['表格结构','“对照评分总表”按H01至H12分组，每个案例连续五行；A—E只代表该案例内的展示位置，不固定对应某种系统。'],
 ['先看案例','本页下半部分列出12个案例。配套HTML也将案例事实和五份回复放在同一处。'],
 ['原文核对','HTML每行可展开英文原句与完整回复。评分以原文为准；给部分、否或有疑问时，应核对原文。摘要错误请另在评语说明。'],
 ['独立填写','两位教师独立评分，不看彼此分数或系统配置映射。请勿将此前逐份展示获得的评分混填入本表。'],
 ['指导质量：是','指导正确、与当前案例相关且内容充分；先收集信息或安全转介也可以是充分指导。'],
 ['指导质量：部分 / 否','部分：存在有用指导，但有不正确、不相关或重要缺漏。否：没有指导，或指导整体明显错误、不相关。'],
 ['可操作性：是','用户能明确下一步要做什么，具体到足以执行；不强制三类行动主体或数字化时间期限。'],
 ['可操作性：部分 / 否','部分：有行动方向但仍笼统、不够清楚。否：无法确定可执行的下一步。两维分别判断：可执行不等于正确。'],
 ['解释边界：是','区分事实与假设，不将群体统计关系当作个体确定原因。无需固定免责声明措辞。'],
 ['解释边界：部分 / 否','部分：局部推测或过度解释，但无决定性无依据归因。否：明确作出无依据个体因果、临床、敏感身份判断，或误将后续支持说成致因。'],
 ['无法判断与完成状态','无法判断不记0分，须写原因。三项分别评完、必要说明写清后选“已完成”；不计算加权总分。'],
 ['方法来源','指导质量、可操作性参考MRBench并改为教师支持报告情境；解释边界为本研究自定义补充维度，并非通用量表。'],
 ['MRBench文献','https://aclanthology.org/2025.naacl-long.57/'],
 ['案例事实','中文为辅助翻译；配套HTML保留英文案例事实。如有含义差异，请以英文原文为准并指出。']
];
const css=`body{margin:0;background:#f5f6f8;color:#222;font:16px/1.65 'Microsoft YaHei',Arial,sans-serif}main{max-width:1420px;margin:28px auto;padding:0 22px}header{background:#fff;padding:24px;border:1px solid #dce2e8;border-radius:8px}h1{font-size:25px;margin:0 0 10px}nav{display:flex;flex-wrap:wrap;gap:14px;margin:16px 0}a{color:#245d8c}table{width:100%;border-collapse:collapse;background:white;table-layout:fixed;margin:20px 0}th{background:#304b67;color:white;text-align:left;padding:12px}td{vertical-align:top;padding:14px 16px;border-bottom:1px solid #dbe0e6;overflow-wrap:anywhere}.id{width:115px}.reply{width:58%}.case td{background:#e9eff5;border-top:2px solid #304b67;padding:18px 22px}.case h2{margin:0 0 10px;font-size:20px}.case p{margin:4px 0}.aid{margin:0 0 12px}.aid strong{font-weight:600}.muted,small{color:#5b6671;font-size:14px}small{display:block}details{margin:10px 0}summary{cursor:pointer;color:#245d8c}blockquote,pre{font:15px/1.6 'Times New Roman',serif;white-space:pre-wrap;overflow-wrap:anywhere;margin:12px 0;padding:10px;background:#f5f7fa}dt{font-weight:600}dd{margin:0 0 10px}tbody tr:last-child td{border-bottom:2px solid #304b67}@media(max-width:800px){main{padding:0 10px}.id{width:80px}.reply{width:58%}td{padding:10px}table{font-size:14px}}@media print{body{background:white}main{max-width:none;margin:0}nav{display:none}thead{display:table-header-group}.case{break-before:page}tr{break-inside:avoid}header{border:0}}`;
const orders={};const exports=[];
for(const teacher of [1,2]){
 const dir=path.join(root,`教师${teacher}`);await fs.mkdir(dir,{recursive:true});
 const ordered=cases.flatMap(c=>mapping.filter(m=>m.caseId.split('_')[0]===c.id)
  .sort((a,b)=>hash('comparison-v3-20261027|'+teacher+'|'+a.blind_id).localeCompare(hash('comparison-v3-20261027|'+teacher+'|'+b.blind_id)))
  .map((m,i)=>({...m,case_short:c.id,slot:'ABCDE'[i]})));
 orders[teacher]=ordered.map(m=>({caseId:m.case_short,slot:m.slot,blind_id:m.blind_id,system:m.system,repeat:m.repeat}));
 const rows=ordered.map(m=>{const a=aids[m.blind_id].reading_aid;return [m.case_short,m.slot+'（'+m.blind_id+'）',
  '主要判断：'+a.main.summary_zh+'\n支持建议：'+a.advice.summary_zh+'\n边界表述：'+a.boundary.summary_zh,null,null,null,null,null];});
 const wb=Workbook.create(),s=wb.worksheets.add('对照评分总表'),guide=wb.worksheets.add('案例与评分说明');
 for(const sheet of [s,guide]){sheet.showGridLines=false;sheet.getRange('A1:H70').format.font={name:'Arial',size:11,color:'#222222'};sheet.getRange('A1:H70').format.verticalAlignment='center';}
 s.getRange('A2').values=[[`同案例五回复对照评分（教师${teacher}）`]];s.getRange('A2').format.font={name:'Arial',size:15,bold:true};s.getRange('A2').format.rowHeight=28;
 s.getRange('A4').values=[['每个案例连续五行。先阅读“案例与评分说明”，核对原文后在黄色栏填写；不计算总分。']];s.getRange('A4').format.rowHeight=26;
 s.getRange('A6:H6').values=[['案例','匿名回复','回复汇总（中文阅读辅助）','指导质量','可操作性','解释边界','教师评语 / 依据','填写状态']];
 s.getRange('A6:H6').format={fill:'#304B67',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:34,wrapText:true,horizontalAlignment:'center',verticalAlignment:'center'};
 s.getRange('A7:H66').values=rows;s.getRange('A7:H66').format.wrapText=true;s.getRange('A7:H66').format.verticalAlignment='top';
 [70,115,640,100,100,100,270,105].forEach((width,i)=>s.getRangeByIndexes(0,i,70,1).format.columnWidthPx=width);
 const widthUnits=t=>Array.from(t).reduce((n,ch)=>n+(/[\u0000-\u00ff]/.test(ch)?0.56:1),0);
 for(let i=0;i<rows.length;i++){
  const lines=rows[i][2].split('\n').reduce((n,t)=>n+Math.ceil(widthUnits(t)/41),0);
  s.getRangeByIndexes(i+6,0,1,8).format.rowHeightPx=Math.max(160,lines*22+24);
  if(i%5===0)s.getRangeByIndexes(i+6,0,1,8).format.borders={top:{style:'medium',color:'#8294A6'}};
  if(Math.floor(i/5)%2===1)s.getRangeByIndexes(i+6,0,1,3).format.fill='#F3F6F8';
 }
 s.getRange('D7:H66').format.fill='#FFF6D8';s.getRange('D7:F66').dataValidation={rule:{type:'list',values:['是','部分','否','无法判断']}};
 s.getRange('H7:H66').dataValidation={rule:{type:'list',values:['已完成','待讨论','无法判断']}};s.freezePanes.freezeRows(6);s.freezePanes.freezeColumns(2);
 guide.getRange('A2').values=[['案例与评分说明']];guide.getRange('A2').format.font={name:'Arial',size:15,bold:true};
 guide.getRange('A1:A40').format.columnWidthPx=220;guide.getRange('B1:B40').format.columnWidthPx=1050;
 guide.getRangeByIndexes(3,0,descriptions.length,2).values=descriptions;guide.getRangeByIndexes(3,0,descriptions.length,2).format.wrapText=true;
 guide.getRangeByIndexes(3,0,descriptions.length,2).format.verticalAlignment='top';guide.getRangeByIndexes(3,0,descriptions.length,1).format.font={name:'Arial',size:11,bold:true};
 guide.getRangeByIndexes(3,0,descriptions.length,2).format.rowHeightPx=58;
 guide.getRange('A20:B20').values=[['案例编号','案例事实（中文辅助）']];guide.getRange('A20:B20').format={fill:'#304B67',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:30};
 guide.getRange('A21:B32').values=cases.map(c=>[c.id,c.text]);guide.getRange('A21:B32').format.wrapText=true;guide.getRange('A21:B32').format.verticalAlignment='top';guide.getRange('A21:B32').format.rowHeightPx=145;
 wb.recalculate();
 const file=path.join(dir,`五种配置回复对照评分_教师${teacher}.xlsx`);await (await SpreadsheetFile.exportXlsx(wb)).save(file);exports.push(file);
 for(const [sheetName,range,name] of [['对照评分总表','A1:H11','总表'],['案例与评分说明','A1:B18','说明'],['案例与评分说明','A20:B23','案例']]){
  const image=await wb.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(preview,`教师${teacher}_${name}.png`),new Uint8Array(await image.arrayBuffer()));
 }
 const check=await wb.inspect({kind:'table',range:'对照评分总表!A6:H8',include:'values,formulas',maxChars:2000,tableMaxRows:3,tableMaxCols:8});await fs.writeFile(path.join(preview,`教师${teacher}_inspect.json`),check.ndjson);
 const body=cases.map(c=>{
  const intro='<tr class="case" id="'+c.id+'"><td colspan="3"><h2>案例 '+c.id+'</h2>'+c.text.split('\n').map(t=>'<p>'+h(t)+'</p>').join('')+'<details><summary>核对中英完整案例事实</summary>'+c.html+'</details></td></tr>';
  const lines=ordered.filter(m=>m.case_short===c.id).map(m=>{
   const doc=aids[m.blind_id],a=doc.reading_aid;
   const parts=[['main','主要判断'],['advice','支持建议'],['boundary','边界表述']];
   const text=parts.map(([k,title])=>'<p class="aid"><strong>'+title+'：</strong>'+h(a[k].summary_zh)+'</p>').join('');
   const quotes=parts.map(([k,title])=>'<details><summary>'+title+'：英文原句</summary>'+a[k].verified_quotes.map(q=>'<blockquote>'+h(q.text)+'</blockquote>').join('')+'</details>').join('');
   return '<tr data-blind-id="'+m.blind_id+'"><td><strong>回复'+m.slot+'</strong><br>'+m.blind_id+'</td><td>'+text+'</td><td>'+quotes+'<details><summary>英文完整回复</summary><pre>'+h(doc.report)+'</pre></details></td></tr>';
  }).join('');return intro+lines;
 }).join('');
 const page='<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>同案例五回复对照表</title><style>'+css+'</style></head><body><main><header><h1>同案例五回复对照表 · 教师'+teacher+'</h1><p>同一个案例的五份回复集中展示。请在配套Excel同名编号行填写指导质量、可操作性和解释边界；本网页不保存评分。</p><p class="muted">中文摘要为AI辅助阅读材料。评分以原始回复为准，摘要错误不得计入模型分数；有疑问或作负面评价时，请展开右侧原句及全文。A—E仅为各案例内的展示位置，不固定对应某个系统。请独立评分，不看另一位教师的结果。</p></header><nav>'+cases.map(c=>'<a href="#'+c.id+'">'+c.id+'</a>').join('')+'</nav><table><thead><tr><th class="id">匿名回复</th><th class="reply">回复汇总（中文）</th><th>原文核对</th></tr></thead><tbody>'+body+'</tbody></table></main></body></html>';
 await fs.writeFile(path.join(dir,'同案例五回复对照表.html'),page);
 await fs.writeFile(path.join(dir,'使用说明.txt'),'先阅读Excel“案例与评分说明”，再在“对照评分总表”填写。每个案例连续五行，对应五种匿名系统配置。HTML将五份回复放在同一表格并提供原句和全文。\nA—E只表示该案例的展示位置，不固定代表同一配置。B编号与此前材料保持对应。请独立评分，不看其他教师结果；不要把旧版逐份展示的评分混填进本表。\n若另计算问题识别F1，仍须先完成阶段A案例参考标注，再查看回复。\n');
}
const manifest={version:'comparison-v3-20261027',created_utc:new Date().toISOString(),workbooks:exports,
 source_mapping_sha256:hash(await fs.readFile(path.join(old,'研究者留存_不要发给老师/anonymous_mapping_DO_NOT_SHARE.json'),'utf8')),
 same_60_original_reports:true,same_chinese_aids_as_v2:true,no_new_api_calls:true,no_teacher_scores_filled:true,
 presentation:'Same-case blocks of five replies in one worksheet/table; case order H01-H12; independently hash-shuffled within-case order for each teacher; source blind IDs retained.',
 disclosure:'Comparative case-block presentation differs from v1/v2 individually shuffled presentation; do not pool scores across presentation versions without identifying the protocol difference. Chinese aids remain secondary to original replies.',
 task:'Evaluate original reply quality, not the quality of the synthetic case. No new system generations, scores or rankings.',
 teacher_orders:orders};
await fs.writeFile(path.join(internal,'manifest.json'),JSON.stringify(manifest,null,2));
console.log(JSON.stringify({root,workbooks:exports,reply_rows_each:60,case_blocks_each:12},null,2));
