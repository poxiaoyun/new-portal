#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""new-portal 内容页的公共派生库。

站内每个内容页（`about/`「公司简介」、`blog/`「公司动态」…）都是这么出来的：
外壳从已定稿的 `index.html` **整篇取来**，只做四件事 ——

  1. 换 head 的 `<title>` 与 `<meta description>`
  2. 追加本页的样式表 `<link>`
  3. 把 `<main>` 的内容换成这一页的板块
  4. 站内相对资源路径按页面深度加 `../` 前缀

导航、移动抽屉、页脚因此永远与首页逐字节相同；首页改了导航，重跑各页生成器即可
同步，不需要在两处改同一段标记。这是不引入模板引擎的前提下能做到的最小的重复面。

**路径深度**：`derive()` 的 `depth` 是产物相对站点根的层数，决定资源前缀：

    about/index.html                depth=1  ->  ../assets/
    blog/index.html                 depth=1  ->  ../assets/
    blog/<slug>/index.html          depth=2  ->  ../../assets/

`about/` 与 `blog/` 的深度恰好相同，所以 depth=1 是默认值；文章详情页是本项目第一个
两级深的产物，depth 参数就是为它加的。

`chrome_fingerprint()` 把这件事实变成可断言的不变量：它把「本页的站芯」归一化后
返回，生成器拿它与首页的同一函数结果逐字节比对。哪天有人手工编辑产物动了导航，
生成器会直接报错。

这些函数原本长在 `tools/build_about.py` 里，出现第二个内容页时才抽出来。
"""

import hashlib
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.join(ROOT, 'index.html')

# 首页 nav 里「关于我们」这一组（`公司简介` / `公司动态` 都在它的下拉里）。
# 用 data 属性定位而不是文本，避免上游改文案时锚点静默失效。
COMPANY_NAV_GROUP = 'class="tf-nav-product tf-nav-company"'

# 首页 nav 里「产品」这一组。产品子页（/products/*/）把 is-active 挪到它身上。
PRODUCT_NAV_GROUP = 'class="tf-nav-product tf-nav-product-menu"'


class Ctx(object):
    """一次生成过程的账本：缺失项与已应用项。"""

    __slots__ = ('miss', 'applied')

    def __init__(self):
        self.miss = []
        self.applied = {}


def esc(text):
    return (str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def ext(href):
    """站外链接统一开新窗口，站内链接保持同窗。"""
    if href.startswith('mailto:') or href.startswith('/') or href.startswith('.'):
        return ''
    return ' target="_blank" rel="noopener noreferrer"'


ARROW = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
         'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
         'stroke-linejoin="round" class="lucide lucide-arrow-right" aria-hidden="true">'
         '<path d="M5 12h14"></path><path d="m12 5 7 7-7 7"></path></svg>')
ARROW_S = ARROW.replace('class="lucide lucide-arrow-right"',
                        'class="lucide lucide-arrow-right h-3.5 w-3.5"')


def reveal(markup, delay=0.05, dy=28, duration=0.9):
    """首页同款的入场包裹：main.js 靠 style 里的 transition-property + opacity:0 认出它。

    `html:not(.js-ready)` 兜底写在 custom.css 里，JS 挂掉也不会留下空白。
    """
    return (
        '<div style="opacity:0;transform:translate3d(0px,%dpx, 0);'
        'transition-property:opacity, transform;transition-duration:%ss;'
        'transition-delay:%ss;transition-timing-function:cubic-bezier(0.22, 1, 0.36, 1);'
        'will-change:opacity, transform">%s</div>' % (dy, duration, delay, markup))


def brand_action(label, href, kind='primary'):
    """复刻首页 `.tf-brand-action`：逐字 span 挂 --tf-brand-char，悬停时错峰变色。

    字符序号用自然下标；首页那串 0/7/2/9 是上游随手写的，没有语义。
    """
    chars = ''.join('<span style="--tf-brand-char:%d">%s</span>' % (i, esc(ch))
                    for i, ch in enumerate(label))
    corners = ''.join('<i class="tf-brand-action-corner is-%s" aria-hidden="true"></i>' % c
                      for c in ('top-left', 'top-right', 'bottom-left', 'bottom-right'))
    return (
        '<a href="%s"%s class="tf-brand-action tf-button tf-button-%s">'
        '<span class="tf-brand-action-label" aria-hidden="true">%s</span>'
        '<span class="sr-only">%s</span>%s</a>'
        % (href, ext(href), kind, chars, esc(label), corners))


def overline(text, live=False):
    return '<span class="tf-overline%s">%s</span>' % (' tf-overline-live' if live else '',
                                                      esc(text))


def code_divider(url, order):
    """首页区块之间的分隔：一行代码 + 光标。结构照抄 index.html 的 .tf-faq-code-divider。"""
    return (
        '<section class="tf-faq-section-divider tf-motion-section" aria-hidden="true" '
        'style="--tf-motion-order: %d;">'
        '<div class="tf-faq-section-divider-inner"><div class="tf-faq-code-divider">'
        '<span></span><p>const next = await fetch("%s");<b>_</b></p><span></span>'
        '</div></div></section>' % (order, url))


VOID = {'br', 'img', 'input', 'link', 'meta', 'source', 'hr', 'area', 'col', 'embed',
        'track', 'wbr'}

_TAG = re.compile(r'<(/?)([a-zA-Z][a-zA-Z0-9-]*)((?:"[^"]*"|\'[^\']*\'|[^>"\'])*)(/?)>')


def match_close(src, open_start):
    """从某个开标签的 '<' 位置找到配对的闭合标签起点。"""
    m = re.match(r'<([a-zA-Z][a-zA-Z0-9-]*)', src[open_start:])
    if not m:
        return -1
    tag = m.group(1).lower()
    depth = 0
    for mm in _TAG.finditer(src, open_start):
        close, name, _attrs, self_close = mm.group(1), mm.group(2).lower(), mm.group(3), mm.group(4)
        if name != tag:
            continue
        if close:
            depth -= 1
            if depth == 0:
                return mm.start()
        elif not self_close:
            depth += 1
    return -1


def block(src, open_marker, label, ctx):
    """取出一个自闭合区间：[open_marker 的开标签 … 配对闭合标签)，两端都是 `<`。"""
    a = src.find(open_marker)
    if a < 0:
        ctx.miss.append('block missing: ' + label)
        return ''
    a = src.rfind('<', 0, a + 1)
    b = match_close(src, a)
    if b < 0:
        ctx.miss.append('block unbalanced: ' + label)
        return ''
    return src[a:b]


def asset_prefix(depth):
    """产物引用站内资源时的前缀：depth=1 -> '../'，depth=2 -> '../../'。"""
    return '../' * depth


def normalize_assets(doc, depth):
    """把产物里按 depth 写出来的资源前缀还原成站点根写法，便于跨深度比对。

    用精确计数而不是 `replace(prefix + 'assets/', 'assets/')`：后者在 depth=2 时
    会因为 `'../../assets/'` 里含 `'../assets/'` 这个子串而只吃掉一层。
    """
    if depth <= 0:
        return doc
    return re.sub(r'(?:\.\./){%d}assets/' % depth, 'assets/', doc)


def chrome_fingerprint(doc, extra_css, ctx, depth=1):
    """把「站芯」归一化后返回，用来断言内容页与首页共用完全相同的 nav / 抽屉 / 页脚。

    这是整个派生流程最重要的一条不变量：外壳从来不是重写的，是搬过来的。

    extra_css 是这一页追加的样式文件名（如 'about.css'）—— head 里设计上要变的
    就是 title / description / 这一条 link 三处，比对前先把它们抹平。

    depth 是产物的路径深度：站芯里的资源引用在产物里带了 `../` 前缀，比对前先
    还原成站点根写法。这样首页（depth=0）与任意深度的产物都能直接逐字节比。
    """
    parts = []
    # nav：唯一允许的差异是 is-active 挪到了「关于我们」。
    # class 属性先做一次空白归一化（`a  b ` → `a b`），否则「去掉 is-active 后
    # 多出的那个尾随空格」会被当成站芯漂移，纯粹是噪音。
    nav = block(doc, '<nav', 'nav', ctx)
    nav = re.sub(r'\s+is-active', '', nav)
    nav = re.sub(r'class="([^"]*)"',
                 lambda m: 'class="%s"' % ' '.join(m.group(1).split()), nav)
    parts.append(normalize_assets(nav, depth))
    parts.append(normalize_assets(block(doc, '<div class="fixed inset-0', 'mobile drawer', ctx),
                                  depth))
    parts.append(normalize_assets(block(doc, '<footer class="tf-reference-footer"', 'footer', ctx),
                                  depth))
    head = normalize_assets(doc[doc.find('<head'):doc.find('</head>')], depth)
    head = re.sub(r'<title>[^<]*</title>', '<title/>', head, count=1)
    head = re.sub(r'(<meta name="description" content=")[^"]*(")', r'\1\2', head, count=1)
    head = head.replace('\n<link rel="stylesheet" href="assets/css/%s">' % extra_css, '')
    parts.append(head)
    return parts


def head_link_anchor():
    """本页样式表插在 custom.css 之后，保证覆写顺序。"""
    return '<link rel="stylesheet" href="assets/css/custom.css"'


def derive(ctx, out_rel, title, description, extra_css, main_markup,
           active_group=COMPANY_NAV_GROUP, main_label=None, nav_label=None, depth=1):
    """派生一个内容页，返回 (产物文本, 首页文本, 首页 md5)。

    title / description 写进 head；extra_css 形如 'blog.css'（产物里会按 depth
    插成 `../assets/css/blog.css` 或 `../../assets/css/blog.css`）；main_markup 是
    `<main>` 里要放的内容；depth 是产物相对站点根的层数。

    active_group 是「导航里哪一组该亮」。传 None 表示这一页不归属任何组
    （404 页），此时只摘掉首页的选中态 —— 见下面「导航选中态」那段。
    """
    if not os.path.exists(HOME):
        raise SystemExit('missing %s — 先跑 tools/reshape_home.py 生成首页' % HOME)
    prefix = asset_prefix(depth)
    home = open(HOME, encoding='utf-8').read()
    home_md5 = hashlib.md5(home.encode('utf-8')).hexdigest()
    home_chrome = chrome_fingerprint(home, extra_css, ctx, depth)
    doc = home

    # ---------------------------------------------------------------- head
    before = doc
    doc = re.sub(r'<title>[^<]*</title>', '<title>%s</title>' % esc(title), doc, count=1)
    doc = re.sub(r'(<meta name="description" content=")[^"]*(")',
                 lambda m: m.group(1) + esc(description) + m.group(2), doc, count=1)
    if doc == before:
        ctx.miss.append('head rewrite did not apply')
    else:
        ctx.applied['head title/description'] = 1

    anchor = head_link_anchor()
    if anchor not in doc:
        ctx.miss.append('custom.css link anchor missing')
    else:
        i = doc.find('>', doc.find(anchor))
        doc = (doc[:i + 1]
               + '\n<link rel="stylesheet" href="%sassets/css/%s">' % (prefix, extra_css)
               + doc[i + 1:])
        ctx.applied['head %s link' % extra_css] = 1

    # ------------------------------------------------------------ 导航选中态
    # 首页把 is-active 挂在「首页」上；内容页要把它挪到自己所属的导航组。
    # active_group=None 表示这一页**不属于任何导航组**（目前只有 404 页）：
    # 只摘掉首页的选中态，不再挂到别处 —— 随便挂一组都是假信息，而且会让人
    # 以为「关于我们」下真有这么一个页面。chrome_fingerprint() 本来就先把
    # is-active 抹平再比，所以这不会影响站芯一致性断言。
    if 'class="tf-nav-menu-link is-active"' not in doc:
        ctx.miss.append('nav active link anchor missing')
    elif active_group is None:
        doc = doc.replace('class="tf-nav-menu-link is-active"',
                          'class="tf-nav-menu-link "', 1)
        if 'class="tf-nav-menu-link is-active"' in doc:
            ctx.miss.append('nav active state survived removal')
        else:
            ctx.applied[nav_label or 'nav active state'] = 1
    else:
        doc = doc.replace('class="tf-nav-menu-link is-active"',
                          'class="tf-nav-menu-link "', 1)
        group = doc.find(active_group)
        if group < 0:
            ctx.miss.append('nav group missing: ' + active_group)
        else:
            tail = doc[group:]
            tail = tail.replace('class="tf-nav-menu-link tf-nav-product-trigger "',
                                'class="tf-nav-menu-link tf-nav-product-trigger is-active"', 1)
            doc = doc[:group] + tail
            ctx.applied[nav_label or 'nav active state'] = 1

    # ---------------------------------------------------------------- main
    m = re.search(r'<main\b[^>]*>', doc)
    if not m:
        ctx.miss.append('<main> not found')
    else:
        b = match_close(doc, m.start())
        if b < 0:
            ctx.miss.append('<main> not balanced')
        else:
            doc = doc[:m.end()] + main_markup + doc[b:]
            ctx.applied[main_label or 'main body'] = 1

    # ------------------------------------------------------- 资源路径加深一级
    # 产物比首页深一级，所有站内相对引用都要加 `../`。
    # 站外绝对地址（https://…、mailto:、/blog 这类根相对）不受影响。
    doc, n = re.subn(r'((?:src|href)=")assets/', r'\1%sassets/' % prefix, doc)
    if n == 0:
        ctx.miss.append('asset path rewrite matched nothing')
    ctx.applied['asset paths (%sassets/)' % prefix] = n

    # ------------------------------------------------- 结构守卫（所有内容页共用）
    if '<html lang="zh-CN"' not in doc:
        ctx.miss.append('html lang lost')
    for marker in ('pipellm-navbar-shell', 'tf-nav-product-menu', 'tf-nav-company-dropdown',
                   'tf-reference-footer', 'tf-footer-columns', 'tf-nav-dropdown-icon'):
        if marker not in doc:
            ctx.miss.append('lifted chrome missing: ' + marker)
    if doc.count('class="tf-nav-dropdown-icon"') != 8:
        # 产品 4 + 关于我们 4：各页共用同一段导航，这里只是防止注入时被切断。
        # 关于我们那组原为 5 项，2026-09-11 移除了「加入我们」
        # （见 reshape_home.py 的 stage_nav_company），期望值因此从 9 落到 8。
        ctx.miss.append('nav dropdown icons changed: %d (expect 8)'
                        % doc.count('class="tf-nav-dropdown-icon"'))
    if not re.search(r'<main class="relative"[^>]*>', doc):
        ctx.miss.append('main wrapper lost')
    if '</main>' not in doc:
        ctx.miss.append('</main> lost')
    # 标签栈平衡（只管结构标签，忽略 void）
    for tag in ('div', 'section', 'li', 'ul', 'ol', 'main', 'h2', 'h3', 'p'):
        opens = len(re.findall(r'<%s[\s>]' % tag, doc))
        closes = doc.count('</%s>' % tag)
        if opens != closes:
            ctx.miss.append('unbalanced <%s>: %d open vs %d close' % (tag, opens, closes))
    # 首页必须原样不动
    now_md5 = hashlib.md5(open(HOME, 'rb').read()).hexdigest()
    if now_md5 != home_md5:
        ctx.miss.append('index.html changed while building (this script must be read-only)')
    # 站芯必须与首页逐字节相同（归一化掉本页设计上要换的三处差异）
    page_chrome = chrome_fingerprint(doc, extra_css, ctx, depth)
    if len(home_chrome) != len(page_chrome):
        ctx.miss.append('chrome part count changed')
    for i, (want, got) in enumerate(zip(home_chrome, page_chrome)):
        if want != got:
            ctx.miss.append('chrome drifted from index.html at part %d (%d vs %d bytes)'
                            % (i, len(want), len(got)))
    # 本页样式表必须存在且被引用
    if not os.path.exists(os.path.join(ROOT, 'assets', 'css', extra_css)):
        ctx.miss.append('missing stylesheet assets/css/' + extra_css)
    if '%sassets/css/%s' % (prefix, extra_css) not in doc:
        ctx.miss.append('%s is not linked from the page' % extra_css)
    # 路径深度：所有站内资源引用都应带**恰好** depth 层前缀。少一层会 404，
    # 多一层说明某处被重复加深了。
    #
    # 2026-09-11 审查发现原来那两条正则有个共同盲区：`../assets/`（depth=2 时少
    # 一层，也是 404）两条都放行 —— 「bare」那条用 `(?<![\w/])` 排除前面是 `/` 的
    # 情况，正好把 `../assets/` 也排除了；「too_deep」那条只抓**更深**的。
    # 现在改成按层数核：把所有 `src="…assets/"` 的前缀层数收成集合，必须等于 depth。
    asset_depths = {m.group(1).count('../')
                    for m in re.finditer(r'(?:src|href)="((?:\.\./)*)assets/', doc)}
    wrong = sorted(asset_depths - {depth})
    if wrong:
        ctx.miss.append('asset path depth %s found, want %d — 一层之差就是 404'
                        % (wrong, depth))

    return doc, home, home_md5


def finish(ctx, doc, out_path, out_rel, home_len, home_md5):
    """写盘 + 汇报。有问题时非零退出。"""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, 'w', encoding='utf-8') as fh:
        fh.write(doc)
    print('built %s: %d -> %d bytes (index.html untouched, md5 %s)'
          % (out_rel, home_len, len(doc), home_md5[:8]))
    print('applied:')
    for k, v in ctx.applied.items():
        print('  + %s x%s' % (k, v))
    if ctx.miss:
        print('ISSUES:')
        for msg in ctx.miss:
            print('  !', msg)
        raise SystemExit(1)
    print('ok')


def finish_many(ctx, pages, home_len, home_md5, extra_lines=()):
    """一次生成多个页面时的收尾：先全写盘，再统一汇报。

    `pages` 是 [(out_path, out_rel, doc), …]。守卫检查在调用前就该做完——
    这里只负责落盘与汇报，不做判断。全部页面用同一个 ctx，所以任何一页的
    问题都会让整个脚本非零退出（不会留下「一半新一半旧」的目录）。
    """
    for out_path, _out_rel, doc in pages:
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as fh:
            fh.write(doc)
    print('built %d pages (index.html untouched, md5 %s)' % (len(pages), home_md5[:8]))
    for _out_path, out_rel, doc in pages:
        print('  %-46s %7d bytes' % (out_rel, len(doc)))
    print('applied:')
    for k, v in ctx.applied.items():
        print('  + %s x%s' % (k, v))
    for line in extra_lines:
        print(line)
    if ctx.miss:
        print('ISSUES:')
        for msg in ctx.miss:
            print('  !', msg)
        raise SystemExit(1)
    print('ok')
