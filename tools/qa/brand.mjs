import { spawn } from 'node:child_process';
const CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT=9345; const URL=process.argv[2]; const W=Number(process.argv[3]||390);
const chrome=spawn(CHROME,['--headless=new','--disable-gpu','--hide-scrollbars',
 `--remote-debugging-port=${PORT}`,'--user-data-dir=/tmp/cdp-profile-br',`--window-size=${W},900`,'about:blank'],{stdio:'ignore'});
const sleep=(ms)=>new Promise(r=>setTimeout(r,ms));
async function target(){for(let i=0;i<40;i++){try{const l=await(await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();const p=l.find(t=>t.type==='page');if(p)return p;}catch(_){}await sleep(250);}throw new Error('no target');}
let id=0;function rpc(ws,m,p){return new Promise((res,rej)=>{const mid=++id;const on=(e)=>{const x=JSON.parse(e.data);if(x.id!==mid)return;ws.removeEventListener('message',on);x.error?rej(new Error(JSON.stringify(x.error))):res(x.result);};ws.addEventListener('message',on);ws.send(JSON.stringify({id:mid,method:m,params:p||{}}));});}
const t=await target();const ws=new WebSocket(t.webSocketDebuggerUrl);
await new Promise(r=>ws.addEventListener('open',r,{once:true}));
await rpc(ws,'Page.enable');await rpc(ws,'Runtime.enable');
await rpc(ws,'Emulation.setDeviceMetricsOverride',{width:W,height:900,deviceScaleFactor:1,mobile:true});
await rpc(ws,'Page.navigate',{url:URL});await sleep(2400);
const r=await rpc(ws,'Runtime.evaluate',{returnByValue:true,expression:`(() => {
  const el=document.querySelector('.tf-footer-brand-word');
  const sp=el&&el.querySelector('span');
  const shell=document.querySelector('.tf-reference-footer-shell');
  const cs=el?getComputedStyle(el):null;
  const out={};
  if(el){const b=el.getBoundingClientRect(); out.word={w:Math.round(b.width),left:Math.round(b.left),right:Math.round(b.right),fs:cs.fontSize,ls:cs.letterSpacing};}
  if(sp){const b=sp.getBoundingClientRect(); out.span={w:Math.round(b.width),left:Math.round(b.left),right:Math.round(b.right),scrollW:sp.scrollWidth};}
  if(shell){const b=shell.getBoundingClientRect(); out.shell={w:Math.round(b.width),left:Math.round(b.left),right:Math.round(b.right)}}
  out.vw=document.documentElement.clientWidth;
  return JSON.stringify(out,null,1); })()`});
console.log(r.result.value);ws.close();chrome.kill();process.exit(0);
