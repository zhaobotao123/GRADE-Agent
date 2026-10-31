import fs from 'node:fs/promises';
import path from 'node:path';
import crypto from 'node:crypto';
import assert from 'node:assert/strict';
import {Workbook,SpreadsheetFile} from '@oai/artifact-tool';
const source='D:/pisa2022/outputs_grade_agent_english_comparison_v2_20261027';
const output='C:/Users/84130/Documents/Codex/2026-08-09/zh/outputs/teacher_comparison_english_v2_20261027';
await fs.mkdir(output,{recursive:true});await fs.mkdir(path.join(output,'internal'),{recursive:true});await fs.mkdir(path.join(output,'qa'),{recursive:true});
const raw=await fs.readFile(path.join(source,'final_replies.json'),'utf8');
const rows=JSON.parse(raw),lock=JSON.parse(await fs.readFile(path.join(source,'protocol_lock.json'),'utf8'));
assert.equal(rows.length,120);assert(rows.every(r=>r.status==='completed'&&r.final_reply&&!r.language_violations?.length));
const systems=['ordinary_llm','grade_agent'];
function rng(seed){return ()=>{seed=(1664525*seed+1013904223)>>>0;return seed/4294967296;};}
function shuffle(items,random){const result=[...items];for(let i=result.length-1;i>0;i--){const j=Math.floor(random()*(i+1));[result[i],result[j]]=[result[j],result[i]];}return result;}
const pairs=shuffle(lock.plan.cases.flatMap(c=>Array.from({length:5},(_,i)=>({case:c,repeat:i+1}))),rng(202610271)).map((p,i)=>({...p,id:`P${String(i+1).padStart(3,'0')}`}));
const key=r=>`${r.job.case_id}__${r.system}__${r.job.repeat}`;
const byKey=new Map(rows.map(r=>[key(r),r]));assert.equal(byKey.size,120);
const labels={trajectory:'Performance over time',confidence:'Confidence and approach',classroom:'Classroom circumstances',safety:'Safety',support:'Support',recentEvent:'Recent event',language:'Instructional language',followThrough:'Independent work',resources:'Resources',records:'Available records',recentChange:'Context not yet checked'};
const anchors=[
 ['情境相关性','没有抓住主要问题，或大部分内容与案例无关。','回应了主要问题，但有泛泛内容、干扰信息，或遗漏重要相关点。','聚焦案例相关的问题与优先事项，不把中性背景自动当作问题。'],
 ['信息一致性','编造或违背关键事实，或把没有依据的个体原因说成已确定。','大体符合事实，但有重要的无依据推断，或没有充分保留判断。','忠实使用已有事实，区分“不清楚”与“不存在”，解释不超出事实支持范围。'],
 ['建议适用性','建议不适合本案例、不安全，或无法使用。','总体方向合适，但不够具体，或未充分结合已知信息。','建议具体、可行，符合案例及其不确定性；必要时先补充信息或保障安全，也可得高分。'],
 ['表达清晰性','难以理解或难以跟上思路。','总体能理解，但有不必要术语、重复或组织不清。','表达清楚、连贯、简洁，教师或家长容易理解。'],
];
const mappings=[],audits=[];
const escaped=s=>String(s).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;').replaceAll('"','&quot;');
for(let teacher=1;teacher<=2;teacher++){
 const folder=path.join(output,`教师${teacher}`);await fs.mkdir(folder,{recursive:true});
 const random=rng(202610280+teacher),order=shuffle(pairs,random),flips=shuffle(Array.from({length:60},(_,i)=>i<30),random);
 const workbook=Workbook.create(),sheet=workbook.worksheets.add('对照评分'),guide=workbook.worksheets.add('评分说明');
 for(const tab of [sheet,guide]){tab.showGridLines=false;tab.getRange('A1:I130').format.font={name:'Arial',size:11};}
 sheet.tabColor='#243D58';
 sheet.getRange('A2').values=[[`教师${teacher} 匿名回复评分`]];sheet.getRange('A2').format.font={name:'Arial',size:15,bold:true};
 sheet.getRange('C3').values=[['先读案例，再分别评A与B。四项各填1—5分，不计算总分。请先阅读“评分说明”。']];
 sheet.getRange('C3:I3').merge();sheet.getRange('C3:I3').format.wrapText=true;sheet.getRange('A3:I3').format.rowHeight=30;
 sheet.getRange('A5:I5').values=[['配对编号','回复编号','完整案例信息（英文）','最终回复原文（英文）','情境相关性\n1—5','信息一致性\n1—5','建议适用性\n1—5','表达清晰性\n1—5','简短说明（有问题或无法评分时填写）']];
 const data=[],html=[];
 for(let index=0;index<order.length;index++){
  const p=order[index],assign=flips[index]?[...systems]:[...systems].reverse();
  const facts=Object.entries(p.case.facts).map(([k,v])=>`${labels[k]||k}: ${v}`).join('\n');
  const replies=[];
  for(let j=0;j<2;j++){
   const letter=j?'B':'A',record=byKey.get(`${p.case.case_id}__${assign[j]}__${p.repeat}`);assert(record);
   const id=p.id+letter,excelRow=data.length+6;
   data.push([p.id,id,facts,record.final_reply,null,null,null,null,null]);
   mappings.push({teacher,pair_id:p.id,reply_id:id,display_order:index+1,excel_row:excelRow,system:assign[j],source_job:record.job.id,case_id:p.case.case_id,repeat:p.repeat,reply_sha256:crypto.createHash('sha256').update(record.final_reply).digest('hex')});
   replies.push({id,letter,reply:record.final_reply});
  }
  html.push(`<section id="${p.id}"><h2>${p.id}</h2><h3>完整案例信息</h3><p class="facts">${escaped(facts)}</p><div class="pair">${replies.map(r=>`<article><h3>回复${r.letter}　${r.id}</h3><p>${escaped(r.reply)}</p></article>`).join('')}</div><p class="hint">请在Excel中分别填写两份回复的四项分数。每组A/B身份不固定。</p></section>`);
 }
 assert.equal(data.length,120);
 sheet.getRange('A6:I125').values=data;
 sheet.getRange('A5:I5').format={fill:'#243D58',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},wrapText:true,horizontalAlignment:'center',verticalAlignment:'center',rowHeight:45};
 sheet.getRange('A6:I125').format.verticalAlignment='top';
 sheet.getRange('C6:D125').format.wrapText=true;sheet.getRange('I6:I125').format.wrapText=true;
 const widths=[13,14,65,100,13,13,13,13,34];
 for(let i=0;i<widths.length;i++)sheet.getRangeByIndexes(0,i,125,1).format.columnWidth=widths[i];
 for(let i=0;i<data.length;i++){
  const n=i+6,factLines=data[i][2].split('\n').reduce((s,l)=>s+Math.ceil(l.length/60),0),replyLines=Math.ceil(data[i][3].length/90);
  sheet.getRange(`A${n}:I${n}`).format.rowHeight=Math.min(350,Math.max(140,(Math.max(factLines,replyLines)+2)*16));
  if(Math.floor(i/2)%2===1)sheet.getRange(`A${n}:D${n}`).format.fill='#F1F4F7';
  if(i%2===0)sheet.getRange(`A${n}:I${n}`).format.borders={top:{style:'thin',color:'#A8B5C3'}};
 }
 sheet.getRange('E6:H125').format.fill='#FFF2CC';sheet.getRange('E6:H125').format.horizontalAlignment='center';sheet.getRange('E6:H125').setNumberFormat('0');
 sheet.dataValidations.add({range:'E6:H125',rule:{type:'whole',operator:'between',formula1:1,formula2:5}});
 sheet.freezePanes.freezeRows(5);sheet.freezePanes.freezeColumns(2);
 guide.getRange('A2').values=[['评分说明与标准']];guide.getRange('A2').format.font={name:'Arial',size:15,bold:true};
 const instructions=[
  ['评价对象','评价最终回复的质量，不评价案例质量，也不判断统计计算或学生的真实因果。'],
  ['材料范围','60组配对，共120份回复。两份回复面对相同案例。A/B身份随配对变化，不代表固定系统。'],
  ['如何评分','先读完整英文案例，再分别评价A、B。四项均填1—5分整数。允许同分，不必强行选赢家。'],
  ['评分尺度','1很差、2较差、3基本合格、4较好、5很好。2分介于1和3之间，4分介于3和5之间。'],
  ['独立完成','两位老师各自独立评分。评分完成前不交换分数或评语，不尝试判断系统身份。'],
  ['分数与空白','未评分或无法评价时留空，不填0分。无法评价或发现明显问题时，请写一句原因。'],
  ['避免偏好','不要因回复更长、语气更专业、包含统计术语就加分。只看与案例的贴合、依据、建议和清晰程度。'],
  ['信息不足与安全','信息不足时合理建议核实、或优先处理安全问题，都可能是合适建议，不因没有给出确定原因而扣分。'],
  ['只评最终回复','本表展示未改写的最终英文回复，不要求评价追问质量或系统界面，也不要求证明实际教学效果。'],
 ];
 for(let i=0;i<instructions.length;i++){
  guide.getRange(`A${i+4}`).values=[[instructions[i][0]]];guide.getRange(`B${i+4}:D${i+4}`).merge();guide.getRange(`B${i+4}`).values=[[instructions[i][1]]];guide.getRange(`A${i+4}:D${i+4}`).format.rowHeight=40;
 }
 guide.getRange('A15:D15').values=[['评价维度','1分','3分','5分']];guide.getRange('A16:D19').values=anchors;
 guide.getRange('A15:D15').format={fill:'#243D58',font:{name:'Arial',size:11,bold:true,color:'#FFFFFF'},rowHeight:26};
 guide.getRange('A4:D19').format.wrapText=true;guide.getRange('A16:D19').format.rowHeight=100;
 guide.getRange('A1:A21').format.columnWidth=23;guide.getRange('B1:D21').format.columnWidth=44;
 guide.getRange('A21').values=[['标准说明']];guide.getRange('B21:D21').merge();guide.getRange('B21').values=[['本评分标准为基于已有生成文本评价框架改编的任务专用标准，不是已验证的教育诊断量表。']];guide.getRange('A21:D21').format.wrapText=true;guide.getRange('A21:D21').format.rowHeight=36;
 workbook.recalculate();
 assert(sheet.getRange('E6:H125').values.every(row=>row.every(v=>v==null||v==='')));
 const inspection=await workbook.inspect({kind:'table',range:'对照评分!A5:I7',include:'values,formulas',tableMaxRows:3,tableMaxCols:9,maxChars:1000});
 await fs.writeFile(path.join(output,'qa',`teacher${teacher}_inspect.ndjson`),inspection.ndjson);
 const errors=await workbook.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:20},maxChars:1000});
 await fs.writeFile(path.join(output,'qa',`teacher${teacher}_errors.ndjson`),errors.ndjson);
 for(const [name,range] of [['对照评分','A5:I7'],['评分说明','A15:D19']]){
  const image=await workbook.render({sheetName:name,range,scale:1,format:'png'});
  await fs.writeFile(path.join(output,'qa',`teacher${teacher}_${name}.png`),new Uint8Array(await image.arrayBuffer()));
 }
 const file=path.join(folder,`教师${teacher}_英文匿名对照评分表.xlsx`);await (await SpreadsheetFile.exportXlsx(workbook)).save(file);
 const htmlPage=`<!doctype html><meta charset="utf-8"><title>教师${teacher} 英文回复对照阅读</title><style>body{font:16px Arial,sans-serif;color:#253548;background:#f3f5f7;max-width:1250px;margin:30px auto;padding:20px}section{background:white;padding:26px;margin:24px 0;border-radius:10px}p{line-height:1.65}.facts{white-space:pre-line;background:#eef2f6;padding:16px}.pair{display:grid;grid-template-columns:1fr 1fr;gap:24px}article{border-top:2px solid #788ba2}.hint{color:#657388;font-size:14px}@media(max-width:800px){.pair{grid-template-columns:1fr}}</style><h1>教师${teacher} 英文回复对照阅读</h1><p>仅用于阅读。请在配套Excel中独立评分。60组配对，四项各1—5分，允许同分。A/B身份随配对变化。</p>${html.join('')}`;
 await fs.writeFile(path.join(folder,`教师${teacher}_英文回复对照阅读.html`),htmlPage);
 audits.push({teacher,workbook:file,n_pairs:60,n_replies:data.length,blank_score_cells:480,first_system_A_count:flips.filter(Boolean).length});
 console.log(`Teacher ${teacher}: exported 120 unmodified replies, 480 blank ratings.`);
}
await fs.writeFile(path.join(output,'internal','blinding_key_DO_NOT_SEND.json'),JSON.stringify({seed_description:'Fixed seeded Fisher-Yates permutation; pair IDs shared, display order and balanced A/B assignment independently randomized for each rater.',mapping:mappings},null,2));
assert.equal(new Set(mappings.filter(m=>m.teacher===1).map(m=>m.source_job)).size,120);
assert.equal(new Set(mappings.filter(m=>m.teacher===2).map(m=>m.source_job)).size,120);
for(const m of mappings){const sourceRow=rows.find(r=>r.job.id===m.source_job);assert.equal(crypto.createHash('sha256').update(sourceRow.final_reply).digest('hex'),m.reply_sha256);}
assert.equal(await fs.readFile(path.join(source,'final_replies.json'),'utf8'),raw);
await fs.writeFile(path.join(output,'qa','audit.json'),JSON.stringify({source_signature:lock.signature,source_sha256:crypto.createHash('sha256').update(raw).digest('hex'),source_unchanged:true,all_120_replies_used_once_per_teacher:true,no_identity_mentions_in_replies:rows.every(r=>!/GRADE.Agent|DeepSeek/i.test(r.final_reply)),all_scores_blank:true,teachers:audits},null,2));
