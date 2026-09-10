import { spawn } from 'node:child_process';
const CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT=9340; const URL=process.argv[2]; const W=Number(process.argv[3]||390);
const chrome=spawn(CHROME,['--headless=new','--disable-gpu','--hide-scrollbars',
 `--remote-debugging-port=${PORT}`,'--user-data-dir=/tmp/cdp-profile-pb',`--window-size=${W},900`,'about:blank'],{stdio:'ignore'});
const sleep=(ms)=>new Promise(r=>setTimeout(r,ms));
async function target(){for(let i=0;i<40;i++){try{const l=await(await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();const p=l.find(t=>t.type==='page');if(p)return p;}catch(_){}await sleep(250);}throw new Error('no target');}
let id=0;function rpc(ws,m,p){return new Promise((res,rej)=>{const mid=++id;const on=(e)=>{const x=JSON.parse(e.data);if(x.id!==mid)return;ws.removeEventListener('message',on);x.error?rej(new Error(JSON.stringify(x.error))):res(x.result);};ws.addEventListener('message',on);ws.send(JSON.stringify({id:mid,method:m,params:p||{}}));});}
const t=await target();const ws=new WebSocket(t.webSocketDebuggerUrl);
await new Promise(r=>ws.addEventListener('open',r,{once:true}));
await rpc(ws,'Page.enable');await rpc(ws,'Runtime.enable');
await rpc(ws,'Emulation.setDeviceMetricsOverride',{width:W,height:900,deviceScaleFactor:1,mobile:true});
await rpc(ws,'Page.navigate',{url:URL});await sleep(2600);
const expr = `(() => {
  const out={};
  const g=document.querySelector('.tf-footer-grid');
  out.gridParents=[]; let e=g;
  while(e&&e!==document.body.parentElement){const cs=getComputedStyle(e);const b=e.getBoundingClientRect();
    out.gridParents.push(e.tagName.toLowerCase()+'.'+(e.className||'').toString().split(' ').slice(0,2).join('.')+' rect='+Math.round(b.width)+' ovf='+cs.overflowX+'/'+cs.overflowY+' pos='+cs.position+' contain='+cs.contain);
    e=e.parentElement;}
  out.scrollW0=document.documentElement.scrollWidth;
  out.innW=window.innerWidth; out.clientW=document.documentElement.clientWidth;
  out.visualW=window.visualViewport?Math.round(window.visualViewport.width):null;
  out.navW0=Math.round(document.querySelector('nav.pipellm-nav-surface').getBoundingClientRect().width);
  g.style.display='none';
  out.scrollW1=document.documentElement.scrollWidth;
  out.innW1=window.innerWidth; out.clientW1=document.documentElement.clientWidth;
  out.navW1=Math.round(document.querySelector('nav.pipellm-nav-surface').getBoundingClientRect().width);
  g.style.display='';
  return JSON.stringify(out,null,1);
})()`;
const r=await rpc(ws,'Runtime.evaluate',{returnByValue:true,expression:expr});
console.log(r.result.value);ws.close();chrome.kill();process.exit(0);
