"""Reshape the 晓石云 homepage around four product boards + the Rune Harness core.

The built `index.html` is a single giant artifact derived from the PipeLLM
reference DOM (see build.py). This script re-derives the homepage from the
pristine snapshot in `tools/ref/index.before-reshape.html` with anchored,
re-runnable replacements, so the story change does not require hand-editing
140 KB of markup.

Story line after this pass::

    Rune 智算 · Moha 资产 · AIRouter 网关 · BOSS 运营
        -> 共享一个云智算内核（Rune Harness，规划中）
        -> 底层由 XCMP 云管理能力提供多云资源底座（只强调优势，不展开）

Run:  python3 tools/reshape_home.py
"""
import os
import re
import sys

REF = 'tools/ref/index.before-reshape.html'
OUT = 'index.html'
MISS = []
applied = {}


# --------------------------------------------------------------- utilities
def need(old, new, key=None):
    """Global replacement that must hit at least once."""
    global body
    n = body.count(old)
    if n == 0:
        MISS.append('miss: ' + (key or old[:70]))
        return False
    body = body.replace(old, new)
    applied[key or old[:40]] = n
    return True


def need1(old, new, key=None):
    n = body.count(old)
    if n != 1:
        MISS.append(f'miss(x{n}): ' + (key or old[:70]))
        return False
    return need(old, new, key)


def open_tag_end(s, idx):
    gt = s.find('>', idx)
    return -1 if gt < 0 else gt + 1


def match_close(s, open_start):
    """Index just past the close tag matching the element opening at open_start."""
    m = re.match(r'<([a-zA-Z0-9-]+)', s[open_start:])
    if not m:
        return -1
    tag = m.group(1).lower()
    void = {'img', 'br', 'hr', 'input', 'meta', 'link', 'source', 'path',
            'circle', 'rect', 'use', 'area', 'col'}
    if tag in void:
        return open_tag_end(s, open_start)
    depth, i = 0, open_start
    pat = re.compile(r'<(/?)' + tag + r'\b', re.I)
    while True:
        mm = pat.search(s, i)
        if not mm:
            return -1
        gt = s.find('>', mm.start())
        if mm.group(1) == '/':
            depth -= 1
            if depth == 0:
                return gt + 1
        elif not s[mm.start():gt].rstrip().endswith('/'):
            depth += 1
        i = mm.end()


def find_by_attr(s, attr, lo=0):
    i = s.find(attr, lo)
    if i < 0:
        return (-1, -1)
    start = s.rfind('<', 0, i)
    return (start, match_close(s, start))


def section_span(anchor, lo=0):
    """(start, end) of the <section> containing `anchor`.

    `anchor` may itself start with `<section`, in which case the rfind must
    include its own offset — otherwise the enclosing section is matched.
    """
    i = body.find(anchor, lo)
    if i < 0:
        return (-1, -1)
    # rfind's end bound is the index *after* the last allowed match, so the
    # whole '<section' token must fit inside it.
    start = body.rfind('<section', 0, i + len('<section'))
    return (start, match_close(body, start))


def replace_section(anchor, markup, label=None):
    global body
    a, b = section_span(anchor)
    if a < 0:
        MISS.append('section miss: ' + (label or anchor))
        return False
    body = body[:a] + markup + body[b:]
    applied['section:' + (label or anchor)] = 1
    return True


def cut_section(anchor, label=None):
    """Remove the section and return its markup."""
    global body
    a, b = section_span(anchor)
    if a < 0:
        MISS.append('cut miss: ' + (label or anchor))
        return ''
    markup = body[a:b]
    body = body[:a] + body[b:]
    applied['cut:' + (label or anchor)] = 1
    return markup


def insert_before(anchor, markup, label=None):
    global body
    a, _ = section_span(anchor)
    if a < 0:
        MISS.append('insert miss: ' + (label or anchor))
        return False
    body = body[:a] + markup + body[a:]
    applied['insert:' + (label or anchor)] = 1
    return True


# ------------------------------------------------------------------ source
here = os.path.dirname(os.path.abspath(__file__))
os.chdir(os.path.dirname(here))


def bootstrap_ref():
    """Rebuild the pristine snapshot from the commit that first added index.html.

    Never fall back to copying the *current* index.html: once this script has
    run, that file is already reshaped and every anchored replacement would be
    applied a second time on top of itself.
    """
    import subprocess
    try:
        sha = subprocess.check_output(
            ['git', 'log', '--diff-filter=A', '--format=%H', '--', OUT],
            stderr=subprocess.DEVNULL, text=True).strip().split('\n')[-1]
        if not sha:
            raise RuntimeError('index.html has no history')
        html = subprocess.check_output(
            ['git', 'show', sha + ':' + OUT], stderr=subprocess.DEVNULL)
    except Exception as exc:  # pragma: no cover - environment dependent
        sys.exit('pristine snapshot %s is missing and could not be rebuilt '
                 'from git (%s).\nRestore it, e.g. '
                 '`git show <sha>:index.html > %s`.' % (REF, exc, REF))
    os.makedirs(os.path.dirname(REF), exist_ok=True)
    with open(REF, 'wb') as fh:
        fh.write(html)
    print('bootstrapped %s from git commit %s' % (REF, sha[:8]))


if not os.path.exists(REF):
    bootstrap_ref()
body = open(REF, encoding='utf-8').read()
before_len = len(body)

ARROW = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
         'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
         'stroke-linejoin="round" class="lucide lucide-arrow-right h-3.5 w-3.5" '
         'aria-hidden="true"><path d="M5 12h14"></path><path d="m12 5 7 7-7 7"></path></svg>')
ARROW4 = ARROW.replace('h-3.5 w-3.5', 'h-4 w-4')
ARROW_R = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
           'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
           'stroke-linejoin="round" class="lucide lucide-arrow-right" aria-hidden="true">'
           '<path d="M5 12h14"></path><path d="m12 5 7 7-7 7"></path></svg>')

# Inline "thinking" orb for the hero overline. The arc length (8 of a ~53.4
# circumference) leaves a single visible sweep, which `.tf-thinking-spin` rotates
# while `.tf-thinking-core` breathes. Both animations are defined in custom.css
# and disabled under prefers-reduced-motion.
HARNESS_ORB = (
    '<svg class="tf-thinking" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
    '<defs><linearGradient id="tf-thinking-grad" x1="0" y1="0" x2="1" y2="1">'
    '<stop offset="0" stop-color="#9fcfff"></stop>'
    '<stop offset=".45" stop-color="#ffffff"></stop>'
    '<stop offset="1" stop-color="#ff8a3d"></stop>'
    '</linearGradient></defs>'
    '<circle class="tf-thinking-track" cx="12" cy="12" r="8.5" fill="none" '
    'stroke="currentColor" stroke-opacity=".16" stroke-width="2"></circle>'
    '<g class="tf-thinking-spin"><circle cx="12" cy="12" r="8.5" fill="none" '
    'stroke="url(#tf-thinking-grad)" stroke-width="2" stroke-linecap="round" '
    'stroke-dasharray="8 45.4"></circle></g>'
    '<circle class="tf-thinking-core" cx="12" cy="12" r="3" fill="url(#tf-thinking-grad)"></circle>'
    '</svg>')


# ======================================================= stages, in order
def stage_head():
    global body
    need('<title>晓石云 | 智算为中心的 AI 原生云内核 — 成都破晓石科技</title>',
         '<title>晓石云 | Rune Harness 云智算内核 — Rune 智算 · Moha 资产 · AIRouter 网关 · BOSS 运营</title>',
         'title')
    need('content="专注云原生开源、混合云与 AI 智算平台，为企业提供覆盖容器云、混合云、智算云及 AI 能力的全栈解决方案。"',
         'content="晓石云以 Rune 智算、Moha 资产、AIRouter 网关、BOSS 运营四大核心板块为基座，'
         '打造 Rune Harness 云智算内核，为企业提供私有化的 AI 智算平台与云管理能力。"',
         'meta description')


ICONS = {
    'rune': '<rect width="8" height="8" x="3" y="3" rx="2"/><path d="M7 11v4a2 2 0 0 0 2 2h4"/>'
            '<rect width="8" height="8" x="13" y="13" rx="2"/>',
    'moha': '<path d="M8.24 1.56a.5.5 0 0 0-.48 0l-7.5 4a.5.5 0 0 0 0 .88L3.19 8 .26 9.56a.5.5 0 0 0 0 .88'
            'l7.5 4a.5.5 0 0 0 .48 0l7.5-4a.5.5 0 0 0 0-.88L12.81 8l2.93-1.56a.5.5 0 0 0 0-.88l-7.5-4Z"/>',
    'airouter': '<circle cx="6" cy="19" r="3"/><path d="M9 19h8.5a3.5 3.5 0 0 0 0-7h-11a3.5 3.5 0 0 1 0-7H15"/>'
                '<circle cx="18" cy="5" r="3"/>',
    'boss': '<rect width="7" height="9" x="3" y="3" rx="1"/><rect width="5" height="5" x="14" y="3" rx="1"/>'
            '<rect width="5" height="9" x="14" y="10" rx="1"/><rect width="7" height="5" x="3" y="16" rx="1"/>',
}

BOARDS = [
    ('rune', 'Rune', 'AI 训推平台', 'AI 训推一体平台，覆盖模型开发、训练、推理与部署全流程。',
     'https://www.poxiaoshi.cn/products/rune/', 'AI 训推一体平台。'),
    ('moha', 'Moha', 'AI 资产仓库', '私有化 AI 模型、数据集与镜像仓库，支持加密存储与版本治理。',
     'https://www.poxiaoshi.cn/products/moha/', '私有化 AI 资产仓库。'),
    ('airouter', 'AIRouter', '模型网关', '统一模型入口，协议翻译、策略路由与配额用量治理。',
     'https://www.poxiaoshi.cn/products/ai-router/', '统一模型网关。'),
    ('boss', 'BOSS', '平台运营', '面向智算中心运营方：租户、配额、计量与运营报表。',
     'https://console.poxiaoshi.cn', '智算中心运营控制台。'),
]


def stage_nav():
    global body
    # --- desktop 产品 dropdown: 3 entries (with swapped copy) -> 4 correct ones
    a, _ = find_by_attr(body, 'data-page-node-id="MxGAw2GdzzKKJRLgPDRZSM"')
    if a < 0:
        MISS.append('desktop 产品 trigger')
    else:
        da, db = find_by_attr(body, 'class="tf-nav-dropdown"', a)
        if da < 0:
            MISS.append('desktop 产品 dropdown')
        else:
            items = []
            for key, name, sub, desc, href, _short in BOARDS:
                tgt = ' target="_blank" rel="noopener noreferrer"' if href.startswith('http') else ''
                items.append(
                    f'<a href="{href}" class="tf-nav-dropdown-item"{tgt}>'
                    f'<span class="tf-nav-dropdown-icon">'
                    f'<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                    f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
                    f'aria-hidden="true">{ICONS[key]}</svg></span>'
                    f'<span><span class="tf-nav-dropdown-title">{name}</span>'
                    f'<span class="tf-nav-dropdown-description">{desc}</span></span></a>')
            body = body[:open_tag_end(body, da)] + ''.join(items) + body[db - 6:]
            applied['nav desktop dropdown'] = 1

    # --- 预约演示 console dropdown
    ca, cb = find_by_attr(body, 'class="tf-nav-console-dropdown"')
    if ca < 0:
        MISS.append('console dropdown')
    else:
        items = ['<p>选择产品_</p>']
        for key, name, _sub, _desc, href, short in BOARDS:
            tgt = ' target="_blank" rel="noopener noreferrer"' if href.startswith('http') else ''
            items.append(
                f'<a href="{href}" class="tf-nav-console-item"{tgt}>'
                f'<span class="tf-nav-console-icon">'
                f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
                f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
                f'stroke-linejoin="round" aria-hidden="true">{ICONS[key]}</svg></span>'
                f'<span><strong>{name}</strong><small>{short}</small></span>{ARROW_R}</a>')
        body = body[:open_tag_end(body, ca)] + ''.join(items) + body[cb - 6:]
        applied['nav console dropdown'] = 1

    # --- mobile drawer product group
    ma, mb = find_by_attr(body, 'data-page-node-id="GUpfus8Amy9mv701ZgQK0A"')
    if ma < 0:
        MISS.append('mobile drawer product group')
    else:
        links = []
        for key, name, _sub, _desc, href, _short in BOARDS:
            tgt = ' target="_blank" rel="noopener noreferrer"' if href.startswith('http') else ''
            links.append(
                f'<a href="{href}"{tgt} class="flex items-center gap-3 rounded-[var(--pl-radius-xxs)] '
                f'border border-white/10 bg-white/[0.04] px-4 py-3 font-mono text-sm text-white/72 '
                f'transition-colors">'
                f'<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
                f'aria-hidden="true">{ICONS[key]}</svg>{name}</a>')
        body = body[:open_tag_end(body, ma)] + ''.join(links) + body[mb - 6:]
        applied['nav mobile drawer'] = 1

    need('>Choose a platform<', '>选择产品<', 'mobile 选择产品')


def stage_hero():
    global body
    # The hero slogan and its subtitle are deliberately NOT touched: they carry
    # the company positioning line and stay as authored upstream. `stage_guards`
    # asserts both strings survive verbatim.
    #
    # The overline is a "coming soon" teaser for Rune Harness. Its leading mark
    # is replaced by an inline animated SVG: `.tf-overline::before` draws a static
    # white play triangle (see vendor.css), so this instance opts out of it via
    # `.tf-overline-live` and supplies a sweeping arc + breathing core instead —
    # the conventional "AI is thinking" read.
    need('<span class="tf-overline" data-page-node-id="xONwR8BFMrwJDv2uXW2pv2">云原生 · 混合云 · AI 智算</span>',
         '<span class="tf-overline tf-overline-live" data-page-node-id="xONwR8BFMrwJDv2uXW2pv2">'
         + HARNESS_ORB + 'Rune Harness 即将开放</span>',
         'hero overline')

    # hero pills (mobile)
    pa, pb = find_by_attr(body, 'class="mt-10 flex flex-wrap items-center justify-center gap-3 md:hidden"')
    if pa < 0:
        MISS.append('hero pills')
    else:
        pills = ''.join(
            f'<span class="tf-pill inline-flex items-center gap-2 border border-white/10 bg-white/[0.04] '
            f'px-3 py-2 text-sm text-white/72"><span class="h-2 w-2" style="background:{c}"></span>{t}</span>'
            for t, c in [('Rune 智算', 'rgba(159,233,255,.85)'), ('Moha 资产', 'rgba(215,197,255,.9)'),
                         ('AIRouter 网关', 'rgba(138,255,193,.85)'), ('BOSS 运营', 'rgba(255,179,107,.9)')])
        body = body[:open_tag_end(body, pa)] + pills + body[pb - 6:]
        applied['hero pills'] = 1

    need('>~/xmcp</p>', '>~/airouter</p>', 'hero terminal title')
    need('$ xiaoshi xmcp attach cluster --cloud huawei', '$ xiaoshi airouter route --model approved',
         'hero terminal cmd')
    need('✔ 多云已纳管', '✔ 模型调用已授权', 'hero terminal ok')
    need('→ 配额与计费就绪', '→ 用量已计量入账', 'hero terminal info')

    need('Rune 2.6 正式发布：训推一体流水线支持英伟达与国产 GPU 异构算力池，多租户配额与弹性伸缩同步上线。'
         '   ·   破晓石完成阿里云 PPU 适配，国产加速卡正式纳入 Rune 调度。',
         'Rune 智算 · Moha 资产 · AIRouter 网关 · BOSS 运营，四大板块共享一个云智算内核。'
         '   ·    Rune Harness 云智算内核进入规划：统一会话、诊断、变更审批与执行追踪。',
         'announcement')


def lane(idx, lane_key, icon_key, label, h3, copy, rows, link_text, href, active=False):
    rows_html = ''.join(f'<span><b>{k}</b>{v}</span>' for k, v in rows)
    tgt = ' target="_blank" rel="noopener noreferrer"' if href.startswith('http') else ''
    return (
        f'<div class="tf-control-lane tf-control-{lane_key}{" is-active" if active else ""}">'
        f'<div class="tf-control-lane-icon">'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{ICONS[icon_key]}</svg></div>'
        f'<p class="tf-runtime-label">{idx} / {label}</p><h3>{h3}</h3><p>{copy}</p>'
        f'<div class="tf-control-lane-summary">{rows_html}</div>'
        f'<a href="{href}"{tgt}>{link_text} {ARROW}</a></div>')


def stage_story():
    global body
    """三大核心产品 -> 四大核心板块 + Rune Harness 内核带。"""
    tabs = ''.join(
        f'<button type="button" role="tab" aria-selected="{"true" if i == 0 else "false"}" '
        f'class="{"is-active" if i == 0 else ""}"><span>0{i + 1}</span>{name}</button>'
        for i, (_k, name, _s, _d, _h, _sh) in enumerate(BOARDS))

    lanes = ''.join([
        lane(1, 'runtime', 'rune', 'Rune · AI 训推平台', '跑通每一次训练。',
             '训练任务、推理服务与算力配额在这里统一编排。',
             [('任务', 'rune-job-2048'), ('GPU 配额', '8 × A800 · pool-cn-southwest'), ('状态', '运行中')],
             '进入 Rune', 'https://www.poxiaoshi.cn/products/rune/', active=True),
        lane(2, 'audit', 'moha', 'Moha · AI 资产仓库', '沉淀每一份资产。',
             '模型、数据集与镜像沉淀为可检索、可追溯的加密资产。',
             [('资产', 'moha/model-llama-3.1'), ('版本', '12 个版本'), ('加密', 'AES-256 已启用')],
             '进入 Moha', 'https://www.poxiaoshi.cn/products/moha/'),
        lane(3, 'airouter', 'airouter', 'AIRouter · 模型网关', '收敛每一次调用。',
             '一个入口接入各家大模型，协议翻译、策略路由与用量审计一次到位。',
             [('模型', '32 个已上架'), ('峰值 QPS', '4.2k'), ('策略', '已授权')],
             '进入 AIRouter', 'https://www.poxiaoshi.cn/products/ai-router/'),
        lane(4, 'boss', 'boss', 'BOSS · 平台运营', '看清每一笔消耗。',
             '租户、配额、计量与运营数据在同一个控制台闭环。',
             [('租户', '36 个在管'), ('配额', '已分配 78%'), ('计量', '实时出账')],
             '进入 BOSS', 'https://console.poxiaoshi.cn'),
    ])

    markup = (
        '<section class="tf-runtime-story text-white"><div class="tf-runtime-story-heading">'
        '<p class="tf-runtime-overline">Rune · Moha · AIRouter · BOSS</p>'
        '<h2>四大核心板块，一个云智算内核。</h2>'
        '<p>Rune 承载 AI 训推，Moha 沉淀模型与数据资产，AIRouter 统一模型网关，BOSS 支撑平台运营与治理。'
        '四者共享同一套权限、配额与可观测体系，共同构成 Rune Harness 云智算内核的基座。</p></div>'
        '<div class="tf-control-stage-nav" role="tablist" aria-label="晓石云四大核心板块">'
        + tabs +
        '</div><div class="tf-control-plane">'
        '<div class="tf-control-plane-bar">'
        '<div class="tf-runtime-console-dots" aria-hidden="true"><span></span><span></span><span></span></div>'
        '<span>~/xiaoshi/control-plane.yaml</span>'
        '<span class="tf-runtime-console-status">四板块在线</span></div>'
        '<div class="tf-control-plane-body">' + lanes + '</div>'
        '<div class="tf-control-harness">'
        '<div class="tf-control-harness-mark"><img src="assets/img/icon-mark.svg" alt=""></div>'
        '<div class="tf-control-harness-copy">'
        '<p class="tf-runtime-label">Rune Harness · 云智算内核</p>'
        '<h3>四大板块之上，一个统一的智算操作内核。</h3>'
        '<p>Rune Harness 统一会话、资源发现、诊断、变更计划、审批与执行追踪，'
        '把四大板块的能力收敛为一个入口。</p></div>'
        '<div class="tf-control-harness-chips">'
        '<span>统一会话</span><span>双安全域</span><span>Plan → Approval → Apply</span>'
        '<span>执行可追溯</span></div></div>'
        '<div class="tf-control-plane-result"><span class="tf-runtime-label">当前结果</span>'
        '<p>✓ 四大板块共享同一套权限、配额与可观测体系</p>'
        '<span>向下由 XCMP 云管理能力提供多云资源底座，向上沉淀为 Rune Harness 云智算内核。</span>'
        '</div></div></section>')
    replace_section('class="tf-runtime-story text-white"', markup, '四大核心板块')


def stage_xcmp():
    global body
    """XMCP 深潜 section -> 紧凑的云管理能力优势带（不展开技术细节）。"""
    cards = [
        ('自动纳管', '识别并接入 Kubernetes、vCenter、OpenStack 与华为云等平台，一次配置即可统一纳管。'),
        ('零信任 Mesh', '跨云通道自动加密，安全策略跟随资源本身，而不是跟随网络位置。'),
        ('统一计量计费', '按租户、命名空间与节点维度实时采集用量，直接对接运营出账。'),
        ('异构资源池', '容器、虚拟机与裸金属在同一个编排面内统一调度与配额管理。'),
        ('信创兼容', '兼容国产服务器、操作系统与算力芯片，支持全栈私有化交付。'),
        ('离线可用', '支持离线环境安装与升级，满足内网与专网部署的安全要求。'),
    ]
    grid = ''.join(
        f'<div class="tf-advantage-card"><span class="tf-advantage-index">0{i + 1}</span>'
        f'<h3>{t}</h3><p>{d}</p></div>'
        for i, (t, d) in enumerate(cards))

    markup = (
        '<section id="gateway" class="tf-section scroll-mt-[90px] text-white tf-motion-section" '
        'style="--tf-motion-order: 1;">'
        '<div class="tf-section-inner tf-section-frame tf-section-wash tf-advantage-inner">'
        '<div class="tf-advantage-head">'
        '<span class="tf-overline">XCMP · 云管理能力</span>'
        '<h2 class="tf-section-title mt-5">把多云真正用成一朵云。</h2>'
        '<p class="tf-section-copy">XCMP 是晓石云的云管理能力底座：自动识别并接入 Kubernetes、vCenter、'
        'OpenStack 与主流公有云，以零信任 Mesh 保障跨云通信，统一策略、统一计量。'
        '它已在 Rune、Moha、AIRouter、BOSS 四大板块之下稳定运行——这里只呈现能力优势，不展开技术实现。</p>'
        '</div><div class="tf-advantage-grid">' + grid + '</div>'
        '<a href="https://console.poxiaoshi.cn" target="_blank" rel="noopener noreferrer" '
        'class="tf-section-link">进入 XCMP ' + ARROW4 + '</a>'
        '</div></section>')
    replace_section('<section id="gateway"', markup, 'XCMP 能力优势')


def stage_rune_moha():
    global body
    # Rune 板块标题
    need('<span class="tf-overline" data-page-node-id="3p3AJIT3xlc3jNbuAEK2Ul">Rune · AI 训推平台</span>',
         '<span class="tf-overline" data-page-node-id="3p3AJIT3xlc3jNbuAEK2Ul">Rune 智算 · AI 训推平台（板块 01）</span>',
         'rune overline')
    # Moha 板块标题
    need('<span class="tf-overline" data-page-node-id="pIgVjtQ6hHonlcqCMluRKe">Moha · AI 资产仓库</span>',
         '<span class="tf-overline" data-page-node-id="pIgVjtQ6hHonlcqCMluRKe">Moha 资产 · AI 资产仓库（板块 02）</span>',
         'moha overline')


def stage_airouter():
    global body
    need1('通过 AI Router 统一调用各家大模型与多模态能力；XMCP 负责通道治理，Moha 保留每一次调用的完整记录。',
          'AIRouter 是晓石云的统一模型网关：一个入口接入各家大模型与多模态能力，'
          '统一密钥与配额、按策略路由请求，并保留每一次调用的用量与审计记录。',
          'airouter copy')
    need('>了解 AI Router <', '>了解 AIRouter <', 'airouter link')
    need('>AI Router API</span>', '>AIRouter API</span>', 'airouter api label')
    need('aria-label="AI Router 接入示例"', 'aria-label="AIRouter 接入示例"', 'airouter tabs label')
    need('<h2 data-page-node-id="j1cabH5RCrpZ6zuopg1PKx">一个入口，接入所有大模型。</h2>',
         '<span class="tf-block-overline">AIRouter 网关 · 板块 03</span>'
         '<h2 data-page-node-id="j1cabH5RCrpZ6zuopg1PKx">一个入口，接入所有大模型。</h2>',
         'airouter heading eyebrow')


def stage_boss():
    global body
    metrics = [
        ('在管租户', '36', '+4 本季度'),
        ('已分配配额', '78%', '1.24 P GPU 卡时'),
        ('本月用量', '412 TB·h', '环比 +12%'),
        ('待出账', '0', '已全部核销'),
    ]
    metric_html = ''.join(
        f'<div class="tf-boss-metric"><b>{k}</b><span>{v}</span><i>{n}</i></div>'
        for k, v, n in metrics)
    rows = [
        ('edu-university-a', 'pool-cn-southwest', '128 TB·h', '已出账', 'ok'),
        ('energy-makinu', 'pool-me-east-1', '96 TB·h', '已出账', 'ok'),
        ('ai-lab-chengdu', 'pool-cn-southwest', '74 TB·h', '计量中', 'live'),
        ('maker-space-03', 'pool-cn-north-2', '38 TB·h', '配额预警', 'warn'),
        ('lab-med-imaging', 'pool-cn-east-1', '52 TB·h', '已出账', 'ok'),
        ('gov-datacenter-01', 'pool-cn-north-2', '24 TB·h', '计量中', 'live'),
    ]
    table = ('<div class="tf-boss-row is-head"><span>租户</span><span>资源池</span>'
             '<span>本月用量</span><span>状态</span></div>')
    table += ''.join(
        f'<div class="tf-boss-row"><span>{t}</span><span>{p}</span><span>{u}</span>'
        f'<span class="is-{c}">{s}</span></div>' for t, p, u, s, c in rows)

    bars = ''.join(f'<i style="--v:{v}"></i>'
                   for v in ['42%', '55%', '48%', '63%', '58%', '72%', '68%', '86%'])
    trend = ('<div class="tf-boss-trend">'
             '<div class="tf-boss-trend-head"><span>近 8 期算力用量 · P GPU 卡时</span>'
             '<span>环比 +12%</span></div>'
             f'<div class="tf-boss-bars" aria-hidden="true">{bars}</div></div>')

    markup = (
        '<section id="boss" class="tf-section scroll-mt-[90px] text-white tf-motion-section" '
        'style="--tf-motion-order: 4;">'
        '<div class="tf-section-inner tf-section-frame tf-section-wash">'
        '<div class="tf-section-split"><div class="tf-section-sidebar">'
        '<span class="tf-overline">BOSS 运营 · 板块 04</span>'
        '<h2 class="tf-section-title mt-5">看清每一笔消耗，管住每一个租户。</h2>'
        '<p class="tf-section-copy">BOSS 面向智算中心与平台的运营方：租户开户、配额分配、计量计费、'
        '资源水位与运营报表在同一控制台闭环，运营决策不再依赖人工台账。</p>'
        '<a href="https://console.poxiaoshi.cn" target="_blank" rel="noopener noreferrer" '
        'class="tf-section-link">进入 BOSS ' + ARROW4 + '</a>'
        '<div class="tf-gateway-capabilities" aria-label="BOSS 运营能力">'
        '<p>BOSS 运营路径</p>'
        '<div><span>01</span><div><h3>开户与授权</h3>'
        '<p>租户、组织与成员在一个入口完成开户与权限下发。</p></div></div>'
        '<div><span>02</span><div><h3>配额与调度</h3>'
        '<p>按租户、资源池与队列分配算力配额，超限自动拦截。</p></div></div>'
        '<div><span>03</span><div><h3>计量与出账</h3>'
        '<p>GPU 时长、存储与调用量实时计量，按月出账并可导出。</p></div></div>'
        '</div></div><div class="tf-panel tf-boss-panel">'
        '<div class="tf-gateway-panel-bar"><div><p>运营视图</p>'
        '<span>2026 年 9 月 · 智算中心 A</span></div></div>'
        '<div class="tf-boss-metrics">' + metric_html + '</div>'
        '<div class="tf-boss-table">' + table + '</div>'
        + trend +
        '<div class="tf-boss-foot"><span>计量周期 2026-09-01 ~ 2026-09-30</span>'
        '<span>✓ 出账已生成</span></div>'
        '</div></div></div></section>')
    insert_before('<section id="blog"', markup, 'BOSS 板块')


def stage_harness():
    global body
    phases = [
        ('阶段一 · 统一操作入口',
         '把分散在各控制面的操作收敛到一个会话入口，调用者不再需要理解多套资源标识、权限和状态机。',
         ['跨资源关联状态、事件、日志与指标', '统一会话与实时权限约束', '面向租户用户的 Tenant Harness']),
        ('阶段二 · 双安全域隔离',
         'Tenant Harness 与 BOSS Harness 属于同一产品，但是两个隔离的安全域，而不是同一个 Agent 的权限开关。',
         ['会话绑定安全域，创建后不可切换', 'BOSS 内置 Kubernetes 运维技能', '短时能力授予，不持有长期凭据']),
        ('阶段三 · 云智算内核',
         '智算、资产、网关与运营在同一个内核里协同，成为平台唯一的智能操作面。',
         ['模型推理统一经 AIRouter 出入', '写操作 Plan → Approval → Apply', '全链路执行证据可追溯']),
    ]
    grid = ''.join(
        f'<div class="tf-harness-phase"><span>{n}</span><h3>{t}</h3><p>{d}</p>'
        + '<ul>' + ''.join(f'<li>{x}</li>' for x in items) + '</ul></div>'
        for n, (t, d, items) in zip(['01', '02', '03'], phases))

    steps = [
        ('ActionManifest', 'Rune 对 Action 的权威声明', '定义受众、目标、权限、风险与结果语义。'),
        ('ChangeSet', '服务端生成的不可变变更计划', '绑定目标、影响、前置条件、审批规则与过期时间。'),
        ('Approval', '有权用户的一次显式决定', '聊天里的「确认」不构成 Approval。'),
        ('Apply', '通过授权与审批后的执行', '执行前再次校验权限、版本与策略。'),
        ('ExecutionReceipt', '不可变的执行证据', '异步场景下进一步跟踪真正的 Operation。'),
    ]
    step_html = ''.join(
        f'<div class="tf-harness-flow-step"><b>{i + 1:02d}</b><strong>{t}</strong>'
        f'<p>{d}</p><span>{x}</span></div>'
        for i, (t, d, x) in enumerate(steps))

    markup = (
        '<section id="harness" class="tf-section scroll-mt-[90px] text-white tf-motion-section" '
        'style="--tf-motion-order: 5;">'
        '<div class="tf-section-inner tf-section-frame tf-section-wash">'
        '<div class="tf-harness-head">'
        '<span class="tf-overline">Rune Harness · 云智算内核（规划中）</span>'
        '<h2 class="tf-section-title mt-5">以四大板块为基座，打造云智算内核。</h2>'
        '<p class="tf-section-copy">四大板块各自拥有完整的领域事实。Rune Harness 不重建这些事实，'
        '而是提供一层小而深的操作入口：在一个会话里发现资源、关联证据、形成诊断、生成变更计划、'
        '按风险完成审批并可靠执行。这是晓石云从「产品集合」走向「云智算内核」的关键一步。</p>'
        '</div><div class="tf-harness-grid">' + grid + '</div>'
        '<div class="tf-harness-flow">'
        '<div class="tf-harness-flow-bar"><p>ActionManifest → ChangeSet → Approval → Apply</p>'
        '<span>R3 及以上风险需重新认证与显式审批</span></div>'
        '<div class="tf-harness-flow-steps">' + step_html + '</div>'
        '</div></div></section>')
    insert_before('<section id="blog"', markup, 'Harness 规划板块')

    # 定价区排到 Harness 之后
    pricing = cut_section('<section id="pricing"', '定价区前移')
    if pricing:
        at, _ = section_span('<section id="blog"')
        if at < 0:
            MISS.append('pricing reinsert anchor')
        else:
            body = body[:at] + pricing + body[at:]
            applied['pricing moved before blog'] = 1


def stage_pricing():
    global body
    need1('XMCP 与 Moha 采用订阅制授权，Rune 按算力与任务量计费，交付与实施服务按项目范围报价。',
          'Rune 按算力与任务量计费，Moha 与 AIRouter 采用订阅制授权，BOSS 面向智算中心运营方按纳管规模订阅，'
          '交付与实施服务按项目范围报价。', 'pricing intro')
    # card 02 -> Moha, card 03 -> AIRouter (keep the board order used above)
    need('<h3 data-page-node-id="oMpelstFk1ivXB3MrICyCg">XMCP</h3>',
         '<h3 data-page-node-id="oMpelstFk1ivXB3MrICyCg">Moha</h3>', 'pricing card 02 name')
    need('<strong data-page-node-id="ixDIlEntVGAL4IfEWrViZJ">订阅 + 节点</strong>',
         '<strong data-page-node-id="ixDIlEntVGAL4IfEWrViZJ">订阅 + 容量</strong>', 'pricing card 02 unit')
    need('<p data-page-node-id="Vw3gxOxts71NBWYoMgxj9w">按纳管集群与节点规模订阅授权。</p>',
         '<p data-page-node-id="Vw3gxOxts71NBWYoMgxj9w">按资产仓库容量与存储时长计费。</p>',
         'pricing card 02 copy')
    need('<h3 data-page-node-id="GC2aAg6dx0GMGQ2EmIe6nH">Moha</h3>',
         '<h3 data-page-node-id="GC2aAg6dx0GMGQ2EmIe6nH">AIRouter</h3>', 'pricing card 03 name')
    need('<strong data-page-node-id="zQEw1QLJgdOUJMG9s3xIrW">订阅 + 节点</strong>',
         '<strong data-page-node-id="zQEw1QLJgdOUJMG9s3xIrW">按调用量阶梯</strong>', 'pricing card 03 unit')
    need('<p data-page-node-id="tmafbdqPfcjFV9Uba3N4Ew">按资产仓库容量与存储时长计费。</p>',
         '<p data-page-node-id="tmafbdqPfcjFV9Uba3N4Ew">网关调用按阶梯计价，企业版支持专属配额与私有化部署。</p>',
         'pricing card 03 copy')
    # card 04: 交付与实施服务 -> BOSS 运营
    need('<h3 data-page-node-id="TS3C06yrka0W0iTGc0dHM2">交付与实施服务</h3>',
         '<h3 data-page-node-id="TS3C06yrka0W0iTGc0dHM2">BOSS</h3>', 'pricing card 04 name')
    need('<strong data-page-node-id="9H4vJnTaNPDn0wZxkAwH7Q">定制报价</strong>',
         '<strong data-page-node-id="9H4vJnTaNPDn0wZxkAwH7Q">按纳管规模订阅</strong>', 'pricing card 04 unit')
    need('<p data-page-node-id="vG555PyLIzBlhCTjBGA1ep">按项目范围提供开发与生产交付。</p>',
         '<p data-page-node-id="vG555PyLIzBlhCTjBGA1ep">面向智算中心运营方，含租户、配额与计量出账能力。</p>',
         'pricing card 04 copy')
    need1('AI Router API：按调用量阶梯计费，企业版支持私有化部署与专属配额。',
          '交付与实施服务按项目范围定制报价；XCMP 云管理能力随平台统一交付。', 'pricing note')


def faq_item(idx, q, a, delay):
    return (
        f'<div class="" style="opacity:0;transform:translate3d(0px, -28px, 0);'
        f'transition-property:opacity, transform;transition-duration:0.55s;'
        f'transition-delay:{delay}s;transition-timing-function:cubic-bezier(0.22, 1, 0.36, 1);'
        f'will-change:opacity, transform"><article class="">'
        f'<button class="tf-faq-question-row" type="button" aria-expanded="false">'
        f'<span class="tf-faq-question-content"><span>{idx}</span><b>{q}</b></span>'
        f'<span class="tf-faq-action-icon"><img src="assets/img/icon-plus.svg" alt="" class=""></span>'
        f'</button><div class="tf-faq-answer-row" aria-hidden="true"><div><p>{a}</p></div></div>'
        f'</article></div>')


def stage_faq():
    global body
    need1('晓石云覆盖云原生开源、混合云与 AI 智算平台。XMCP 负责多云纳管，Rune 提供 AI 训推一体化能力，'
          'Moha 沉淀模型与数据资产，AI Router 与 ChatBox 面向 AI 应用层。',
          '晓石云的产品矩阵由四大核心板块组成：Rune 承载 AI 训推，Moha 沉淀模型与数据资产，'
          'AIRouter 统一模型网关，BOSS 面向智算中心运营方提供租户、配额与计量管理。'
          'XCMP 云管理能力为四大板块提供多云资源底座，并共同向 Rune Harness 云智算内核演进。',
          'faq 01')
    need1('支持。XMCP 可自动识别并接入 Kubernetes、vCenter、OpenStack、华为云等平台；'
          'Rune 兼容主流训练框架与 Transformer 生态，并提供集成 IDE 与桌面仿真环境。',
          '支持。AIRouter 兼容 OpenAI 等主流接口协议，替换 base URL 即可接入；'
          'XCMP 可自动识别并接入 Kubernetes、vCenter、OpenStack、华为云等平台；'
          'Rune 兼容主流训练框架与 Transformer 生态，并提供集成 IDE 与桌面仿真环境。',
          'faq 03')

    # 定位最后一条 FAQ，把它连同两条新增项一起重建
    anchor = 'XMCP、Rune、Moha 与 AI Router 均已提供商业版，可通过官网演示，我们会在一个工作日内与您联系，并安排专家团队深入交流。'
    anchor = anchor.replace('官网演示', '官网预约演示')
    idx_tail = body.find('XMCP、Rune、Moha 与 AI Router 均已提供商业版')
    if idx_tail < 0:
        MISS.append('faq last item')
    else:
        wrap = body.rfind('<div class="" style=', 0, idx_tail)
        w_end = match_close(body, wrap)
        if wrap < 0 or w_end < 0:
            MISS.append('faq last wrapper')
        else:
            rebuilt = faq_item('07', '如何获取产品与试用？',
                               'Rune、Moha、AIRouter 与 BOSS 均已提供商业版，XCMP 云管理能力随平台交付。'
                               '可通过官网预约演示，我们会在一个工作日内与您联系，并安排专家团队深入交流。',
                               '0.5')
            rebuilt += faq_item('08', 'BOSS 面向谁？',
                                'BOSS 面向智算中心与平台的运营方：租户开户与授权、算力配额分配、'
                                'GPU 时长与存储计量、按月出账与运营报表，都在同一个控制台完成。', '0.57')
            rebuilt += faq_item('09', 'Rune Harness 云智算内核是什么？',
                                'Rune Harness 是晓石云正在规划的平台级智能操作内核，由 Tenant Harness 与 '
                                'BOSS Harness 两个隔离安全域组成，统一会话、资源发现、诊断、变更计划、'
                                '审批与执行追踪。它不重建各领域事实，也不持有底层长期凭据；'
                                '写操作一律走 Plan → Approval → Apply。', '0.64')
            body = body[:wrap] + rebuilt + body[w_end:]
            applied['faq items rebuilt'] = 1


def stage_footer_cta():
    global body
    # 页脚「产品」列：四大板块置顶，XCMP 作为云管理能力
    fa, fb = find_by_attr(body, 'data-page-node-id="DSx57Z0vBkGaSPFY5k1RWp"')
    if fa < 0:
        MISS.append('footer 产品列')
    else:
        links = [
            ('产品总览', 'https://www.poxiaoshi.cn/', True),
            ('Rune 智算', 'https://www.poxiaoshi.cn/products/rune/', True),
            ('Moha 资产', 'https://www.poxiaoshi.cn/products/moha/', True),
            ('AIRouter 网关', 'https://www.poxiaoshi.cn/products/ai-router/', True),
            ('BOSS 运营', 'https://console.poxiaoshi.cn', True),
            ('XCMP 云管理', 'https://www.poxiaoshi.cn/products/xmcp/', True),
            ('KubeGems', 'https://kubegems.io', True),
        ]
        html = ''.join(
            f'<a class="tf-footer-link hover-scramble" href="{h}"'
            f'{" target=\"_blank\" rel=\"noopener noreferrer\"" if ext else ""}>{t}</a>'
            for t, h, ext in links)
        body = body[:open_tag_end(body, fa)] + html + body[fb - 6:]
        applied['footer 产品列'] = 1

    need('>云原生与 AI 之旅？</strong>', '>云智算内核之旅？</strong>', 'cta h2')
    need('一个底座，贯穿多云纳管到 AI 训推全流程。',
         '四大板块为基座，共同构建 Rune Harness 云智算内核。', 'cta copy')
    # blog snippet still used the retired XMCP naming
    need('通过 XMCP 统一纳管多地域资源', '通过 XCMP 统一纳管多地域资源', 'blog XCMP naming')


def stage_guards():
    global body
    """Sanity checks that must not regress."""
    opens = len(re.findall(r'<div\b', body))
    closes = len(re.findall(r'</div>', body))
    if opens != closes:
        MISS.append(f'unbalanced <div>: {opens} vs {closes} (delta {opens - closes})')
    for leftover in ('XMCP · 多云纳管', '不改现有体系，纳管每一朵云。', '三大核心产品',
                     'PipeLLM', 'pipellm.ai', 'AI Router', 'ChatBox'):
        if leftover in body:
            MISS.append('leftover copy: ' + leftover)
    for required in ('Rune Harness 即将开放', 'tf-overline-live', 'tf-thinking-spin',
                     '智算为中心的 </span>', 'AI 原生云内核</span>',
                     '专注云原生开源、混合云与 AI 智算平台，为企业提供覆盖容器云、混合云、智算云及 AI 能力的全栈解决方案。',
                     'Rune Harness · 云智算内核', 'tf-control-harness', 'tf-advantage-grid',
                     'tf-boss-metrics', 'tf-harness-flow', 'id="harness"', 'id="boss"'):
        if required not in body:
            MISS.append('missing: ' + required)


for fn in (stage_head, stage_nav, stage_hero, stage_story, stage_xcmp,
           stage_rune_moha, stage_airouter, stage_boss, stage_harness,
           stage_pricing, stage_faq, stage_footer_cta, stage_guards):
    fn()

open(OUT, 'w', encoding='utf-8').write(body)

print(f'reshaped {OUT}: {before_len} -> {len(body)} bytes')
print('applied:')
for k, v in applied.items():
    print(f'  + {k} x{v}')
if MISS:
    print('ISSUES:')
    for m in MISS:
        print('  !', m)
    sys.exit(1)
print('ok')
