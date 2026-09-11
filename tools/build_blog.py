#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成「关于我们 / 公司动态」的整条链路：

    content/blog/<slug>.md  ->  blog/index.html            （列表页）
                            ->  blog/<slug>/index.html     （5 个详情页）

本站自持内容
------------
2026-09 之前，列表页每张卡都跳到线上 poxiaoshi.cn —— 站点是要**替换** poxiaoshi.cn
的，跳出去等于把内容留在别人家里。现在内容源在 `content/blog/`，每篇一个 Markdown
文件，正文与元信息全在本仓库，改完重跑本脚本即可。

第一份内容由 `tools/import_posts.py` 从线上搬来（保留 provenance，可追溯、可复核），
之后就在这里维护了。内容源格式见 `content/blog/README.md`。

版式来源
--------
原站的 /blog 与 /blog/<slug>（换牌前的那套模板）。与 about 页一样，这一页**几乎不需要
新写样式**：原站列表页的 `.tf-blog-index-*` 与详情页的 `.tf-blog-detail-*`
整份都在本站的 `assets/css/vendor.css` 里 —— 上游那份样式表换牌时被一起搬了过来，
只是首页从来没引用过这批类名。所以做法是照原站的 DOM 骨架搭结构、类名原样用，
样式自动继承；`assets/css/blog.css` 只补上游靠 Tailwind 工具类做、而本站没有
Tailwind 的那些属性（整页容器底色、以及 vendor 里缺的 `.prose table`）。

路径深度
--------
    列表页  blog/index.html          depth=1  ->  ../assets/
    详情页  blog/<slug>/index.html   depth=2  ->  ../../assets/

所以本文件里的 main markup 一律写**站点根相对**的 `assets/…`，由
`portal_page.derive(depth=…)` 统一加前缀。不要在 markup 里手写 `../`，两套写法
混用迟早会写出少一层或多一层的路径。
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import mdrender  # noqa: E402
from portal_page import (ARROW, ARROW_S, Ctx, derive, esc, ext,  # noqa: E402
                         finish_many, match_close, upstream_brand)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CONTENT_DIR = os.path.join(ROOT, 'content', 'blog')
LIST_OUT = os.path.join(ROOT, 'blog', 'index.html')
LIST_REL = 'blog/index.html'
BLOG_CSS = 'blog.css'
SITE_NAME = '破晓石科技'

# ---------------------------------------------------------- 列表页页头（线上原文）
PAGE_TITLE = '公司动态 | 破晓石科技'
PAGE_DESC = '浏览成都破晓石科技的公司动态、行业观察、技术文章与 AI 智算实践内容。'
KICKER = '动态_'
HEADING = '公司动态'
LEAD = '了解我们的最新进展、产品发布和行业洞察。'
READ_LABEL = '阅读全文'
DIVIDER_CODE = 'const next = await fetch("https://api.poxiaoshi.cn/blog");'

# ------------------------------------------------------------ 详情页文案
# 「更多动态_ / 继续阅读。」对应原站详情页的「More from …_ / Keep reading.」。
RELATED_OVERLINE = '更多动态_'
RELATED_HEADING = '继续阅读。'
RELATED_ID = 'related-insights'
RELATED_COUNT = 2
AUTHOR = SITE_NAME

DITHER_BG = 'assets/img/dither-bg-01.webp'
# 详情页里 `![](assets/img/news/x.webp)` 这类站点根相对路径由 derive() 按深度加前缀，
# 这里不需要也知道 depth。
NEWS_DIR = 'assets/img/news'

# frontmatter 的必需字段。少任何一个都不该猜默认值——猜出来的日期会安静地排错序。
REQUIRED_FIELDS = ('title', 'slug', 'date', 'cover', 'tag', 'summary')

_CJK = re.compile(r'[\u4e00-\u9fff]')
_LATIN = re.compile(r'[A-Za-z]+')


# ============================================================ 内容源
def parse_front_matter(text, path):
    """解析 `---` 包起来的 frontmatter。手写而不引 yaml：只有 6 个扁平字符串字段，
    引一个依赖不值当，而且生成器要能在裸环境跑。
    """
    if not text.startswith('---\n'):
        raise SystemExit('%s: front matter 必须以 --- 开头' % path)
    end = text.find('\n---\n', 4)
    if end < 0:
        raise SystemExit('%s: front matter 没有收尾的 ---' % path)
    meta = {}
    for lineno, line in enumerate(text[4:end].split('\n'), start=2):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        if ':' not in line:
            raise SystemExit('%s:%d: front matter 行无法解析: %r' % (path, lineno, line))
        key, value = line.split(':', 1)
        meta[key.strip()] = value.strip()
    return meta, text[end + 5:]


def load_posts():
    """读 content/blog/ 下所有内容源，按日期倒序返回。"""
    if not os.path.isdir(CONTENT_DIR):
        raise SystemExit('missing %s' % CONTENT_DIR)
    posts = []
    for name in sorted(os.listdir(CONTENT_DIR)):
        if not name.endswith('.md') or name.upper() == 'README.MD':
            continue
        path = os.path.join(CONTENT_DIR, name)
        meta, body = parse_front_matter(open(path, encoding='utf-8').read(), path)
        for key in REQUIRED_FIELDS:
            if not meta.get(key):
                raise SystemExit('%s: front matter 缺 %s' % (path, key))
        # 文件名就是 slug。两者不一致时目录名与内容源会各说各话，必须当场报错。
        if name[:-3] != meta['slug']:
            raise SystemExit('%s: 文件名与 slug 不符（slug=%s）' % (path, meta['slug']))
        if not re.fullmatch(r'\d{4}-\d{2}-\d{2}', meta['date']):
            raise SystemExit('%s: date 必须是 YYYY-MM-DD，得到 %r' % (path, meta['date']))
        cover = meta['cover']
        if not os.path.exists(os.path.join(ROOT, cover)):
            raise SystemExit('%s: 封面不存在: %s' % (path, cover))
        posts.append({
            'title': meta['title'],
            'slug': meta['slug'],
            'date': meta['date'],
            'cover': cover,
            'tag': meta['tag'],
            'summary': meta['summary'],
            'body': body.strip(),
            'href': '/blog/%s/' % meta['slug'],
        })
    if not posts:
        raise SystemExit('content/blog/ 里没有任何 .md 内容源')
    posts.sort(key=lambda p: (p['date'], p['slug']), reverse=True)
    return posts


def read_minutes(body):
    """从正文长度推算阅读时长。中文与英文词各计一次，按 400/分钟，最低 1 分钟。

    这是**推算值**，不是从别处抄来的事实：同一篇内容改了字数，这里跟着变。
    """
    text = re.sub(r'<[^>]+>', '', mdrender.render(body))
    n = len(_CJK.findall(text)) + len(_LATIN.findall(text))
    return max(1, int(round(n / 400.0)))


def fmt_date_cn(iso):
    y, m, d = iso.split('-')
    return '%d 年 %d 月 %d 日' % (int(y), int(m), int(d))


def clamp_desc(text, limit=110):
    """把摘要裁到合适 meta description 的长度：优先断在句末，其次加省略号。"""
    text = re.sub(r'\s+', ' ', text).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    for mark in ('。', '；', '！', '？'):
        i = cut.rfind(mark)
        if i > limit * 0.5:
            return cut[:i + 1]
    return cut.rstrip('，、；：') + '…'


def _main_html(doc):
    """取 `<main>` 的内容（不含开闭标签）。

    站芯（nav / footer）里有几十处指向线上产品页的链接，那是另一件事；要断「这一页
    自己有没有引用线上」时必须只看 <main>，否则会被站芯淹没。
    """
    m = re.search(r'<main\b[^>]*>', doc)
    if not m:
        return ''
    b = match_close(doc, m.start())
    return doc[m.end():b] if b > 0 else ''


# ============================================================ 列表页渲染
def hero():
    # `is-motion-visible` 不在这一页出现：整块版式都来自 vendor.css 的
    # `.tf-blog-index-*`，它自带视觉重量（38rem 高、大标题、dither 背景），
    # 不叠加站内的 .tf-motion-section 入场轨 —— 那套要靠 main.js 的探针驱动，
    # 而这里的容器层级（page 容器的 z-index:40 装饰边）不比首页，少一层变量。
    return (
        '<section class="tf-blog-index-hero">'
        '<div class="tf-blog-index-hero-shell">'
        # 与首页 hero 同一张 dither 底图（vendor.css 会给它 grayscale + 遮罩）
        '<img src="%s" alt="" aria-hidden="true" '
        'width="1440" height="759" decoding="async">'
        '<div class="tf-blog-index-hero-content">'
        '<span class="tf-blog-index-kicker"><i aria-hidden="true">▶</i> %s</span>'
        '<h1>%s</h1><p>%s</p>'
        '</div></div></section>' % (DITHER_BG, esc(KICKER), esc(HEADING), esc(LEAD)))


def snippet(post):
    """列表里的一条动态。标题用裸 <a>（上游就没有包 h2/h3），样式按这个骨架写。

    href 是站内根相对路径，`ext()` 因此不会加 target —— 点进去留在本站。
    """
    src = '%s/%s' % (NEWS_DIR, os.path.basename(post['cover']))
    link_attr = ext(post['href'])
    return (
        '<article class="tf-blog-index-snippet">'
        '<a class="tf-blog-index-image" aria-label="查看%s" href="%s"%s>'
        '<img src="%s" alt="%s" loading="lazy" decoding="async"></a>'
        '<div class="tf-blog-index-snippet-content"><div>'
        '<a class="tf-blog-index-title" href="%s"%s>%s</a>'
        '<p class="tf-blog-index-meta">%s <span>•</span> %s</p>'
        '</div>'
        '<a class="tf-blog-index-read" href="%s"%s>%s %s</a>'
        '</div></article>'
        % (esc(post['title']), post['href'], link_attr, src, esc(post['title']),
           post['href'], link_attr, esc(post['title']),
           esc(post['date']), esc(post['tag']),
           post['href'], link_attr, esc(READ_LABEL), ARROW_S))


def list_divider():
    """收尾装饰。上游那段没有光标 `<b>_</b>`，照抄；整块 aria-hidden。"""
    return ('<div class="tf-blog-index-divider" aria-hidden="true"><span></span>'
            '<code>%s</code><span></span></div>' % esc(DIVIDER_CODE))


def list_markup(posts):
    rows = ''.join(snippet(p) for p in posts)
    return (
        '<div class="tf-blog-index-page">'
        + hero()
        + '<section class="tf-blog-index-list">'
          '<div class="tf-blog-index-list-shell">'
          '<div class="tf-blog-index-row-frame">' + rows + '</div>'
          '</div></section>'
        + list_divider()
        + '</div>')


# ============================================================ 详情页渲染
def detail_hero(post):
    return (
        '<section class="tf-blog-detail-hero">'
        '<div class="tf-blog-detail-hero-shell">'
        '<img src="%s" alt="" aria-hidden="true" decoding="async">'
        '<header class="tf-blog-detail-hero-content">'
        # 分类胶囊指回列表页。本站还没有按分类筛选的页面，所以 href 就是 /blog。
        '<a class="tf-blog-detail-category" href="/blog">%s_</a>'
        '<h1>%s</h1><p>%s</p>'
        '<div class="tf-blog-detail-info">'
        '<time datetime="%s">%s</time>'
        '<span aria-hidden="true">•</span><span>%d 分钟阅读</span>'
        '<span aria-hidden="true">•</span><span>%s</span>'
        '</div></header></div></section>'
        % (DITHER_BG, esc(post['tag']), esc(post['title']), esc(post['summary']),
           post['date'], esc(fmt_date_cn(post['date'])),
           read_minutes(post['body']), esc(AUTHOR)))


def detail_related(related):
    if not related:
        return ''
    cards = []
    for r in related:
        cards.append(
            '<a class="tf-blog-detail-related-card" href="%s">'
            '<img src="%s/%s" alt="" loading="lazy" decoding="async">'
            '<span>%s <i>•</i> %s</span>'
            '<strong>%s</strong>'
            '<em>%s %s</em></a>'
            % (r['href'], NEWS_DIR, os.path.basename(r['cover']),
               esc(r['date']), esc(r['tag']), esc(r['title']),
               esc(READ_LABEL), ARROW))
    return (
        '<section class="tf-blog-detail-related" aria-labelledby="%s">'
        '<div class="tf-blog-detail-related-heading">'
        '<span>%s</span><h2 id="%s">%s</h2>'
        '</div>'
        '<div class="tf-blog-detail-related-grid">%s</div>'
        '</section>'
        % (RELATED_ID, esc(RELATED_OVERLINE), RELATED_ID, esc(RELATED_HEADING),
           ''.join(cards)))


def detail_markup(post, related):
    # 正文由 mdrender 渲染。图片在 md 里写的是站点根相对路径（assets/img/...），
    # 交给 derive() 按 depth 统一加前缀。
    body_html = mdrender.render(post['body'])
    article = (
        '<article class="tf-blog-detail-article">'
        '<figure class="tf-blog-detail-image">'
        '<img src="%s" alt="%s" decoding="async">'
        '</figure>'
        '<div class="tf-blog-detail-richtext"><div class="prose">%s</div></div>'
        '</article>' % (post['cover'], esc(post['title']), body_html))
    return ('<div class="tf-blog-detail-page">'
            + detail_hero(post) + article + detail_related(related)
            + '</div>')


def related_for(post, posts):
    """除自己之外最新的 N 篇。列表本身已按日期倒序，取前 N 个排除自己即可。"""
    others = [p for p in posts if p['slug'] != post['slug']]
    return others[:RELATED_COUNT]


# ============================================================ 装配 + 守卫
def main():
    ctx = Ctx()
    posts = load_posts()

    # ------------------------------------------------------------ 列表页
    doc, _home, home_md5 = derive(
        ctx,
        out_rel=LIST_REL,
        title=PAGE_TITLE,
        description=PAGE_DESC,
        extra_css=BLOG_CSS,
        main_markup=list_markup(posts),
        main_label='main body -> 公司动态列表',
        nav_label='nav active state -> 关于我们',
        depth=1,
    )

    # 列表页守卫：条数与内容源一致，且每条三处链接都指向**本地**详情页
    if doc.count('tf-blog-index-snippet"') != len(posts):
        ctx.miss.append('snippets on the page: %d, want %d'
                        % (doc.count('tf-blog-index-snippet"'), len(posts)))
    for p in posts:
        for needle in (p['title'], p['date'], p['tag']):
            if esc(needle) not in doc:
                ctx.miss.append('list: post field lost: %s' % needle)
        # 封面 / 标题 / 按钮三处。`(?! target)` 保证没被 ext() 当成外链开新窗口。
        got = len(re.findall(r'href="%s"(?! target=)' % re.escape(p['href']), doc))
        if got != 3:
            ctx.miss.append('list: local link count for %s: %d, want 3' % (p['slug'], got))
        if 'href="%s" target=' % p['href'] in doc:
            ctx.miss.append('list: %s still opens in a new tab (should stay in-site)'
                            % p['slug'])
        if '%s/%s' % (NEWS_DIR, os.path.basename(p['cover'])) not in doc:
            ctx.miss.append('list: cover not linked: %s' % p['cover'])
    # 站芯（nav / footer）自带一批指向线上的产品页链接，那些不在本轮范围内。
    # 但 <main> 里除了这条 divider 的示例代码，不该再有任何 poxiaoshi.cn 引用——
    # 那正是「内容自持」这件事的反面。
    if 'poxiaoshi.cn' in _main_html(doc).replace(DIVIDER_CODE, ''):
        ctx.miss.append('list: unexpected poxiaoshi.cn reference inside <main>')
    order = ['tf-blog-index-hero', 'tf-blog-index-list', 'tf-blog-index-divider',
             'tf-reference-footer']
    pos = [doc.find(x) for x in order]
    if -1 in pos:
        ctx.miss.append('list: section order anchor missing: '
                        + ', '.join(x for x, q in zip(order, pos) if q < 0))
    elif pos != sorted(pos):
        ctx.miss.append('list: sections are out of order')
    if 'tf-blog-index-page' not in doc:
        ctx.miss.append('list: the page container is gone')
    else:
        m = re.search(r'<main\b[^>]*>', doc)
        if doc.find('tf-blog-index-page') < m.end():
            ctx.miss.append('list: the page container must sit inside <main>')
    for leftover in ('Our Blog', 'Explore Our Latest Insights', 'Get Started',
                     'Cover image', 'reading time',
                     'agent-memory-next-bottleneck', 'context-engineering-for-ai-agents',
                     'why-unified-llm-gateway'):
        if leftover in doc:
            ctx.miss.append('list: leftover: ' + leftover)
    if upstream_brand(doc):
        ctx.miss.append('list: leftover: 上游品牌名')
    if re.search(r'alt="(Agent memory|Context engineering|Unified LLM)', doc):
        ctx.miss.append('list: reused the stale English alt text from the homepage cards')

    pages = [(LIST_OUT, LIST_REL, doc)]

    # ------------------------------------------------------------ 详情页
    for post in posts:
        d, _h, _m = derive(
            ctx,
            out_rel='blog/%s/index.html' % post['slug'],
            title='%s | %s' % (post['title'], SITE_NAME),
            description=clamp_desc(post['summary']),
            extra_css=BLOG_CSS,
            main_markup=detail_markup(post, related_for(post, posts)),
            main_label='main body -> %s' % post['slug'],
            nav_label='nav active state -> 关于我们',
            depth=2,
        )
        slug = post['slug']

        # --- 本页专属守卫 ------------------------------------------------
        rel = 'blog/%s/index.html' % slug
        if d.count('tf-blog-detail-page"') != 1:
            ctx.miss.append('%s: page container count %d' % (slug, d.count('tf-blog-detail-page"')))
        # 标题与摘要逐字落盘
        for needle in (esc(post['title']), esc(post['tag']), esc(post['summary'])):
            if needle not in d:
                ctx.miss.append('%s: hero field lost' % slug)
        if '<title>%s</title>' % esc('%s | %s' % (post['title'], SITE_NAME)) not in d:
            ctx.miss.append('%s: <title> not rewritten' % slug)
        if 'datetime="%s"' % post['date'] not in d:
            ctx.miss.append('%s: <time datetime> lost' % slug)
        # 正文字数：渲染后的纯文本长度应与内容源一致（±2 位是标签差异的余量）
        src_chars = len(_CJK.findall(post['body']))
        out_chars = len(_CJK.findall(re.sub(r'<[^>]+>', '', d)))
        if out_chars < src_chars:
            ctx.miss.append('%s: 正文中文字数掉了 %d -> %d' % (slug, src_chars, out_chars))
        # 正文里的每张图都要在磁盘上，且走 ../../assets/
        body_imgs = set(re.findall(r'<img src="(\.\./\.\./assets/img/[^"]+)"', d))
        for im in sorted(body_imgs):
            if not os.path.exists(os.path.join(ROOT, im.replace('../../', ''))):
                ctx.miss.append('%s: missing image %s' % (slug, im))
        if not body_imgs:
            ctx.miss.append('%s: 正文里一张图都没有（至少应有封面）' % slug)
        # 封面、相关阅读、正文图都应指到 assets/img/news/ 下的真实文件
        if '%s/%s' % (NEWS_DIR, os.path.basename(post['cover'])) not in d:
            ctx.miss.append('%s: cover not linked' % slug)
        # 相关阅读：恰好 RELATED_COUNT 篇，且都不指向自己
        rel_cards = re.findall(r'href="(/blog/[^"]+)"', d)
        # 每个 related 卡片一次 + 分类胶囊一次（/blog，无尾斜杠，不匹配）
        if len(rel_cards) != RELATED_COUNT:
            ctx.miss.append('%s: related cards %d, want %d'
                            % (slug, len(rel_cards), RELATED_COUNT))
        if post['href'] in rel_cards:
            ctx.miss.append('%s: related list links back to itself' % slug)
        # 章节顺序：hero < article < related < footer
        seq = ['tf-blog-detail-hero', 'tf-blog-detail-article', 'tf-blog-detail-related',
               'tf-reference-footer']
        ppos = [d.find(x) for x in seq]
        if -1 in ppos:
            ctx.miss.append('%s: section order anchor missing: %s'
                            % (slug, ', '.join(x for x, q in zip(seq, ppos) if q < 0)))
        elif ppos != sorted(ppos):
            ctx.miss.append('%s: sections are out of order' % slug)
        # 上游残留
        for leftover in ('More from', 'Keep reading', 'Read article'):
            if leftover in d:
                ctx.miss.append('%s: leftover: %s' % (slug, leftover))
        if upstream_brand(d):
            ctx.miss.append('%s: leftover: 上游品牌名' % slug)
        # 新标签页只在站外出现。详情页的链接全是站内（分类胶囊 / 相关阅读），
        # 正文里若出现站外链接则应当有 target —— 这里只断「站内链接带 target」。
        for href in re.findall(r'href="(/blog/[^"]+)" target=', d):
            ctx.miss.append('%s: in-site link opens in a new tab: %s' % (slug, href))

        pages.append((os.path.join(ROOT, rel), rel, d))

    finish_many(ctx, pages, len(_home), home_md5, extra_lines=[
        'content sources: %d' % len(posts),
        '  ' + ', '.join('%s (%s)' % (p['slug'], p['date']) for p in posts),
    ])


if __name__ == '__main__':
    main()
