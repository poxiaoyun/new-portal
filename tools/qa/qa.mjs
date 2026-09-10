import { spawn } from 'node:child_process';
const CHROME='/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT=9344; const URL=process.argv[2];
const chrome=spawn(CHROME,['--headless=new','--disable-gpu','--hide-scrollbars',
 `--remote-debugging-port=${PORT}`,'--user-data-dir=/tmp/cdp-profile-qa','--window-size=1440,900','about:blank'],{stdio:'ignore'});
const sleep=(ms)=>new Promise(r=>setTimeout(r,ms));
async function target(){for(let i=0;i<40;i++){try{const l=await(await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();const p=l.find(t=>t.type==='page');if(p)return p;}catch(_){}await sleep(250);}throw new Error('no target');}
let id=0;const events=[];
function rpc(ws,m,p){return new Promise((res,rej)=>{const mid=++id;const on=(e)=>{const x=JSON.parse(e.data);if(x.id!==mid)return;ws.removeEventListener('message',on);x.error?rej(new Error(JSON.stringify(x.error))):res(x.result);};ws.addEventListener('message',on);ws.send(JSON.stringify({id:mid,method:m,params:p||{}}));});}
const t=await target();const ws=new WebSocket(t.webSocketDebuggerUrl);
await new Promise(r=>ws.addEventListener('open',r,{once:true}));
ws.addEventListener('message',e=>{const x=JSON.parse(e.data);
  if(x.method==='Runtime.exceptionThrown') events.push('EXCEPTION '+JSON.stringify(x.params.exceptionDetails.exception&&x.params.exceptionDetails.exception.description||x.params.exceptionDetails.text));
  if(x.method==='Runtime.consoleAPICalled'&&['error','warning'].includes(x.params.type)) events.push(x.params.type.toUpperCase()+' '+x.params.args.map(a=>a.value||a.description||'').join(' ').slice(0,200));
  if(x.method==='Log.entryAdded'&&x.params.entry.level==='error') events.push('LOG '+x.params.entry.text.slice(0,200));
});
await rpc(ws,'Page.enable');await rpc(ws,'Runtime.enable');await rpc(ws,'Log.enable');await rpc(ws,'Network.enable');
const fails=[];
ws.addEventListener('message',e=>{const x=JSON.parse(e.data);
  if(x.method==='Network.loadingFailed') fails.push(x.params.errorText+' '+(x.params.type||''));
  if(x.method==='Network.responseReceived'&&x.params.response.status>=400) fails.push('HTTP '+x.params.response.status+' '+x.params.response.url);
});
await rpc(ws,'Page.navigate',{url:URL});await sleep(3000);
const r=await rpc(ws,'Runtime.evaluate',{returnByValue:true,expression:`(() => {
  const imgs=[...document.querySelectorAll('img')];
  const broken=imgs.filter(i=>i.complete && i.naturalWidth===0).map(i=>i.getAttribute('src'));
  const noalt=imgs.filter(i=>!i.hasAttribute('alt')).length;
  const links=[...document.querySelectorAll('a[href]')].map(a=>a.getAttribute('href'));
  const ext=links.filter(h=>/^https?:/.test(h));
  const empty=[...document.querySelectorAll('a')].filter(a=>!a.textContent.trim() && !a.querySelector('svg,img')).length;
  const res=performance.getEntriesByType('resource');
  const slow=res.filter(x=>x.duration>400).map(x=>Math.round(x.duration)+'ms '+x.name.split('/').pop());
  return JSON.stringify({imgCount:imgs.length,broken,noalt,linkCount:links.length,extLinks:ext.length,
    emptyLinks:empty, resources:res.length, slow,
    title:document.title, h1:document.querySelector('h1')?document.querySelector('h1').textContent.trim():null},null,1);
})()`});
console.log(r.result.value);
console.log('--- console/exceptions ---'); console.log(events.slice(0,20).join('\n')||'(none)');
console.log('--- network failures ---'); console.log([...new Set(fails)].slice(0,20).join('\n')||'(none)');
ws.close();chrome.kill();process.exit(0);
