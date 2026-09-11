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
  function cm(t) { return '<span class="tf-syntax-comment">' + esc(t) + '</span>'; }

  /* ---------------------------------------------------------------- nav */
  var nav = $('.pipellm-nav-surface');
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
      desc: 'AIRouter 统一模型入口，协议翻译、策略路由与用量审计一次到位。' },
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

  /* -------- 2. gateway cloud-platform tabs ------------------------------ */
  var GW = [
    { name: 'Kubernetes', protocol: 'Kubernetes',
      hint: '保留原有 Kubernetes 访问方式，由 XMCP 完成跨云连接与统一纳管。',
      code: [[kw('const'), ' cluster = ' + kw('await'), ' ' + fn('xmcp'), '.' + fn('attach') + '({'],
             ['  ' + pr('context') + ': ' + st('"prod-cn-southwest"') + ','],
             ['  ' + pr('namespace') + ': ' + st('"ai-platform"') + ','],
             ['  ' + pr('policy') + ': ' + st('"zero-trust"')],
             ['});']] },
    { name: 'vCenter', protocol: 'vCenter',
      hint: '纳管虚拟化资源池，与容器集群统一编排、统一计量。',
      code: [[kw('const'), ' dc = ' + kw('await'), ' ' + fn('xmcp'), '.' + fn('register') + '({'],
             ['  ' + pr('endpoint') + ': ' + st('"vcenter.corp.local"') + ','],
             ['  ' + pr('cluster') + ': ' + st('"cluster-a"') + ','],
             ['  ' + pr('metering') + ': ' + st('true')],
             ['});']] },
    { name: 'OpenStack', protocol: 'OpenStack',
      hint: '对接私有云资源池，按租户维度做配额与计费。',
      code: [[kw('const'), ' pool = ' + kw('await'), ' ' + fn('xmcp'), '.' + fn('register') + '({'],
             ['  ' + pr('endpoint') + ': ' + st('"https://keystone.internal"') + ','],
             ['  ' + pr('project') + ': ' + st('"ai-lab"') + ','],
             ['  ' + pr('quota') + ': ' + st('"gpu=64"')],
             ['});']] },
    { name: '华为云', protocol: '华为云',
      hint: '公有云通道即插即用，跨云网络与策略一次配置。',
      code: [[kw('const'), ' link = ' + kw('await'), ' ' + fn('xmcp'), '.' + fn('connect') + '({'],
             ['  ' + pr('provider') + ': ' + st('"huaweicloud"') + ','],
             ['  ' + pr('region') + ': ' + st('"cn-southwest-2"') + ','],
             ['  ' + pr('mesh') + ': ' + st('true')],
             ['});']] }
  ];

  var gwRoot = $('.tf-gateway-code');
  function gwCodeCol() {
    var grid = gwRoot && gwRoot.querySelector('div.grid');
    return grid ? grid.lastElementChild : null;
  }
  function gwLineCol() {
    var grid = gwRoot && gwRoot.querySelector('div.grid');
    return grid ? grid.firstElementChild : null;
  }
  function renderGw(i) {
    var d = GW[i];
    if (!d || !gwRoot) return;
    var p = gwRoot.querySelector(':scope > p');
    if (p) p.textContent = d.hint;
    var col = gwCodeCol();
    if (col) {
      col.innerHTML = d.code.map(function (l) {
        return '<div class="h-[21px] relative whitespace-pre">' + l.join('') + '</div>';
      }).join('');
    }
    var nums = gwLineCol();
    if (nums) {
      nums.innerHTML = d.code.map(function (_l, k) {
        return '<div class="h-[21px]">' + (k + 1) + '</div>';
      }).join('');
    }
    var decision = $$('.tf-gateway-decision span');
    if (decision[0]) decision[0].innerHTML = '<b>平台</b>' + esc(d.protocol);
  }
  bindTabs($('.tf-gateway-sdk-tabs'), renderGw, 0);

  var copyBtn = $('.tf-gateway-panel-bar button[title]');
  if (copyBtn) copyBtn.addEventListener('click', function () {
    var col = gwCodeCol();
    if (col && navigator.clipboard) navigator.clipboard.writeText(col.innerText.replace(/\n+/g, '\n').trim());
  });

  /* -------- 3. runtime language tabs ------------------------------------ */
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

  /* ------------------------------------------ replay step selection */
  $$('.tf-lens-replay-step, .tf-decision-replay-item').forEach(function (s) {
    s.addEventListener('click', function () {
      $$('.tf-lens-replay-step, .tf-decision-replay-item').forEach(function (o) { o.classList.remove('is-active'); });
      s.classList.add('is-active');
    });
  });

  /* ---------------------------------------------- scramble hover label */
  var GLYPHS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/\\<>-_*';
  var busy = new WeakMap();
  function scramble(host) {
    if (!host || busy.get(host)) return;
    var live = host.querySelector('.tf-scramble-live');
    if (!live) return;
    var original = live.getAttribute('data-text') || live.textContent;
    live.setAttribute('data-text', original);
    var frame = 0;
    busy.set(host, true);
    var id = setInterval(function () {
      frame += 1;
      live.textContent = original.split('').map(function (ch, i) {
        if (ch === ' ') return ch;
        if (i < frame / 2) return original[i];
        return GLYPHS[Math.floor(Math.random() * GLYPHS.length)];
      }).join('');
      if (frame / 2 > original.length) {
        clearInterval(id);
        live.textContent = original;
        busy.delete(host);
      }
    }, 26);
  }
  $$('.tf-nav-menu-link, .tf-footer-link').forEach(function (el) {
    var host = el.querySelector('.tf-scramble-label');
    if (!host) return;
    el.addEventListener('mouseenter', function () { scramble(host); });
  });
})();