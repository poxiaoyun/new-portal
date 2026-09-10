import { spawn } from 'node:child_process';
import { writeFileSync, mkdirSync } from 'node:fs';
const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9342;
const URL = process.argv[2];
const OUT = process.argv[3];
const W = Number(process.argv[4] || 390);
const TALL = Number(process.argv[5] || 900);
if (OUT.includes('/')) mkdirSync(OUT.replace(/\/[^/]+$/, ''), { recursive: true });
const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu',
  `--remote-debugging-port=${PORT}`, '--user-data-dir=/tmp/cdp-profile-shot',
  `--window-size=${W},${TALL}`, 'about:blank'], { stdio: 'ignore' });
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
await rpc(ws, 'Emulation.setDeviceMetricsOverride', { width: W, height: TALL, deviceScaleFactor: 1, mobile: true });
await rpc(ws, 'Page.navigate', { url: URL });
await sleep(2600);
// walk the page to fire IntersectionObserver reveals, then settle at the top
await rpc(ws, 'Runtime.evaluate', { expression: `(async () => {
  const H = document.body.scrollHeight;
  for (let y = 0; y < H; y += 700) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 130)); }
  window.scrollTo(0, H); await new Promise(r => setTimeout(r, 500));
  document.querySelectorAll('.tf-motion-section').forEach(el => el.classList.add('is-motion-visible'));
  window.scrollTo(0, 0);
})()`, awaitPromise: true, returnByValue: true });
await sleep(1500);
const m = await rpc(ws, 'Page.getLayoutMetrics');
const h = Math.ceil(m.cssContentSize.height || m.contentSize.height);
const shot = await rpc(ws, 'Page.captureScreenshot', {
  format: 'png', captureBeyondViewport: true,
  clip: { x: 0, y: 0, width: W, height: Math.min(h, 30000), scale: 1 } });
writeFileSync(OUT, Buffer.from(shot.data, 'base64'));
console.log('saved', OUT, W + 'x' + h, 'cssW', m.cssContentSize.width);
ws.close(); chrome.kill(); process.exit(0);
