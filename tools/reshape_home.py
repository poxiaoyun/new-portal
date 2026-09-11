"""Reshape the 晓石云 homepage around four product boards + the Rune Harness core.

The built `index.html` is a single giant artifact derived from the upstream
reference DOM (that first hand-off was a rebrand of the original template, and
its pipeline script has since been retired). This script re-derives the
homepage from the pristine snapshot in `tools/ref/index.before-reshape.html`
with anchored, re-runnable replacements, so the story change does not require
hand-editing 140 KB of markup.

Story line after this pass::

    Rune 智算 / Moha 资产 / AIRouter · AI聚合网关 / BOSS 运营
        -> 共享一个云智算内核（Rune Harness，规划中）
        -> 底层由 XCMP 云管理能力提供多云资源底座（只强调优势，不展开）

Run:  python3 tools/reshape_home.py
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seo  # noqa: E402

REF = 'tools/ref/index.before-reshape.html'
OUT = 'index.html'
MISS = []
applied = {}

# --------------------------------------------------------- head 的文案常量
# title / description 现在各有两个消费方：stage_head() 写进 <title> 与
# <meta description>，stage_seo() 写进 og:title / og:description / 结构化数据。
# 所以提成常量 —— 同一句话存两份定义迟早会漂。
HOME_TITLE = ('晓石云 | Rune Harness 云智算内核 — Rune 智算 / Moha 资产 / '
              'AIRouter · AI聚合网关 / BOSS 运营')
HOME_DESC = ('晓石云以 Rune 智算、Moha 资产、AIRouter · AI聚合网关、BOSS 运营'
             '四大核心板块为基座，打造 Rune Harness 云智算内核，为企业提供私有化的 '
             'AI 智算平台与云管理能力。')
# 社交卡片另给一个短标题：上面那条 74 字符，是给搜索引擎的全文标题用的，
# 放进卡片里会被平台截成半句。
HOME_TITLE_OG = '破晓石科技 | Rune Harness 云智算内核'

# 上游品牌名的回归哨兵 —— 与 tools/portal_page.py 里那条是同一份判据
# （本脚本不依赖 portal_page 的派生逻辑，只 import 了纯常量的 seo，所以在这里
#  再写一份；改一处请同步另一处，还有 tools/qa/reshape.mjs 里那条 JS 版本）。
# 用正则而非字面量：既咬得住品牌名被写成两个词（带空格）的变体，也让
# 全仓搜它归零 —— 哨兵不能自己是那唯一的命中项。
UPSTREAM_BRAND_RE = re.compile(r'pipe\s*llm', re.I)


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


def post_cover(slug):
    """读这一篇内容源里声明的封面，用来给首页卡片配图。

    首页卡片与详情页必须是**同一张**封面，所以首页不自己另写图名，而是和
    tools/build_blog.py 一样从 `content/blog/<slug>.md` 的 `cover:` 读。
    两边各存一份路径迟早会漂——2026-09-11 之前首页用的就是换牌时自造的
    `assets/img/blog/cover-*.png`，与详情页的 `assets/img/news/*.webp`
    根本不是一套图，同一个站点两处封面各说各话。
    """
    path = os.path.join('content', 'blog', slug + '.md')
    if not os.path.exists(path):
        MISS.append('content source missing: ' + path)
        return None
    with open(path, encoding='utf-8') as fh:
        head = fh.read(4096)          # frontmatter 很短，读够就行
    m = re.search(r'(?m)^cover:\s*(\S+)\s*$', head)
    if not m:
        MISS.append('cover missing in ' + path)
        return None
    cover = m.group(1)
    if not os.path.exists(cover):
        MISS.append('cover file does not exist: ' + cover)
        return None
    return cover


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


def close_tag_start(s, open_start, close_end):
    """Index of the `<` that opens the close tag ending at `close_end`.

    Callers used to write `body[db - 6:]`, i.e. they hard-coded the length of
    `</div>`: the trick silently corrupts the markup the moment the container is
    a `<section>` / `<span>`. Deriving the offset from the tag itself removes
    both the magic number and that trap.
    """
    return s.rfind('<', open_start, close_end)


def ext(href):
    """Anchor attributes for an off-site link.

    Every product link leaves the page, and the same three attributes were
    spelled out at eight call sites before this helper existed.
    """
    return ' target="_blank" rel="noopener noreferrer"' if href.startswith('http') else ''


def scramble(text):
    """Wrap `text` in the three-span host that drives the hover scramble.

    The nesting is load-bearing, not decorative — vendor.css defines the three
    pieces as one unit:
        .tf-scramble-label    inline-grid + nowrap
        .tf-scramble-measure  hidden, grid-area 1/1   <- holds the width
        .tf-scramble-live     absolute inset:0        <- the only visible copy
    Drop the measure and the box collapses to the width of whatever glyphs the
    last frame happened to draw, so the line (and everything after it) jitters
    while the animation runs. Drop the `.sr-only` and the label reaches screen
    readers as random glyphs — both visible copies are aria-hidden.

    Only short labels belong here. main.js runs one frame per ~2 characters with
    the count capped, so the footer's `AIRouter · AI聚合网关` (17 chars, the
    longest label on the site) settles in 0.67s — a little slower than a
    four-character nav item (0.43s), versus the 1.68s it would take uncapped.
    Don't wrap sentences: a description-length line still reads as "the site is
    glitching" even at the cap.

    main.js discovers these hosts by class rather than by a list of container
    class names, so wrapping a label here is all it takes to make it animate.
    """
    if any(c in text for c in '<&'):
        raise ValueError('scramble() takes plain text, got %r' % text)
    return ('<span class="tf-scramble-label">'
            '<span class="tf-scramble-measure" aria-hidden="true">%s</span>'
            '<span class="tf-scramble-live" aria-hidden="true">%s</span>'
            '<span class="sr-only">%s</span>'
            '</span>' % (text, text, text))


# 乱码动效的覆盖率基线。
#
# 这类 bug 的形状很特别：hover 时的**背景过渡照常工作**，只有文字不动 ——
# 看上去「这一项有交互」，不逐条慢慢看就发现不了。实际连错三次：产品下拉四项、
# 预约弹层四项、页脚 21 条，长期都在 main.js 的绑定选择器里，而它们的文字从来
# 没有宿主（2026-09-11 用户报的就是产品下拉那四条）。
#
# 两条纪律落在这里：
#   * 条数写死。从 body 里现算的期望会跟着错误一起漂移，等于没查。
#   * 两个方向都查 —— 宿主包住了标签、但不在可点元素里，动效同样是死的，
#     只是断在 JS 那一侧（closest() 找不到宿主）。
SCRAMBLE_TARGETS = [
    # (容器类, 条数, 这些是什么)
    ('tf-nav-menu-link', 7, '首页/产品/解决方案/价格与服务/文档中心/关于我们/预约演示'),
    ('tf-nav-dropdown-item', 8, '产品下拉 4 + 关于我们下拉 4'),
    ('tf-nav-console-item', 4, '预约演示弹层 4'),
    ('tf-footer-link', 21, '页脚四列 21（每一页都有，因为它在站芯里）'),
]


def scramble_guard():
    for cls, want, note in SCRAMBLE_TARGETS:
        # 同时认 `<a>` 与 `<button>`：导航里两个下拉触发器就是 button，只认 a
        # 的话七个菜单项会被数成五个，而数量对不上本来就该报错 —— 报错信息却会
        # 指向「少了两个」，与真实原因（正则太窄）完全无关。
        # `(?=[\s"])` 而不是 `\b`：`-` 不是 word 字符，裸的 \b 在改名成
        # `tf-footer-link-x` 之后照样匹配，守卫就静默失效了。
        items = re.findall(
            r'<(?:a|button)\b[^>]*\b' + cls + r'(?=[\s"])[^>]*>(.*?)</(?:a|button)>',
            body, re.S)
        if len(items) != want:
            MISS.append('scramble: %s — expected %d, found %d (%s)'
                        % (cls, want, len(items), note))
        for idx, item in enumerate(items, 1):
            if 'tf-scramble-label' not in item:
                text = re.sub(r'<[^>]+>', '', item).strip()[:36]
                MISS.append('scramble: %s #%d has no host — %r' % (cls, idx, text))

    # 反向：宿主必须落在可点元素里。按 tag 逐对记账（`<a>` 不嵌 `<a>`），
    # 而不是「往前找最近一个 <a>」那种靠字符窗口的写法 —— 窗口开大了会漏、
    # 开小了会误报，而这两件事都只会在改动当天看起来是绿的。
    def clickable(tag):
        spans, depth, start = [], 0, None
        for t in re.finditer(r'<' + tag + r'\b[^>]*>|</' + tag + r'>', body):
            if t.group(0).startswith('</'):
                if depth == 1 and start is not None:
                    spans.append((start, t.end()))
                depth = max(0, depth - 1)
            else:
                if depth == 0:
                    start = t.start()
                depth += 1
        return spans

    live_anchors = clickable('a') + clickable('button')
    for m in re.finditer(r'class="tf-scramble-label"', body):
        if not any(a <= m.start() < b for a, b in live_anchors):
            MISS.append('scramble: host not inside a clickable — %r'
                        % body[m.start():m.start() + 180])

    # 三段式必须齐、且三份文本一致。缺一段的后果都是**静默**的：
    #   * 缺 live    -> main.js 的 querySelector 拿不到节点，直接 return，动效没了
    #   * 缺 measure -> 盒子按乱码帧里最宽的那一帧撑开，整行字在动画期间左右抖
    #   * 三份不一致 -> 屏幕阅读器念的和眼睛看到的不是同一个词
    # 生成器只有 scramble() 一个出口，正常不可能缺；这条是防「手改产物」与
    # 「照抄时少抄一段」——两种都只会在浏览器里表现为「看起来有点不对」。
    hosts = re.findall(
        # `[^>]*>` 不能省：快照自带的宿主（导航七个菜单项、关于我们下拉四项、
        # 预约触发器）每个标签上都挂着 data-page-node-id，写成 `class="…">`
        # 会把它们全部判成「不合格」，而这 12 个恰恰是原本就正确的那些。
        r'<span class="tf-scramble-label"[^>]*>'
        r'<span class="tf-scramble-measure"[^>]*>([^<]*)</span>'
        r'<span class="tf-scramble-live"[^>]*>([^<]*)</span>'
        r'<span class="sr-only"[^>]*>([^<]*)</span>'
        r'</span>', body)
    declared = body.count('class="tf-scramble-label"')
    if len(hosts) != declared:
        MISS.append('scramble: %d hosts declared, %d well formed'
                    % (declared, len(hosts)))
    for measure_text, live_text, screen_reader_text in hosts:
        if not measure_text == live_text == screen_reader_text:
            MISS.append('scramble: the three copies disagree — %r / %r / %r'
                        % (measure_text, live_text, screen_reader_text))


def seo_guard():
    """首页 head 里那一整块 SEO 标签的守卫。

    这一块是**全站 SEO 的源头**：13 个内容页的 head 都从这份 index.html 整篇
    搬走，只是 derive() 认标记换成各自的一份。所以首页这一块缺了、或者标记被
    改名，症状是「内容页静默少掉全部 canonical / og / 结构化数据」—— 页面照常
    渲染，只有爬虫那边不对。必须在这里钉死。

    期望值一律**不取自被检查对象**：url 与实体 id 来自 tools/seo.py 的常量，
    图片与图标的「存在性」来自磁盘。
    """
    blocks = re.findall(seo.SEO_BLOCK_RE, body)
    if len(blocks) != 1:
        MISS.append('seo: expected exactly 1 block, found %d' % len(blocks))
        return
    block = blocks[0]

    home_url = seo.page_url('index.html')
    expected = [
        ('canonical', '<link rel="canonical" href="%s">' % home_url),
        ('og:url', '<meta property="og:url" content="%s">' % home_url),
        # 首页必须可收录：noindex 只该出现在 404 页
        ('robots indexable', 'content="%s"' % seo.ROBOTS_INDEX),
        ('og:site_name', 'content="%s"' % seo.SITE_NAME),
        ('og:locale', 'content="%s"' % seo.LOCALE),
        # og:title / og:description 与 <title> / <meta description> 必须同源
        ('og:title from HOME_TITLE_OG',
         '<meta property="og:title" content="%s">' % seo.esc(HOME_TITLE_OG)),
        ('og:description from HOME_DESC',
         '<meta property="og:description" content="%s">' % seo.esc(HOME_DESC)),
        ('twitter card', 'name="twitter:card" content="summary_large_image"'),
        ('theme color', 'name="theme-color" content="%s"' % seo.THEME_COLOR),
        ('block start', seo.SEO_START),
        ('block end', seo.SEO_END),
    ]
    for label, needle in expected:
        if needle not in block:
            MISS.append('seo: missing %s in the home block' % label)

    # 结构化数据：必须解析得动，且实体种类对得上（一个坏 JSON 在浏览器里
    # 完全无声 —— 页面照常，只是那一段被爬虫整块丢弃）。
    m = re.search(r'<script type="application/ld\+json">(.*?)</script>', block, re.S)
    if not m:
        MISS.append('seo: home block carries no JSON-LD')
    else:
        try:
            data = json.loads(m.group(1))
        except ValueError as exc:
            MISS.append('seo: home JSON-LD does not parse: %s' % exc)
        else:
            types = [e.get('@type') for e in data.get('@graph', [])]
            if types != ['Organization', 'WebSite']:
                MISS.append('seo: home @graph is %s, want [Organization, WebSite]' % types)
            ids = [e.get('@id') for e in data.get('@graph', [])]
            if seo.ORG_ID not in ids or seo.SITE_ID not in ids:
                MISS.append('seo: Organization / WebSite @id changed — 其余 13 页'
                            '用 @id 指过来，改了这里等于断了全站实体')

    # 页面不能出现 noindex（这是首页，唯一的 noindex 在 404 页）
    if seo.ROBOTS_NOINDEX.split(',')[0] in block:
        MISS.append('seo: the home page must not be noindex')

    # 引用的图必须真在磁盘上。og:image 404 时社交平台只是静默不显示图，
    # 抓取器不会报错 —— 没人会发现。
    for rel in (seo.DEFAULT_OG_IMAGE, seo.ORG_LOGO,
                'assets/img/favicon-96.png', 'assets/img/apple-touch-icon.png'):
        if not os.path.exists(rel):
            MISS.append('seo: %s is referenced but missing — 跑 tools/gen_og.py' % rel)

    # 图标两条：PNG 在前、SVG 在后（顺序有意义，见 stage_icons）
    if body.find('href="assets/img/favicon-96.png"') > body.find(
            'href="assets/img/icon-mark.svg"'):
        MISS.append('seo: the svg icon must come after the png one')


def body_without_seo():
    """整页除去 head 里那块 SEO 标签。

    **只给两类守卫用：数出现次数、查「还有没有指向旧站的链接」。** 两边都是
    被这次改动打红之后才补上的（2026-09-11 晚加 SEO）：

      * SEO 块里本来就带着 `<title>` 与 `<meta description>` 的原文 ——
        og:title / og:description / twitter:* 是**同一份入参**渲染出来的。
        拿整页数品牌全称，会从 16 涨到 20，看着像「品牌写法多写了四处」。
      * canonical、og:url、og:image 与结构化数据里的 @id 天然是本站的绝对
        地址（`https://www.poxiaoshi.cn/…`）。而下面那条「全站不再指向旧站」
        用的是最强判据「主域零出现」—— 不把这一块摘掉，它会把自己报成旧站链接。

    反面同样要注意：**查「不该出现的文案」时必须用整页 body，不能摘 SEO 块** ——
    那一块里的文案也是文案，旧品牌名漏进 og:title 一样是回归。
    """
    return seo.SEO_BLOCK_RE.sub('', body)


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


def fill_children(attr, markup, label=None, key=None, lo=0):
    """Replace the children of the element whose start tag contains `attr`.

    Four call sites (the two desktop dropdowns, the mobile drawer product group
    and the footer product column) all rebuilt the same
    `body[:open_tag_end(...)] + items + body[db - 6:]` slice by hand. The
    container keeps its own attributes, so the original node ids stay put.
    """
    global body
    a, b = find_by_attr(body, attr, lo)
    if a < 0:
        MISS.append('children miss: ' + (label or attr))
        return False
    body = body[:open_tag_end(body, a)] + markup + body[close_tag_start(body, a, b):]
    applied[key or ('children:' + (label or attr))] = 1
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

# Inline "thinking" orb. The arc length (8 of a ~53.4 circumference) leaves a
# single visible sweep, which `.tf-thinking-spin` rotates while
# `.tf-thinking-core` breathes. Both animations are defined in custom.css and
# disabled under prefers-reduced-motion. `grad_id` is intentionally required:
# the orb can be stamped more than once, and duplicated gradient ids would make
# the second copy silently reference the first one's defs.
def harness_orb(grad_id):
    return (
        '<svg class="tf-thinking" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
        '<defs><linearGradient id="' + grad_id + '" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#9fcfff"></stop>'
        '<stop offset=".45" stop-color="#ffffff"></stop>'
        '<stop offset="1" stop-color="#ff8a3d"></stop>'
        '</linearGradient></defs>'
        '<circle class="tf-thinking-track" cx="12" cy="12" r="8.5" fill="none" '
        'stroke="currentColor" stroke-opacity=".16" stroke-width="2"></circle>'
        '<g class="tf-thinking-spin"><circle cx="12" cy="12" r="8.5" fill="none" '
        'stroke="url(#' + grad_id + ')" stroke-width="2" stroke-linecap="round" '
        'stroke-dasharray="8 45.4"></circle></g>'
        '<circle class="tf-thinking-core" cx="12" cy="12" r="3" fill="url(#' + grad_id + ')"></circle>'
        '</svg>')


# The hero's centre terminal is replayed as a Rune Harness conversation: the
# user asks in plain language, the harness thinks for 3s, then the deploy
# lands and the thinking label settles on 已处理. The timeline is pure CSS (see
# `.tf-chat-*` in custom.css) so it keeps running without JS, and every row is
# visible at once under prefers-reduced-motion.
HERO_CHAT = (
    '<div class="tf-chat" role="img" '
    'aria-label="在 Rune Harness 中用自然语言部署模型：部署 DeepSeek V4.1 Flash，'
    'harness 思考三秒后显示已处理，模型已调度部署完成">'
    '<div class="tf-chat-row tf-chat-user">'
    '<p class="tf-chat-bubble">部署 DeepSeek V4.1 Flash</p>'
    '</div>'
    '<div class="tf-chat-row tf-chat-ai">'
    '<span class="tf-chat-avatar" aria-hidden="true">' + harness_orb('tf-chat-orb-grad') + '</span>'
    '<div class="tf-chat-thinking">'
    # two stacked states: the label flips to 已处理 the instant the result
    # lands, so the row never contradicts the green line underneath
    '<span class="tf-chat-label">'
    '<span class="tf-chat-state tf-chat-state-thinking">正在思考</span>'
    '<span class="tf-chat-state tf-chat-state-done">已处理</span>'
    '</span>'
    '<span class="tf-chat-dots" aria-hidden="true"><i></i><i></i><i></i></span>'
    '</div>'
    '</div>'
    '<div class="tf-chat-done">'
    '<span class="tf-chat-check" aria-hidden="true">✔</span>'
    '<span>模型已调度部署完成</span>'
    '</div>'
    '</div>')


# ======================================================= stages, in order
def stage_head():
    global body
    # 四板块并列的串改用 `/` 分隔：AIRouter 的品牌写法现在是
    # `AIRouter · AI聚合网关`，它自带一个 `·`；若并列仍用 `·`，标题会变成
    # 五个 `·` 串成的段落，被读成五个板块，和「四大核心板块」的叙事打架。
    # `/` 只在这一处（title 与跑马灯）出现，负责分层：`/` 分板块、`·` 分主副。
    #
    # 替换成哪两句由 HOME_TITLE / HOME_DESC 决定（stage_seo() 也用它们）。
    need('<title>晓石云 | 智算为中心的 AI 原生云内核 — 成都破晓石科技</title>',
         '<title>%s</title>' % HOME_TITLE,
         'title')
    need('content="专注云原生开源、混合云与 AI 智算平台，为企业提供覆盖容器云、混合云、智算云及 AI 能力的全栈解决方案。"',
         'content="%s"' % HOME_DESC,
         'meta description')


# 图标：PNG 一份 + SVG 一份。**顺序有意义** —— 现代浏览器在两者都够用时
# 倾向最后一条，所以 SVG 放最后（矢量在任何 DPI 下都更利），PNG 放前面兜底
# 老爬虫与老浏览器。Google 搜索结果的站点图标要求「正方形且是 48 的整数倍」，
# 它对 SVG 的支持不如位图稳，96x96 那份就是给它的。
PGN_ICONS = ('<link rel="icon" type="image/png" sizes="96x96" href="assets/img/favicon-96.png">\n'
             '<link rel="apple-touch-icon" sizes="180x180" href="assets/img/apple-touch-icon.png">\n')
ICON_SVG_LINK = '<link rel="icon" type="image/svg+xml" href="assets/img/icon-mark.svg"'


def stage_icons():
    need1(ICON_SVG_LINK, PGN_ICONS + ICON_SVG_LINK, 'png icons')


def stage_seo():
    """把整块 SEO 标签钉进首页 head。

    位置选在 `<link rel="preconnect"` 之前：**锚点不带 node id**
    （其它的 head 标签都拖着 `data-page-node-id="…"` 那串上游快照的 id，
    锚在它上面等于把上游的 id 写死进生成器）。

    这一步必须早于所有内容页生成器：它们从已定稿的 index.html 整篇搬 head，
    derive() 再认标记整块换掉。首页没有这一块，内容页就会「换了个不存在的
    标记」而静默少掉全部 SEO 标签。
    """
    block = seo.seo_block(
        title=HOME_TITLE,
        description=HOME_DESC,
        url=seo.page_url('index.html'),
        kind='website',
        og_title=HOME_TITLE_OG,
    )
    need1('<link rel="preconnect" href="https://fonts.googleapis.com"',
          block + '\n<link rel="preconnect" href="https://fonts.googleapis.com"',
          'seo block')


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

# ----------------------------------------------------------------- products
# The single product registry. Every list the page says about the four boards is
# read from this table: the nav 产品 dropdown, the 预约演示 dropdown, the mobile
# drawer, the hero pills, the control-plane tabs and lanes, and the footer
# column. Before it existed the four names / hrefs were retyped in three places
# (a tuple list plus hand-written lane() calls plus the tab loop), so adding a
# board or moving a URL meant editing several spots and hoping they agreed.
#
# `page` 是**站内产品页**（根相对）—— 2026-09-11 起这五处目录型入口全部指向它，
# 不再跳旧站的 `www.poxiaoshi.cn/products/*`。旧站那四条路径此刻仍指向上一版
# 站点，换牌之后就是四个死链；而「产品名 → 旧站」这件事本身与新站自相矛盾。
#
# 去「用」的入口**不从这里走**：控制台（CONSOLE_HREF）、文档站、演示站各在自己
# 的 stage 里硬编码，因为它们是真实系统，与产品目录不是一回事 —— 产品页只承接
# 「了解」，去控制台的那一步落在产品页自己的页尾 CTA 上（2026-09-11 晚起首页不再
# 直连控制台，见 CONSOLE_HREF）。
#
# Colours are the board accent as it appears in the pills, custom.css and
# assets/js/main.js — keep the three in sync when a board is added.
PRODUCTS = [
    {
        'key': 'rune', 'name': 'Rune', 'sub': 'AI 训推平台',
        'desc': 'AI 训推一体平台，覆盖模型开发、训练、推理与部署全流程。',
        'page': '/products/rune/',
        'short': 'AI 训推一体平台。',
        'pill': ('Rune 智算', 'rgba(159,233,255,.85)'),
        'lane': ('runtime', 'Rune · AI 训推平台', '跑通每一次训练。',
                 '训练任务、推理服务与算力配额在这里统一编排。',
                 [('任务', 'rune-job-2048'), ('GPU 配额', '8 × A800 · pool-cn-southwest'),
                  ('状态', '运行中')],
                 '进入 Rune'),
    },
    {
        'key': 'moha', 'name': 'Moha', 'sub': 'AI 资产仓库',
        'desc': '私有化 AI 模型、数据集与镜像仓库，支持加密存储与版本治理。',
        'page': '/products/moha/',
        'short': '私有化 AI 资产仓库。',
        'pill': ('Moha 资产', 'rgba(215,197,255,.9)'),
        'lane': ('audit', 'Moha · 数字仓库', '沉淀每一份资产。',
                 '模型、数据集与镜像沉淀为可检索、可追溯的加密资产。',
                 [('资产', 'moha/model-llama-3.1'), ('版本', '12 个版本'),
                  ('加密', 'AES-256 已启用')],
                 '进入 Moha'),
    },
    {
        # 品牌写法 2026-09-11 统一为 `AIRouter · AI聚合网关`（用户拍板）：
        # 此前「模型网关 / 统一网关 / 统一模型网关 / 统一模型入口」四种说法并存。
        # `pill[0]` 同时喂 hero pills（:466）与 footer 产品列（:974），改一处两处同步；
        # nav 下拉给的是 name（AIRouter）+ desc，console 下拉给的是 short。
        'key': 'airouter', 'name': 'AIRouter', 'sub': 'AI聚合网关',
        'desc': 'AI聚合网关，协议翻译、策略路由与配额用量治理。',
        'page': '/products/ai-router/',
        'short': 'AI聚合网关。',
        'pill': ('AIRouter · AI聚合网关', 'rgba(138,255,193,.85)'),
        'lane': ('airouter', 'AIRouter · AI聚合网关', '收敛每一次调用。',
                 '一个入口接入各家大模型，协议翻译、策略路由与用量审计一次到位。',
                 [('模型', '32 个已上架'), ('峰值 QPS', '4.2k'), ('策略', '已授权')],
                 '进入 AIRouter'),
    },
    {
        'key': 'boss', 'name': 'BOSS', 'sub': '平台运营',
        'desc': '面向智算中心运营方：租户、配额、计量与运营报表。',
        'page': '/products/boss/',
        'short': '智算中心运营控制台。',
        'pill': ('BOSS 运营', 'rgba(255,179,107,.9)'),
        'lane': ('boss', 'BOSS · 平台运营', '看清每一笔消耗。',
                 '租户、配额、计量与运营数据在同一个控制台闭环。',
                 [('租户', '36 个在管'), ('配额', '已分配 78%'), ('计量', '实时出账')],
                 '进入 BOSS'),
    },
]

def product(key):
    """按 key 取 `PRODUCTS` 里的那条。各处 CTA 要引某个板块的站内页时走这里，
    别写 `PRODUCTS[3]` —— 顺序是展示顺序，不是标识。"""
    for p in PRODUCTS:
        if p['key'] == key:
            return p
    raise KeyError('unknown product: %s' % key)


# 去「用」的真实系统入口。与 PRODUCTS['page'] 分开是有意的：产品页讲定位，控制台
# 才是干活的地方；把两者混成一个字段，迟早会有人为了让某个 CTA 直连控制台而把
# 整个产品目录一起改回去（2026-09-11 之前 BOSS 就是这么直连的）。
#
# 本站首页**不再**直连控制台（2026-09-11 晚，用户要求「全部指向新页面」）：原来那三处
# 直达已收归站内 —— 品牌带与页尾的按钮文字本来就是「预约演示」（去 /contact），
# BOSS 深潜那条「进入 BOSS」去 /products/boss/。
#
# 2026-09-11 晚（十三）之后，这行常量在**产物里**已无落点：产品页页首那条「进入控制台」
# 也改指 /contact 了（tools/build_products.py），全站不再有任何链接指向它。
# 它现在只作为**改写的旧值**留在两处 `retarget_link` 的第二个参数里（品牌带、页尾 CTA）
# —— 那是「只删除这一个方向」的写法：断的是「这两个按钮当初指的是它」，而不是
# 「页面上还有没有它」。stage_guards 里那条 `body.count(CONSOLE_HREF) == 0` 因此
# 仍然是活的断言，不用改。
CONSOLE_HREF = 'https://console.poxiaoshi.cn'

# ============================================= 全站不再指向旧站（2026-09-11 晚）
# 用户要求：本站里所有指向旧站 `www.poxiaoshi.cn` 的链接，以及首页三处控制台直达，
# 全部改指站内。旧站的 solutions / cases / chatbox / xmcp 四类**在新站没有对应页**，
# 所以落点按语义就近，不按路径对齐 —— 新站只需要一个「别再把人送走」的结果：
#
#   混合云 / 智算中心 / XCMP 云管理 → /products/rune/   云智算内核与它的多云底座都在这一页
#   教育行业 / 能源制造             → /blog/            站内交付故事（马基努油田那篇就是能源）
#   AI 应用                         → /products/ai-router/  AI 应用统一经聚合网关接入
#   关于我们                        → /about             站内有这一页，原先却指旧站
#
# 定价区那几条（查看完整报价 / 查看商务条款）与两处「预约演示」→ /contact：站内没有
# 报价页，报价与条款都是商务动作，联系页是唯一诚实的落点。
CONTACT_PAGE = '/contact'
PRICING_ANCHOR = '/#pricing'          # 首页定价区自带 id="pricing"（上游就有）
FOOTER_RETARGET = (
    # (说明, node-id, 旧 href, 新 href)
    ('混合云', 'KvS53dW9vEx7LJrNEYJagV', 'https://www.poxiaoshi.cn/solutions', '/products/rune/'),
    ('智算中心', 'UlASgYyW9LUmjefpD40YaY', 'https://www.poxiaoshi.cn/solutions', '/products/rune/'),
    ('教育行业', 'kaDnRWG8B81dbK9QH30BPT', 'https://www.poxiaoshi.cn/cases', '/blog/'),
    ('能源制造', '3nLfikIfe3k1Wz3SKL7X7q', 'https://www.poxiaoshi.cn/cases', '/blog/'),
    ('AI 应用', 'beRStKhjjBgU5lWd2yGLEF', 'https://www.poxiaoshi.cn/products/chatbox/',
     '/products/ai-router/'),
    ('关于我们', 'WQs06tBb1wDxj7OvovKSYT', 'https://www.poxiaoshi.cn/about/', '/about'),
)
PRICING_RETARGET = (
    # (说明, node-id, 新 href)
    ('查看完整报价', 'KzqwG3wBNrJseLX8MK7Q6t', CONTACT_PAGE),
    ('Rune 定价卡', 'ZhyZQulQXmzD9AqnS288TG', '/products/rune/'),
    ('Moha 定价卡', 'CZGmZ1pVmz1Rh4x43yhH0C', '/products/moha/'),
    ('AIRouter 定价卡', 'OE6IAszB9aBchN1K8oiIhX', '/products/ai-router/'),
    ('BOSS 定价卡', 'IuFB8gEaT5wuGld1IMzGjf', '/products/boss/'),
    ('查看商务条款', 'lBUjO9RAZouPGOUfJKWGoT', CONTACT_PAGE),
)
PRICING_HREF = 'https://www.poxiaoshi.cn/'   # 定价区六条原本都指旧站首页


# ================================= 商务出口统一收口 /contact（2026-09-11 晚（十三））
# 用户要求：站内所有「预约演示 / 联系我们 / 进入控制台」一律跳 /contact。首页那三类
# 早在晚（八）就落好了（品牌带与页尾写着「预约演示」，nav 下拉写着「联系我们」），
# 剩下的不在这三类里 —— 但同属商务出口，用户当场拍板一并收口：
#   * 导航条右侧的 CTA「联系销售」（桌面 + 移动抽屉各一条）
#   * 页脚「公司」列的两条：联系我们 / 联系销售
#
# 四条**全在站芯**（首页的 nav / 抽屉 / footer），所以改这一处就随 `derive()` 传导到
# 全部 13 个产物页。这既是它们的价值，也是它们此前一直不一致的原因 —— 站芯是派生源，
# 只改产品页的按钮永远动不了它。
#
# **不动**页脚社交区那枚邮件图标（node-id `polAgWExWsNunLcPb43EiU`，`aria-label="邮箱"`）：
# 它答的是「怎么发邮件给我们」，不是「怎么联系我们」—— 改成 /contact 不是收口，
# 是把一个邮箱地址按钮变成表单入口。见 stage_guards 里那条「站芯 mailto 恰好剩它一条」。
CONTACT_MAIL = 'mailto:support@xiaoshiai.cn'
CONTACT_RETARGET = (
    # (说明, node-id, 旧 href, 新 href)
    ('导航 CTA·联系销售', 'zxaCUK9WR98iS1VSgJ9R8D', CONTACT_MAIL, CONTACT_PAGE),
    ('移动抽屉·联系销售', 'apBekVVhWXm0SWiaX8tzcI', CONTACT_MAIL, CONTACT_PAGE),
    ('页脚公司列·联系我们', 'zbLbV2t257YjfBBzYmvRr6', CONTACT_MAIL, CONTACT_PAGE),
    ('页脚公司列·联系销售', 'SYsMTR7fVuunITHCuHrkrp', CONTACT_MAIL, CONTACT_PAGE),
)


def stage_nav():
    global body
    # the brand lockup in the nav frame: the wordmark is the company name now
    # (the mark itself is mono, baked into assets/img/logo.svg by
    # tools/gen_icons.py — only the alt text needs touching here)
    need1('alt="晓石云 logo"', 'alt="破晓石科技 logo"', 'nav logo alt')

    # --- desktop 产品 dropdown: 3 entries (with swapped copy) -> 4 correct ones
    #
    # The entries are lucide stroke icons (fill:none + stroke:currentColor), but
    # vendor.css carries `.tf-nav-product-menu .tf-nav-dropdown-icon svg
    # {stroke-width:0}` — correct for the upstream filled icons, fatal for these.
    # The counter-rule lives in assets/css/custom.css; keep the two in sync or
    # all four rows render blank next to the product names.
    #
    # 2026-09-11：四条都改指站内产品页（`p['page']`）。`p['page']` 是根相对路径，
    # `ext()` 因此不会加 target/rel —— 站内跳转开新窗是错的，而在此之前这四处
    # 每一条都带着 `target="_blank"`。
    #
    # 同日晚：`.tf-nav-dropdown-title` 里的文本包成乱码宿主。此前这四行 hover 时
    # 只有背景过渡、文字是死的 —— 而「关于我们」那四项（vendor 快照自带）一直有
    # 乱码动效，两列下拉并排放在一起，差异一眼可见。title 的 `height:20px` /
    # `line-height:19.6px` 与 company 那份逐字相同，所以同样的内嵌结构在这里也成立。
    ta, _ = find_by_attr(body, 'data-page-node-id="MxGAw2GdzzKKJRLgPDRZSM"')
    if ta < 0:
        MISS.append('desktop 产品 trigger')
    else:
        items = ''.join(
            f'<a href="{p["page"]}" class="tf-nav-dropdown-item"{ext(p["page"])}>'
            f'<span class="tf-nav-dropdown-icon">'
            f'<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
            f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
            f'aria-hidden="true">{ICONS[p["key"]]}</svg></span>'
            f'<span><span class="tf-nav-dropdown-title">{scramble(p["name"])}</span>'
            f'<span class="tf-nav-dropdown-description">{p["desc"]}</span></span></a>'
            for p in PRODUCTS)
        fill_children('class="tf-nav-dropdown"', items, lo=ta,
                      key='nav desktop dropdown')

    # --- 预约演示 console dropdown
    #
    # 这里的产品名同样包成乱码宿主。注意 `<strong>` 的 `display:block` 不妨碍内嵌
    # inline-grid —— 「关于我们」下拉的 title 就是同一种组合，已经在线上跑着。
    # `small`（一句话简介）不包：它 8~10 字，按 main.js 的节奏封顶后仍会拖到
    # 半秒以上，而且它跟标题一起跳会让整个弹层像出了故障。
    items = ['<p>选择产品_</p>']
    items += [
        f'<a href="{p["page"]}" class="tf-nav-console-item"{ext(p["page"])}>'
        f'<span class="tf-nav-console-icon">'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" '
        f'fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true">{ICONS[p["key"]]}</svg></span>'
        f'<span><strong>{scramble(p["name"])}</strong><small>{p["short"]}</small></span>{ARROW_R}</a>'
        for p in PRODUCTS]
    fill_children('class="tf-nav-console-dropdown"', ''.join(items),
                  key='nav console dropdown')

    # --- mobile drawer product group
    links = ''.join(
        f'<a href="{p["page"]}"{ext(p["page"])} class="flex items-center gap-3 '
        f'rounded-[var(--pxs-radius-xxs)] '
        f'border border-white/10 bg-white/[0.04] px-4 py-3 font-mono text-sm text-white/72 '
        f'transition-colors">'
        f'<svg class="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{ICONS[p["key"]]}</svg>{p["name"]}</a>'
        for p in PRODUCTS)
    fill_children('data-page-node-id="GUpfus8Amy9mv701ZgQK0A"', links,
                  key='nav mobile drawer')

    need('>Choose a platform<', '>选择产品<', 'mobile 选择产品')


# ================================================ 「关于我们」下拉（2026-09-11）
# 五项来自参考页原样：桌面下拉（.tf-nav-company-dropdown）与移动抽屉
# （「关于我们」标题下那个 .grid.gap-2 容器）各一份，图标与 data-page-node-id
# 都是上游的。2026-09-11 用户要求两处调整：
#
#   * 开源项目：/affiliates -> https://www.kubegems.io/（站外，开新窗）
#   * 加入我们：/careers 整项移除
#
# 做法是**定向修补**而不是重写整个下拉。五个 item 各带自己的内联图标，重写等于把
# 图标全搬一遍，还会丢掉 data-page-node-id 这条 DOM 血缘（那正是其他 stage 用来
# 精确落位的东西）。node-id 抄自参考页，用它定位而不是文本 —— 上游改文案时锚点
# 不会静默失效，而这里本来就要改文案。
COMPANY_NAV_RETARGET = (
    # (名称, 桌面下拉 node-id, 移动抽屉 node-id, 旧 href, 新 href)
    ('开源项目', 'TiAwzD3ggnRELge0dsQMjT', 'ZdH35ccVkpyOMHzNrzxChv',
     '/affiliates', 'https://www.kubegems.io/'),
)
COMPANY_NAV_DROPPED = (
    # 招聘入口不从这里走：about 页的招聘条（tf-about-hiring）始终指向
    # support@xiaoshiai.cn 收简历，导航里保留一个 /careers 空页没有意义。
    ('加入我们', 'jKfw3lp2WDD1cdT6kbG9Gt', '5sPmJPVIK2Lfnhhgtz5f5R', '/careers'),
)


def retarget_nav_item(node_id, old_href, new_href, label):
    """把某个下拉项的开标签换成新 href（站外自动带 target/rel）。"""
    global body
    i = body.find('data-page-node-id="%s"' % node_id)
    if i < 0:
        MISS.append('nav item anchor missing: %s (%s)' % (label, node_id))
        return False
    a = body.rfind('<a ', 0, i)
    end = body.find('>', i)
    if a < 0 or end < 0:
        MISS.append('nav item <a> not found: ' + label)
        return False
    tag = body[a:end + 1]
    if 'href="%s"' % old_href not in tag:
        got = re.search(r'href="[^"]*"', tag)
        MISS.append('nav item %s: expected href="%s", got %s'
                    % (label, old_href, got.group(0) if got else '<no href>'))
        return False
    new_tag = tag.replace('href="%s"' % old_href,
                          'href="%s"%s' % (new_href, ext(new_href)))
    body = body[:a] + new_tag + body[end + 1:]
    return True


def retarget_link(node_id, old_href, new_href, label):
    """按 `data-page-node-id` 找到链接并改指 `new_href`（站内目标顺带摘掉 target/rel）。

    与 `retarget_nav_item` 的差别只有一个，但正是页脚那批链接需要的那一个：目标在站内
    时，标签里**原本带着的** `target="_blank" rel="noopener noreferrer"` 也要一起摘掉。
    nav 的顶层菜单上游没写 target，所以那边不需要；页脚六条全都写着 —— 只换 href 的话
    会得到「站内链接开新窗」，而这正是本轮要消掉的症状（见 stage_guards 的反向断言）。
    """
    global body
    i = body.find('data-page-node-id="%s"' % node_id)
    if i < 0:
        MISS.append('link anchor missing: %s (%s)' % (label, node_id))
        return False
    a = body.rfind('<a ', 0, i)
    end = body.find('>', i)
    if a < 0 or end < 0:
        MISS.append('link <a> not found: ' + label)
        return False
    tag = body[a:end + 1]
    if 'href="%s"' % old_href not in tag:
        got = re.search(r'href="[^"]*"', tag)
        MISS.append('link %s: expected href="%s", got %s'
                    % (label, old_href, got.group(0) if got else '<no href>'))
        return False
    new_tag = tag.replace('href="%s"' % old_href,
                          'href="%s"%s' % (new_href, ext(new_href)))
    if not ext(new_href):
        # 站内目标：把 href 旁边本来就写着的那两个属性摘掉。`ext()` 只负责「该加」的
        # 场合，不管「该删」的场合 —— 这是两个方向，别指望一个函数包圆。
        new_tag = re.sub(r'\s+target="_blank"', '', new_tag)
        new_tag = re.sub(r'\s+rel="noopener noreferrer"', '', new_tag)
    body = body[:a] + new_tag + body[end + 1:]
    return True


def drop_nav_item(node_id, old_href, label):
    """整块删掉一个下拉项（含它的内联图标）。

    只删 <a>…</a>：两项之间的换行与缩进留原样，拼起来仍是干净的一行 —— 这与
    cut_section 里「连缩进一起吃掉」的处理不同，那里删的是一整个 <section>，
    留着缩进会变成两段之间的空行。
    """
    global body
    i = body.find('data-page-node-id="%s"' % node_id)
    if i < 0:
        MISS.append('dropped nav item anchor missing: %s (%s)' % (label, node_id))
        return False
    a = body.rfind('<a ', 0, i)
    if a < 0 or ('href="%s"' % old_href) not in body[a:a + 240]:
        MISS.append('dropped nav item %s is not the expected link (%s)'
                    % (label, old_href))
        return False
    # match_close 的返回值是「闭合标签之后」的索引（见它的 docstring），
    # 直接当终点用 —— 别再多找一次 '>'，那会越过下一项的 `<a …>` 开标签，
    # 把紧随其后的那一项也吃掉（2026-09-11 差点就这么发：删「加入我们」时
    # 把「联系我们」的开标签一并带走了）。
    end = match_close(body, a)
    if end < 0:
        MISS.append('dropped nav item %s is unbalanced' % label)
        return False
    body = body[:a] + body[end:]
    return True


# ================================================ 顶层菜单「解决方案」（2026-09-11）
# 「解决方案」是桌面 nav 的**顶层项**（.tf-nav-menu-link），不是下拉项 —— 桌面与
# 移动抽屉各一份，两处原本都指向旧站的 https://www.poxiaoshi.cn/products/（新站
# 没有这个路径）。2026-09-11 用户要求改为跳转到演示站的第一页。
#
# 裸 products/ 在 nav 里**只有这 2 处**：产品下拉里的是 products/rune/ 这类带子
# 路径的链接（另有 9 处），改这个 href 不会碰到它们 —— 守卫按精确形态咬住这点。
NAV_MENU_RETARGET = (
    # (名称, 桌面 node-id, 移动抽屉 node-id, 旧 href, 新 href)
    ('解决方案', 'YR7a557saso22RZ5nfXC1O', 'Woje1sxC8xj3MiPZ2Cg9sr',
     'https://www.poxiaoshi.cn/products/', 'https://ppt.poxiaoshi.cn/#slide-1'),
    # 「价格与服务」原本指旧站首页（那里是旧站的报价页）。站内定价区就在首页，
    # 且上游已经带着 `id="pricing"` —— 直接锚过去，别再外跳一层。
    # 两个 node-id 是顶层菜单项，`ext()` 对根相对路径返回空串，所以不会带 target。
    ('价格与服务', 'qU1gGX21TPSK0f4D3iwmhe', 'Pa4xBL5i4j0AN2kDBOwNM8',
     'https://www.poxiaoshi.cn/', PRICING_ANCHOR),
)


def stage_nav_menu():
    for label, desk, mob, old_href, new_href in NAV_MENU_RETARGET:
        n = sum(1 for nid in (desk, mob)
                if retarget_nav_item(nid, old_href, new_href, label))
        if n != 2:
            MISS.append('nav menu retarget %s applied %d/2 (desktop + drawer)' % (label, n))
        if n:
            applied['nav 顶层菜单·%s -> %s' % (label, new_href)] = n


def stage_nav_company():
    for label, desk, mob, old_href, new_href in COMPANY_NAV_RETARGET:
        n = sum(1 for nid in (desk, mob)
                if retarget_nav_item(nid, old_href, new_href, label))
        if n != 2:
            MISS.append('nav retarget %s applied %d/2 (desktop + drawer)' % (label, n))
        if n:
            applied['nav 关于我们·%s -> %s' % (label, new_href)] = n
    for label, desk, mob, old_href in COMPANY_NAV_DROPPED:
        n = sum(1 for nid in (desk, mob) if drop_nav_item(nid, old_href, label))
        if n != 2:
            MISS.append('nav drop %s applied %d/2 (desktop + drawer)' % (label, n))
        if n:
            applied['nav 关于我们·移除「%s」' % label] = n


def stage_hero():
    global body
    # The hero slogan and its subtitle are deliberately NOT touched: they carry
    # the company positioning line and stay as authored upstream. `stage_guards`
    # asserts both strings survive verbatim.
    #
    # The overline is a "coming soon" teaser for Rune Harness, plain text only.
    # `.tf-overline::before` draws a static white play triangle (see
    # vendor.css), so this instance opts out of it via `.tf-overline-live`;
    # the orb that used to sit here now lives only on the chat avatar.
    need('<span class="tf-overline" data-page-node-id="xONwR8BFMrwJDv2uXW2pv2">云原生 · 混合云 · AI 智算</span>',
         '<span class="tf-overline tf-overline-live" data-page-node-id="xONwR8BFMrwJDv2uXW2pv2">'
         'Rune Harness 即将开放</span>',
         'hero overline')

    # hero pills (mobile)
    pills = ''.join(
        f'<span class="tf-pill inline-flex items-center gap-2 border border-white/10 bg-white/[0.04] '
        f'px-3 py-2 text-sm text-white/72"><span class="h-2 w-2" style="background:{c}"></span>{t}</span>'
        for t, c in [p['pill'] for p in PRODUCTS])
    fill_children('class="mt-10 flex flex-wrap items-center justify-center gap-3 md:hidden"',
                  pills, key='hero pills')

    # The centre terminal no longer runs shell commands, so its title bar drops
    # the `~/rune` prompt in favour of the product the replay belongs to.
    need('<p data-page-node-id="0YGm8zMP3PqwVL6FF5zcUE">~/rune</p>',
         '<p data-page-node-id="0YGm8zMP3PqwVL6FF5zcUE">Rune Harness</p>',
         'hero main terminal title')
    need('>~/xmcp</p>', '>~/airouter</p>', 'hero terminal title')
    need('$ xiaoshi xmcp attach cluster --cloud huawei', '$ xiaoshi airouter route --model approved',
         'hero terminal cmd')
    need('✔ 多云已纳管', '✔ 模型调用已授权', 'hero terminal ok')
    need('→ 配额与计费就绪', '→ 用量已计量入账', 'hero terminal info')

    need('Rune 2.6 正式发布：训推一体流水线支持英伟达与国产 GPU 异构算力池，多租户配额与弹性伸缩同步上线。'
         '   ·   破晓石完成阿里云 PPU 适配，国产加速卡正式纳入 Rune 调度。',
         'Rune 智算 / Moha 资产 / AIRouter · AI聚合网关 / BOSS 运营，四大板块共享一个云智算内核。'
         '   ·    Rune Harness 云智算内核进入规划：统一会话、诊断、变更审批与执行追踪。',
         'announcement')

    # The centre terminal drops its upstream command/result lines and replays a
    # Rune Harness conversation instead (see HERO_CHAT). The neighbouring
    # terminals keep the command-line look, so the hero shows both entry points.
    need1('<p data-page-node-id="hEFokRTgW8hIuQZfUhpOoS">$ xiaoshi rune job submit --gpu 8</p>'
          '<p class="success" data-page-node-id="LQQ3OAnzNViIZzBDf4KlMb">✔ 训练任务已调度</p>'
          '<p class="info" data-page-node-id="AlGjaAAgEhKoTdmI9C7YaF">→ 推理服务弹性伸缩</p>',
          HERO_CHAT, 'hero chat')

    # 品牌带 CTA（按钮文字「预约演示」）：上游直连控制台，语义不搭 —— 预约演示是
    # 商务动作，落地在 /contact。首页三处控制台直达之一，2026-09-11 晚收归站内。
    retarget_link('IUeOC7hH1y3BdmrFmMXc1z', CONSOLE_HREF, CONTACT_PAGE,
                  '品牌带·预约演示')


def lane(idx, product, active=False):
    """One control-plane lane, rendered from the product registry.

    The four lanes used to be four hand-written calls whose label, hrefs and
    rows repeated PRODUCTS word for word — adding a board meant editing the
    registry and the lane list, and the two could disagree. `idx` stays an
    argument because the lane number is a position, not a product attribute.
    """
    lane_key, label, h3, copy, rows, link_text = product['lane']
    rows_html = ''.join(f'<span><b>{k}</b>{v}</span>' for k, v in rows)
    return (
        f'<div class="tf-control-lane tf-control-{lane_key}{" is-active" if active else ""}">'
        f'<div class="tf-control-lane-icon">'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" '
        f'stroke="currentColor" stroke-width="1.7" stroke-linecap="round" stroke-linejoin="round" '
        f'aria-hidden="true">{ICONS[product["key"]]}</svg></div>'
        f'<p class="tf-runtime-label">{idx} / {label}</p><h3>{h3}</h3><p>{copy}</p>'
        f'<div class="tf-control-lane-summary">{rows_html}</div>'
        f'<a href="{product["page"]}"{ext(product["page"])}>{link_text} {ARROW}</a></div>')


def stage_story():
    global body
    """三大核心产品 -> 四大核心产品 + Rune Harness 内核带。"""
    # tab strip and lanes are two views of the same registry, so the numbering,
    # the names and the hrefs cannot drift apart any more
    tabs = ''.join(
        f'<button type="button" role="tab" aria-selected="{"true" if i == 0 else "false"}" '
        f'class="{"is-active" if i == 0 else ""}"><span>0{i + 1}</span>{p["name"]}</button>'
        for i, p in enumerate(PRODUCTS))

    lanes = ''.join(lane(i + 1, p, active=(i == 0)) for i, p in enumerate(PRODUCTS))

    markup = (
        '<section class="tf-runtime-story text-white"><div class="tf-runtime-story-heading">'
        '<p class="tf-runtime-overline">Rune · Moha · AIRouter · BOSS</p>'
        '<h2>四大核心产品构筑云内核</h2>'
        # 正文并列句里不塞 ` · `：` · ` 是标签用的主副分隔符，放进句子会和
        # 句读打架（「…资产，AIRouter · AI聚合网关，BOSS…」读起来像五段）。
        # 句子内保留「主名 + 定位词」的自然语序，取消的只是「统一」这个形容词。
        '<p>Rune 承载算力，Moha 沉淀资产，AIRouter 聚合网关，BOSS 运营治理。'
        '<br>共同构筑 Rune Harness 云智算内核的基座</p></div>'
        '<div class="tf-control-stage-nav" role="tablist" aria-label="晓石云四大核心板块">'
        + tabs +
        '</div><div class="tf-control-plane">'
        '<div class="tf-control-plane-bar">'
        '<div class="tf-runtime-console-dots" aria-hidden="true"><span></span><span></span><span></span></div>'
        '<span>https://rune.poxiaoshi.cn</span></div>'
        '<div class="tf-control-plane-body">' + lanes + '</div>'
        '<div class="tf-control-harness">'
        '<div class="tf-control-harness-mark"><img src="assets/img/icon-mark.svg" alt=""></div>'
        '<div class="tf-control-harness-copy">'
        '<p class="tf-runtime-label">Rune Harness · 云智算内核</p>'
        '<h3>四大产品之上，一个统一的智算云内核操控。</h3>'
        '<p>Rune Harness 统一会话、资源发现、诊断、变更计划、审批与执行追踪，'
        '把四大板块的能力收敛为一个入口。</p></div>'
        '<div class="tf-control-harness-chips">'
        '<span>Harness</span><span>Agents</span><span>Skills</span><span>Execute</span>'
        '</div></div>'
        '<div class="tf-control-plane-result"><span class="tf-runtime-label">当前结果</span>'
        '<p>✓ 四大板块共享同一套权限、配额与可观测体系</p>'
        '<span>向下由 XCMP 云管理能力提供多云资源底座，向上沉淀为 Rune Harness 云智算内核。</span>'
        '</div></div></section>')
    replace_section('class="tf-runtime-story text-white"', markup, '四大核心产品')


def stage_xcmp():
    """XCMP · 云管理能力优势带已于 2026-09-11 下午整块移除。

    用户要求删掉 `tf-section-inner tf-section-frame tf-section-wash
    tf-advantage-inner` 这个区域。全页只有 XCMP 优势带用这一组 class（#boss 是
    同组少一个类，XCMP 独有 `tf-advantage-inner`），它同时是整页唯一的
    `<section id="gateway">`，所以定位唯一。

    注意这里**仍然必须 cut 一次**：pristine 快照里那一段是原「XMCP · 多云纳管」
    深潜 section，同样靠 `id="gateway"` 定位。只把生成 markup 的代码停掉的话，
    快照里的原板块会原样留在产物里。删的是整个 section 而不是内层 div ——
    只删 inner 会留一条带 padding 的空白带。

    保留的 XCMP 表述（这次只删这一个板块）：story 区「向下由 XCMP 云管理能力提供
    多云资源底座」、FAQ 07、博客案例卡、页尾 CTA 正文、footer 产品列。
    """
    global body
    cut_section('<section id="gateway"', 'XCMP 板块移除')


def stage_rune_moha():
    global body
    # Rune 板块标题
    need('<span class="tf-overline" data-page-node-id="3p3AJIT3xlc3jNbuAEK2Ul">Rune · AI 训推平台</span>',
         '<span class="tf-overline" data-page-node-id="3p3AJIT3xlc3jNbuAEK2Ul">Rune · 智算Infra</span>',
         'rune overline')
    need('<h2 class="tf-section-title mt-5" data-page-node-id="TmyPZwed44pBXCrWStRkHW">'
         '一体化的训推流水线。</h2>',
         '<h2 class="tf-section-title mt-5" data-page-node-id="TmyPZwed44pBXCrWStRkHW">'
         '智算与应用基础设施融合平台</h2>',
         'rune heading')
    need('覆盖模型开发、训练、推理与部署全流程，同时保持克制简洁的操作界面：'
         '算力配额、任务状态与调度记录一屏可见。',
         '覆盖模型开发、训练、推理与部署全流程，同时保持云原生容器能力：'
         '算力配额、任务状态与调度记录清晰可见。',
         'rune copy')

def replace_el(attr, markup, label=None):
    """Swap the whole element whose start tag contains `attr`."""
    global body
    a, b = find_by_attr(body, attr)
    if a < 0:
        MISS.append('element miss: ' + (label or attr))
        return False
    body = body[:a] + markup + body[b:]
    applied['el:' + (label or attr)] = 1
    return True


# lucide icon bodies reused by the asset-audit detail panes (see main.js)
SVG_HEAD = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
            'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" '
            'stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-')
ICON_UPLOAD = (SVG_HEAD + 'upload" aria-hidden="true"><path d="M12 3v12"></path>'
               '<path d="m17 8-5-5-5 5"></path>'
               '<path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path></svg>')
ICON_SHIELD = (SVG_HEAD + 'shield-check" aria-hidden="true">'
               '<path d="M20 13c0 5-3.5 7.5-7.66 8.95a1 1 0 0 1-.67-.01C7.5 20.5 4 18 4 13V6a1 1 0 0 1 '
               '1-1c2 0 4.5-1.2 6.24-2.72a1.17 1.17 0 0 1 1.52 0C14.51 3.81 17 5 19 5a1 1 0 0 1 1 1z">'
               '</path><path d="m9 12 2 2 4-4"></path></svg>')
ICON_CHECK = (SVG_HEAD + 'check" aria-hidden="true"><path d="M20 6 9 17l-5-5"></path></svg>')
ICON_ALERT = (SVG_HEAD + 'circle-alert" aria-hidden="true"><circle cx="12" cy="12" r="10"></circle>'
              '<line x1="12" x2="12" y1="8" y2="12"></line>'
              '<line x1="12" x2="12.01" y1="16" y2="16"></line></svg>')

# The asset-audit pane shown before any click. main.js holds the same four
# records and re-renders on click; keeping the first one in the static markup
# means the panel is never empty without JS.
AUDIT_DEFAULT_DETAILS = [('提交者', 'user: ma.qing', False),
                         ('目标仓库', 'moha://models/llama-3.1-8b', False),
                         ('结果', '已生成版本 v1.0.0', True)]
AUDIT_DEFAULT_EVIDENCE = ['repo: moha://models/llama-3.1-8b',
                          'revision: v1.0.0 · sha256:3f9a…',
                          'content: 15.2 GB · 4 个分片']


def stage_moha():
    global body
    # Moha 板块标题
    need('<span class="tf-overline" data-page-node-id="pIgVjtQ6hHonlcqCMluRKe">Moha · AI 资产仓库</span>',
         '<span class="tf-overline" data-page-node-id="pIgVjtQ6hHonlcqCMluRKe">Moha · 数字仓库</span>',
         'moha overline')
    need('<h2 class="tf-section-title mt-5" data-page-node-id="rZQhPlodq8NIUKUEHAqESw">每一份资产都可追溯。</h2>',
         '<h2 class="tf-section-title mt-5" data-page-node-id="rZQhPlodq8NIUKUEHAqESw">'
         '你的私有化HuggingFace，每一份数据都可追溯</h2>',
         'moha heading')
    need('<p class="tf-section-copy" data-page-node-id="M1zQOHXYY7QD37a4dmKZhf">'
         '看清谁在什么时候访问了什么、为什么被允许，以及留下了哪些证据。</p>',
         '<p class="tf-section-copy" data-page-node-id="M1zQOHXYY7QD37a4dmKZhf">'
         '统一社区化管理模型、数据集、镜像、空间和技能</p>',
         'moha copy')

    # Default selection moves to record 01 so the timeline reads top-down.
    need('<button type="button" class="tf-audit-event is-cyan" aria-pressed="false" '
         'data-page-node-id="Ft5tlHEBHQDmXfVOSJMgp9">',
         '<button type="button" class="tf-audit-event is-cyan is-selected" aria-pressed="true" '
         'data-page-node-id="Ft5tlHEBHQDmXfVOSJMgp9">',
         'audit select 01')
    need('<button type="button" class="tf-audit-event is-amber is-selected" aria-pressed="true" '
         'data-page-node-id="IhnZNLvJFABSDNskHukJ3A">',
         '<button type="button" class="tf-audit-event is-amber" aria-pressed="false" '
         'data-page-node-id="IhnZNLvJFABSDNskHukJ3A">',
         'audit deselect 03')

    # The right-hand panes were carried over from the reference page and still
    # described a generic approval flow. Re-anchor them on moha.push.
    details = ''.join(
        '<div><dt>%s</dt><dd>%s%s</dd></div>' % (k, ICON_CHECK if ok else '', v)
        for k, v, ok in AUDIT_DEFAULT_DETAILS)
    replace_el(
        'class="tf-audit-decision"',
        '<div class="tf-audit-decision" aria-live="polite">'
        '<div class="tf-audit-panel-label"><span>选中记录</span>'
        '<small>01<!-- --> / 04</small></div>'
        '<div class="tf-audit-decision-icon is-cyan">' + ICON_UPLOAD + '</div>'
        '<h3>上传即入库，版本自动冻结。</h3>'
        '<p>模型、数据集、镜像、空间与技能包统一收纳，自动计算校验摘要并生成不可变版本标签。</p>'
        '<dl class="tf-audit-decision-details">' + details + '</dl></div>',
        'audit decision pane')
    replace_el(
        'class="tf-audit-evidence"',
        '<div class="tf-audit-evidence">'
        '<div class="tf-audit-panel-label"><span>证据包</span>' + ICON_ALERT + '</div>'
        '<p>本次上传的原始文件、提交信息与校验摘要，都与这条记录绑定在一起。</p>'
        '<ul>' + ''.join('<li>%s</li>' % i for i in AUDIT_DEFAULT_EVIDENCE) + '</ul>'
        '<div class="tf-audit-evidence-footer">' + ICON_CHECK + ' 完整且可导出</div></div>',
        'audit evidence pane')


AIR_AMBIENT = ('<img src="assets/img/grid-ambient.webp" alt="" width="1440" height="958" '
               'loading="lazy" decoding="async" class="pointer-events-none absolute '
               'right-[-9rem] top-10 w-[42rem] max-w-none opacity-18 mix-blend-screen">')
AIR_COPY = ('AIRouter 是晓石云的 AI聚合网关：一个入口接入各家大模型与多模态能力，'
            '统一密钥与配额、按策略路由请求，并保留每一次调用的用量与审计记录。')


def board_section(sid, order, overline, title, copy, link_text, link_href, panel,
                  section_class='tf-section scroll-mt-[90px] tf-motion-section',
                  wash=False, ambient='', sidebar_extra='',
                  title_attr='', copy_attr='', section_attr=''):
    """The shared tf-section-* board shell.

    Rune rides the vendor markup, but AIRouter and BOSS are both authored here
    and were each spelling out the same six nested wrappers (section → frame →
    split → sidebar → overline/title/copy/link → panel). Two copies already
    meant every layout tweak had to be made twice; a fifth board or a
    /products/* landing page built by hand would have made it three.

    `panel` is raw markup and keeps its own wrapper class, because the boards
    legitimately differ there (code panel vs. operations panel). `_attr`
    arguments carry the node ids harvested from the snapshot so the
    rebuilt sections keep their DOM ancestry.
    """
    frame = 'tf-section-inner tf-section-frame' + (' tf-section-wash' if wash else '')
    return (
        f'<section id="{sid}" class="{section_class}" style="--tf-motion-order: {order};"'
        + section_attr + '>'
        + ambient
        + f'<div class="{frame}"><div class="tf-section-split">'
        f'<div class="tf-section-sidebar">'
        f'<span class="tf-overline">{overline}</span>'
        f'<h2 class="tf-section-title mt-5"{title_attr}>{title}</h2>'
        f'<p class="tf-section-copy"{copy_attr}>{copy}</p>'
        f'<a href="{link_href}"{ext(link_href)} class="tf-section-link">{link_text} {ARROW4}</a>'
        + sidebar_extra
        + '</div>'
        + panel
        + '</div></div></section>')


def stage_airouter():
    """把 AIRouter 板块换到 Rune / BOSS 同款的 tf-section-* 排版体系。

    参考页给 AIRouter 单独做了一套皮肤（.tf-managed-api-section / -shell /
    -intro）：自带 #111 底色、4rem 盒宽、按钮式链接和一枚终端标记，和 Rune 的
    tf-section-inner + tf-section-split + tf-section-sidebar 完全不同。整页看下来
    只有这个板块不像同一套设计，所以这里只替换外壳与左栏，右栏的代码面板原样
    保留（main.js 依赖它的 class，见 assets/css/custom.css 里的对齐规则）。
    """
    global body
    need('aria-label="AI Router 接入示例"', 'aria-label="AIRouter 接入示例"',
         'airouter tabs label')

    a, b = section_span('<section id="tools"')
    if a < 0:
        MISS.append('AIRouter section missing')
        return
    seg = body[a:b]
    ia, ib = find_by_attr(seg, 'class="tf-managed-api-intro"')
    ca, cb = find_by_attr(seg, 'class="tf-managed-api-code-panel"')
    if min(ia, ib, ca, cb) < 0:
        MISS.append('AIRouter 布局锚点缺失（-intro / -code-panel）')
        return

    intro = seg[ia:ib]
    code = seg[ca:cb]
    # keep the original node ids so the pane keeps its DOM ancestry
    sec_id = re.search(r'<section[^>]*?(\sdata-page-node-id="[^"]+")', seg)
    h2_id = re.search(r'<h2(\sdata-page-node-id="[^"]+")', intro)
    p_id = re.search(r'<p(\sdata-page-node-id="[^"]+")', intro)

    markup = board_section(
        'tools', 5, 'AIRouter · AI聚合网关', '一个入口，接入所有大模型', AIR_COPY,
        '了解 AIRouter', 'https://docs.poxiaoshi.cn', code,
        ambient=AIR_AMBIENT,
        title_attr=h2_id.group(1) if h2_id else '',
        copy_attr=p_id.group(1) if p_id else '',
        section_attr=sec_id.group(1) if sec_id else '')
    body = body[:a] + markup + body[b:]
    applied['section:AIRouter 布局对齐 Rune'] = 1


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

    markup = board_section(
        'boss', 4, 'BOSS · 运营平台', '看清每一笔消耗，管住每一个租户',
        'BOSS 面向智算中心与平台的运营方：租户开户、配额分配、计量计费、'
        '资源水位与运营报表在同一控制台闭环，运营决策不再依赖人工台账。',
        '进入 BOSS', product('boss')['page'],
        '<div class="tf-panel tf-boss-panel">'
        '<div class="tf-gateway-panel-bar"><div><p>运营视图</p>'
        '<span>2026 年 9 月 · 智算中心 A</span></div></div>'
        '<div class="tf-boss-metrics">' + metric_html + '</div>'
        '<div class="tf-boss-table">' + table + '</div>'
        + trend +
        '<div class="tf-boss-foot"><span>计量周期 2026-09-01 ~ 2026-09-30</span>'
        '<span>✓ 出账已生成</span></div>'
        '</div>',
        section_class='tf-section scroll-mt-[90px] text-white tf-motion-section',
        wash=True,
        sidebar_extra=(
            '<div class="tf-gateway-capabilities" aria-label="BOSS 运营能力">'
            '<p>BOSS 运营路径</p>'
            '<div><span>01</span><div><h3>开户与授权</h3>'
            '<p>租户、组织与成员在一个入口完成开户与权限下发。</p></div></div>'
            '<div><span>02</span><div><h3>配额与调度</h3>'
            '<p>按租户、资源池与队列分配算力配额，超限自动拦截。</p></div></div>'
            '<div><span>03</span><div><h3>计量与出账</h3>'
            '<p>GPU 时长、存储与调用量实时计量，按月出账并可导出。</p></div></div>'
            '</div>'))
    insert_before('<section id="blog"', markup, 'BOSS 板块')


def stage_harness():
    """Rune Harness 规划板块已于 2026-09-11 移除。

    用户要求删掉那个「Rune Harness · 云智算内核（规划中）」的区域，也就是本脚本
    插入的 <section id="harness">（外壳 class 为 tf-section-inner tf-section-frame
    tf-section-wash）。pristine 快照里没有这个板块，所以删除动作就是「不再插入」，
    连同它专属的 .tf-harness-* 样式与回归探针一起清掉。

    Rune Harness 的表述在别处仍然保留：hero overline、story 区的内核带、
    FAQ 09 与页尾 CTA —— 这次只删这一个板块，没有动那些。
    """
    global body

    # 定价区排到 blog 之前（原来是为了排到 Harness 板块之后，板块删了位置不动）
    pricing = cut_section('<section id="pricing"', '定价区前移')
    if pricing:
        at, _ = section_span('<section id="blog"')
        if at < 0:
            MISS.append('pricing reinsert anchor')
        else:
            body = body[:at] + pricing + body[at:]
            applied['pricing moved before blog'] = 1


# 定价区的四张卡。每张卡三个槽位（名称 / 单价 / 说明），每个槽位都由
# (node-id, 快照原文, 新文案) 三元组描述 —— 拉平成一个大表后，加第五张卡或
# 改一句报价说明都只是往这里加一行，不必再写三遍 need()。
# 卡片 01 的名称栏原文就是 Rune，所以 name 为 None。node-id 必须来自快照。
PRICING_CARDS = [
    {'card': '01', 'name': None,
     'unit': ('WNwMBzyBGd3VCOtBk3WVrx', '按算力与任务量', '算力订阅 · 训练推理'),
     'copy': ('m6eON9HHogaZtgOfuH7W1D', '以统一的算力单价支撑训练与推理。',
              '训练、推理与容器编排随订阅开通，按 GPU 算力规格计价。')},
    {'card': '02',
     'name': ('oMpelstFk1ivXB3MrICyCg', 'XMCP', 'Moha'),
     'unit': ('ixDIlEntVGAL4IfEWrViZJ', '订阅 + 节点', '算力订阅 · 资产模块'),
     'copy': ('Vw3gxOxts71NBWYoMgxj9w', '按纳管集群与节点规模订阅授权。',
              '资产仓库随订阅开通，存储、加密与审计按容量叠加。')},
    {'card': '03',
     'name': ('GC2aAg6dx0GMGQ2EmIe6nH', 'Moha', 'AIRouter'),
     'unit': ('zQEw1QLJgdOUJMG9s3xIrW', '订阅 + 节点', '算力订阅 · 网关模块'),
     'copy': ('tmafbdqPfcjFV9Uba3N4Ew', '按资产仓库容量与存储时长计费。',
              'AI聚合网关随订阅开通，路由策略与用量看板按调用规模叠加。')},
    {'card': '04',
     'name': ('TS3C06yrka0W0iTGc0dHM2', '交付与实施服务', 'BOSS'),
     'unit': ('9H4vJnTaNPDn0wZxkAwH7Q', '定制报价', '算力订阅 · 运营模块'),
     'copy': ('vG555PyLIzBlhCTjBGA1ep', '按项目范围提供开发与生产交付。',
              '运营控制台随订阅开通，租户、配额与计量出账按纳管规模叠加。')},
]
PRICING_SLOTS = (('name', 'h3'), ('unit', 'strong'), ('copy', 'p'))


def stage_pricing():
    """定价区：统一按算力订阅 + 模块组合（2026-09-11 下午重写）。

    原口径是「每条产品线各用一种计价方式」——Moha 按容量、AIRouter 按调用量阶梯、
    BOSS 按纳管规模。用户明确「产品都是按算力订阅制报价，可以按不同模块组合」，
    所以四张卡统一成「算力订阅 · XX 模块」：订阅制是计价主体，模块是可选组合项。

    只替换文本节点：类名、DOM 结构、卡片数量与顺序一律不动，样式零变化。
    四个槽位的内容来自 PRICING_CARDS，这里只负责按 (node-id, old, new) 落锤。
    """
    global body
    need1('灵活的计价方式_', '算力订阅制_', 'pricing overline')
    need1('按使用的产品线计价。', '按算力订阅，按模块组合。', 'pricing heading')
    need1('XMCP 与 Moha 采用订阅制授权，Rune 按算力与任务量计费，交付与实施服务按项目范围报价。',
          '四大产品共用一套算力订阅计价：以算力为基准，按需选择模块组合，统一订阅、统一出账。',
          'pricing intro')
    for card in PRICING_CARDS:
        for slot, tag in PRICING_SLOTS:
            spec = card[slot]
            if not spec:
                continue
            attr, old, new = spec
            need(f'<{tag} data-page-node-id="{attr}">{old}</{tag}>',
                 f'<{tag} data-page-node-id="{attr}">{new}</{tag}>',
                 f'pricing card {card["card"]} {slot}')
    need1('AI Router API：按调用量阶梯计费，企业版支持私有化部署与专属配额。',
          '模块可按需增减，变更于下一订阅周期生效；交付与实施服务按项目范围单独报价。',
          'pricing note')

    # 六处 href：四张卡各指自己的产品页，两处「查看完整报价 / 查看商务条款」指 /contact。
    # 它们原本**都**指向旧站首页（旧站的报价页在那里），是首页最后一处成规模的旧站出链。
    # 四张卡与产品页的顺序不靠下标对齐：node-id 与 slug 逐条写死在 PRICING_RETARGET 里，
    # 上游哪天调换卡片顺序，这里会按 node-id 报错而不是静默错配。
    for label, nid, new_href in PRICING_RETARGET:
        if retarget_link(nid, PRICING_HREF, new_href, '定价·' + label):
            applied['定价·%s -> %s' % (label, new_href)] = 1


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
          'AIRouter 聚合网关，BOSS 面向智算中心运营方提供租户、配额与计量管理。'
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
    # 页脚「产品」列：四大板块置顶（名称与 hero pill 同源）→ 站内产品页。
    # 「产品总览」也一并收回站内 `/`：它原本指旧站首页，而旧站正是本站在替换的东西，
    # 页脚里留一条「回旧站」的入口与整站口径自相矛盾。
    # XCMP 云管理 2026-09-11 晚也收回站内了 —— 新站仍然没有这一页（它被明确排除在
    # 深潜之外），所以落点是 Rune 产品页：XCMP 是 Rune 那一层的多云资源底座，
    # 首页正文就是这么写的（「向下由 XCMP 云管理能力提供多云资源底座」）。
    # 留在旧站的只剩 KubeGems —— 它本来就是站外的开源项目，不是换牌残留。
    #
    # 文本包成乱码宿主（2026-09-11 晚）。这里此前写的是
    # `class="tf-footer-link hover-scramble"`：`hover-scramble` 在 vendor.css 与
    # main.js 里都没有任何定义，是个只在生成器里出现过一次的死类名 —— 页脚这
    # 21 条链接的 hover 动效从来就没生效过。类名删掉，改包真宿主；动效的真相源
    # 只剩 `.tf-scramble-label` 一处，不留第二个看起来像实现的空壳。
    footer_links = [('产品总览', '/')]
    footer_links += [(p['pill'][0], p['page']) for p in PRODUCTS]
    footer_links += [('XCMP 云管理', '/products/rune/'),
                     ('KubeGems', 'https://kubegems.io')]
    html = ''.join(
        f'<a class="tf-footer-link" href="{h}"{ext(h)}>{scramble(t)}</a>'
        for t, h in footer_links)
    fill_children('data-page-node-id="DSx57Z0vBkGaSPFY5k1RWp"', html,
                  key='footer 产品列')

    # 页脚巨型 wordmark：晓石云智算平台 → 破晓石科技（2026-09-11）
    # 只换文本节点，不动 .tf-footer-brand-word 的任何样式；字号是按 7 个全角字
    # 调的，改成 5 字后 wordmark 会居中变窄，需要的话按字数比例调 clamp 即可。
    need1('<span data-page-node-id="pHvRqXDT6WITPlOY4FYuEp">晓石云智算平台</span>',
          '<span data-page-node-id="pHvRqXDT6WITPlOY4FYuEp">破晓石科技</span>',
          'footer wordmark')
    # 底部「所有服务运行正常」状态条：整条 div 删掉（2026-09-11）。
    # 连它前面那截换行 + 缩进一起吃掉，避免在两份 div 之间留一条缩进空行。
    # vendor.css 里的 .tf-footer-status 规则随之成为死代码，按约定不动 vendor。
    need1('\n    <div class="tf-footer-status" data-page-node-id="4sAsYiGLxHkpLWCX852rpb">'
          '<a href="https://www.poxiaoshi.cn/" target="_blank" rel="noopener noreferrer"'
          ' data-page-node-id="lDFIyjgjwfLvzDbs2tPxD9">'
          '<i data-page-node-id="lSpxwnMkzP5DDnhxa0s8uj"></i>所有服务运行正常</a></div>',
          '', 'footer status pill')
    # 版权行的备案号占位（` · 蜀ICP备·备案号占位`）：真实备案号下来之前先不占位，
    # 只留「© 年份 公司 · 地址」。前缀 ` · ` 一起删，避免尾随分隔符。
    need1(' · 蜀ICP备·备案号占位', '', 'footer ICP placeholder')
    # 页脚「公司」列里的「加入我们」指向的是 /about/（关于我们），名不对题；
    # 2026-09-11 晚新建 about/ 公司简介页时顺手改成正确的标签。真正的招聘入口
    # 在导航「关于我们 → 加入我们」（/careers），页脚这一条只负责公司简介。
    need1('data-page-node-id="WQs06tBb1wDxj7OvovKSYT">加入我们</a>',
          'data-page-node-id="WQs06tBb1wDxj7OvovKSYT">关于我们</a>',
          'footer 公司列 关于我们')
    need('>云原生与 AI 之旅？</strong>', '>云智算内核之旅？</strong>', 'cta h2')
    need('一个底座，贯穿多云纳管到 AI 训推全流程。',
         '四大板块为基座，共同构建 Rune Harness 云智算内核。', 'cta copy')
    # blog snippet still used the retired XMCP naming
    need('通过 XMCP 统一纳管多地域资源', '通过 XCMP 统一纳管多地域资源', 'blog XCMP naming')
    # 页脚社交区的「联系我们」图标原先指向旧站 https://www.poxiaoshi.cn/contact/。
    # 站内 /contact 页建好后（2026-09-11）改指站内 —— 站外那版是换牌残留，
    # 两个「联系我们」在不同域名下打架。注意只摘掉 href/aria-label 之后的
    # target+rel：站内链接不该开新窗。
    need1('<a href="https://www.poxiaoshi.cn/contact/" aria-label="联系我们" '
          'target="_blank" rel="noopener noreferrer" data-page-node-id="Sh4XaPA5s3t2UYzD5mfs9P">',
          '<a href="/contact" aria-label="联系我们" '
          'data-page-node-id="Sh4XaPA5s3t2UYzD5mfs9P">',
          'footer 联系我们 -> /contact')

    # 页脚另外两列（解决方案 / 客户案例）与「公司」列一条，连同 XCMP 那条上游链接：
    # 六条全部指旧站，2026-09-11 晚按 FOOTER_RETARGET 的语义就近收归站内。
    # 这批标签原本都带 `target="_blank" rel="noopener noreferrer"`，retarget_link 会在
    # 目标为站内时把这两个属性摘掉 —— 站内跳转开新窗是错的，页脚尤其明显。
    for label, nid, old_href, new_href in FOOTER_RETARGET:
        if retarget_link(nid, old_href, new_href, '页脚·' + label):
            applied['页脚·%s -> %s' % (label, new_href)] = 1

    # 页尾 CTA（同样写着「预约演示」）：与品牌带那处置同样改法。
    retarget_link('pZ011MTZ4ISN6rqe9QHCZt', CONSOLE_HREF, CONTACT_PAGE,
                  '页尾 CTA·预约演示')


def stage_footer_scramble():
    """给页脚所有链接的纯文本包上乱码宿主，并清掉死类名 `hover-scramble`。

    「产品」列由 stage_footer_cta() 整段重写成带宿主的形式；其余 14 条（文档 /
    解决方案 / 客户案例 / 公司四列）来自 pristine 快照，而快照给每一条都写了
    `class="tf-footer-link hover-scramble"` —— `hover-scramble` 在 vendor.css 与
    main.js 里**都没有定义**（整个仓库只有快照和生成器里出现过这个字符串）。
    原作者显然打算给页脚做乱码动效，实现从未落地：hover 时只有颜色与位移，
    文字是死的。

    这一遍刻意不按来源区分，只认「`<a>` 里还是纯文本」这一条 —— 已经包过宿主的
    产品列那 7 条，内容里是 `<span>`，天然不匹配。于是本函数跑第二遍是空操作，
    不会把宿主套成两层（幂等，别改成按 class 白名单跳过的写法）。
    """
    global body
    count = [0]

    def wrap(m):
        count[0] += 1
        return m.group(1) + scramble(m.group(2)) + m.group(3)

    # 内容用 `[^<]+` 而不是 `.*?`：一旦内容里出现标签，就说明它不是一条单纯的
    # 文字链接（图标 + 文字的社交入口），那种不该包。
    body = re.sub(r'(<a\b[^>]*\btf-footer-link(?=[\s"])[^>]*>)([^<]+)(</a>)',
                  wrap, body)
    applied['页脚链接乱码宿主'] = count[0]

    # 空壳类名到此为止不该再出现在产物里。留着它，下一个读代码的人会以为页脚的
    # 动效由它驱动，而真相在 .tf-scramble-label 上 —— 这次排查的时间就花在这上面。
    leftover = body.count('hover-scramble')
    if leftover:
        body = re.sub(r'\s*hover-scramble\b', '', body)
        applied['hover-scramble 空壳类名清理'] = leftover
    if 'hover-scramble' in body:
        MISS.append('hover-scramble survived the footer pass')


def stage_contact_retarget():
    """站芯里的商务邮件链接统一改指 /contact（2026-09-11 晚（十三））。

    改的是 nav / 移动抽屉 / footer —— 也就是 `portal_page.derive()` 从首页取走的
    那部分站芯，所以这一处改动会同时落到全部 13 个产物页上。
    """
    for label, nid, old_href, new_href in CONTACT_RETARGET:
        if retarget_link(nid, old_href, new_href, label):
            applied['%s -> %s' % (label, new_href)] = 1


def stage_blog_cards():
    """首页博客预览区三张卡 + 顶部公告条：把指向线上的链接收回站内。

    2026-09-11 把 `/blog` 做成**自持内容**之后（列表页 + 5 个详情页，内容源在
    `content/blog/*.md`，见 tools/build_blog.py），首页就不该再跳到 poxiaoshi.cn
    —— 这个站点的目的正是替换 poxiaoshi.cn。

    三张卡原先的 href 是换牌时留下的上游博客 slug，三个都是本站不存在的死链：
    `/blog/agent-memory-next-bottleneck` 等等；`alt` 也还是那批英文。公告条那 10 个
    副本（marquee 横向滚动需要把同一段重复多份）指向线上 `/blog/`，一并收回。

    目标 slug 是**从每张卡自己的标题读出来的**，不是另抄一份顺序表——将来换掉某张卡
    时，href 与标题必须一起改，这里的三元组就是那个约束。

    封面同理：图名不再写在这里，而是从内容源的 `cover:` 读（见 post_cover），
    与详情页共用同一张图。
    """
    global body
    # (换牌遗留的上游 slug, 本站 slug, 旧英文 alt, 新中文 alt,
    #  换牌自造的旧封面, 该卡图片框的 node id)
    cards = [
        ('agent-memory-next-bottleneck', '2026-03-27-aliyun-ppu',
         'Agent memory architecture with semantic recall layers',
         '破晓石完成阿里云 PPU 适配',
         'assets/img/blog/cover-ppu.png', 'TijzkcUxPr4TrlDeNq1sfL'),
        ('context-engineering-for-ai-agents', '2024-12-15-hygon',
         'Context engineering compression pipeline for AI agents',
         '破晓石与海光完成兼容性认证',
         'assets/img/blog/cover-hygon.png', 'uwd0Ho9QbzQ7egGasHW15k'),
        ('why-unified-llm-gateway', '2025-07-24-majnoon',
         'Unified LLM gateway routing multiple AI model providers',
         '破晓石交付马基努油田云项目',
         'assets/img/blog/cover-oilfield.png', None),
    ]
    for stale, slug, old_alt, new_alt, old_cover, frame_id in cards:
        key = 'blog card href -> ' + slug
        # 首页每张卡是**一个** <a> 把封面图、标题、摘要、阅读全文按钮整块包住
        # （与 /blog 列表页那种三段式结构不同），所以每张卡只有一处 href。
        if need('/blog/' + stale, '/blog/%s/' % slug, key):
            got = applied.get(key)
            if got != 1:
                MISS.append(f'blog card {slug}: href replaced {got} times, expected 1')
        need1(f'alt="{old_alt}"', f'alt="{new_alt}"', 'blog card alt -> ' + slug)

        # 封面：换成内容源里那一张，首页与详情页从此同图。
        cover = post_cover(slug)
        if cover:
            need1(f'src="{old_cover}"', f'src="{cover}"', 'blog card cover -> ' + slug)

        # 图片框的处理档位。换牌时三张是**为深色卡片画的抽象线稿**（黑底 + 细线），
        # 默认档 `transform:scale(1.3)` 那种强放大裁切对它们是加分的。
        # 现在换成内容源自带的实拍照片与品牌图（芯片实物照 / 海光 logo / 会议室实景），
        # 构图本身有意义、不该被裁——尤其 logo 图放大后会切掉两侧。
        # `.is-wide-art` 档是 `scale(1.04)` + `object-position:center`（完整呈现），
        # 第三张原本就带这个类，这里把前两张补齐，三张统一。
        if frame_id:
            old_frame = f'class="tf-blog-image-frame " data-page-node-id="{frame_id}"'
            need1(old_frame, old_frame.replace('tf-blog-image-frame ',
                                               'tf-blog-image-frame is-wide-art '),
                  'blog card frame -> is-wide-art (' + slug + ')')
    # 公告条：整条 <aside class="tf-announcement-bar"> 里的轨道副本
    ann = 'href="https://www.poxiaoshi.cn/blog/"'
    count = body.count(ann)
    if count == 0:
        MISS.append('miss: announcement bar blog links')
    else:
        body = body.replace(ann, 'href="/blog"')
        applied['announce bar -> /blog'] = count


def stage_guards():
    global body
    """Sanity checks that must not regress."""

    def link_href_of(nid):
        """取带该 node-id 的 `<a>` 的 href；找不到返回 None。

        按 node-id 把标签捞出来核 href，**不是**核「新 href 在页面里出现过」—— 后者
        几乎永远为真（站内路径满页都是），等于没断言。第一版就是这么写的：反向自测
        把某条链接改回旧目标，只有总数那条报，逐条这条一声不响。
        有三处用它（商务收口 / 定价区 / 页脚回收），所以定义提到函数最上面。
        """
        i = body.find('data-page-node-id="%s"' % nid)
        if i < 0:
            return None
        a = body.rfind('<a ', 0, i)
        end = body.find('>', i)
        if a < 0 or end < 0:
            return ''
        m = re.search(r'href="([^"]*)"', body[a:end + 1])
        return m.group(1) if m else ''

    opens = len(re.findall(r'<div\b', body))
    closes = len(re.findall(r'</div>', body))
    if opens != closes:
        MISS.append(f'unbalanced <div>: {opens} vs {closes} (delta {opens - closes})')
    for leftover in ('XMCP · 多云纳管', '不改现有体系，纳管每一朵云。', '三大核心产品',
                     'AI Router', 'ChatBox',
                     # 换牌时给首页三张博客卡自造的封面目录；2026-09-11 起首页
                     # 与详情页共用内容源的 cover（assets/img/news/…）
                     'assets/img/blog/',
                     # AIRouter 曾误写成 AiIRouter（多一个 i），2026-09-11 修正
                     'AiIRouter',
                     # AIRouter 的定位词 2026-09-11 统一为 `AI聚合网关`（用户拍板）。
                     # 下面这些是它取代掉的四种旧说法 + 加长变体，任何一个回来
                     # 都说明某处文案回退了。注意 `AIRouter 网关`（空格）与正式
                     # 写法 `AIRouter · AI聚合网关`（点号）不是子串关系，能咬住。
                     'AIRouter 网关', 'AIRouter · 模型网关', 'AIRouter 统一网关',
                     'AIRouter 统一模型网关', '统一模型网关', '统一模型入口',
                     # 「关于我们」下拉 2026-09-11 的调整（见 stage_nav_company）：
                     # 开源项目改指站外 kubegems.io、加入我们整项移除、
                     # 页脚「联系我们」图标从旧站外链改指站内 /contact
                     '/careers', '/affiliates', 'poxiaoshi.cn/contact/',
                     '$ xiaoshi rune job submit', '→ 推理服务弹性伸缩',
                     '>~/rune</p>', '四大核心板块，一个云智算内核。',
                     '共同构成 Rune Harness 云智算内核的基座',
                     '~/xiaoshi/control-plane.yaml',
                     '四板块在线',
                     '四大板块之上',
                     # Rune 板块的旧 overline / 标题 / 正文（各在整页出现 1 次）
                     '一体化的训推流水线。',
                     'Rune 智算 · AI 训推平台（板块 01）',
                     '克制简洁的操作界面',
                     # the two Rune-board lines superseded on 2026-09-11 pm
                     'Rune 智算Infra',
                     'AI智算与容器一体化平台',
                     # Moha 板块的旧 overline / 标题 / 正文
                     'Moha · AI 资产仓库',
                     'Moha 资产 · AI 资产仓库（板块 02）',
                     '每一份资产都可追溯。',
                     '看清谁在什么时候访问了什么、为什么被允许，以及留下了哪些证据。',
                     # the reference page's generic approval story, replaced by
                     # the moha.push record (main.js carries the other three)
                     '一次越权访问被策略拦截。',
                     '该请求超出了所属租户的访问范围',
                     # the four harness chips used to spell out capabilities
                     '<span>统一会话</span><span>双安全域</span>',
                     # the AIRouter board's own skin; retired when it moved onto
                     # the shared tf-section-* layout (see stage_airouter)
                     'tf-managed-api-section', 'tf-managed-api-shell',
                     'tf-managed-api-intro', 'tf-managed-api-mark',
                     'tf-block-overline', '>AI Router API</span>',
                     # AIRouter board copy superseded on 2026-09-11 pm
                     'AIRouter 网关 · 板块 03',
                     '一个入口，接入所有大模型。',
                     # the second entry link was dropped, so its flex wrapper
                     # (.tf-section-actions) went away with it
                     '密钥与用量', 'tf-section-actions',
                     # BOSS board copy superseded on 2026-09-11 pm
                     'BOSS 运营 · 板块 04',
                     '看清每一笔消耗，管住每一个租户。',
                     # the Rune Harness planning board was removed entirely
                     # (see stage_harness) -- its section, heading and flow strip
                     # must not come back through a stale stage
                     'id="harness"', 'tf-harness-flow', 'tf-harness-phase',
                     'Rune Harness · 云智算内核（规划中）',
                     '以四大板块为基座，打造云智算内核。',
                     # pricing board rewritten to "算力订阅 + 模块组合" on
                     # 2026-09-11 pm; these are the superseded lines
                     '灵活的计价方式_',
                     '按使用的产品线计价。',
                     '订阅 + 容量', '按调用量阶梯',
                     '按纳管规模订阅', '定制报价',
                     '按算力与任务量', '以统一的算力单价支撑训练与推理。',
                     '按纳管集群与节点规模订阅授权。',
                     '按资产仓库容量与存储时长计费。',
                     '网关调用按阶梯计价，企业版支持专属配额与私有化部署。',
                     '面向智算中心运营方，含租户、配额与计量出账能力。',
                     'AI Router API：按调用量阶梯计费，企业版支持私有化部署与专属配额。',
                     '交付与实施服务按项目范围定制报价；XCMP 云管理能力随平台统一交付。',
                     # the XCMP capability band was removed entirely on
                     # 2026-09-11 pm (see stage_xcmp) -- its section, cards and
                     # entry link must not come back through a stale stage
                     'id="gateway"', 'tf-advantage-inner', 'tf-advantage-grid',
                     'tf-advantage-card', 'tf-advantage-head', 'tf-advantage-index',
                     'XCMP · 云管理能力', '把多云真正用成一朵云。',
                     '<p class="tf-section-copy">XCMP 是晓石云的云管理能力底座',
                     '>进入 XCMP ',
                     # footer wordmark renamed to the company name, and the
                     # status pill / ICP placeholder were removed from the foot
                     '晓石云智算平台',
                     'tf-footer-status', '所有服务运行正常',
                     '蜀ICP备·备案号占位',
                     # nav brand renamed to the company name on 2026-09-11 pm
                     # (the visible half lives in assets/img/logo.svg, which no
                     # rewrite can reach, so this only guards the alt text)
                     '晓石云 logo',
                     # the footer 公司 column pointed at /about/ while being
                     # labelled 加入我们; corrected when about/ was built
                     'data-page-node-id="WQs06tBb1wDxj7OvovKSYT">加入我们</a>',
                     # the blog preview cards carried three upstream blog
                     # slugs (all dead links) until /blog became self-hosted,
                     # and the announcement bar still pointed at the live
                     # poxiaoshi.cn blog -- see stage_blog_cards
                     'agent-memory-next-bottleneck',
                     'context-engineering-for-ai-agents',
                     'why-unified-llm-gateway',
                     'Agent memory architecture',
                     'Context engineering compression',
                     'Unified LLM gateway routing',
                     'href="https://www.poxiaoshi.cn/blog/"'):
        if leftover in body:
            MISS.append('leftover copy: ' + leftover)
    if UPSTREAM_BRAND_RE.search(body):
        MISS.append('leftover copy: 上游品牌名（UPSTREAM_BRAND_RE 命中）')
    for required in ('Rune Harness 即将开放', 'tf-overline-live', 'tf-thinking-spin',
                     '智算为中心的 </span>', 'AI 原生云内核</span>',
                     '专注云原生开源、混合云与 AI 智算平台，为企业提供覆盖容器云、混合云、智算云及 AI 能力的全栈解决方案。',
                     'Rune Harness · 云智算内核', 'tf-control-harness',
                     'tf-boss-metrics', 'id="boss"',
                     'tf-chat-bubble">部署 DeepSeek V4.1 Flash', 'tf-chat-dots',
                     'tf-chat-orb-grad', '✔</span><span>模型已调度部署完成',
                     'tf-chat-state-done">已处理',
                     '四大核心产品构筑云内核',
                     # the copy is two sentences on purpose: the boards on one
                     # line, the kernel they build on the next. 正文并列句里给的是
                     # 「主名 + 定位词」（不带 ` · `，理由见 stage_story）
                     'Rune 承载算力，Moha 沉淀资产，AIRouter 聚合网关，BOSS 运营治理。',
                     '<br>共同构筑 Rune Harness 云智算内核的基座',
                     'https://rune.poxiaoshi.cn',
                     '四大产品之上，一个统一的智算云内核操控。',
                     # the pricing board now sells one thing -- a compute
                     # subscription -- with optional modules stacked on top
                     '>算力订阅制_</span>',
                     '>按算力订阅，按模块组合。</h2>',
                     '四大产品共用一套算力订阅计价：以算力为基准，按需选择模块组合，统一订阅、统一出账。',
                     '算力订阅 · 训练推理', '算力订阅 · 资产模块',
                     '算力订阅 · 网关模块', '算力订阅 · 运营模块',
                     '模块可按需增减，变更于下一订阅周期生效；交付与实施服务按项目范围单独报价。',
                     '<span>Harness</span><span>Agents</span><span>Skills</span><span>Execute</span>',
                     '0YGm8zMP3PqwVL6FF5zcUE">Rune Harness</p>',
                     '>Rune · 智算Infra</span>',
                     '>智算与应用基础设施融合平台</h2>',
                     '覆盖模型开发、训练、推理与部署全流程，同时保持云原生容器能力：'
                     '算力配额、任务状态与调度记录清晰可见。',
                     '>Moha · 数字仓库</span>',
                     '你的私有化HuggingFace，每一份数据都可追溯',
                     '统一社区化管理模型、数据集、镜像、空间和技能',
                     # the audit pane is pre-filled with record 01 so it is never
                     # blank before main.js binds the click handler
                     '<small>01<!-- --> / 04</small>',
                     '上传即入库，版本自动冻结。',
                     'moha://models/llama-3.1-8b',
                     # AIRouter now rides the shared board layout
                     '<span class="tf-overline">AIRouter · AI聚合网关</span>',
                     '>了解 AIRouter ',
                     '<h2 class="tf-section-title mt-5"'
                     ' data-page-node-id="j1cabH5RCrpZ6zuopg1PKx">',
                     # footer wordmark now carries the company name
                     'class="tf-footer-brand-word"',
                     'data-page-node-id="pHvRqXDT6WITPlOY4FYuEp">破晓石科技</span>',
                     # the nav lockup names the company too
                     'alt="破晓石科技 logo"',
                     # 页脚「公司」列现在给的是公司简介页。名字包进乱码宿主之后，
                     # 这一条的形态从「文本 + `</a>`」变成「文本在三段式宿主里」，
                     # 锚点就落在宿主开标签上 —— 文案本身由 stage_footer_cta 的
                     # need1 负责，这里只证「这条链接还在、且已接上动效」。
                     'data-page-node-id="WQs06tBb1wDxj7OvovKSYT">'
                     '<span class="tf-scramble-label">',
                     # the 产品 dropdown entries carry lucide stroke icons; the
                     # width comes from the custom.css override that cancels the
                     # vendor rule zeroing the stroke for the old filled icons
                     'tf-nav-dropdown-icon"><svg class="h-4 w-4" viewBox="0 0 24 24"'
                     ' fill="none" stroke="currentColor" stroke-width="2"',
                     # the blog preview cards point at the self-hosted pages now
                     'href="/blog/2026-03-27-aliyun-ppu/"',
                     'href="/blog/2024-12-15-hygon/"',
                     'href="/blog/2025-07-24-majnoon/"',
                     'alt="破晓石完成阿里云 PPU 适配"',
                     # 品牌写法统一 2026-09-11：四板块并列串改用 `/` 分层
                     # （`·` 让给「主名 · 定位词」），AIRouter 段带全称。
                     # 四处独立出现的位置（hero pill / footer 产品列 / overline /
                     # 控制平面 lane）都要有全称，漏一处就是没统一。
                     '<title>%s</title>' % HOME_TITLE,
                     '<span class="tf-overline">AIRouter · AI聚合网关</span>',
                     '</span>AIRouter · AI聚合网关</span>'):
        if required not in body:
            MISS.append('missing: ' + required)
    # 品牌写法 2026-09-11 统一后，首页全称该出现 16 次：title 1 + meta 1 +
    # 跑马灯 10（无缝滚动把同一条文案复制成 10 份）+ hero pill 1 + 控制平面 lane 1 +
    # 板块 overline 1 + footer 产品列 1。少一处是某个 stage 漏改，多一处是旧写法
    # 没清干净 —— 这条计数比逐个 required 更能兜住「只改了一半」。
    #
    # 计数前先把乱码宿主的重复副本摘掉：一条文字链接包成宿主后，同一份文本在
    # measure / live / sr-only 里各出现一次，页脚那条会让计数从 16 涨到 18 ——
    # 那是动效的结构开销，不是品牌写法多写了一处。剥掉可见的两份（两份都
    # aria-hidden），留 sr-only 那份代表这一处「锁定的文案」。
    #
    # 再剥掉 head 里那块 SEO 标签（body_without_seo）：它把 title 与 description
    # 又渲染了四次（og:title / og:description / twitter:title / twitter:description），
    # 不剥就是 20。两处都是**结构开销**，不是「品牌写法多写了」。
    countable = re.sub(
        r'<span class="tf-scramble-(?:measure|live)"[^>]*>[^<]*</span>',
        '', body_without_seo())
    got = countable.count('AIRouter · AI聚合网关')
    if got != 16:
        MISS.append('expected sixteen `AIRouter · AI聚合网关` lockups on the homepage, got %d'
                    % got)
    # 「关于我们」下拉：桌面与移动抽屉各 4 项（原 5 项，见 stage_nav_company）。
    # 逐项断言 node-id 而不是数个数 —— 删一项时若删除范围越界吃了紧随其后那一项，
    # 症状正是某个 node-id 整块消失，而「项数」看着仍像是改对了。
    for nid, what in (('viVcdTEAIACrvRBlmtJQ1t', '公司简介(桌面)'),
                      ('4wCDZu1TV6PgNK5S5vaRhe', '公司动态(桌面)'),
                      ('TiAwzD3ggnRELge0dsQMjT', '开源项目(桌面)'),
                      ('2ENFg0O3Yx5eXhSjfmxnCl', '联系我们(桌面)'),
                      ('R7nETQV1mNT6F1weAPfygl', '公司简介(移动)'),
                      ('gqYzTmgj4gK6ap8EQFrzhA', '公司动态(移动)'),
                      ('ZdH35ccVkpyOMHzNrzxChv', '开源项目(移动)'),
                      ('F19UN7oUuZvbAUrbUBmcRS', '联系我们(移动)')):
        if 'data-page-node-id="%s"' % nid not in body:
            MISS.append('关于我们下拉丢了一项: ' + what)
    # 开源项目现在只有一个站外目标，桌面与抽屉各一份，两处都必须开新窗
    got = body.count('href="https://www.kubegems.io/" target="_blank" rel="noopener noreferrer"')
    if got != 2:
        MISS.append('开源项目外链应有两处（桌面 + 抽屉），实得 %d' % got)
    # 站内 /contact 十一处：导航下拉 + 移动抽屉 + 页脚社交区图标（原有三处），
    # 加上 2026-09-11 晚收回的四条 —— 品牌带「预约演示」、页尾「预约演示」、
    # 定价区「查看完整报价」与「查看商务条款」；再加晚（十三）商务收口的四条
    # （导航 CTA「联系销售」、移动抽屉「联系销售」、页脚「联系我们」「联系销售」）。
    # 落点全是同一个 /contact，所以按总数咬住。
    got = body.count('href="/contact"')
    if got != 11:
        MISS.append('站内 /contact 应有十一处（桌面 + 抽屉 + 页脚图标 + 品牌带 + 页尾 CTA '
                    '+ 定价区两条 + 商务收口四条），实得 %d' % got)
    # 商务收口（晚十三）：四条逐条核 href。**别只用上面的总数** —— 全局替换把某条
    # 带偏、另一条恰好补上的话，总数一分不变。逐条核才知道是哪一条。
    #
    # 先钉名单长度：逐条断言只看得见**名单里**的条目，有人把某一项从
    # `CONTACT_RETARGET` 里删掉时，循环对那条一声不响（漏改的那条还剩着 mailto，
    # 只有总数和 mailto 计数会响，说不清是哪一条被漏了）。反向自测的 C 用例正是
    # 这么演的 —— 数字型断言要跟着「这个数是谁算出来的」一起写，否则它只防手滑。
    if len(CONTACT_RETARGET) != 4:
        MISS.append('商务收口名单应为 4 条（导航 CTA / 移动抽屉 / 页脚联系我们 / '
                    '页脚联系销售），实得 %d 条' % len(CONTACT_RETARGET))
    for label, nid, old_href, new_href in CONTACT_RETARGET:
        got_href = link_href_of(nid)
        if got_href is None:
            MISS.append('站芯 %s 的链接没了（node-id %s）' % (label, nid))
        elif got_href != CONTACT_PAGE:
            # 期望值写死 `CONTACT_PAGE`，**不读 `new_href`**。名单与断言是同一份数据时，
            # 把某条的目标改成 `/about`（或旧站、mailto）会让断言跟着一起改，于是它报
            # 「一切正常」—— 反向自测的 E 用例就是这么骗过第一版的。分两句写：这句管
            # 「页面上实际是哪儿」，下一句管「名单里写的是哪儿」，两者都不许离开 /contact。
            MISS.append('站芯 %s 应指向 %s，实得 %s' % (label, CONTACT_PAGE, got_href))
        elif new_href != CONTACT_PAGE:
            MISS.append('商务收口名单里 %s 的目标被改成了 %s（本站商务落点只有 %s）'
                        % (label, new_href, CONTACT_PAGE))
    # 站芯里除了那枚邮箱图标，不该再有 mailto。断言写成「恰好剩它一条」而不是
    # 「mailto 归零」：归零会连**正当的**邮件入口一起判违规，而那个按钮的语义
    # （怎么发邮件）与 /contact（怎么联系我们）是两件事 —— 用户没点名删它。
    mails = re.findall(r'href="(mailto:[^"]*)"', body)
    if mails != [CONTACT_MAIL]:
        MISS.append('站芯 mailto 应只剩页脚邮箱图标 1 条，实得 %d 条: %s'
                    % (len(mails), sorted(set(mails))))
    # 顶层菜单「解决方案」2026-09-11 改指演示站（见 stage_nav_menu）：桌面与抽屉
    # 各一份，两处都必须开新窗（ext() 对 http 开头自动加，不必在这里写死 target）。
    # 只改看得见的那一份是本轮之前踩过的坑，所以按计数咬住。
    got = body.count('href="https://ppt.poxiaoshi.cn/#slide-1"')
    if got != 2:
        MISS.append('「解决方案」应有两处指向演示站（桌面 + 抽屉），实得 %d' % got)

    # ------------------------------------------- 产品目录改指站内产品页（2026-09-11）
    # 六处目录型入口 —— 产品下拉、预约演示下拉、移动抽屉、控制平面 lane、页脚产品列、
    # 定价卡 —— 每个产品各一条，全部指向 /products/<slug>/。
    #
    # 这一段按**来源**逐项断言，不再按「每个产品总共几条」断言。2026-09-11 晚加了
    # 定价卡、页脚又多出三条指向 Rune 的别名（混合云 / 智算中心 / XCMP 云管理）之后，
    # 总量就成了一个每加一条入口都要跟着改的数字，而且它分不清「漏改一处」和
    # 「另一处被删」。按来源数则两条都咬得住：漏改那处计数变 0。
    for p in PRODUCTS:
        href = 'href="%s"' % p['page']
        for source, frag in (('产品下拉', 'tf-nav-dropdown-item'),
                             ('预约演示下拉', 'tf-nav-console-item'),
                             ('移动抽屉', 'flex items-center gap-3'),
                             ('控制平面 lane', None),
                             ('页脚产品列', 'tf-footer-link'),
                             ('定价卡', 'tf-home-pricing-item')):
            got = sum(1 for m in re.finditer(r'<a\b[^>]*>', body)
                      if href in m.group(0)
                      and (frag in m.group(0) if frag else 'class=' not in m.group(0)))
            # 页脚还挂着「混合云 / 智算中心 / XCMP 云管理」三条指向 Rune 的别名，
            # 它们与产品列同名同类，无法在这里分开数 —— 所以页脚只要「至少一条」，
            # 少了会变 0。这三条本身由下面的「旧站零出现」兜住。
            room = got >= 1 if source == '页脚产品列' else got == 1
            if not room:
                MISS.append('%s：%s 应有 1 条指向 %s，实得 %d'
                            % (source, p['name'], p['page'], got))
        # 按路径末段取 slug 来拼旧站 URL。**别把 p['page'] 直接接在域名后面** ——
        # page 若已经被改回绝对 URL，那样会拼出一个「https://…/https://…」的四不像，
        # 于是恰好漏掉这轮最该抓的回归（2026-09-11 反向自测就是这么发现的：
        # 把两条 page 退回旧站，只有总数那条报，逐条这条一声不响）。
        slug = p['page'].strip('/').split('/')[-1]
        stale = 'href="https://www.poxiaoshi.cn/products/%s/"' % slug
        if stale in body:
            MISS.append('产品目录仍指向旧站: ' + stale)

    # ------------------------------------------- 全站不再指向旧站（2026-09-11 晚）
    # 用户的说法是「全站指向到旧站的，全部要指向到本站」。这里就用最强的那条断言：
    # 主域零出现。不再有「保留几条例外」——上一轮留着的 XCMP 与 chatbox 两条也收回了，
    # 逐条列名单的写法会漏掉新加的那一条，主域零出现不会。
    #
    # 三个**含 poxiaoshi.cn 但不是旧站**的域名，别被下面那条咬住：
    # `api.poxiaoshi.cn`（站内 API 域名，代码分隔线用）、`docs.poxiaoshi.cn`（文档站）、
    # `ppt.poxiaoshi.cn`（路演站）。它们都不是 `www.` 开头，所以精确到 `www.` 即可。
    #
    # 扫的是 body_without_seo()：本站**自己**的规范地址就是 `https://www.poxiaoshi.cn/`，
    # canonical / og:url / og:image / 结构化数据的 @id 一律是绝对地址，用整页扫
    # 会把自家的自指（self-reference）当成站外链接报出来。要抓的本来就是「正文里
    # 还有没有指向旧站的 `<a href>`」，那一块里没有 href。
    stale = re.findall(r'https://www\.poxiaoshi\.cn/[^"]*', body_without_seo())
    if stale:
        MISS.append('本站仍有指向旧站的链接 %d 条: %s' % (len(stale), sorted(set(stale))[:4]))
    # 定价区那六条：两条「查看完整报价 / 查看商务条款」→ /contact，四张卡 → 各自产品页。
    # （核 href 的办法见函数最上面的 `link_href_of`。）
    for label, nid, new_href in PRICING_RETARGET:
        got = link_href_of(nid)
        if got is None:
            MISS.append('定价区 %s 的链接没了（node-id %s）' % (label, nid))
        elif got != new_href:
            MISS.append('定价区 %s 应指向 %s，实得 %s' % (label, new_href, got))
    # 「价格与服务」两处（桌面 + 抽屉）→ 首页定价区。顺带核锚点本身还在：
    # `/#pricing` 指一个不存在的 id 就是死链，而且是那种「能点、不报错、不跳」的死。
    got = body.count('href="%s"' % PRICING_ANCHOR)
    if got != 2:
        MISS.append('「价格与服务」应有 2 处指向首页定价区（桌面 + 抽屉），实得 %d' % got)
    if 'id="pricing"' not in body:
        MISS.append('首页定价区丢了 id="pricing"，%s 会变成死锚点' % PRICING_ANCHOR)
    # 页脚那六条（旧站 solutions / cases / chatbox / about）逐条核落点
    for label, nid, old_href, new_href in FOOTER_RETARGET:
        got = link_href_of(nid)
        if got is None:
            MISS.append('页脚 %s 的链接没了（node-id %s）' % (label, nid))
        elif got != new_href:
            MISS.append('页脚 %s 应指向 %s，实得 %s' % (label, new_href, got))
    got = body.count('href="/blog/"')
    if got != 2:
        MISS.append('页脚两条行业案例应指 /blog/，实得 %d' % got)
    # 首页三处控制台直达已全部收归站内（品牌带 / 页尾 → /contact，BOSS 深潜 → 产品页）。
    # 去控制台的路改由产品页承接：首页 → 产品页 → 页尾「进入控制台」。
    got = body.count(CONSOLE_HREF)
    if got != 0:
        MISS.append('首页不应再有控制台直达，实得 %d 处' % got)
    # 站内跳转不开新窗。`p['page']` 是根相对路径，ext() 对它返回空串；改之前这五处
    # 每一条都是旧站 URL、每一条都带 target，所以回归的症状是「点产品名弹新标签」。
    offenders = re.findall(r'href="/products/[a-z-]+/"[^>]*target=', body)
    if offenders:
        MISS.append('产品页入口不应开新窗，实得 %d 处带 target' % len(offenders))
    # 上一条只管 /products/*。这一轮从页脚收回来的还有 /blog/ /about /contact 三条，
    # 它们的原标签同样写着 target —— 断言放宽到「所有站内根相对链接」，别只覆盖
    # 恰好被想到的那一类。`(?!/)` 排除 `//host` 这种协议相对写法（本站暂无，防将来）。
    offenders = re.findall(r'href="/(?!/)[^"]*"[^>]*target="_blank"', body)
    if offenders:
        MISS.append('站内链接不应开新窗，实得 %d 处: %s' % (len(offenders), offenders[:3]))

    # 三张博客卡各是一整块 <a>，所以每张只需一处站内链接；仍有一处指向
    # poxiaoshi.cn 的 blog 就说明 stage_blog_cards 没生效
    for slug in ('2026-03-27-aliyun-ppu', '2024-12-15-hygon', '2025-07-24-majnoon'):
        got = body.count('href="/blog/%s/"' % slug)
        if got != 1:
            MISS.append('blog card %s: %d local links, expected 1' % (slug, got))
    if 'https://www.poxiaoshi.cn/blog/' in body:
        MISS.append('the homepage still links out to the online blog')
    # 三张卡的封面必须来自内容源（与详情页同图）。need1 只证明「替换发生了」，
    # 这里独立再核一遍产物里真的有那三张 —— 万一 post_cover 给回别的路径、
    # 或某一张漏渲染，这条会咬住。
    for slug in ('2026-03-27-aliyun-ppu', '2024-12-15-hygon', '2025-07-24-majnoon'):
        cover = post_cover(slug)
        if cover and f'src="{cover}"' not in body:
            MISS.append(f'blog card cover for {slug} is absent from the page: {cover}')
    got = body.count('src="assets/img/news/')
    if got != 3:
        MISS.append(f'expected three news/ covers on the homepage, got {got}')
    # 三张都该走「完整呈现」档（换图源后是实拍照片与品牌图，见 stage_blog_cards）
    got = body.count('tf-blog-image-frame is-wide-art')
    if got != 3:
        MISS.append(f'expected all three blog covers on the is-wide-art framing, got {got}')
    # Rune / AIRouter / BOSS each own one sidebar, and AIRouter's grid must be
    # the shared one — a stray .tf-managed-api-shell would break the rhythm again
    if body.count('class="tf-section-sidebar"') != 3:
        MISS.append('expected three .tf-section-sidebar boards (Rune/AIRouter/BOSS), got %d'
                    % body.count('class="tf-section-sidebar"'))
    if body.count('class="tf-section-split"') != 3:
        MISS.append('expected three .tf-section-split boards, got %d'
                    % body.count('class="tf-section-split"'))
    # one icon per 产品 dropdown entry — the icons are what the custom.css
    # stroke-width override restores, so a dropped icon is a silent regression.
    # Scoped to the 产品 container: the 企业 dropdown carries five of the same
    # spans with a stroke of their own, so a page-wide count proves nothing.
    pa, pb = find_by_attr(body, 'tf-nav-product-menu')
    if pa < 0:
        MISS.append('产品 dropdown container missing')
    else:
        got = body[pa:pb].count('class="tf-nav-dropdown-icon"')
        if got != 4:
            MISS.append('expected four 产品 dropdown icons, got %d' % got)
    # the orb lives only on the chat avatar now; a stray copy would either
    # duplicate a gradient id or bring the retired overline mark back
    if body.count('id="tf-thinking-grad"') != 0:
        MISS.append('tf-thinking-grad id should be gone (overline mark removed)')
    if body.count('id="tf-chat-orb-grad"') != 1:
        MISS.append('tf-chat-orb-grad id must appear exactly once')
    if body.count('class="tf-thinking"') != 1:
        MISS.append('the thinking orb must appear exactly once (chat avatar only)')
    # the XCMP band is gone, so `#gateway` must not exist anywhere: a stray
    # section_span would silently drop a second copy back into the page. The
    # closing CTA is the last block and must still follow the FAQ.
    f, c = body.find('id="faq"'), body.find('tf-contact-cta-section')
    if min(f, c) < 0:
        MISS.append('section anchors missing: faq/cta')
    elif not f < c:
        MISS.append(f'closing CTA is out of place (faq@{f} cta@{c})')
    if body.count('id="gateway"') != 0:
        MISS.append('the XCMP band should be gone, found id="gateway"')

    # ---------------------------------------------------------- companion files
    # Two of the assets this script writes against cannot be guarded from the
    # markup alone, and both have already drifted once:
    #   * main.js re-declares the board lane classes and the two lucide glyph
    #     paths the client-side audit pane draws — nothing at runtime ties those
    #     strings back to PRODUCTS / ICON_* above;
    #   * custom.css has to cancel the vendor rule that zeroes the 产品 dropdown
    #     stroke, or all four icons render invisible (2026-09-11).
    # Assert the shared strings here so a rename on either side fails the build
    # instead of surfacing as "the icon disappeared" in the browser.
    def read(path):
        try:
            return open(path, encoding='utf-8').read()
        except OSError as exc:  # pragma: no cover - environment dependent
            MISS.append('cannot read %s (%s)' % (path, exc))
            return ''

    js = read('assets/js/main.js')
    css = read('assets/css/custom.css')
    for product in PRODUCTS:
        cls = 'tf-control-' + product['lane'][0]
        # quoted, not a bare substring: `'tf-control-boss'` survives a rename to
        # `'tf-control-boss-x'` and the check would pass while the lane broke
        if js and not re.search(r'[\'"]' + re.escape(cls) + r'[\'"]', js):
            MISS.append('main.js no longer drives ' + cls)
    # Fragments, not whole `d=` paths: main.js splits every long path across
    # concatenated string literals, so only a short contiguous run is checkable.
    for fragment in ('M12 3v12',              # ICON_UPLOAD / GLYPH.upload
                     'm9 12 2 2 4-4',         # ICON_SHIELD / GLYPH.shield
                     'M20 6 9 17l-5-5'):      # ICON_CHECK / CHECK_SVG
        if js and fragment not in js:
            MISS.append('main.js lost the shared glyph fragment ' + fragment)
    # conditional on purpose: the veto only applies while the dropdown carries
    # stroke icons. Swap them for the upstream filled ones and the override
    # legitimately goes away — the `required` entry above pins the markup side.
    css_bare = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    if 'tf-nav-dropdown-icon"><svg class="h-4 w-4" viewBox="0 0 24 24"' in body and not re.search(
            r'\.tf-nav-product-menu \.tf-nav-dropdown-icon svg\s*\{\s*stroke-width:\s*[1-9]',
            css_bare):
        MISS.append('custom.css lost the 产品 dropdown stroke override')

    # 乱码动效的覆盖率。放在最后：它看的是所有 stage 都跑完之后的 body。
    scramble_guard()

    # head 里那块 SEO 标签。同样放在最后：stage_seo 是第一个 stage，
    # 但后面没有任何 stage 碰 head（内容页生成器才是消费方），
    # 所以这里看到的与它们搬走的是同一份。
    seo_guard()


for fn in (stage_head, stage_icons, stage_seo,
           stage_nav, stage_nav_menu, stage_nav_company, stage_hero,
           stage_story, stage_xcmp,
           stage_rune_moha, stage_moha, stage_airouter, stage_boss, stage_harness,
           stage_pricing, stage_faq, stage_blog_cards, stage_footer_cta,
           stage_contact_retarget,
           # 必须排在 stage_footer_cta 与 stage_contact_retarget 之后：前者把
           # 「产品」列整段换掉、后者会改写页脚链接的开标签，这一遍要在两者都
           # 定稿之后才数得准，也才包得全。
           stage_footer_scramble,
           stage_guards):
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
