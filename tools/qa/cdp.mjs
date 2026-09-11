// 共享的 headless-Chrome 会话（CDP）。
//
// tools/qa 下的脚本原本各自抄了一份「spawn Chrome → 轮询 /json/list 找 target →
// 连 WebSocket → 手写 rpc」，十份样板各有各的端口和 user-data-dir；改一次启动
// 参数要改十处，删一个脚本又留下没人用的 profile 目录。这里把那段样板收成
// 一个 `session()`，脚本只保留自己的断言。
//
//   import { session } from './cdp.mjs';
//   const page = await session({ port: 9346, url, waitFor: '#tools' });
//   const v = await page.evaluate('document.title');
//   page.close();
//
// 端口按脚本分配（不冲突即可），profile 名会展开成 /tmp/cdp-profile-<name>。
import { spawn } from 'node:child_process';

export const CHROME = '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
export const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

/**
 * 起一个单页 Chrome 会话并导航到 `url`。
 *
 * @param {object}  o
 * @param {number}  o.port      远程调试端口（每个脚本自选，避免与并行的脚本撞车）
 * @param {string}  o.url       要打开的页面
 * @param {number} [o.width]    视口宽（默认 1440）
 * @param {number} [o.height]   视口高（默认 900）
 * @param {string} [o.profile]  user-data-dir 名（默认 'qa'；传绝对路径则原样使用）
 * @param {boolean}[o.mobile]   是否按移动设备模拟（默认 false）
 * @param {string} [o.waitFor]  导航后轮询等待的选择器；不传则只等固定时长
 * @returns {Promise<object>} { ws, rpc, evaluate, errors, layout, reveal, screenshot, close }
 */
export async function session({ port, url, width = 1440, height = 900,
                               profile = 'qa', mobile = false, waitFor = '' }) {
  const dir = profile.startsWith('/') ? profile : '/tmp/cdp-profile-' + profile;
  const chrome = spawn(CHROME, ['--headless=new', '--disable-gpu', '--hide-scrollbars',
    `--remote-debugging-port=${port}`, `--user-data-dir=${dir}`,
    `--window-size=${width},${height}`, 'about:blank'], { stdio: 'ignore' });

  let id = 0;
  const rpc = (ws, method, params) => new Promise((res, rej) => {
    const mid = ++id;
    const on = (e) => {
      const x = JSON.parse(e.data);
      if (x.id !== mid) return;
      ws.removeEventListener('message', on);
      x.error ? rej(new Error(JSON.stringify(x.error))) : res(x.result);
    };
    ws.addEventListener('message', on);
    ws.send(JSON.stringify({ id: mid, method, params: params || {} }));
  });

  // 冷启动的 profile 里 /json/list 要几百毫秒才出现，且偶发 5xx，所以重试
  let target = null;
  for (let i = 0; i < 40 && !target; i++) {
    try {
      const list = await (await fetch(`http://127.0.0.1:${port}/json/list`)).json();
      target = list.find((t) => t.type === 'page') || null;
    } catch (_) { /* retry */ }
    if (!target) await sleep(250);
  }
  if (!target) { chrome.kill(); throw new Error('no CDP target on :' + port); }

  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise((r) => ws.addEventListener('open', r, { once: true }));

  // 页面自己抛的异常与控制台 error 全程收集，脚本用 errors 数组断言「零错误」
  const errors = [];
  ws.addEventListener('message', (e) => {
    const x = JSON.parse(e.data);
    if (x.method === 'Runtime.exceptionThrown')
      errors.push('EXCEPTION ' + (x.params.exceptionDetails.text || ''));
    if (x.method === 'Runtime.consoleAPICalled' && x.params.type === 'error')
      errors.push('console.error ' + x.params.args
        .map((a) => a.value || a.description || '').join(' ').slice(0, 160));
  });

  const send = (method, params) => rpc(ws, method, params || {});
  await send('Page.enable');
  await send('Runtime.enable');
  await send('Emulation.setDeviceMetricsOverride',
    { width, height, deviceScaleFactor: 1, mobile });
  await send('Page.navigate', { url });

  const evaluate = async (expression, { awaitPromise = false } = {}) => {
    const r = await send('Runtime.evaluate', { expression, returnByValue: true, awaitPromise });
    if (r.exceptionDetails) throw new Error('evaluate threw: ' + r.exceptionDetails.text);
    return r.result ? r.result.value : undefined;
  };

  if (waitFor) {
    // 水合是异步的：页面构建完最后一个标记才算可用，纯 sleep 在冷 profile 上会赛跑
    for (let i = 0; i < 40; i++) {
      await sleep(300);
      if (await evaluate(`!!document.querySelector(${JSON.stringify(waitFor)})`)) break;
    }
  } else {
    await sleep(600);
  }

  const layout = async () => {
    const m = await send('Page.getLayoutMetrics');
    return { width: Math.ceil(m.cssContentSize.width || m.contentSize.width),
             height: Math.ceil(m.cssContentSize.height || m.contentSize.height) };
  };

  // 截图前必须把整页滚一遍：滚动入场（IntersectionObserver）不会自己触发，
  // 冻结在首屏会拍出大片空白。同时兜底给 .tf-motion-section 加上可见类。
  const reveal = async () => {
    await evaluate(`(async () => {
      const H = document.body.scrollHeight;
      for (let y = 0; y < H; y += 700) { window.scrollTo(0, y); await new Promise(r => setTimeout(r, 130)); }
      window.scrollTo(0, H); await new Promise(r => setTimeout(r, 500));
      document.querySelectorAll('.tf-motion-section').forEach(el => el.classList.add('is-motion-visible'));
      window.scrollTo(0, 0);
    })()`, { awaitPromise: true });
    await sleep(1500);
  };

  const screenshot = async () => {
    const { width, height } = await layout();
    const shot = await send('Page.captureScreenshot', {
      format: 'png', captureBeyondViewport: true,
      clip: { x: 0, y: 0, width, height: Math.min(height, 30000), scale: 1 } });
    return Buffer.from(shot.data, 'base64');
  };

  const close = () => { try { ws.close(); } catch (_) { /* already closed */ } chrome.kill(); };

  return { ws, rpc: send, evaluate, errors, layout, reveal, screenshot, close, chrome };
}
