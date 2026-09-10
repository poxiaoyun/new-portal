// Interaction assertions + targeted screenshots.
import { spawn } from 'node:child_process';
import fs from 'node:fs';

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9334;
const URL = process.argv[2];
const OUTDIR = process.argv[3] || '.';
const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars',
  `--remote-debugging-port=${PORT}`, '--user-data-dir=/tmp/cdp-profile-xiashi2',
  '--window-size=1440,1000', 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

async function target() {
  for (let i = 0; i < 40; i++) {
    try {
      const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const p = l.find((t) => t.type === 'page');
      if (p) return p;
    } catch (_) {}
    await sleep(250);
  }
  throw new Error('no target');
}
let id = 0;
function rpc(ws, method, params) {
  return new Promise((res, rej) => {
    const mid = ++id;
    const on = (ev) => { const m = JSON.parse(ev.data); if (m.id !== mid) return;
      ws.removeEventListener('message', on); m.error ? rej(new Error(JSON.stringify(m.error))) : res(m.result); };
    ws.addEventListener('message', on);
    ws.send(JSON.stringify({ id: mid, method, params: params || {} }));
  });
}
const t = await target();
const ws = new WebSocket(t.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
await rpc(ws, 'Page.enable'); await rpc(ws, 'Runtime.enable');
await rpc(ws, 'Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
await rpc(ws, 'Page.navigate', { url: URL });
await sleep(2200);
const evalx = async (e) => {
  const r = await rpc(ws, 'Runtime.evaluate', { expression: e, awaitPromise: true, returnByValue: true });
  if (r.exceptionDetails) throw new Error(JSON.stringify(r.exceptionDetails).slice(0, 500));
  return r.result.value;
};
const shot = async (n) => {
  const r = await rpc(ws, 'Page.captureScreenshot', { format: 'png' });
  fs.writeFileSync(`${OUTDIR}/${n}.png`, Buffer.from(r.data, 'base64'));
};

const checks = [];
async function check(name, expr, expect) {
  const v = await evalx(expr);
  checks.push({ name, value: v, ok: expect === undefined ? undefined : String(v) === String(expect) });
}

await check('control tab 3 -> lane', `(() => {
  document.querySelectorAll('.tf-control-stage-nav button')[2].click();
  return document.querySelector('.tf-control-audit').classList.contains('is-active');
})()`, true);
await check('control tab 3 -> heading', `document.querySelector('.tf-control-gateway-heading h3').textContent`, 'Moha');
await check('control tab 3 -> url', `document.querySelector('.tf-control-request-row p').textContent`, 'https://api.poxiaoshi.cn/assets');
await evalx(`document.querySelectorAll('.tf-control-stage-nav button')[0].click(); 1`);
await check('control tab 1 -> code', `document.querySelector('.tf-control-code-surface pre code').textContent.includes('rune.submit')`, true);
await check('control tab 1 -> result', `document.querySelector('.tf-control-plane-result p').textContent.trim()`, '✓ 训练任务已调度');

await check('router tab 4 -> vision url', `(() => {
  document.querySelectorAll('.tf-managed-api-tabs button')[3].click();
  return document.querySelector('.tf-managed-api-code-panel pre code').textContent.includes('/v1/vision');
})()`, true);

await check('gateway tab 4 -> 华为云', `(() => {
  document.querySelectorAll('.tf-gateway-sdk-tabs button')[3].click();
  return document.querySelector('.tf-gateway-decision span b').nextSibling.textContent;
})()`, '华为云');
await check('gateway line numbers', `document.querySelector('.tf-gateway-code div.grid').firstElementChild.children.length`, 5);

await check('runtime tab 2 -> yaml', `(() => {
  document.querySelectorAll('.tf-runtime-session-tabs button')[1].click();
  return document.querySelector('#runtime code.tf-syntax-code').textContent.includes('TrainingJob');
})()`, true);

await check('faq toggle', `(() => {
  const a = document.querySelectorAll('.tf-faq-list article')[2];
  a.querySelector('.tf-faq-question-row').click();
  return a.classList.contains('is-open') + '/' + a.querySelector('.tf-faq-action-icon img').classList.contains('is-open');
})()`, 'true/true');

// pixel comparisons
await evalx(`document.querySelector('#gateway').scrollIntoView({block:'start'}); 1`);
await sleep(900); await shot('v2-gateway');
await evalx(`document.querySelectorAll('.tf-control-stage-nav button')[0].click();
  document.querySelector('.tf-runtime-showcase').scrollIntoView({block:'start'}); 1`);
await sleep(900); await shot('v2-control-rune');

console.log(checks.map((c) => `${c.ok === false ? 'FAIL' : 'ok  '} ${c.name} = ${JSON.stringify(c.value)}`).join('\n'));
ws.close(); chrome.kill(); process.exit(0);
