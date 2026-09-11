/* =========================================================================
   晓石云 demo · interactions
   Reproduces the reference page behaviour with plain DOM APIs:
   sticky-nav state, scroll reveal, product tabs, code samples, FAQ, drawer.
   ========================================================================= */
(function () {
  'use strict';
  document.documentElement.classList.add('js-ready');

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  function esc(t) { return String(t).replace(/&/g, '&amp;').replace(/</g, '&lt;'); }
  function kw(t) { return '<span class="tf-syntax-keyword">' + esc(t) + '</span>'; }
  function st(t) { return '<span class="tf-syntax-string">' + esc(t) + '</span>'; }
  function pr(t) { return '<span class="tf-syntax-property">' + esc(t) + '</span>'; }
  function fn(t) { return '<span class="tf-syntax-function">' + esc(t) + '</span>'; }

  /* ---------------------------------------------------------------- nav */
  var nav = $('.pxs-nav-surface');
  function onScroll() { if (nav) nav.classList.toggle('is-scrolled', window.scrollY > 12); }
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  var drawer = $$('div').filter(function (d) {
    return d.classList.contains('fixed') && d.classList.contains('inset-0') &&
           d.classList.contains('md:hidden') && /bg-\[rgba\(5,5,6/.test(d.className);
  })[0];
  var burger = $('button[aria-label="Toggle menu"]');
  if (burger && drawer) {
    burger.addEventListener('click', function () {
      var open = drawer.classList.toggle('tf-mobile-open');
      document.body.style.overflow = open ? 'hidden' : '';
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    drawer.addEventListener('click', function (e) {
      if (e.target.closest('a')) {
        drawer.classList.remove('tf-mobile-open');
        document.body.style.overflow = '';
      }
    });
  }

  /* ------------------------------------------------------- scroll reveal */
  var sections = $$('.tf-motion-section');
  var blocks = $$('[style]').filter(function (el) {
    return /transition-property/.test(el.getAttribute('style') || '') &&
           /opacity\s*:\s*0/.test(el.getAttribute('style') || '');
  });

  function show(el) {
    el.style.opacity = '1';
    el.style.transform = 'translate3d(0,0,0)';
  }

  if ('IntersectionObserver' in window) {
    var ioA = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        e.target.classList.add('is-motion-visible');
        ioA.unobserve(e.target);
      });
    }, { rootMargin: '0px 0px -6% 0px', threshold: 0.02 });

    var ioB = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        show(e.target);
        ioB.unobserve(e.target);
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.03 });

    sections.forEach(function (el) {
      if (/is-motion-visible/.test(el.className)) return;
      ioA.observe(el);
    });
    blocks.forEach(function (el) { ioB.observe(el); });
  } else {
    sections.forEach(function (el) { el.classList.add('is-motion-visible'); });
    blocks.forEach(show);
  }

  /* ------------------------------------------------------------ tab sets */
  function bindTabs(list, render, initial) {
    if (!list) return;
    var btns = $$('button[role="tab"]', list);
    btns.forEach(function (btn, i) {
      btn.addEventListener('click', function () {
        btns.forEach(function (b) {
          b.classList.remove('is-active');
          b.setAttribute('aria-selected', 'false');
        });
        btn.classList.add('is-active');
        btn.setAttribute('aria-selected', 'true');
        render && render(i);
      });
    });
    var active = btns.findIndex(function (b) { return b.classList.contains('is-active'); });
    if (typeof initial !== 'undefined' && render) render(initial);
    else if (active > 0 && render) render(active);
  }

  /* -------- 1. control plane: Rune / Moha / AIRouter / BOSS ------------- */
  /* The four boards share the plane; selecting a tab highlights its lane and
     refreshes the outcome row. There is no centre stage panel any more — the
     Rune Harness core band below the lanes plays that role. */
  var CONTROL = [
    { lane: 'tf-control-runtime', title: '训练任务已调度',
      desc: 'Rune 承载训练、调优、推理与部署全流程，算力配额与数据来源全程可见。' },
    { lane: 'tf-control-audit', title: '资产已加密入库',
      desc: 'Moha 把模型、数据集与镜像沉淀为可检索、可追溯的加密资产。' },
    { lane: 'tf-control-airouter', title: '模型调用已授权',
      desc: 'AIRouter · AI聚合网关，协议翻译、策略路由与用量审计一次到位。' },
    { lane: 'tf-control-boss', title: '计量出账已完成',
      desc: 'BOSS 让租户、配额、计量与运营数据在同一个控制台闭环。' }
  ];

  function renderControl(i) {
    var d = CONTROL[i];
    if (!d) return;
    CONTROL.forEach(function (x, k) {
      var lane = $('.' + x.lane);
      if (lane) lane.classList.toggle('is-active', k === i);
    });
    var plane = $('.tf-control-plane');
    if (!plane) return;
    var resTitle = $('.tf-control-plane-result p', plane);
    if (resTitle) resTitle.innerHTML = '✓ ' + esc(d.title);
    var resDesc = $('.tf-control-plane-result span:last-child', plane);
    if (resDesc) resDesc.textContent = d.desc;
  }
  bindTabs($('.tf-control-stage-nav'), renderControl, 0);

  /* -------- 2. runtime language tabs ------------------------------------ */
  var RT = [
    { label: 'Python', code: [[kw('from'), ' xiaoshi ' + kw('import'), ' rune'],
             [],
             [kw('job'), ' = ' + fn('rune'), '.' + fn('submit') + '('],
             ['    job=' + st('"llm-finetune-7b"') + ','],
             ['    pool=' + st('"gpu-a800-8"') + ','],
             ['    dataset=' + st('"moha://datasets/corpus-v3"') + ','],
             [')']] },
    { label: 'YAML', code: [[st('apiVersion:') + ' ai.xiaoshi.cn/v1'],
             [st('kind:') + ' TrainingJob'],
             [st('metadata:')],
             ['  ' + pr('name') + ': llm-finetune-7b'],
             [st('spec:')],
             ['  ' + pr('pool') + ': gpu-a800-8'],
             ['  ' + pr('dataset') + ': moha://datasets/corpus-v3'],
             ['  ' + pr('framework') + ': pytorch']] },
    { label: 'cURL', code: [['$ curl -X POST https://api.poxiaoshi.cn/v1/jobs \\'],
             ['    -H ' + st('"Authorization: Bearer $XIAOSHI_API_KEY"') + ' \\'],
             ['    -d ' + st('\'{"job":"llm-finetune-7b","pool":"gpu-a800-8"}\'')],
             [],
             ['{ ' + st('"status"') + ': ' + st('"scheduled"') + ', ' + st('"gpu"') + ': 8 }']] }
  ];
  var rtCode = $('#runtime code.tf-syntax-code');
  bindTabs($('.tf-runtime-session-tabs'), function (i) {
    if (rtCode && RT[i]) rtCode.innerHTML = RT[i].code.map(function (l) { return l.join(''); }).join('\n');
  }, 0);

  /* -------- 4. AI Router route tabs ------------------------------------- */
  function apiLine(l) { return '<span class="tf-managed-api-code-line">' + (l.join('') || '&nbsp;') + '</span>'; }
  var ROUTES = [
    [[kw('const'), ' response = ' + kw('await'), ' ' + fn('fetch') + '('],
     ['  ' + st('"https://api.poxiaoshi.cn/v1/chat/completions"') + ','],
     ['  { ' + pr('method') + ': ' + st('"POST"') + ','],
     ['    ' + pr('headers') + ': { ' + pr('Authorization') + ': ' + st('"Bearer "') + ' + process.env.XIAOSHI_API_KEY },'],
     ['    ' + pr('body') + ': JSON.' + fn('stringify') + '({ ' + pr('model') + ': ' + st('"deepseek-v3"') + ', messages })'],
     ['  }'],
     [');'],
     [],
     [kw('const'), ' { choices } = ' + kw('await'), ' response.' + fn('json') + '();']],
    [[kw('const'), ' response = ' + kw('await'), ' ' + fn('fetch') + '('],
     ['  ' + st('"https://api.poxiaoshi.cn/v1/embeddings"') + ','],
     ['  { ' + pr('method') + ': ' + st('"POST"') + ','],
     ['    ' + pr('headers') + ': { ' + pr('Authorization') + ': ' + st('"Bearer "') + ' + process.env.XIAOSHI_API_KEY },'],
     ['    ' + pr('body') + ': JSON.' + fn('stringify') + '({ ' + pr('model') + ': ' + st('"bge-large"') + ', input })'],
     ['  }'],
     [');'],
     [],
     [kw('const'), ' { data } = ' + kw('await'), ' response.' + fn('json') + '();']],
    [[kw('const'), ' response = ' + kw('await'), ' ' + fn('fetch') + '('],
     ['  ' + st('"https://api.poxiaoshi.cn/v1/rerank"') + ','],
     ['  { ' + pr('method') + ': ' + st('"POST"') + ','],
     ['    ' + pr('headers') + ': { ' + pr('Authorization') + ': ' + st('"Bearer "') + ' + process.env.XIAOSHI_API_KEY },'],
     ['    ' + pr('body') + ': JSON.' + fn('stringify') + '({ ' + pr('query') + ', documents })'],
     ['  }'],
     [');'],
     [],
     [kw('const'), ' { results } = ' + kw('await'), ' response.' + fn('json') + '();']],
    [[kw('const'), ' form = ' + kw('new'), ' ' + fn('FormData') + '();'],
     ['form.' + fn('append') + '(' + st('"file"') + ', image);'],
     [],
     [kw('const'), ' response = ' + kw('await'), ' ' + fn('fetch') + '('],
     ['  ' + st('"https://api.poxiaoshi.cn/v1/vision"') + ','],
     ['  { ' + pr('method') + ': ' + st('"POST"') + ', ' + pr('body') + ': form }'],
     [');'],
     [],
     [kw('const'), ' caption = ' + kw('await'), ' response.' + fn('text') + '();']]
  ];
  var routeCode = $('.tf-managed-api-code-panel pre code');
  bindTabs($('.tf-managed-api-tabs'), function (i) {
    if (routeCode && ROUTES[i]) routeCode.innerHTML = ROUTES[i].map(apiLine).join('');
  }, 0);

  /* ------------------------------------------------------------- FAQ */
  $$('.tf-faq-list article').forEach(function (art) {
    var btn = $('.tf-faq-question-row', art);
    var row = $('.tf-faq-answer-row', art);
    var icon = $('.tf-faq-action-icon img', art);
    if (!btn || !row) return;
    btn.addEventListener('click', function () {
      var open = art.classList.toggle('is-open');
      btn.setAttribute('aria-expanded', open ? 'true' : 'false');
      row.setAttribute('aria-hidden', open ? 'false' : 'true');
      if (icon) icon.classList.toggle('is-open', open);
    });
  });

  /* -------------------------------------- Moha asset-audit detail panes */
  /* The reference page listed four asset events but only ever rendered one
     generic approval pane. Each record now drives its own decision + evidence
     copy, re-rendered into the two existing grid columns so the layout and
     every `.tf-audit-*` rule in vendor.css stay exactly as they are. */
  var SVG_ATTR = 'xmlns="http://www.w3.org/2000/svg" width="24" height="24" ' +
    'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" ' +
    'stroke-linecap="round" stroke-linejoin="round"';
  var CHECK_SVG = '<svg ' + SVG_ATTR + ' class="lucide lucide-check" aria-hidden="true">' +
    '<path d="M20 6 9 17l-5-5"></path></svg>';
  var GLYPH = {
    upload: '<path d="M12 3v12"></path><path d="m17 8-5-5-5 5"></path>' +
      '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>',
    shield: '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 ' +
      '1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z"></path>' +
      '<path d="m9 12 2 2 4-4"></path>',
    file: '<path d="M10.5 22H6a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h8a2.4 2.4 0 0 1 1.706.706l3.588 3.588' +
      'A2.4 2.4 0 0 1 20 8v6"></path><path d="M14 2v5a1 1 0 0 0 1 1h5"></path>' +
      '<path d="m14 20 2 2 4-4"></path>'
  };
  function glyph(key, cls) {
    return '<svg ' + SVG_ATTR + ' class="lucide lucide-' + cls + '" aria-hidden="true">' +
      GLYPH[key] + '</svg>';
  }

  var AUDIT = [
    { color: 'is-cyan', title: '上传即入库，版本自动冻结。',
      icon: glyph('upload', 'upload'),
      desc: '模型、数据集、镜像、空间与技能包统一收纳，自动计算校验摘要并生成不可变版本标签。',
      details: [['提交者', 'user: ma.qing', false],
                ['目标仓库', 'moha://models/llama-3.1-8b', false],
                ['结果', '已生成版本 v1.0.0', true]],
      note: '本次上传的原始文件、提交信息与校验摘要，都与这条记录绑定在一起。',
      items: ['repo: moha://models/llama-3.1-8b',
              'revision: v1.0.0 · sha256:3f9a…',
              'content: 15.2 GB · 4 个分片'] },
    { color: 'is-green', title: '落盘即加密，密钥留在你自己手里。',
      icon: glyph('shield', 'shield-check'),
      desc: '写入对象存储前按 AES-256 分块加密，密钥由租户自持，平台侧不持有明文。',
      details: [['加密算法', 'AES-256-GCM · 分块加密', false],
                ['密钥归属', 'tenant: edu-university-a · 自持 KMS', false],
                ['结果', '密文已入库，明文已清除', true]],
      note: '算法、密钥标识与密文摘要随记录一并留存，可随时复核。',
      items: ['cipher: AES-256-GCM',
              'key-id: kms://tenant-edu/key-07',
              'digest: sha256:9c41…'] },
    { color: 'is-amber', title: '一次越权的资产读取被拦截。',
      icon: glyph('shield', 'shield-check'),
      desc: '该请求超出了所属租户的资产访问范围，操作被暂停并交由管理员复核。',
      details: [['触发条件', 'tenant: edu-university-a', false],
                ['策略', '跨租户读取需管理员授权', false],
                ['结果', '已由管理员批准', true]],
      note: '所有能解释这次操作的材料，都与这条记录绑定在一起。',
      items: ['approver: ma.qing',
              'policy: tenant.access.scope',
              'decision: approved'] },
    { color: 'is-violet', title: '训练拉取了哪份资产，同样留痕。',
      icon: glyph('file', 'file-check-corner'),
      desc: 'Rune 训练任务按引用地址拉取模型与数据集，来源、版本与用途一并记入资产档案。',
      details: [['引用方', 'rune://jobs/llm-finetune-7b', false],
                ['资产', 'moha://datasets/corpus-v3@v3', false],
                ['结果', '拉取成功，已记录引用关系', true]],
      note: '引用关系与拉取凭据一并归档，训练结果可回指到具体数据版本。',
      items: ['grant: token/9f2c… · 有效期 30 分钟',
              'asset: moha://datasets/corpus-v3@v3',
              'consumer: rune://jobs/llm-finetune-7b'] }
  ];

  var auditButtons = $$('.tf-audit-event');
  var auditDecision = $('.tf-audit-decision');
  var auditEvidence = $('.tf-audit-evidence');

  function renderAudit(i) {
    var d = AUDIT[i];
    if (!d) return;
    auditButtons.forEach(function (b, k) {
      var on = k === i;
      b.classList.toggle('is-selected', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    if (auditDecision) {
      var label = $('.tf-audit-panel-label small', auditDecision);
      if (label) label.textContent = '0' + (i + 1) + ' / 0' + AUDIT.length;
      var icon = $('.tf-audit-decision-icon', auditDecision);
      if (icon) {
        icon.className = 'tf-audit-decision-icon ' + d.color;
        icon.innerHTML = d.icon;
      }
      var head = $('h3', auditDecision);
      if (head) head.textContent = d.title;
      var copy = $(':scope > p', auditDecision);
      if (copy) copy.textContent = d.desc;
      var dl = $('.tf-audit-decision-details', auditDecision);
      if (dl) {
        dl.innerHTML = d.details.map(function (row) {
          return '<div><dt>' + esc(row[0]) + '</dt><dd>' +
            (row[2] ? CHECK_SVG : '') + esc(row[1]) + '</dd></div>';
        }).join('');
      }
    }
    if (auditEvidence) {
      var note = $(':scope > p', auditEvidence);
      if (note) note.textContent = d.note;
      var ul = $('ul', auditEvidence);
      if (ul) ul.innerHTML = d.items.map(function (x) { return '<li>' + esc(x) + '</li>'; }).join('');
    }
  }

  if (auditButtons.length && auditDecision && auditEvidence) {
    auditButtons.forEach(function (b, i) {
      b.addEventListener('click', function () { renderAudit(i); });
    });
    renderAudit(0);
  }

  /* ---------------------------------------------- scramble hover label */
  var GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/\\<>-_*';
  var busy = new WeakMap();
  /* 每帧毫秒数。一次 hover 的总时长 = 帧数 × 这个数，帧数由字数决定
     （见下面 scramble()），所以它同时决定所有标签「乱码跳动 → 还原」的快慢：
       四字（解决方案 / 文档中心）  9 帧   0.43s
       五字（价格与服务）          11 帧   0.53s
     2026-09-11 由 26 放慢到 48（用户反馈顶部导航的 hover 动效偏快、
     时间偏短）。要再调快慢，改这一个数就够了 —— 别去动帧数公式，
     那个公式同时管着「逐字还原」的顺序感。 */
  var SCRAMBLE_FRAME_MS = 48;
  /* 帧数上限。不封顶时帧数 = 2×字数+1，页脚那条「AIRouter · AI聚合网关」
     （17 字符）就要跑 35 帧 ≈ 1.68s —— 鼠标扫过页脚，一行字要乱一秒半还多，
     是导航菜单项（4~5 字，0.43~0.53s）的三倍多。封顶后它落在 0.67s，只比短
     标签长一点，而长标签本来就该稍慢。实测：4 字 9 帧 0.432s / 5 字 11 帧
     0.528s / 7 字以上一律 14 帧 0.672s。 */
  var SCRAMBLE_MAX_FRAMES = 14;
  function scramble(host) {
    if (!host || busy.get(host)) return;
    var live = host.querySelector('.tf-scramble-live');
    if (!live) return;
    var original = live.getAttribute('data-text') || live.textContent;
    live.setAttribute('data-text', original);
    var total = Math.min(original.length * 2 + 1, SCRAMBLE_MAX_FRAMES);
    var frame = 0;
    busy.set(host, true);
    var id = setInterval(function () {
      frame += 1;
      /* 已还原的字符数，随帧均匀推进到 original.length。按「已还原几个字」判断
         而不是按帧号直接取整 —— 中英混排的标签（`Rune 智算`、`XCMP 云管理`）
         这样才不会还原得忽快忽慢。 */
      var settled = original.length * (frame / total);
      live.textContent = original.split('').map(function (ch, i) {
        if (ch === ' ') return ch;
        if (i < settled) return original[i];
        return GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
      }).join('');
      if (frame >= total) {
        clearInterval(id);
        live.textContent = original;
        busy.delete(host);
      }
    }, SCRAMBLE_FRAME_MS);
  }
  /* 绑定范围：扫**所有乱码宿主**，往上找它所在的可点元素。
     这里刻意不维护「哪些容器类该有动效」的白名单。此前是白名单
     （`.tf-nav-menu-link` / `.tf-footer-link` / 两处下拉项 / 弹层项），代价是
     「类名加进选择器」和「文字真的包了宿主」成了两份分散在不同文件里的清单 ——
     必然漂移：产品下拉四项、预约弹层四项、页脚 21 条长期都在选择器里，而它们的
     文字从来没有宿主，hover 时只有背景过渡、文字是死的（用户 2026-09-11 报的
     就是产品下拉那四条）。改成自发现后宿主即唯一真相源：生成器里包一层
     `scramble()` 就生效，不用回来改这里。
     开了「减弱动态效果」就整段不绑：CSS 那边只是把过渡时长归零，
     乱码跳动照样会跑，两边得一起关。 */
  if (!window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    $$('.tf-scramble-label').forEach(function (host) {
      var el = host.closest('a, button, [role="button"]');
      if (!el) return;
      el.addEventListener('mouseenter', function () { scramble(host); });
    });
  }
})();