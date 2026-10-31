import assert from 'node:assert/strict';
import fs from 'node:fs';
import {onRequestPost,onRequestGet} from '../functions/api/chat.js';
import {KNOWLEDGE_CONTEXT} from '../functions/lib/knowledge.js';
const root=new URL('../knowledge/pisa-jpn-2022-v2/',import.meta.url);
const library=JSON.parse(fs.readFileSync(new URL('knowledge.json',root)));
const csv=fs.readFileSync(new URL('sources/extra_trees.csv',root),'utf8').replace(/^\uFEFF/,'').trim().split(/\r?\n/);
const header=csv.shift().split(',');
const rows=csv.map(line=>Object.fromEntries(line.split(',').map((v,i)=>[header[i],v]))).filter(r=>r.model==='ExtraTrees');
assert.equal(rows.length,5);
const fields=['coef_pooled','std_error_pooled','p_value_pooled','within_var','between_var','n_mean','pv_count','significant_pv_count','ci_low','ci_high'];
for(const source of rows){
 const record=library.records.find(r=>r.factor_code===source.treatment);
 const mapped=record.sensitivity.find(r=>r.source_id==='extra_trees');
 assert.equal(mapped.model,'ExtraTrees');
 for(const field of fields)assert.equal(mapped[field],Number(source[field]),`${source.treatment}.${field}`);
 assert.equal(mapped.signal_direction,source.signal_direction);
 assert.equal(mapped.direction_consistent,source.direction_consistent==='True');
 const md=fs.readFileSync(new URL('knowledge.md',root),'utf8');
 const section=md.split(`## ${source.treatment} `)[1].split('\n\n## ')[0];
 const line=section.split('\n').find(s=>s.startsWith('敏感性 extra_trees：'));
 const values=line.match(/coef=([^;]+); p=([^;]+); 95%CI=\[([^,]+), ([^\]]+)\]/).slice(1).map(Number);
 for(const [i,field] of ['coef_pooled','p_value_pooled','ci_low','ci_high'].entries())assert.equal(values[i],Number(source[field]),`${source.treatment} Markdown ${field}`);
}
assert.equal(library.records.length,42);
assert.equal(library.records.filter(r=>r.dml_main).length,12);
assert.ok(!KNOWLEDGE_CONTEXT.includes('support_example_draft'));
const original=globalThis.fetch;let calls=0;
globalThis.fetch=async(url,options)=>{
 calls++;const body=JSON.parse(options.body);const prompt=body.messages[0].content;
 assert.match(prompt,/CURRENT STRUCTURED RESEARCH EVIDENCE/);
 const records=JSON.parse(prompt.split('EVIDENCE RECORDS JSON:\n')[1].split('\nEND STRUCTURED')[0]);
 const teacher=records.find(r=>r.code==='TEACHSUP');
 const et=teacher.sensitivity.find(r=>r.source==='extra_trees');
 assert.equal(et.coef,-2.3119492435809166);assert.ok(et.p>.05);assert.ok(et.ci95[1]>0);
 assert.equal(body.messages.at(-1).content,'老师是在下降以后才提供辅导，请先梳理。');
 return Response.json({model:'deepseek-flash',choices:[{finish_reason:'stop',message:{content:JSON.stringify({phase:'summary',reply:'可以先了解学生在哪些任务上遇到困难，再和教师讨论当前帮助的内容；帮助开始于下降之后，不能由此认定帮助导致了下降。',coverage:{confirmed:['support_timing']},suggestedReplies:[]})}}]});
};
try{
 const result=await onRequestPost({request:new Request('http://localhost/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:[{role:'user',content:'老师是在下降以后才提供辅导，请先梳理。'}]})}),env:{AI_PROVIDER:'deepseek',DEEPSEEK_API_KEY:'mock-key',DEEPSEEK_MODEL:'deepseek-flash'}});
 assert.equal(result.status,200);assert.equal((await result.json()).knowledge.version,'pisa-jpn-2022-v2');
 assert.equal((await onRequestGet().json()).knowledge.rag,false);assert.equal(calls,1);
}finally{globalThis.fetch=original;}
console.log('PASS: all 5 ExtraTrees rows, 65 numeric/category fields, Markdown values, actual outbound knowledge context, response version; mocked model only.');
