// One isolated conversation per process. Secrets arrive only through stdin.
import fs from 'node:fs';
import path from 'node:path';
import readline from 'node:readline';
import {pathToFileURL} from 'node:url';
const input=readline.createInterface({input:process.stdin,terminal:false});
const cfg=await new Promise(resolve=>input.once('line',line=>resolve(JSON.parse(line))));input.close();
const key=cfg.apiKey;delete cfg.apiKey;
const save=(file,data)=>{const temp=file+'.tmp';fs.writeFileSync(temp,JSON.stringify(data,null,2));fs.renameSync(temp,file);};
const dir=cfg.directory;fs.mkdirSync(dir,{recursive:true});
const nativeFetch=globalThis.fetch;let apiCalls=0;
globalThis.fetch=async(url,options)=>{
 if(url!=='https://api.deepseek.com/chat/completions')throw Error('Unexpected endpoint');
 const request=JSON.parse(options.body),call=++apiCalls;
 const record={call,started_utc:new Date().toISOString(),request};
 const target=path.join(dir,`api_call_${String(call).padStart(3,'0')}.json`);
 save(target,record);
 for(let retry=0;retry<4;retry++){
  try{
   const res=await nativeFetch(url,{...options,signal:AbortSignal.timeout(90000),redirect:'error'});
   const text=await res.text();let payload;try{payload=JSON.parse(text);}catch{payload={unparseable:true,body:text};}
   const attempt={status:res.status,payload,finished_utc:new Date().toISOString()};
   record.attempts=[...(record.attempts||[]),attempt];save(target,record);
   if((res.status===429||res.status>=500)&&retry<3){await new Promise(r=>setTimeout(r,5000*2**retry));continue;}
   return new Response(text,{status:res.status,headers:{'Content-Type':'application/json'}});
  }catch(error){
   record.attempts=[...(record.attempts||[]),{error:error.name,finished_utc:new Date().toISOString()}];save(target,record);
   if(retry===3)throw error;
   await new Promise(r=>setTimeout(r,5000*2**retry));
  }
 }
};
const {onRequestPost}=await import(pathToFileURL(path.join(cfg.project,'functions/api/chat.js')));
const {parseTurn}=await import(pathToFileURL(path.join(cfg.project,'functions/lib/conversation.js')));
const history=[],turns=[];
let status='completed';
try{
 for(let index=0;index<cfg.userTurns.length;index++){
  history.push({role:'user',content:cfg.userTurns[index]});
  let result;
  if(cfg.system==='grade_agent'){
   const response=await onRequestPost({request:new Request('http://localhost/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({messages:history})}),env:{AI_PROVIDER:'deepseek',DEEPSEEK_API_KEY:key,DEEPSEEK_MODEL:'deepseek-flash'}});
   result=await response.json();if(!response.ok)throw Error('Agent HTTP '+response.status+' '+(result.errorCode||'generation_error'));
  }else{
   let correction='';
   for(let attempt=0;attempt<2;attempt++){
    const messages=history.map(m=>m.role==='assistant'?{role:m.role,content:JSON.stringify({phase:/[?？]/.test(m.content)?'question':'summary',reply:m.content})}:m);
    const response=await globalThis.fetch('https://api.deepseek.com/chat/completions',{method:'POST',headers:{Authorization:'Bearer '+key,'Content-Type':'application/json'},body:JSON.stringify({model:'deepseek-flash',messages:[{role:'system',content:cfg.baselinePrompt+correction},...messages],response_format:{type:'json_object'},thinking:{type:'disabled'},temperature:attempt?0:.25,max_tokens:1400,stream:false})});
    const data=await response.json();if(!response.ok)throw Error('Baseline HTTP '+response.status);
    const choice=data.choices?.[0];
    try{
     if(choice?.finish_reason!=='stop')throw Error('Reply incomplete; return shorter complete JSON.');
     result={...parseTurn(choice.message.content,history),model:data.model,provider:'deepseek'};break;
    }catch(error){correction='\nThe previous output failed the contract: '+error.message+' Return a complete corrected conversational turn, not a report or generic example.';}
   }
   if(!result)throw Error('Baseline format failed after one repair');
  }
  if(result.provider==='deepseek'&&!String(result.model).includes('flash'))throw Error('Unexpected returned model');
  history.push({role:'assistant',content:result.reply});
  turns.push({index:index+1,user:cfg.userTurns[index],result});
  save(path.join(dir,'conversation.json'),{job:cfg.job,system:cfg.system,status:'running',turns});
 }
}catch(error){status='failed';save(path.join(dir,'failure.json'),{name:error.name,message:String(error.message).replaceAll(key,'[REDACTED]')});}
const final=turns.length===cfg.userTurns.length?turns.at(-1).result.reply:null;
const row={job:cfg.job,system:cfg.system,status,turns,final_reply:final,api_calls:apiCalls,finished_utc:new Date().toISOString()};
save(path.join(dir,'conversation.json'),row);
console.log(JSON.stringify({job:cfg.job,status,turn_count:turns.length,api_calls:apiCalls}));
