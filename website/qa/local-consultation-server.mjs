// Local-only development server. Credential comes from a hidden parent stdin pipe,
// never from source code, browser code, a local secret file or command arguments.
import http from 'node:http';
import readline from 'node:readline';
import {createServer as createViteServer} from 'vite';
const lines=readline.createInterface({input:process.stdin,terminal:false});
const config=await new Promise(resolve=>lines.once('line',line=>resolve(JSON.parse(line))));lines.close();
const env=config.provider==='zhipu'?{AI_PROVIDER:'zhipu',ZHIPU_API_KEY:config.apiKey,ZHIPU_MODEL:'glm-4.5-flash'}:config.provider==='deepseek'?{AI_PROVIDER:'deepseek',DEEPSEEK_API_KEY:config.apiKey,DEEPSEEK_MODEL:'deepseek-flash'}:{};
config.apiKey=null;
env.LOCAL_CONVERSATION_DEBUG='1';
const vite=await createViteServer({server:{middlewareMode:true,host:'127.0.0.1',hmr:{port:5182}},appType:'spa'});
const server=http.createServer(async(req,res)=>{
 if(req.url.split('?')[0]!=='/api/chat')return vite.middlewares(req,res,()=>{res.writeHead(404);res.end();});
 try {
  const {onRequestGet,onRequestPost}=await import('../functions/api/chat.js?local='+Date.now());
  let response;
  if(req.method==='GET')response=onRequestGet();
  else if(req.method==='POST'){
   const parts=[];let size=0;
   for await(const c of req){size+=c.length;if(size>1200000)throw Error('Request too large');parts.push(c);}
   response=await onRequestPost({request:new Request('http://127.0.0.1:5181/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:Buffer.concat(parts)}),env});
  }else response=new Response('',{status:405});
  res.writeHead(response.status,Object.fromEntries(response.headers));res.end(await response.text());
 }catch{res.writeHead(500,{'Content-Type':'application/json'});res.end(JSON.stringify({error:'Local conversation request failed.'}));}
});
server.listen(5181,'127.0.0.1',()=>console.log('Local conversation preview: http://127.0.0.1:5181/?view=agent (no deployment)'));
