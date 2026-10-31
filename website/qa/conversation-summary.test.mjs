import assert from 'node:assert/strict';
import {onRequestPost} from '../functions/api/chat.js';
import {CONVERSATION_PROMPT,parseTurn,cleanMessages,hasAffirmativeSafetyConcern} from '../functions/lib/conversation.js';
assert.match(CONVERSATION_PROMPT,/not mandatory checklist items/);
assert.match(CONVERSATION_PROMPT,/Do not assume the user is a parent/);
assert.match(CONVERSATION_PROMPT,/answer that question directly/);
assert.match(CONVERSATION_PROMPT,/suggestedReplies=\[\]/);
const env={AI_PROVIDER:'zhipu',ZHIPU_API_KEY:'fake-test-key'};
const req=messages=>new Request('http://localhost/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages})});
const user=content=>({role:'user',content});
const turn=(phase,reply)=>({phase,reply,questionFocus:phase==='summary'?'summary':'classroom',coverage:{confirmed:['trajectory','confidence','support_timing'],missing:['classroom'],readyForSummary:phase==='summary'},suggestedReplies:[]});
assert.equal(hasAffirmativeSafetyConcern([user('没有欺凌，课堂很安静')]),false);
assert.equal(hasAffirmativeSafetyConcern([user('没有威胁，但是同学经常嘲笑她，她害怕进教室')]),true);
assert.equal(hasAffirmativeSafetyConcern([user('No bullying, but the student is being ridiculed')]),true);
assert.equal(hasAffirmativeSafetyConcern([user('孩子被欺凌'),user('现在已经安全，学校已经处理，想继续讨论练习情况')]),false);
assert.equal(hasAffirmativeSafetyConcern([user('有没有欺凌还不清楚')]),false);
assert.throws(()=>cleanMessages(Array(101).fill(user('x'))),/too long/);
const summary=turn('summary','可以先关注独立解题时卡住的步骤，以及出错后是否很快放弃。先用几道相似题逐步减少提示，再观察一周；目前还不能确定成绩变化的原因。');
assert.throws(()=>parseTurn(JSON.stringify(turn('assessment','报告完成。')),[user('成绩下降了')]),/conversational/);
assert.throws(()=>parseTurn(JSON.stringify(turn('summary','MATHEFF与DML显示个体因素。')),[user('成绩下降了')]),/everyday/);
assert.throws(()=>parseTurn(JSON.stringify(turn('question','何时下降？课堂怎样？')),[user('成绩下降了')]),/one focused/);
const filtered=parseTurn(JSON.stringify({...summary,assessment:{riskLevel:'fake'},score:100}),[user('最近做题容易放弃')]);
assert.ok(!('assessment' in filtered)&&!('score' in filtered));
assert.equal(filtered.reply,summary.reply);
const fetchOriginal=globalThis.fetch;let calls=0;const histories=[];
const responses=[turn('question','他在课堂上遇到不会做的题时通常会怎么办？'),summary,turn('question','你提到最近缺课，主要发生在什么时候？')];
globalThis.fetch=async(url,opts)=>{
 assert.equal(url,'https://open.bigmodel.cn/api/paas/v4/chat/completions');
 const body=JSON.parse(opts.body);assert.equal(body.model,'glm-4.5-flash');
 assert.match(body.messages[0].content,/NOT a diagnostic report/);
 histories.push(body.messages);const result=responses[calls++]||summary;
 return Response.json({model:'glm-4.5-flash',choices:[{finish_reason:'stop',message:{content:JSON.stringify(result)}}]});
};
try {
 const history=[user('最近三次数学成绩在下降，遇到错误很快放弃')];
 for(let i=0;i<3;i++){
  if(i===1)history.push(user('课堂比较安静，老师是在下降后才增加辅导，跟例题可以但自己做就卡住'));
  if(i===2)history.push(user('还有个新情况：最近连续缺课'));
  const response=await onRequestPost({request:req(history),env});assert.equal(response.status,200);
  const result=await response.json();assert.equal(result.phase,responses[i].phase);assert.ok(!result.assessment);
  assert.equal(result.reply,responses[i].reply);assert.equal(response.headers.get('Cache-Control'),'no-store');
  history.push({role:'assistant',content:result.reply});
 }
 assert.equal(histories[2].length,6);assert.equal(histories[2][1].content,history[0].content);
 assert.equal(JSON.parse(histories[2][2].content).reply,responses[0].reply);
 const before=calls;const safe=await onRequestPost({request:req([user('同学反复嘲笑孩子，孩子害怕进入教室')]),env:{}});
 assert.equal((await safe.json()).phase,'safety_escalation');assert.equal(calls,before);
 assert.equal((await onRequestPost({request:req([user('成绩下降了')]),env:{}})).status,503);
 assert.equal((await onRequestPost({request:req([]),env})).status,400);
 const beforeQuota=calls;
 globalThis.fetch=async()=>Response.json({error:{code:'1113',message:'Insufficient resources'}},{status:429});
 const quota=await onRequestPost({request:req([user('成绩最近下降了')]),env});
 assert.equal(quota.status,503);assert.equal((await quota.json()).errorCode,'MODEL_QUOTA_UNAVAILABLE');
 assert.equal(calls,beforeQuota);
} finally {globalThis.fetch=fetchOriginal;}
console.log('PASS: multi-turn question → summary → new question, preserved context, plain output, no reports/scores, safety, errors, provider isolation.');
