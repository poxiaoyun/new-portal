#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""一次性迁移：把 poxiaoshi.cn 的 blog 详情页正文搬成**本站自持**的内容源。

为什么存在
----------
`/blog` 原先只是列表页，每张卡都跳到线上 poxiaoshi.cn。目标是把 poxiaoshi.cn
整个替换掉，所以内容必须落到本仓库、可编辑、可离线渲染。

本脚本负责第一份内容的搬家：抓线上详情页 -> 抽正文 -> 转 Markdown ->
写 `content/blog/<slug>.md`。**它只跑一次**：`content/blog/` 里已存在的文件一律
拒绝覆盖，否则之后在本地做的编辑会被静默冲掉。要真的重来，显式加 `--force`。

保留在仓库里的意义是 provenance：任何人可以重跑它，验证 md 与线上原文的对应
关系，而不是面对一份来历不明的文本。

往返自检
--------
转换完立刻做一次 `未转换前的 HTML 文本` vs `Markdown 渲染回来的 HTML 文本` 比对：
  * 纯文本（压掉空白）必须逐字相同
  * 强调/链接/图片/表格/标题/列表的标签计数必须相同
对不上就报错并不写盘 —— 宁可让人看一眼，也不要静默丢格式。
"""

import argparse
import html as html_mod
import os
import re
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import mdrender  # noqa: E402

CONTENT_DIR = os.path.join(ROOT, 'content', 'blog')
UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
      '(KHTML, like Gecko) Chrome/126 Safari/537.36')

# 线上 5 篇。slug 沿用线上路径 —— 替换站点时 URL 保持不变，外链和搜索引擎
# 索引都不会断。（注意第 2、3 条的 slug 日期与正文日期并不一致，线上本来就
# 这样；这里原样保留，md 的 frontmatter 里 date 另记真实日期。）
SOURCES = [
    '2026-03-27-aliyun-ppu',
    '2024-12-15-hygon',
    '2025-10-12-paizi',
    '2025-07-24-majnoon',
    '2024-11-01-nvidia',
]
BASE = 'https://www.poxiaoshi.cn/blog/'

# 线上图片是 /images/news/xxx；本站放在 assets/img/news/。
# 写成站点根相对路径（不带 ../），由页面深度决定前缀——渲染时才加前缀。
LOCAL_IMG_DIR = 'assets/img/news'

VOID = {'br', 'img', 'input', 'link', 'meta', 'source', 'hr', 'area', 'col', 'embed',
        'track', 'wbr'}
_TAG = re.compile(r'<(/?)([a-zA-Z][a-zA-Z0-9-]*)((?:"[^"]*"|\'[^\']*\'|[^>"\'])*)(/?)>')

# 往返自检要逐一点数的标签
COUNTED = ('h2', 'h3', 'h4', 'p', 'ul', 'ol', 'li', 'table', 'tr', 'th', 'td',
           'strong', 'em', 'blockquote', 'hr', 'img')


def esc_attr(text):
    return mdrender.esc(text).replace('"', '&quot;')


def fetch(slug, cache_dir=None):
    if cache_dir:
        p = os.path.join(cache_dir, 'pxs-%s.html' % slug)
        if os.path.exists(p):
            return open(p, encoding='utf-8').read(), p
    url = BASE + slug + '/'
    req = urllib.request.Request(url, headers={'User-Agent': UA})
    with urllib.request.urlopen(req, timeout=45) as fh:
        return fh.read().decode('utf-8', 'replace'), url


# ------------------------------------------------------------------ HTML 小工具
def match_close(src, open_start):
    m = re.match(r'<([a-zA-Z][a-zA-Z0-9-]*)', src[open_start:])
    if not m:
        return -1
    tag = m.group(1).lower()
    depth = 0
    for mm in _TAG.finditer(src, open_start):
        close, name, _a, self_close = mm.group(1), mm.group(2).lower(), mm.group(3), mm.group(4)
        if name != tag:
            continue
        if close:
            depth -= 1
            if depth == 0:
                return mm.start()
        elif not self_close:
            depth += 1
    return -1


def split_top(fragment):
    """把一段 HTML 拆成顶层块：[(tag, open_tag_str, inner, full)]，文本段落用 tag='text'。"""
    out = []
    pos = 0
    while pos < len(fragment):
        m = re.compile(r'<([a-zA-Z][a-zA-Z0-9-]*)').search(fragment, pos)
        if not m:
            tail = fragment[pos:].strip()
            if tail:
                out.append(('text', '', tail, tail))
            break
        if m.start() > pos:
            text = fragment[pos:m.start()].strip()
            if text:
                out.append(('text', '', text, text))
        tag = m.group(1).lower()
        if tag in VOID:
            end = fragment.find('>', m.start()) + 1
            out.append((tag, fragment[m.start():end], '', fragment[m.start():end]))
            pos = end
            continue
        close_at = match_close(fragment, m.start())
        if close_at < 0:
            out.append(('text', '', fragment[m.start():], fragment[m.start():]))
            break
        open_end = fragment.find('>', m.start()) + 1
        close_end = fragment.find('>', close_at) + 1
        out.append((tag, fragment[m.start():open_end],
                    fragment[open_end:close_at], fragment[m.start():close_end]))
        pos = close_end
    return out


def strip_comments(s):
    return re.sub(r'<!--.*?-->', '', s, flags=re.S)


# ------------------------------------------------------------ 行内 HTML -> Markdown
def rewrite_src(src):
    """线上图片地址 -> 本站站点根相对路径。"""
    src = src.strip()
    for pat in (r'^(?:https?:)?//www\.poxiaoshi\.cn/images/news/',
                r'^/images/news/'):
        if re.match(pat, src):
            return '%s/%s' % (LOCAL_IMG_DIR, re.sub(pat, '', src))
    return src


def rewrite_href(href):
    """线上 blog 详情页 -> 本站根相对路径。其余原样。"""
    href = href.strip()
    m = re.match(r'^(?:https?:)?//www\.poxiaoshi\.cn/blog/([^/]+)/?$', href)
    if m:
        return '/blog/%s/' % m.group(1)
    if re.match(r'^(?:https?:)?//www\.poxiaoshi\.cn/blog/?$', href):
        return '/blog'
    return href


def inline_md(frag):
    """行内 HTML -> Markdown 文本。"""
    s = strip_comments(frag).strip()
    if not s:
        return ''

    # code 里的内容不参与后续任何替换
    codes = []

    def stash_code(m):
        codes.append(m.group(1))
        return '\x01%d\x01' % (len(codes) - 1)

    s = re.sub(r'<code[^>]*>(.*?)</code>', stash_code, s, flags=re.S)

    # 图片（含 alt 为空的）
    def img_repl(m):
        tag = m.group(0)
        src = re.search(r'src="([^"]*)"', tag)
        alt = re.search(r'alt="([^"]*)"', tag)
        title = re.search(r'title="([^"]*)"', tag)
        if not src:
            return ''
        alt_text = html_mod.unescape(alt.group(1)) if alt else ''
        out = '![%s](%s' % (alt_text, rewrite_src(src.group(1)))
        if title and title.group(1):
            out += ' "%s"' % title.group(1)
        return out + ')'

    s = re.sub(r'<img\b[^>]*>', img_repl, s)

    # <br> 原样保留成 <br>，mdrender 会透传（GFM 表格单元格里要用它换行）
    s = re.sub(r'<br\s*/?>', '<br>', s)

    # 强调。先 strong 后 em，避免 `<strong>` 里的 `<em>` 顺序错乱；本站正文嵌套极浅。
    s = re.sub(r'<(?:strong|b)\b[^>]*>(.*?)</(?:strong|b)>', r'**\1**', s, flags=re.S)
    s = re.sub(r'<(?:em|i)\b[^>]*>(.*?)</(?:em|i)>', r'*\1*', s, flags=re.S)

    # 链接
    def a_repl(m):
        attrs, inner = m.group(1), m.group(2)
        href = re.search(r'href="([^"]*)"', attrs)
        if not href:
            return inner
        return '[%s](%s)' % (inline_md(inner), rewrite_href(href.group(1)))

    s = re.sub(r'<a\b([^>]*)>(.*?)</a>', a_repl, s, flags=re.S)

    # 其余无语义标签直接剥掉
    s = re.sub(r'</?(?:span|div|figure|figcaption|section|time|small|sup|sub)\b[^>]*>', '', s)

    s = html_mod.unescape(s)
    # 压掉标签间被格式化引入的换行/缩进，但保留中文文本原样
    s = re.sub(r'[ \t]*\n[ \t]*', '', s)
    s = re.sub(r'  +', ' ', s).strip()

    # 还原 code
    for i, code in enumerate(codes):
        s = s.replace('\x01%d\x01' % i, '`%s`' % code)
    return s


def cell_md(cell_html):
    """表格单元格专用：图片与紧跟其后的文字之间补一个 <br>。

    线上是 `<td><img><strong>标题</strong></td>`，块级元素自然分行；Markdown 表格
    里只有行内元素，直接转出来会变成「图片和粗体标题挤在同一行」。<br> 是 GFM
    表格单元格里唯一的换行手段。
    """
    s = inline_md(cell_html)
    return re.sub(r'(!\[[^\]]*\]\([^)]*\))(?=\S)', r'\1<br>', s)


# ------------------------------------------------------------------ 块级 HTML -> Markdown
def blocks_md(fragment):
    """把顶层块转成 Markdown 行列表。"""
    lines = []
    for tag, _open, inner, _full in split_top(fragment):
        if tag == 'text':
            t = inline_md(inner)
            if t:
                lines.append(t)
            continue

        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
            lvl = int(tag[1])
            t = inline_md(inner)
            if t:
                if lines and lines[-1] != '':
                    lines.append('')
                lines.append('#' * lvl + ' ' + t)
                lines.append('')
            continue

        if tag == 'p':
            t = inline_md(inner)
            if t:
                if lines and lines[-1] != '':
                    lines.append('')
                lines.append(t)
                lines.append('')
            continue

        if tag in ('ul', 'ol'):
            items = [t for t in split_top(inner) if t[0] == 'li']
            if items:
                if lines and lines[-1] != '':
                    lines.append('')
                for n, (_li, _o, li_inner, _f) in enumerate(items, 1):
                    prefix = '%d. ' % n if tag == 'ol' else '- '
                    lines.append(prefix + inline_md(li_inner))
                lines.append('')
            continue

        if tag == 'table':
            lines.extend(table_md(inner))
            continue

        if tag == 'figure':
            imgs = [x for x in split_top(inner) if x[0] == 'img']
            caps = [x for x in split_top(inner) if x[0] == 'figcaption']
            if lines and lines[-1] != '':
                lines.append('')
            for _img, _o, _i, full in imgs:
                lines.append(inline_md(full))
            for _c, _o, ci, _f in caps:
                lines.append(inline_md(ci))
            lines.append('')
            continue

        if tag == 'img':
            if lines and lines[-1] != '':
                lines.append('')
            lines.append(inline_md(_full))
            lines.append('')
            continue

        if tag == 'hr':
            if lines and lines[-1] != '':
                lines.append('')
            lines.append('---')
            lines.append('')
            continue

        if tag == 'blockquote':
            for para in blocks_md(inner):
                if para.strip():
                    lines.append('> ' + para)
                else:
                    lines.append('>')
            lines.append('')
            continue

        # 其余容器（div/section）递归进去
        lines.extend(blocks_md(inner))

    # 收尾：压掉多余空行，保证块间恰好一个空行
    out = []
    for line in lines:
        if line == '' and (not out or out[-1] == ''):
            continue
        out.append(line)
    while out and out[-1] == '':
        out.pop()
    return out


def table_md(inner):
    """`<table>` inner -> GFM 表格行。"""
    head, body = [], []
    for tag, _o, tinner, _f in split_top(inner):
        if tag == 'thead':
            for rtag, _ro, rinner, _rf in split_top(tinner):
                if rtag == 'tr':
                    head.append([cell_md(c[2]) for c in split_top(rinner) if c[0] in ('th', 'td')])
        elif tag == 'tbody':
            for rtag, _ro, rinner, _rf in split_top(tinner):
                if rtag == 'tr':
                    body.append([cell_md(c[2]) for c in split_top(rinner) if c[0] in ('th', 'td')])
        elif tag == 'tr':
            # 没有 thead/tbody 的裸表格：第一行进表头
            row = [cell_md(c[2]) for c in split_top(tinner) if c[0] in ('th', 'td')]
            (head if not head else body).append(row)

    if not head:
        return []
    width = len(head[0])
    # 线上有用空表头表格来排版图片网格的（`<th></th>` 全空）。GFM 语法上第一行
    # 必须是表头，所以这里保留一行空的表头占位；mdrender 认得出「表头全空」并
    # 不生成 <thead>，于是产物里就是一张没有表头行的网格表。
    lines = ['| ' + ' | '.join(head[0]) + ' |',
             '|' + '|'.join(['---'] * width) + '|']
    for row in body:
        row = row + [''] * (width - len(row))
        lines.append('| ' + ' | '.join(row[:width]) + ' |')
    return [''] + lines + ['']


# ------------------------------------------------------------------ 提取线上正文
def extract_post(doc, slug, base_url):
    """从线上详情页抽出 (title, date, cover, body_html, summary)。"""
    m = re.search(r'<title>(.*?)</title>', doc, re.S)
    title = html_mod.unescape(m.group(1).split('|')[0].strip()) if m else slug

    h1 = re.search(r'<h1[^>]*>(.*?)</h1>', doc, re.S)
    if h1:
        title = re.sub(r'\s+', ' ', html_mod.unescape(re.sub(r'<[^>]+>', '', h1.group(1)))).strip()

    # 正文：优先找 .prose；找不到就退回 h1 之后到 </main>
    pm = re.search(r'<div class="prose\b[^>]*>', doc)
    if pm:
        end = match_close(doc, pm.start())
        body_html = doc[pm.end():end]
        hero_zone = doc[:pm.start()]
    else:
        i = doc.find('<h1')
        j = doc.find('</main>', i)
        body_html = doc[i:j]
        hero_zone = doc[:i]

    # 封面：hero 区里的第一张 img（线上把封面放在 h1 附近的容器里）
    imgs = re.findall(r'<img\b[^>]*>', hero_zone)
    cover = ''
    for t in reversed(imgs):
        s = re.search(r'src="([^"]*)"', t)
        if s and 'images/news/' in s.group(1):
            cover = rewrite_src(s.group(1))
            break

    # 线上好几篇把封面图在正文开头又放了一次（hero 一张 + 正文一张）。本站版式里
    # 封面由 .tf-blog-detail-image 单独呈现，正文里那张是纯冗余，去掉——否则同一张
    # 图会在页面上出现两次。
    if cover:
        fname = re.escape(cover.rsplit('/', 1)[-1])
        pat = re.compile(r'<img\b[^>]*src="[^"]*' + fname + r'"[^>]*>')
        body_html, dup = pat.subn('', body_html, count=1)
        if dup:
            body_html = re.sub(r'<p>\s*</p>', '', body_html)

    # 日期：正文首段里的 `YYYY 年 M 月 D 日` 或 hero 区的 YYYY-MM-DD
    body_text = html_mod.unescape(re.sub(r'<[^>]+>', '', body_html))
    date = ''
    d = re.search(r'<time[^>]*datetime="(\d{4}-\d{2}-\d{2})', hero_zone)
    if d:
        date = d.group(1)
    if not date:
        d = re.search(r'(\d{4})-(\d{2})-(\d{2})', html_mod.unescape(re.sub(r'<[^>]+>', '', hero_zone)))
        if d:
            date = '%s-%s-%s' % d.groups()
    if not date:
        d = re.search(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', body_text)
        if d:
            date = '%04d-%02d-%02d' % tuple(int(x) for x in d.groups())

    return title.strip(), date, cover, body_html


def first_paragraph(md_lines):
    """取正文首段当摘要。

    逐字来自原文，不改写——新闻稿的首段本来就是导语。跳过图片行、标题、表格与
    内嵌 HTML 块；去掉 Markdown 标记后返回。
    """
    for line in md_lines:
        s = line.strip()
        if not s or s.startswith('#') or s.startswith('|') or s.startswith('<'):
            continue
        if s.startswith('!['):
            continue
        if re.match(r'^([-*+]|\d+\.)\s+', s):
            continue
        return re.sub(r'\*\*|\*|`', '', s)
    return ''


# ------------------------------------------------------------------ 往返自检
def plain_text(html_frag):
    """去标签 + 压空白，用于「转换前后文本必须一致」的比对。"""
    s = strip_comments(html_frag)
    s = re.sub(r'<br\s*/?>', ' ', s)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = html_mod.unescape(s)
    return re.sub(r'\s+', '', s)


def tag_counts(html_frag):
    counts = {}
    for tag in COUNTED:
        counts[tag] = len(re.findall(r'<%s[\s>]' % tag, html_frag))
    counts['figure'] = len(re.findall(r'<figure[\s>]', html_frag))
    return counts


def empty_thead_stats(html_frag):
    """数出源里「表头格子全为空」的表格 -> (表格数, 空 th 合计)。

    这类表格在线上是用来排图片网格的。Markdown 语法强制第一行必须是表头，
    转换时保留了一行空表头占位，mdrender 认出来并不生成 <thead>。所以产物里
    的 <tr>/<th> 会少掉这些，属于设计内损失，比对时要先扣掉。
    """
    tables = 0
    ths = 0
    for m in re.finditer(r'<thead\b.*?</thead>', html_frag, re.S):
        cells = re.findall(r'<th\b[^>]*>(.*?)</th>', m.group(0), re.S)
        if cells and all(not re.sub(r'<[^>]+>', '', c).strip() for c in cells):
            tables += 1
            ths += len(cells)
    return tables, ths


def roundtrip_check(label, source_html, markdown):
    """源 HTML 与 Markdown 渲染结果必须等价。返回问题列表。"""
    problems = []
    back = mdrender.render(markdown)

    a, b = plain_text(source_html), plain_text(back)
    if a != b:
        # 找出第一处差异，方便定位
        k = 0
        while k < min(len(a), len(b)) and a[k] == b[k]:
            k += 1
        problems.append('%s: text differs at char %d: source=%r rendered=%r'
                        % (label, k, a[max(0, k - 30):k + 30], b[max(0, k - 30):k + 30]))

    ca, cb = tag_counts(source_html), tag_counts(back)
    dropped_tables, dropped_ths = empty_thead_stats(source_html)

    # 逐标签比对。三处「设计内损失」各按差额扣：
    #   <p>      -> 独立成段的图片升级为 <figure>（.prose figure 才有 margin/边框）
    #   <tr>/<th> -> 空表头表格不生成 <thead>
    expected = {
        'p': cb['figure'] - ca['figure'],
        'tr': -dropped_tables,
        'th': -dropped_ths,
    }
    for tag in COUNTED:
        want = ca[tag] + expected.get(tag, 0)
        if want != cb[tag]:
            problems.append('%s: <%s> count %d -> %d (期望 %d)'
                            % (label, tag, ca[tag], cb[tag], want))
    return problems


# ------------------------------------------------------------------ 主流程
def build_markdown(slug, doc, base_url, problems):
    title, date, cover, body_html = extract_post(doc, slug, base_url)
    lines = blocks_md(body_html)
    body = '\n'.join(lines).strip()

    summary = first_paragraph(lines)

    if not date:
        problems.append('%s: could not determine the post date' % slug)
    if not cover:
        problems.append('%s: could not find a cover image' % slug)
    if not summary:
        problems.append('%s: could not derive a summary' % slug)
    problems.extend(roundtrip_check(slug, body_html, body))

    # frontmatter。手写解析（tools/build_blog.py 里那个 parse_front_matter 认这个格式），
    # 不引 yaml 依赖。
    fm = ['---',
          'title: %s' % title,
          'slug: %s' % slug,
          'date: %s' % (date or '1970-01-01'),
          'cover: %s' % (cover or '%s/unknown.webp' % LOCAL_IMG_DIR),
          'summary: %s' % summary,
          '---', '']
    return '\n'.join(fm) + body + '\n'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--only', action='append', default=None,
                    help='只处理指定 slug（可重复）')
    ap.add_argument('--force', action='store_true',
                    help='允许覆盖已存在的 content/blog/<slug>.md')
    ap.add_argument('--from-dir', default=None,
                    help='从本地已抓好的 HTML 目录读取（文件名形如 pxs-<slug>.html）')
    ap.add_argument('--dry-run', action='store_true',
                    help='只打印，不写盘')
    args = ap.parse_args()

    slugs = args.only or SOURCES
    problems = []
    written = []
    skipped = []

    for slug in slugs:
        out_path = os.path.join(CONTENT_DIR, '%s.md' % slug)
        if os.path.exists(out_path) and not args.force:
            skipped.append(slug)
            continue
        try:
            doc, where = fetch(slug, args.from_dir)
        except Exception as exc:  # noqa: BLE001
            problems.append('%s: fetch failed: %s' % (slug, exc))
            continue
        md = build_markdown(slug, doc, where, problems)
        if args.dry_run:
            print('=' * 70)
            print('--- %s (from %s)' % (slug, where))
            print(md)
            continue
        os.makedirs(CONTENT_DIR, exist_ok=True)
        with open(out_path, 'w', encoding='utf-8') as fh:
            fh.write(md)
        written.append((slug, len(md)))

    print('content/blog/')
    for slug, size in written:
        print('  + %s.md  %d chars' % (slug, size))
    for slug in skipped:
        print('  = %s.md  (exists, kept — 用 --force 才会覆盖)' % slug)
    if problems:
        print('ISSUES:')
        for msg in problems:
            print('  !', msg)
        if written and not args.dry_run and not args.force:
            # 已经有文件落盘了，但发现了问题：明确告诉人别当真
            print('  ! 上面已写盘的文件不可信，请修好后用 --force 重跑')
        raise SystemExit(1)
    print('ok')


if __name__ == '__main__':
    main()
