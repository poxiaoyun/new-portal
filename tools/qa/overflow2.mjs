import { spawn } from 'node:child_process';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9336;
const URL = process.argv[2];
const W = Number(process.argv[3] || 390);
const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars',
  `--remote-debugging-port=${PORT}`, '--user-data-dir=/tmp/cdp-profile-xiashi4',
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
await sleep(2200);
const r = await rpc(ws, 'Runtime.evaluate', { returnByValue: true, expression: `(() => {
  const vw = document.documentElement.clientWidth;
  const clipped = (el) => { let p = el.parentElement;
    while (p) { const cs = getComputedStyle(p);
      if (cs.overflowX !== 'visible' || cs.overflow !== 'visible') return true; p = p.parentElement; }
    return false; };
  const out = [];
  document.querySelectorAll('body *').forEach(el => {
    const b = el.getBoundingClientRect();
    if (b.width > vw + 1 && !clipped(el)) {
      const cs = getComputedStyle(el);
      out.push({ sel: el.tagName.toLowerCase() + '.' + (el.className||'').toString().split(' ').slice(0,3).join('.'),
        w: Math.round(b.width), left: Math.round(b.left),
        disp: cs.display, pos: cs.position, ws: cs.whiteSpace, maxw: cs.maxWidth, ovf: cs.overflowX,
        txt: (el.textContent||'').trim().slice(0,40) });
    }
  });
  // dedupe by sel+txt
  const seen = new Set(); const uniq = [];
  for (const o of out) { const k = o.sel + '|' + o.txt; if (seen.has(k)) continue; seen.add(k); uniq.push(o); }
  return JSON.stringify({ vw, scrollW: document.documentElement.scrollWidth, n: uniq.length, list: uniq.slice(0, 20) }, null, 1);
})()` });
console.log(r.result.value);
ws.close(); chrome.kill(); process.exit(0);
