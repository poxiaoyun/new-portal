// 页面体检：零 JS 错误、零网络失败、资源完整、四档视口无横向溢出。
// 取代了原先四个各自抄了一份 CDP 样板的脚本（qa.mjs / overflow2.mjs /
// verify3.mjs / shot.mjs）——它们查的都是同一件事的不同侧面。
//
//   python3 -m http.server 8899 &
//   node tools/qa/page.mjs http://127.0.0.1:8899/index.html
//   node tools/qa/page.mjs http://127.0.0.1:8899/index.html --shots tmp/shots
//
// 有任何一项不过就以非 0 退出，可直接当门禁用。
import { writeFileSync, mkdirSync } from 'node:fs';
import { session } from './cdp.mjs';

const URL = process.argv[2] || 'http://127.0.0.1:8899/index.html';
const shotsAt = process.argv.indexOf('--shots');
const SHOTS = shotsAt > 0 ? (process.argv[shotsAt + 1] || 'tmp/shots') : '';
const WIDTHS = [390, 768, 1024, 1440];

// 只在「没有被祖先裁掉」的元素上判溢出：很多装饰元素本来就故意比视口宽，
// 祖先的 overflow:hidden 已经把它裁掉了，报出来是噪声。
const OVERFLOW_PROBE = `(() => {
  const vw = document.documentElement.clientWidth;
  const clipped = (el) => {
    let p = el.parentElement;
    while (p) { const cs = getComputedStyle(p);
      if (cs.overflowX !== 'visible' || cs.overflow !== 'visible') return true;
      p = p.parentElement; }
    return false; };
  const out = [];
  document.querySelectorAll('body *').forEach((el) => {
    const b = el.getBoundingClientRect();
    if (b.width > vw + 1 && !clipped(el)) {
      out.push({ sel: el.tagName.toLowerCase() + '.'
        + (el.className || '').toString().split(' ').slice(0, 3).join('.'),
        w: Math.round(b.width), txt: (el.textContent || '').trim().slice(0, 40) });
    }
  });
  const seen = new Set(); const uniq = [];
  for (const o of out) { const k = o.sel + '|' + o.txt; if (!seen.has(k)) { seen.add(k); uniq.push(o); } }
  return { vw, scrollW: document.documentElement.scrollWidth, list: uniq.slice(0, 12) };
})()`;

const ASSET_PROBE = `(() => {
  const imgs = [...document.querySelectorAll('img')];
  const links = [...document.querySelectorAll('a[href]')];
  return {
    imgCount: imgs.length,
    broken: imgs.filter((i) => i.complete && i.naturalWidth === 0).map((i) => i.getAttribute('src')),
    noalt: imgs.filter((i) => !i.hasAttribute('alt')).length,
    emptyLinks: [...document.querySelectorAll('a')]
      .filter((a) => !a.textContent.trim() && !a.querySelector('svg,img')).length,
    extLinks: links.filter((a) => /^https?:/.test(a.getAttribute('href'))).length,
  };
})()`;

let failed = 0;
const check = (label, ok, detail) => {
  console.log((ok ? '  ok   ' : '  FAIL ') + label + (ok || !detail ? '' : '\n         ' + detail));
  if (!ok) failed += 1;
};

for (const width of WIDTHS) {
  // 每档宽度一套独立会话：换个视口复用同一个 profile 会让上一档的样式缓存留存
  const page = await session({
    port: 9350 + WIDTHS.indexOf(width), width, height: 900,
    profile: 'page-' + width, mobile: width < 768, url: URL,
  });
  const { errors, evaluate } = page;

  const assets = await evaluate(ASSET_PROBE);
  const overflow = await evaluate(OVERFLOW_PROBE);

  console.log(`\n== ${width}px ==`);
  check(`${width}: 无横向溢出`, overflow.scrollW <= overflow.vw + 1 && !overflow.list.length,
    `scrollW=${overflow.scrollW} vw=${overflow.vw} ${JSON.stringify(overflow.list)}`);
  check(`${width}: 无 JS 异常 / console.error`, errors.length === 0, errors.slice(0, 5).join(' | '));
  check(`${width}: 图片全部加载`, assets.broken.length === 0, assets.broken.join(', '));
  check(`${width}: 图片都有 alt`, assets.noalt === 0, `${assets.noalt} 张缺 alt`);
  check(`${width}: 无空链接`, assets.emptyLinks === 0, `${assets.emptyLinks} 个空 <a>`);

  if (SHOTS) {
    await page.reveal();                       // 滚动入场要先跑一遍，否则拍出空白
    const png = await page.screenshot();
    mkdirSync(SHOTS, { recursive: true });
    const file = `${SHOTS}/page-${width}.png`;
    writeFileSync(file, png);
    console.log(`  shot   ${file}`);
  }
  page.close();
}

console.log(failed ? `\n${failed} check(s) failed` : '\nall checks passed');
process.exit(failed ? 1 : 0);
