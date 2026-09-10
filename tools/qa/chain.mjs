import { spawn } from 'node:child_process';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9338;
const URL = process.argv[2];
const W = Number(process.argv[3] || 390);
const SEL = process.argv[4] || 'aside.tf-announcement-bar';
const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars',
  `--remote-debugging-port=${PORT}`, '--user-data-dir=/tmp/cdp-profile-chain',
  `--window-size=${W},900`, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function target() {
  for (let i = 0; i < 40; i++) {
    try { const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const p = l.find((t) => t.type === 'page'); if (p) return p; } catch (_) {}
    await sleep(250);
  }
  throw new Error('no target');
}
let id = 0;
function rpc(ws, m, p) {
  return new Promise((res, rej) => { const mid = ++id;
    const on = (e) => { const x = JSON.parse(e.data); if (x.id !== mid) return;
      ws.removeEventListener('message', on); x.error ? rej(new Error(JSON.stringify(x.error))) : res(x.result); };
    ws.addEventListener('message', on); ws.send(JSON.stringify({ id: mid, method: m, params: p || {} })); });
}
const t = await target();
const ws = new WebSocket(t.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
await rpc(ws, 'Page.enable'); await rpc(ws, 'Runtime.enable');
await rpc(ws, 'Emulation.setDeviceMetricsOverride', { width: W, height: 900, deviceScaleFactor: 1, mobile: true });
await rpc(ws, 'Page.navigate', { url: URL });
await sleep(2600);
const r = await rpc(ws, 'Runtime.evaluate', { returnByValue: true, expression: `(() => {
  const el0 = document.querySelector(${JSON.stringify(SEL)});
  const lines = [];
  let el = el0;
  while (el && el !== document.documentElement.parentElement) {
    const cs = getComputedStyle(el); const b = el.getBoundingClientRect();
    lines.push([el.tagName.toLowerCase()+'.'+(el.className||'').toString().split(' ').slice(0,3).join('.'),
      'rect='+Math.round(b.width)+' client='+el.clientWidth+' scroll='+el.scrollWidth,
      'w='+cs.width+' minW='+cs.minWidth+' maxW='+cs.maxWidth+' ovfX='+cs.overflowX+' pos='+cs.position+' disp='+cs.display+' flex='+cs.flex].join(' | '));
    el = el.parentElement;
  }
  // also: widest descendants of el0
  const wide = [];
  if (el0) el0.querySelectorAll('*').forEach(x => { const b = x.getBoundingClientRect();
    if (b.width > 60) wide.push(x.tagName.toLowerCase()+'.'+(x.className||'').toString().split(' ').slice(0,2).join('.')+'='+Math.round(b.width)+'@'+Math.round(b.left)+' ovfX='+getComputedStyle(x).overflowX); });
  return JSON.stringify({ chain: lines, wide: wide.slice(0, 14) }, null, 1);
})()` });
console.log(r.result.value);
ws.close(); chrome.kill(); process.exit(0);
