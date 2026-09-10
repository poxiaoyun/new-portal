import { spawn } from 'node:child_process';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9337;
const URL = process.argv[2];
const W = Number(process.argv[3] || 390);
const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars',
  `--remote-debugging-port=${PORT}`, '--user-data-dir=/tmp/cdp-profile-cmp',
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
  const pick = (el) => { if (!el) return null; const cs = getComputedStyle(el); const b = el.getBoundingClientRect();
    return { w: Math.round(b.width), h: Math.round(b.height), fs: cs.fontSize, lh: cs.lineHeight,
             ovf: cs.overflowX, ws: cs.whiteSpace, pos: cs.position, disp: cs.display, maxw: cs.maxWidth }; };
  const q = (s) => document.querySelector(s);
  const res = { vw: document.documentElement.clientWidth, scrollW: document.documentElement.scrollWidth };
  res.footer = pick(q('footer.tf-reference-footer'));
  res.fg = pick(q('.tf-footer-grid'));
  res.hero = pick(q('h1'));
  res.ann = pick(q('.tf-announcement-bar'));
  res.anntrack = pick(q('.tf-announcement-track'));
  res.shell = pick(q('main'));
  const wide = [];
  document.querySelectorAll('body *').forEach(el => {
    const b = el.getBoundingClientRect();
    if (b.width > res.vw + 1) wide.push(el.tagName.toLowerCase()+'.'+(el.className||'').toString().split(' ').slice(0,2).join('.')+'='+Math.round(b.width));
  });
  res.wideCount = wide.length; res.wide = wide.slice(0, 12);
  return JSON.stringify(res, null, 1);
})()` });
console.log(r.result.value);
ws.close(); chrome.kill(); process.exit(0);
