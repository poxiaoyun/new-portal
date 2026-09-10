import { spawn } from 'node:child_process';
import { writeFileSync } from 'node:fs';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9343;
const URL = process.argv[2];
const OUT = process.argv[3] || 'verify';
const W = Number(process.argv[4] || 390);
const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars',
  `--remote-debugging-port=${PORT}`, '--user-data-dir=/tmp/cdp-profile-v3',
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
await rpc(ws, 'Emulation.setDeviceMetricsOverride', { width: W, height: 844, deviceScaleFactor: 1, mobile: true });
await rpc(ws, 'Page.navigate', { url: URL });
await sleep(2400);
const ev = (e) => rpc(ws, 'Runtime.evaluate', { expression: e, returnByValue: true, awaitPromise: true });
const shot = async (name, clip) => {
  const s = await rpc(ws, 'Page.captureScreenshot', { format: 'png', ...(clip ? { clip: { ...clip, scale: 1 } } : {}) });
  writeFileSync(`${OUT}/${name}.png`, Buffer.from(s.data, 'base64'));
};
const log = (m) => console.log(m);

// ---- nav scroll state
await ev(`window.scrollTo(0,400)`); await sleep(600);
log('nav scrolled class = ' + (await ev(`document.querySelector('nav.pipellm-nav-surface').className.includes('is-scrolled')`)).result.value);
await ev(`window.scrollTo(0,0)`); await sleep(400);

// ---- mobile drawer
const openState = await ev(`(() => {
  const b = document.querySelector('nav button');
  if (!b) return 'no-burger';
  b.click();
  const hidden = [...document.querySelectorAll('a')].filter(a => a.closest('nav') && a.getBoundingClientRect().height > 0);
  return 'clicked links=' + hidden.length; })()`);
log('drawer: ' + openState.result.value);
await sleep(700);
await shot('v3-drawer-open');
const bodyLock = await ev(`JSON.stringify({ overflow: getComputedStyle(document.body).overflow, drawerH: (() => { const d=[...document.querySelectorAll('div')].find(x=>x.getBoundingClientRect().height>500 && getComputedStyle(x).position==='fixed'); return d? Math.round(d.getBoundingClientRect().height) : 0 })() })`);
log('drawer metrics = ' + bodyLock.result.value);
log('drawer links = ' + (await ev(`[...document.querySelectorAll('nav a')].filter(a=>a.getBoundingClientRect().height>0 && a.closest('nav')).length`)).result.value);
ws.close(); chrome.kill(); process.exit(0);
