// Regression guard for the four-board homepage reshape (see tools/reshape_home.py).
//
//   python3 -m http.server 8899 &
//   node tools/qa/reshape.mjs http://127.0.0.1:8899/index.html
//
// Asserts the story structure that reshape_home.py establishes, so a later
// hand-edit or a generator re-run cannot silently drop a board again.
import { readFileSync } from 'node:fs';
import { session } from './cdp.mjs';

const URL = process.argv[2] || 'http://127.0.0.1:8899/index.html';
const W = Number(process.argv[3] || 1440);

const page = await session({
  port: 9346, width: W, profile: 'reshape', url: URL,
  // 等水合：reshape 的标记是页面最后构建出来的，冷 profile 上纯 sleep 会赛跑。
  // 这个选择器必须指向**始终存在**的板块 —— 它曾指向 #harness，板块删掉后
  // 不会报错，只是每次静默跑满 40 轮重试。
  waitFor: '#tools .tf-section-sidebar',
});
const { errors } = page;

const probe = `(() => {
  const $$ = (s) => Array.from(document.querySelectorAll(s));
  const clean = (s) => (s || '').replace(/\\s+/g, ' ').trim();
  const one = (s) => clean((document.querySelector(s) || {}).textContent);
  return {
    title: document.title,
    heroTitle: one('#home h1'),
    heroSubtitle: one('#home h1 + p'),
    heroOverline: one('#home .tf-overline'),
    // the thinking orb is a chat-avatar-only mark now: the overline is a plain
    // text pill, and exactly one `.tf-thinking` should exist on the page
    heroOrb: $$('#home .tf-overline-live .tf-thinking').length,
    heroOrbSpin: (() => {
      const e = document.querySelector('#home .tf-thinking-spin');
      return e ? getComputedStyle(e).animationName : '';
    })(),
    heroOrbCore: (() => {
      const e = document.querySelector('#home .tf-thinking-core');
      return e ? getComputedStyle(e).animationName : '';
    })(),
    heroOrbCount: $$('#home .tf-thinking').length,
    heroOrbTriangle: (() => {
      const e = document.querySelector('#home .tf-overline-live');
      return e ? getComputedStyle(e, '::before').display : '';
    })(),
    heroPills: $$('#home .tf-pill').map((e) => clean(e.textContent)),
    terminalTitles: $$('#home .tf-terminal-bar > p').map((e) => clean(e.textContent)),
    chatUser: one('#home .tf-chat-user .tf-chat-bubble'),
    // 正在思考 and 已处理 are stacked in one grid cell and cross-faded, so probe
    // the two state spans rather than the container's textContent
    chatStates: $$('#home .tf-chat-ai .tf-chat-label .tf-chat-state').map((e) => clean(e.textContent)),
    chatStateTimeline: $$('#home .tf-chat-ai .tf-chat-label .tf-chat-state').map((e) => {
      const cs = getComputedStyle(e);
      return cs.animationName + '/' + cs.animationDuration;
    }),
    chatDots: $$('#home .tf-chat-dots i').length,
    chatDotsTimeline: (() => {
      const e = document.querySelector('#home .tf-chat-dots');
      if (!e) return '';
      const cs = getComputedStyle(e);
      return cs.animationName + '/' + cs.animationDuration;
    })(),
    chatAvatarOrb: !!document.querySelector('#home .tf-chat-avatar .tf-thinking'),
    chatDone: one('#home .tf-chat-done'),
    chatDoneColor: (() => {
      const e = document.querySelector('#home .tf-chat-done');
      return e ? getComputedStyle(e).color : '';
    })(),
    // every row rides the same 9.6s cycle; the per-row offset lives in the
    // keyframes, so equal durations + distinct animation names is the signature
    chatTimeline: ['user', 'ai', 'done'].map((row) => {
      const e = document.querySelector('#home .tf-chat-' + row);
      if (!e) return '';
      const cs = getComputedStyle(e);
      return cs.animationName + '/' + cs.animationDuration;
    }),
    navTitles: $$('.tf-nav-dropdown-item .tf-nav-dropdown-title').map((e) => clean(e.textContent)),
    // 「关于我们」下拉单列一份：2026-09-11 调整过（开源项目改指站外、加入我们移除），
    // 见 reshape_home.py 的 stage_nav_company。带上 target 是为了同时断「站外开新窗」
    companyNav: $$('.tf-nav-company-dropdown .tf-nav-dropdown-item').map((e) => {
      const t = e.querySelector('.tf-nav-dropdown-title');
      return {
        title: t ? clean(t.textContent) : '',
        href: e.getAttribute('href'),
        blank: e.getAttribute('target') === '_blank',
      };
    }),
    // 顶层菜单项（.tf-nav-menu-link）：2026-09-11「解决方案」改指演示站，见
    // reshape_home.py 的 stage_nav_menu。注意三点：
    //   * 这个类在 <a> 与 <button>（产品/关于我们两个下拉 trigger）上都用，
    //     button 没有 href，取到 null 是正常的；
    //   * 标签外面套着 tf-scramble-label 的三重 span（measure / live / sr-only
    //     各存一份同样的文案），直接 textContent 会得到「解决方案解决方案解决
    //     方案」，所以只取 measure 那一层；
    //   * 移动抽屉那一份没有这个类 —— 抽屉侧由 Python 守卫的计数咬住
    //     （两处必须同时改，只改看得见的那份是踩过的坑）。
    navMenu: $$('.tf-nav-menu-link').map((e) => ({
      title: clean((e.querySelector('.tf-scramble-measure') || e).textContent),
      href: e.getAttribute('href'),
    })),
    // the nav brand is a single <img>; its wordmark is painted inside the SVG,
    // so the DOM can only confirm which asset is mounted and what it announces
    navLogo: (() => {
      const e = document.querySelector('.tf-nav-frame img[src$="logo.svg"]');
      return e ? { src: e.getAttribute('src'), alt: e.getAttribute('alt') } : null;
    })(),
    // vendor.css zeroes the svg stroke in the 产品 dropdown because the upstream
    // entries carried filled icons; the four boards ship lucide stroke icons, so
    // without the custom.css override every row renders blank beside its title
    navDropdownIconStrokes: $$('.tf-nav-product-menu .tf-nav-dropdown-icon svg')
      .map((e) => getComputedStyle(e).strokeWidth),
    tabs: $$('.tf-control-stage-nav button').map((b) => clean(b.textContent)),
    lanes: $$('.tf-control-plane-body .tf-control-lane')
      .map((e) => (e.className.match(/tf-control-(runtime|audit|airouter|boss)/) || [])[1]),
    harnessChips: $$('.tf-control-harness-chips > *').map((e) => clean(e.textContent)),
    // the Rune board carries the authored product wording; #runtime has exactly
    // one sidebar, so these selectors are unambiguous
    runeOverline: one('#runtime .tf-section-sidebar .tf-overline'),
    runeTitle: one('#runtime .tf-section-sidebar .tf-section-title'),
    runeCopy: one('#runtime .tf-section-sidebar .tf-section-copy'),
    // the Moha board is a stacked layout (full-width .tf-section-heading over the
    // audit replay), NOT a .tf-section-sidebar one — probing for a sidebar there
    // silently yields '' and fails every Moha copy assertion
    mohaOverline: one('#audit .tf-section-heading .tf-overline'),
    mohaTitle: one('#audit .tf-section-heading .tf-section-title'),
    mohaCopy: one('#audit .tf-section-heading .tf-section-copy'),
    auditLaneLabel: one('.tf-control-plane-body .tf-control-audit .tf-runtime-label'),
    auditRecords: $$('.tf-audit-event').map((e) => clean(e.querySelector('b').textContent)),
    auditSelected: $$('.tf-audit-event').findIndex((e) => e.classList.contains('is-selected')),
    // the four records share one pair of detail columns, so click each one and
    // read back what the pane rendered — the HTML only carries record 01
    auditPanes: (() => {
      const btns = $$('.tf-audit-event');
      const d = document.querySelector('.tf-audit-decision');
      const ev = document.querySelector('.tf-audit-evidence');
      if (!btns.length || !d || !ev) return [];
      const out = btns.map((b) => {
        b.click();
        return {
          index: clean(d.querySelector('.tf-audit-panel-label small').textContent),
          icon: d.querySelector('.tf-audit-decision-icon').className
            .replace('tf-audit-decision-icon', '').trim(),
          title: clean(d.querySelector('h3').textContent),
          rows: Array.from(d.querySelectorAll('.tf-audit-decision-details > div')).length,
          evidence: Array.from(ev.querySelectorAll('li')).map((x) => clean(x.textContent)),
          live: b.classList.contains('is-selected') && b.getAttribute('aria-pressed') === 'true',
        };
      });
      btns[0].click();
      return out;
    })(),
    // the XCMP capability band was removed on 2026-09-11 pm: no section, no
    // cards, no entry link -- but the XCMP wording survives in five other places
    xcmpBandGone: !document.querySelector('#gateway')
      && !document.querySelector('.tf-advantage-card')
      && !document.querySelector('.tf-advantage-inner'),
    // textContent, not innerText: the runtime story sits in a tab lane and the
    // hidden lanes are display:none, so innerText would miss them
    xcmpSurvivors: ['向下由 XCMP 云管理能力提供多云资源底座',
      '通过 XCMP 统一纳管多地域资源',
      'XCMP 云管理能力为四大板块提供多云资源底座',
      'XCMP 可自动识别并接入 Kubernetes',
      'XCMP 云管理能力随平台交付',
      'XCMP 云管理']
      .filter((k) => document.body.textContent.includes(k)).length,
    footerWordmark: one('.tf-footer-brand-word > span'),
    // the "all systems operational" pill and the ICP placeholder were dropped
    // from the foot of the page on 2026-09-11
    footerStatusGone: !document.querySelector('.tf-footer-status'),
    footerQuote: one('.tf-footer-bottom > p'),
    airouterEyebrow: one('#tools .tf-section-sidebar .tf-overline'),
    airouterTitle: one('#tools .tf-section-sidebar .tf-section-title'),
    airouterCopy: one('#tools .tf-section-sidebar .tf-section-copy'),
    airouterLinks: $$('#tools .tf-section-sidebar .tf-section-link').map((e) => clean(e.textContent)),
    airouterPanelInSplit: !!document.querySelector('#tools .tf-section-split > .tf-managed-api-code-panel'),
    // AIRouter was authored with its own skin (.tf-managed-api-section / -shell /
    // -intro); it now rides the shared board layout, so compare the *computed*
    // styles of both sidebars instead of trusting the class names
    boardShellEq: (() => {
      const pick = (id) => {
        const split = document.querySelector(id + ' .tf-section-split');
        const side = document.querySelector(id + ' .tf-section-sidebar');
        const over = document.querySelector(id + ' .tf-section-sidebar .tf-overline');
        const title = document.querySelector(id + ' .tf-section-sidebar .tf-section-title');
        const copy = document.querySelector(id + ' .tf-section-sidebar .tf-section-copy');
        if (!split || !side || !over || !title || !copy) return null;
        const cs = (e) => getComputedStyle(e);
        return [cs(split).gridTemplateColumns, cs(split).gap,
          cs(side).padding, cs(side).position,
          cs(over).fontSize, cs(over).fontWeight, cs(over).borderRadius, cs(over).padding,
          cs(title).fontSize, cs(title).fontWeight, cs(title).lineHeight,
          cs(copy).fontSize, cs(copy).lineHeight];
      };
      const a = pick('#runtime');
      const b = pick('#tools');
      return { matched: !!a && !!b && JSON.stringify(a) === JSON.stringify(b), rune: a, airouter: b };
    })(),
    // The Moha board puts its title in a full-width .tf-section-heading instead
    // of a .tf-section-sidebar, so it used to inherit the vendor's base title
    // size (clamp(2.35rem,4vw,3.55rem)) — one step larger than the sidebar
    // variant. custom.css pins it to the sidebar value; assert on the computed
    // size rather than on the class name.
    mohaTitleSizeEqRune: (() => {
      const a = document.querySelector('#audit .tf-section-title');
      const b = document.querySelector('#runtime .tf-section-title');
      if (!a || !b) return { matched: false, moha: null, rune: null };
      const sa = getComputedStyle(a).fontSize;
      const sb = getComputedStyle(b).fontSize;
      return { matched: sa === sb, moha: sa, rune: sb };
    })(),
    mohaTitleInHeading: !!document.querySelector('#audit .tf-section-heading .tf-section-title'),
    bossEyebrow: one('#boss .tf-overline'),
    bossTitle: one('#boss .tf-section-title'),
    bossMetrics: $$('#boss .tf-boss-metric').length,
    bossRows: $$('#boss .tf-boss-row:not(.is-head)').length,
    bossBars: $$('#boss .tf-boss-bars > *').length,
    bossSteps: $$('#boss .tf-gateway-capabilities h3').map((e) => clean(e.textContent)),
    // the Rune Harness planning board was removed on 2026-09-11 pm, so the
    // section element itself must be gone rather than merely emptied
    harnessBoardGone: !document.querySelector('#harness')
      && !document.querySelector('.tf-harness-phase'),
    // the pricing board sells one thing -- a compute subscription -- with
    // optional modules stacked on top; assert the copy on all four cards
    pricingEyebrow: one('.tf-home-pricing-overline'),
    pricingTitle: one('#home-pricing-title'),
    pricingIntro: one('.tf-home-pricing-intro > p'),
    pricingNames: $$('.tf-home-pricing-item h3').map((e) => clean(e.textContent)),
    pricingUnits: $$('.tf-home-pricing-item strong').map((e) => clean(e.textContent)),
    pricingCopies: $$('.tf-home-pricing-item p').map((e) => clean(e.textContent)),
    pricingNote: one('.tf-home-pricing-note > span'),
    faqCount: $$('.tf-faq-list article').length,
    footerProducts: $$('footer a').map((a) => clean(a.textContent))
      .filter((x) => /^(产品总览|Rune 智算|Moha 资产|AIRouter · AI聚合网关|BOSS 运营|XCMP 云管理|KubeGems)$/.test(x)),
    ids: $$('section[id]').map((e) => e.id),
    docW: document.documentElement.scrollWidth,
    innerW: window.innerWidth,
    leftover: [
      // 上游残留文案（探针只读 innerText，所以这里查的是可见文字）
      ...['AI Router', 'ChatBox', 'XMCP',
        'Moha · AI 资产仓库', '每一份资产都可追溯', '看清谁在什么时候访问了什么',
        // the XCMP capability band was removed on 2026-09-11 pm
        'XCMP · 云管理能力', '把多云真正用成一朵云。',
        // footer status pill + ICP placeholder, dropped on 2026-09-11 pm
        '所有服务运行正常', '蜀ICP备',
        // the reference page's generic approval story, retired with the Moha pass
        '一次越权访问被策略拦截']
        .filter((k) => document.body.innerText.includes(k)),
      // 上游品牌名哨兵 —— 与 tools/portal_page.py 的 UPSTREAM_BRAND_RE 同一份判据。
      // 写成正则而不是字面量：既咬得住品牌名被拆成两个词的变体，也让这个名字
      // 在仓库里归零（哨兵不能自己是那唯一的命中项）。
      ...(/pipe\s*llm/i.test(document.body.innerText) ? ['上游品牌名'] : []),
    ],
  };
})()`;
const evaluated = await page.rpc('Runtime.evaluate', { expression: probe, returnByValue: true });
page.close();
if (!evaluated.result || !evaluated.result.value) {
  console.error('probe failed:', JSON.stringify(evaluated, null, 1).slice(0, 800));
  process.exit(1);
}
const v = evaluated.result.value;

// The nav lockup is an <img>, so neither its wordmark nor its colours are in the
// DOM: read the asset itself. tools/gen_icons.py §10 bakes the hero hub's mono
// treatment (grayscale/contrast/brightness on assets/img/icon-mark.svg) into the
// mark's stops, so the brand gradient hexes must not appear in this file.
const navLogoSvg = readFileSync(new URL('../../assets/img/logo.svg', import.meta.url), 'utf8');
// 品牌的另一份 mark（favicon / hero hub / Harness 带标共用同一张图），
// 与 logo 的 mark 保持同形 —— 见 gen_icons.py §6 与 §10。
const hubMarkSvg = readFileSync(new URL('../../assets/img/icon-mark.svg', import.meta.url), 'utf8');

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
  // 「关于我们」下拉：开源项目现在指向站外 KubeGems，加入我们整项移除（2026-09-11）
  eq('company dropdown lists four entries', v.companyNav.map((e) => e.title),
    ['公司简介', '公司动态', '开源项目', '联系我们']),
  eq('company dropdown carries the expected targets', v.companyNav.map((e) => e.href),
    ['/about', '/blog', 'https://www.kubegems.io/', '/contact']),
  has('the opensource entry opens in a new tab', String(v.companyNav[2].blank), 'true'),
  has('the contact entry stays in-site', String(v.companyNav[3].blank), 'false'),
  // 顶层菜单「解决方案」2026-09-11 改指演示站第一页（见 stage_nav_menu）。
  // 按 label 查找而不是按索引 —— 这个选择器还命中两个下拉 trigger（button，
  // 无 href）与「联系销售」，索引会随上游增删项漂移。
  eq('the solutions menu entry points at the deck',
    (v.navMenu.find((e) => e.title === '解决方案') || {}).href,
    'https://ppt.poxiaoshi.cn/#slide-1'),
  // 商务出口统一收口 /contact（2026-09-11 晚（十三），见 reshape_home.py 的
  // stage_contact_retarget）。这里只核导航条右侧那条 CTA —— 它是四条里唯一能在
  // 现有采集字段（navMenu）里读到的；页脚两条与移动抽屉那条由 Python 守卫按
  // data-page-node-id 断言，浏览器通道看不到 node-id 的语义，别在这里重复实现一遍。
  // 注意按 label 找而不是按索引：navMenu 里还有两个下拉 trigger（button，无 href）。
  eq('the nav sales CTA points at the contact page',
    (v.navMenu.find((e) => e.title === '联系销售') || {}).href, '/contact'),
  eq('nav logo keeps its asset', v.navLogo && v.navLogo.src, 'assets/img/logo.svg'),
  eq('nav logo announces the company', v.navLogo && v.navLogo.alt, '破晓石科技 logo'),
  eq('nav logo wordmark names the company', /<text[^>]*>破晓石科技<\/text>/.test(navLogoSvg), true),
  eq('nav logo mark is mono, like the hub glyph',
    /7DF3F0|2CC7D8|8E7BFF|5A46E0/i.test(navLogoSvg), false),
  // 两条 mark 顶部对齐（2026-09-11 用户要求，见 gen_icons.py §10 的注释）。
  // 这是一个纯视觉约定，图画错不会有任何报错 —— 而且旧坐标（右条低 4）看着
  // 也挺正常，最容易被人「顺手改回去」，所以在这里钉死。
  eq('nav logo bars share one top edge', (() => {
    const ys = [...navLogoSvg.matchAll(/<rect x="[-\d.]+" y="([-\d.]+)"/g)].map((m) => m[1]);
    return ys.length === 2 && ys[0] === ys[1];
  })(), true),
  // 渐变必须跟着矩形走：右条上移后 y1/y2 还停在旧位置的话，色阶会整体偏下
  eq('nav logo short bar gradient tracks the bar', (() => {
    const g = navLogoSvg.match(/id="lg-mono" x1="[-\d.]+" y1="([-\d.]+)" x2="[-\d.]+" y2="([-\d.]+)"/);
    const r = navLogoSvg.match(/<rect x="11\.4" y="([-\d.]+)" width="7\.6" height="([-\d.]+)"/);
    if (!g || !r) return false;
    return Number(g[1]) === Number(r[1])
      && Number(g[2]) === Number(r[1]) + Number(r[2]);
  })(), true),
  // brand mark（favicon / hero hub / Harness 带标）。同一天改成顶部对齐，
  // 两条 mark 从此几何同源（nav lockup 是它的 0.5x）—— 断言也一起钉住，
  // 免得只改一边又飘回去。
  eq('brand mark bars share one top edge', (() => {
    const ys = [...hubMarkSvg.matchAll(/<rect x="[-\d.]+" y="([-\d.]+)"/g)].map((m) => m[1]);
    return ys.length === 2 && ys[0] === ys[1];
  })(), true),
  eq('brand mark short bar gradient tracks the bar', (() => {
    const g = hubMarkSvg.match(/id="mk-violet" x1="[-\d.]+" y1="([-\d.]+)" x2="[-\d.]+" y2="([-\d.]+)"/);
    const r = hubMarkSvg.match(/<rect x="31" y="([-\d.]+)" width="15" height="([-\d.]+)"/);
    if (!g || !r) return false;
    return Number(g[1]) === Number(r[1])
      && Number(g[2]) === Number(r[1]) + Number(r[2]);
  })(), true),
  // 两个文件的绑定关系：bar 尺寸恰好 2:1（48/30 vs 24/15），顶部关系一致。
  // 这条是「同一份素材只声明一次」的可执行版本 —— 谁只调一边就会在这里断。
  eq('the two marks keep the same bar geometry at 2:1', (() => {
    const dims = (svg) => [...svg.matchAll(/<rect x="[-\d.]+" (?:y="[-\d.]+" )?width="([\d.]+)" height="([\d.]+)"/g)]
      .map((m) => [Number(m[1]), Number(m[2])]);
    const [hub, nav] = [dims(hubMarkSvg), dims(navLogoSvg)];
    if (hub.length !== 2 || nav.length !== 2) return false;
    return hub.every((d, i) => d[1] === nav[i][1] * 2);
  })(), true),
  eq('product dropdown icons keep their stroke', v.navDropdownIconStrokes,
    ['2px', '2px', '2px', '2px']),
  eq('hero slogan stays as authored upstream', v.heroTitle, '智算为中心的 AI 原生云内核'),
  eq('hero subtitle stays as authored upstream', v.heroSubtitle,
    '专注云原生开源、混合云与 AI 智算平台，为企业提供覆盖容器云、混合云、智算云及 AI 能力的全栈解决方案。'),
  eq('hero overline teases Rune Harness', v.heroOverline, 'Rune Harness 即将开放'),
  eq('overline carries no leading mark', v.heroOrb, 0),
  eq('orb arc is animated', v.heroOrbSpin.includes('tf-thinking-spin'), true),
  eq('orb core is animated', v.heroOrbCore.includes('tf-thinking-breathe'), true),
  eq('one thinking orb on the page, on the chat avatar', v.heroOrbCount, 1),
  eq('static play triangle is suppressed', v.heroOrbTriangle, 'none'),
  eq('hero pills list the four boards', v.heroPills,
    ['Rune 智算', 'Moha 资产', 'AIRouter · AI聚合网关', 'BOSS 运营']),
  eq('hero chat asks in plain language', v.chatUser, '部署 DeepSeek V4.1 Flash'),
  eq('hero chat stacks a thinking and a settled label', v.chatStates, ['正在思考', '已处理']),
  eq('the two chat labels cross-fade off one timeline', v.chatStateTimeline,
    ['tf-chat-thinking-visible/9.6s', 'tf-chat-state-settled/9.6s']),
  eq('hero chat animates three thinking dots', v.chatDots, 3),
  eq('thinking dots retire when the label settles', v.chatDotsTimeline, 'tf-chat-thinking-visible/9.6s'),
  eq('hero chat reuses the thinking mark', v.chatAvatarOrb, true),
  eq('hero chat reports the deploy result', v.chatDone, '✔模型已调度部署完成'),
  eq('deploy result is rendered in success green', v.chatDoneColor, 'rgb(138, 255, 193)'),
  eq('hero chat rows share one CSS timeline', v.chatTimeline,
    ['tf-chat-turn-user/9.6s', 'tf-chat-turn-ai/9.6s', 'tf-chat-turn-done/9.6s']),
  eq('centre terminal is titled Rune Harness', v.terminalTitles, ['~/moha', 'Rune Harness', '~/airouter']),
  has('document title sells Rune Harness', v.title, 'Rune Harness 云智算内核'),
  // 2026-09-11 品牌写法统一：四板块并列串用 `/` 分层（`·` 让给「主名 · 定位词」），
  // 标题里 AIRouter 段必须带全称 —— 这是 `AIRouter 网关` 旧写法最外面的那一处
  eq('document title carries the unified AIRouter lockup', v.title,
    '晓石云 | Rune Harness 云智算内核 — Rune 智算 / Moha 资产 / AIRouter · AI聚合网关 / BOSS 运营'),
  eq('control plane exposes four tabs', v.tabs, ['01Rune', '02Moha', '03AIRouter', '04BOSS']),
  eq('control plane exposes four lanes', v.lanes, ['runtime', 'audit', 'airouter', 'boss']),
  eq('harness band lists its four chips', v.harnessChips,
    ['Harness', 'Agents', 'Skills', 'Execute']),
  eq('the XCMP capability band is gone', v.xcmpBandGone, true),
  eq('XCMP wording survives in the five other places', v.xcmpSurvivors, 6),
  eq('footer wordmark carries the company name', v.footerWordmark, '破晓石科技'),
  eq('the all-systems-operational pill is gone', v.footerStatusGone, true),
  eq('copyright line keeps company and address only', v.footerQuote,
    '© 2026 成都破晓石科技有限公司 · 四川省成都市高新区银泰悦坊17号楼9层'),
  eq('Rune board overline reads Rune · 智算Infra', v.runeOverline, 'Rune · 智算Infra'),
  eq('Rune board headline', v.runeTitle, '智算与应用基础设施融合平台'),
  eq('Rune board copy', v.runeCopy,
    '覆盖模型开发、训练、推理与部署全流程，同时保持云原生容器能力：算力配额、任务状态与调度记录清晰可见。'),
  eq('Moha board overline', v.mohaOverline, 'Moha · 数字仓库'),
  eq('Moha board headline', v.mohaTitle, '你的私有化HuggingFace，每一份数据都可追溯'),
  eq('Moha board copy', v.mohaCopy, '统一社区化管理模型、数据集、镜像、空间和技能'),
  eq('Moha board headline sits in the full-width heading block', v.mohaTitleInHeading, true),
  eq('Moha board headline is the same size as the Rune board one',
    v.mohaTitleSizeEqRune.matched, true),
  eq('control plane lane 02 is renamed', v.auditLaneLabel, '2 / Moha · 数字仓库'),
  eq('audit timeline lists the four Moha records', v.auditRecords,
    ['moha.push', 'encrypt.aes256', 'access.grant', 'rune.pull']),
  eq('record 01 is selected on load', v.auditSelected, 0),
  eq('each record renders its own decision pane', v.auditPanes.map((p) => p.title), [
    '上传即入库，版本自动冻结。',
    '落盘即加密，密钥留在你自己手里。',
    '一次越权的资产读取被拦截。',
    '训练拉取了哪份资产，同样留痕。']),
  eq('the pane index follows the click', v.auditPanes.map((p) => p.index),
    ['01 / 04', '02 / 04', '03 / 04', '04 / 04']),
  eq('the pane accent follows the record', v.auditPanes.map((p) => p.icon),
    ['is-cyan', 'is-green', 'is-amber', 'is-violet']),
  eq('every pane keeps three detail rows', v.auditPanes.map((p) => p.rows), [3, 3, 3, 3]),
  eq('every pane keeps three evidence items', v.auditPanes.map((p) => p.evidence.length), [3, 3, 3, 3]),
  eq('clicking a record sets it selected and pressed', v.auditPanes.map((p) => p.live),
    [true, true, true, true]),
  has('AIRouter section overline reads AIRouter · AI聚合网关', v.airouterEyebrow,
    'AIRouter · AI聚合网关'),
  eq('AIRouter board rides the shared panel layout', v.boardShellEq.matched, true),
  eq('AIRouter board headline', v.airouterTitle, '一个入口，接入所有大模型'),
  eq('AIRouter board copy',
    v.airouterCopy,
    'AIRouter 是晓石云的 AI聚合网关：一个入口接入各家大模型与多模态能力，统一密钥与配额、按策略路由请求，并保留每一次调用的用量与审计记录。'),
  eq('AIRouter keeps a single entry link on the board link style', v.airouterLinks,
    ['了解 AIRouter']),
  eq('the AIRouter code panel stays inside the shared grid', v.airouterPanelInSplit, true),
  has('BOSS section overline reads BOSS · 运营平台', v.bossEyebrow, 'BOSS · 运营平台'),
  has('BOSS board headline', v.bossTitle, '看清每一笔消耗，管住每一个租户'),
  eq('BOSS panel shows four metrics', v.bossMetrics, 4),
  eq('BOSS panel lists six tenants', v.bossRows, 6),
  eq('BOSS panel charts eight periods', v.bossBars, 8),
  eq('BOSS names its three operating steps', v.bossSteps, ['开户与授权', '配额与调度', '计量与出账']),
  // the Rune Harness planning board was cut on 2026-09-11 pm: assert the whole
  // section is gone, so a stale stage cannot quietly bring it back
  eq('the Rune Harness planning board is gone', v.harnessBoardGone, true),
  eq('pricing board overline', v.pricingEyebrow, '算力订阅制_'),
  eq('pricing board headline', v.pricingTitle, '按算力订阅，按模块组合。'),
  eq('pricing board intro', v.pricingIntro,
    '四大产品共用一套算力订阅计价：以算力为基准，按需选择模块组合，统一订阅、统一出账。'),
  eq('pricing covers the four boards', v.pricingNames, ['Rune', 'Moha', 'AIRouter', 'BOSS']),
  eq('every board is sold as a compute subscription', v.pricingUnits,
    ['算力订阅 · 训练推理', '算力订阅 · 资产模块', '算力订阅 · 网关模块', '算力订阅 · 运营模块']),
  eq('each card names the module it adds', v.pricingCopies,
    ['训练、推理与容器编排随订阅开通，按 GPU 算力规格计价。',
      '资产仓库随订阅开通，存储、加密与审计按容量叠加。',
      'AI聚合网关随订阅开通，路由策略与用量看板按调用规模叠加。',
      '运营控制台随订阅开通，租户、配额与计量出账按纳管规模叠加。']),
  eq('pricing note explains module changes', v.pricingNote,
    '模块可按需增减，变更于下一订阅周期生效；交付与实施服务按项目范围单独报价。'),
  eq('FAQ carries nine entries', v.faqCount, 9),
  eq('footer product column is complete', v.footerProducts,
    ['产品总览', 'Rune 智算', 'Moha 资产', 'AIRouter · AI聚合网关', 'BOSS 运营', 'XCMP 云管理', 'KubeGems']),
  // the XCMP band was cut from the foot of the page, so the closing CTA is now
  // the last block: the FAQ must still precede it
  eq('section order is stable, CTA last', v.ids,
    ['home', 'runtime', 'audit', 'tools', 'boss', 'pricing', 'blog', 'faq']),
  eq('no rebrand leftovers', v.leftover, []),
  eq('no horizontal overflow', v.docW <= v.innerW, true),
  eq('no runtime errors', errors, []),
];
const failed = results.filter((r) => !r).length;
console.log(`\n${failed === 0 ? 'PASS' : 'FAIL'} — ${results.length - failed}/${results.length} checks`);
process.exit(failed === 0 ? 0 : 1);
