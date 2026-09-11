// Regression guard for the four-board homepage reshape (see tools/reshape_home.py).
//
//   python3 -m http.server 8899 &
//   node tools/qa/reshape.mjs http://127.0.0.1:8899/index.html
//
// Asserts the story structure that reshape_home.py establishes, so a later
// hand-edit or a re-run of build.py cannot silently drop a board again.
import { spawn } from 'node:child_process';

const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const PORT = 9346;
const URL = process.argv[2] || 'http://127.0.0.1:8899/index.html';
const W = Number(process.argv[3] || 1440);

const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars',
  `--remote-debugging-port=${PORT}`, '--user-data-dir=/tmp/cdp-profile-reshape',
  `--window-size=${W},900`, 'about:blank'], { stdio: 'ignore' });
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function target() {
  for (let i = 0; i < 40; i++) {
    try { const l = await (await fetch(`http://127.0.0.1:${PORT}/json/list`)).json();
      const p = l.find((t) => t.type === 'page'); if (p) return p; } catch (_) { /* retry */ }
    await sleep(250);
  }
  throw new Error('no target');
}
let id = 0;
function rpc(ws, m, p) {
  return new Promise((res, rej) => { const mid = ++id;
    const on = (e) => { const x = JSON.parse(e.data); if (x.id !== mid) return;
      ws.removeEventListener('message', on);
      x.error ? rej(new Error(JSON.stringify(x.error))) : res(x.result); };
    ws.addEventListener('message', on);
    ws.send(JSON.stringify({ id: mid, method: m, params: p || {} })); });
}
const t = await target();
const ws = new WebSocket(t.webSocketDebuggerUrl);
await new Promise((r) => ws.addEventListener('open', r, { once: true }));
const errors = [];
ws.addEventListener('message', (e) => { const x = JSON.parse(e.data);
  if (x.method === 'Runtime.exceptionThrown') errors.push('EXCEPTION ' + (x.params.exceptionDetails.text || ''));
  if (x.method === 'Runtime.consoleAPICalled' && x.params.type === 'error')
    errors.push('console.error ' + x.params.args.map((a) => a.value || a.description || '').join(' ').slice(0, 160));
});
await rpc(ws, 'Page.enable'); await rpc(ws, 'Runtime.enable');
await rpc(ws, 'Emulation.setDeviceMetricsOverride', { width: W, height: 900, deviceScaleFactor: 1, mobile: false });
await rpc(ws, 'Page.navigate', { url: URL });
// Wait for hydration: the reshape markers are the last thing the page builds,
// and a plain sleep races the load on a cold profile.
for (let i = 0; i < 40; i++) {
  await sleep(300);
  const r = await rpc(ws, 'Runtime.evaluate', { returnByValue: true,
    expression: `!!document.querySelector('#harness .tf-harness-flow-step')` });
  if (r.result && r.result.value) break;
}

const probe = `(() => {
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const one = (s) => clean((document.querySelector(s) || {}).textContent);
  return {
    title: document.title,
    heroTitle: one('#home h1'),
    heroSubtitle: one('#home h1 + p'),
    heroOverline: one('#home .tf-overline'),
    heroOrb: !!document.querySelector('#home .tf-overline-live .tf-thinking'),
    heroOrbSpin: (() => {
      const e = document.querySelector('#home .tf-thinking-spin');
      return e ? getComputedStyle(e).animationName : '';
    })(),
    heroOrbCore: (() => {
      const e = document.querySelector('#home .tf-thinking-core');
      return e ? getComputedStyle(e).animationName : '';
    })(),
    heroOrbTriangle: (() => {
      const e = document.querySelector('#home .tf-overline-live');
      return e ? getComputedStyle(e, '::before').display : '';
    })(),
    heroPills: $$('#home .tf-pill').map((e) => clean(e.textContent)),
    navTitles: $$('.tf-nav-dropdown-item .tf-nav-dropdown-title').map((e) => clean(e.textContent)),
    tabs: $$('.tf-control-stage-nav button').map((b) => clean(b.textContent)),
    lanes: $$('.tf-control-plane-body .tf-control-lane')
      .map((e) => (e.className.match(/tf-control-(runtime|audit|airouter|boss)/) || [])[1]),
    harnessChips: $$('.tf-control-harness-chips > *').map((e) => clean(e.textContent)),
    gatewayCards: $$('#gateway .tf-advantage-card').length,
    airouterEyebrow: one('#tools .tf-block-overline'),
    bossEyebrow: one('#boss .tf-overline'),
    bossMetrics: $$('#boss .tf-boss-metric').length,
    bossRows: $$('#boss .tf-boss-row:not(.is-head)').length,
    bossBars: $$('#boss .tf-boss-bars > *').length,
    bossSteps: $$('#boss .tf-gateway-capabilities h3').map((e) => clean(e.textContent)),
    harnessEyebrow: one('#harness .tf-overline'),
    harnessPhases: $$('#harness .tf-harness-phase h3').map((e) => clean(e.textContent)),
    harnessFlow: $$('#harness .tf-harness-flow-step strong')
      .map((e) => clean(e.textContent)),
    pricingNames: $$('.tf-home-pricing-item h3').map((e) => clean(e.textContent)),
    faqCount: $$('.tf-faq-list article').length,
    footerProducts: $$('footer a').map((a) => clean(a.textContent))
      .filter((x) => /^(产品总览|Rune 智算|Moha 资产|AIRouter 网关|BOSS 运营|XCMP 云管理|KubeGems)$/.test(x)),
    ids: $$('section[id]').map((e) => e.id),
    docW: document.documentElement.scrollWidth,
    innerW: window.innerWidth,
    leftover: ['PipeLLM', 'pipellm.ai', 'AI Router', 'ChatBox', 'XMCP']
      .filter((k) => document.body.innerText.includes(k)),
  };
})()`;
const evaluated = await rpc(ws, 'Runtime.evaluate', { expression: probe, returnByValue: true });
ws.close(); chrome.kill();
if (!evaluated.result || !evaluated.result.value) {
  console.error('probe failed:', JSON.stringify(evaluated, null, 1).slice(0, 800));
  process.exit(1);
}
const v = evaluated.result.value;

const eq = (label, got, want) => {
  const ok = JSON.stringify(got) === JSON.stringify(want);
  console.log((ok ? '  ok   ' : '  FAIL ') + label + (ok ? '' : `\n         got  ${JSON.stringify(got)}\n         want ${JSON.stringify(want)}`));
  return ok;
};
const has = (label, got, needle) => {
  const ok = got.includes(needle);
  console.log((ok ? '  ok   ' : '  FAIL ') + label + (ok ? '' : `  (missing ${JSON.stringify(needle)})`));
  return ok;
};
const results = [
  eq('four boards in the product dropdown', v.navTitles.slice(0, 4), ['Rune', 'Moha', 'AIRouter', 'BOSS']),
  eq('hero slogan stays as authored upstream', v.heroTitle, '智算为中心的 AI 原生云内核'),
  eq('hero subtitle stays as authored upstream', v.heroSubtitle,
    '专注云原生开源、混合云与 AI 智算平台，为企业提供覆盖容器云、混合云、智算云及 AI 能力的全栈解决方案。'),
  eq('hero overline teases Rune Harness', v.heroOverline, 'Rune Harness 即将开放'),
  eq('overline carries the animated SVG mark', v.heroOrb, true),
  eq('orb arc is animated', v.heroOrbSpin.includes('tf-thinking-spin'), true),
  eq('orb core is animated', v.heroOrbCore.includes('tf-thinking-breathe'), true),
  eq('static play triangle is suppressed', v.heroOrbTriangle, 'none'),
  eq('hero pills list the four boards', v.heroPills, ['Rune 智算', 'Moha 资产', 'AIRouter 网关', 'BOSS 运营']),
  has('document title sells Rune Harness', v.title, 'Rune Harness 云智算内核'),
  eq('control plane exposes four tabs', v.tabs, ['01Rune', '02Moha', '03AIRouter', '04BOSS']),
  eq('control plane exposes four lanes', v.lanes, ['runtime', 'audit', 'airouter', 'boss']),
  eq('harness band lists its four claims', v.harnessChips,
    ['统一会话', '双安全域', 'Plan → Approval → Apply', '执行可追溯']),
  eq('XCMP stays a capability band', v.gatewayCards, 6),
  has('AIRouter section is labelled as board 03', v.airouterEyebrow, 'AIRouter 网关 · 板块 03'),
  has('BOSS section is labelled as board 04', v.bossEyebrow, 'BOSS 运营 · 板块 04'),
  eq('BOSS panel shows four metrics', v.bossMetrics, 4),
  eq('BOSS panel lists six tenants', v.bossRows, 6),
  eq('BOSS panel charts eight periods', v.bossBars, 8),
  eq('BOSS names its three operating steps', v.bossSteps, ['开户与授权', '配额与调度', '计量与出账']),
  has('harness section is flagged as a plan', v.harnessEyebrow, '规划中'),
  eq('harness plans three phases', v.harnessPhases,
    ['阶段一 · 统一操作入口', '阶段二 · 双安全域隔离', '阶段三 · 云智算内核']),
  eq('harness flow runs the five-step chain', v.harnessFlow,
    ['ActionManifest', 'ChangeSet', 'Approval', 'Apply', 'ExecutionReceipt']),
  eq('pricing covers the four boards', v.pricingNames, ['Rune', 'Moha', 'AIRouter', 'BOSS']),
  eq('FAQ carries nine entries', v.faqCount, 9),
  eq('footer product column is complete', v.footerProducts,
    ['产品总览', 'Rune 智算', 'Moha 资产', 'AIRouter 网关', 'BOSS 运营', 'XCMP 云管理', 'KubeGems']),
  eq('section order is stable', v.ids,
    ['home', 'gateway', 'runtime', 'audit', 'tools', 'boss', 'harness', 'pricing', 'blog', 'faq']),
  eq('no rebrand leftovers', v.leftover, []),
  eq('no horizontal overflow', v.docW <= v.innerW, true),
  eq('no runtime errors', errors, []),
];
const failed = results.filter((r) => !r).length;
console.log(`\n${failed === 0 ? 'PASS' : 'FAIL'} — ${results.length - failed}/${results.length} checks`);
process.exit(failed === 0 ? 0 : 1);
