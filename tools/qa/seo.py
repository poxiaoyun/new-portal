#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""SEO 资产的静态体检：canonical / og / twitter / JSON-LD / robots / sitemap。

为什么需要它
------------
这一整层有一个共同的失效模式：**页面照常渲染，只有爬虫那边不对**。
canonical 指错主机、og:image 指向不存在的图、JSON-LD 少一个逗号导致整段被丢弃、
sitemap 漏掉一整个目录 —— 这些在浏览器里全都没有任何症状，本地预览也全绿。
`qa/links.py` 与 `qa/classes.py` 覆盖不到它们（那两个管的是链接能不能点开、
类名有没有样式）。所以这里补上第三个门禁。

判据一律**不取自被检查对象**：
  * 规范主机与实体 id 来自 tools/seo.py 的常量
  * 「og 图是否存在 / 尺寸对不对」来自磁盘上那个文件本身（现读 PNG/JPEG 头，
    不信任页面里声明的 width/height —— 那两个数字正是可能写错的东西）
  * sitemap 的页面集合与 `qa/links.py` 的页面发现算法对账

用法：
    python3 tools/qa/seo.py            # 查全站
    python3 tools/qa/seo.py --quiet    # 只输出问题与汇总

有问题时非零退出，可以直接当门禁。
"""

import argparse
import json
import os
import re
import struct
import sys
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import seo  # noqa: E402
from qa.links import discover_pages  # noqa: E402

# 逐页的期望 JSON-LD 实体。**写死在这里**而不是从页面推出来 —— 如果期望值
# 也从产物里算，那段结构化数据被整块删掉时这条检查会一起变成「通过」。
NOINDEX_PAGES = {'404.html'}

TITLE_RE = re.compile(r'<title>(.*?)</title>', re.S)
DESC_RE = re.compile(r'<meta name="description" content="([^"]*)"', re.S)
LD_RE = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)


def meta_map(html):
    """(attr, name) -> content，覆盖 name= 与 property= 两种写法。"""
    out = {}
    for m in re.finditer(r'<meta\s+(name|property)="([^"]+)"\s+content="([^"]*)"', html):
        out[(m.group(1), m.group(2))] = m.group(3)
    return out


def link_href(html, rel):
    m = re.search(r'<link\s+rel="%s"[^>]*href="([^"]*)"' % re.escape(rel), html)
    return m.group(1) if m else None


def image_size(path):
    """现读文件头拿真实尺寸，支持 PNG 与 JPEG。

    自己实现而不是复用 tools/gen_og.py 的 png_size()：体检与生成器共用一段
    解析代码时，那段代码里的同一个 bug 会静默地同时骗过两边。这里的价值恰恰
    在于**独立**。
    """
    with open(path, 'rb') as fh:
        head = fh.read(32)
        if head[:8] == b'\x89PNG\r\n\x1a\n' and head[12:16] == b'IHDR':
            return (struct.unpack('>I', head[16:20])[0],
                    struct.unpack('>I', head[20:24])[0], 'image/png')
        if head[:2] == b'\xff\xd8':                      # JPEG：扫 SOF 段
            fh.seek(2)
            while True:
                b = fh.read(1)
                if not b:
                    return None
                if b != b'\xff':
                    continue
                while b == b'\xff':
                    b = fh.read(1)
                marker = b[0] if b else 0
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA,
                              0xCB, 0xCD, 0xCE, 0xCF):
                    fh.read(3)
                    h, w = struct.unpack('>HH', fh.read(4))
                    return (w, h, 'image/jpeg')
                if marker in (0xD8, 0xD9) or 0xD0 <= marker <= 0xD7:
                    continue
                seg = fh.read(2)
                if len(seg) < 2:
                    return None
                fh.seek(struct.unpack('>H', seg)[0] - 2, os.SEEK_CUR)
    return None


def expected_types(out_rel, posts):
    if out_rel == 'index.html':
        return ['Organization', 'WebSite']
    if out_rel == 'blog/index.html':
        return ['Blog']
    if out_rel.startswith('blog/') and out_rel.endswith('/index.html'):
        return ['BlogPosting', 'BreadcrumbList']
    return ['WebPage']


def check(quiet=False):
    problems = []
    pages = discover_pages(ROOT)
    posts = {}
    content_dir = os.path.join(ROOT, 'content', 'blog')
    for name in os.listdir(content_dir):
        if name.endswith('.md') and name != 'README.md':
            text = open(os.path.join(content_dir, name), encoding='utf-8').read()
            m = re.search(r'(?m)^slug:\s*(\S+)\s*$', text)
            d = re.search(r'(?m)^date:\s*(\S+)\s*$', text)
            if m and d:
                posts[m.group(1)] = d.group(1)

    canonicals = {}
    og_images = {}
    rows = []

    for page in pages:
        html = open(os.path.join(ROOT, page), encoding='utf-8').read()
        metas = meta_map(html)
        noindex_expected = page in NOINDEX_PAGES

        # ------------------------------------------------------------ 基本项
        title = TITLE_RE.search(html)
        desc = DESC_RE.search(html)
        if not title or not title.group(1).strip():
            problems.append('%s: <title> 为空' % page)
        if not desc or not desc.group(1).strip():
            problems.append('%s: <meta name="description"> 为空' % page)
        if '<html lang="zh-CN"' not in html:
            problems.append('%s: <html lang> 不是 zh-CN' % page)

        # ------------------------------------------------------- SEO 块结构
        blocks = seo.SEO_BLOCK_RE.findall(html)
        if len(blocks) != 1:
            problems.append('%s: SEO 块 %d 个（必须恰好 1 个）' % (page, len(blocks)))
            continue
        block = blocks[0]

        robots = metas.get(('name', 'robots'), '')
        if noindex_expected:
            # 404 页：反过来说话，且**不能**指一个 canonical 把爬虫引过去
            if not robots.startswith('noindex'):
                problems.append('%s: robots=%r，这一页应当 noindex' % (page, robots))
            if link_href(html, 'canonical'):
                problems.append('%s: 这一页不该有 canonical' % page)
            if ('property', 'og:url') in metas:
                problems.append('%s: 这一页不该有 og:url' % page)
            if LD_RE.search(block):
                problems.append('%s: 这一页不该有结构化数据' % page)
        else:
            if robots != seo.ROBOTS_INDEX:
                problems.append('%s: robots=%r，期望 %r' % (page, robots, seo.ROBOTS_INDEX))

            want = seo.page_url(page)
            got = link_href(html, 'canonical')
            if got != want:
                problems.append('%s: canonical=%r，期望 %r' % (page, got, want))
            # canonical 必须唯一 —— 两页互指会让搜索引擎自己挑一个
            if got:
                canonicals.setdefault(got, []).append(page)
            og_url = metas.get(('property', 'og:url'))
            if og_url != got:
                problems.append('%s: og:url=%r 与 canonical=%r 不一致' % (page, og_url, got))

        # ---------------------------------------------------- og / twitter
        # og:type 只有可收录的页面才有：noindex 页按设计不声明自己是什么
        # （见 tools/seo.py 的 seo_block），这条要求得跟着那个设计走。
        required_meta = [('property', 'og:site_name'), ('property', 'og:locale'),
                         ('property', 'og:title'), ('property', 'og:description'),
                         ('property', 'og:image'),
                         ('name', 'twitter:card'), ('name', 'twitter:title'),
                         ('name', 'twitter:description'), ('name', 'twitter:image')]
        if not noindex_expected:
            required_meta.append(('property', 'og:type'))
        for key in required_meta:
            if not metas.get(key):
                problems.append('%s: 缺 %s=%s' % (page, key[0], key[1]))
        if metas.get(('name', 'twitter:card')) not in (None, 'summary_large_image'):
            problems.append('%s: twitter:card 应为 summary_large_image' % page)
        if metas.get(('property', 'og:locale')) not in (None, seo.LOCALE):
            problems.append('%s: og:locale 应为 %s' % (page, seo.LOCALE))
        if metas.get(('property', 'og:type')) == 'article' and page != NOINDEX_PAGES:
            if not metas.get(('property', 'article:published_time')):
                problems.append('%s: og:type=article 但没有 article:published_time' % page)

        # ---------------------------------------------- og 图：绝对 + 存在 + 尺寸
        image = metas.get(('property', 'og:image'))
        if image:
            if not image.startswith('https://'):
                problems.append('%s: og:image 不是绝对地址: %s' % (page, image))
            elif not image.startswith(seo.SITE_URL + '/'):
                problems.append('%s: og:image 不在本站主机下: %s' % (page, image))
            else:
                rel = image[len(seo.SITE_URL) + 1:]
                disk = os.path.join(ROOT, rel)
                og_images.setdefault(rel, []).append(page)
                if not os.path.exists(disk):
                    problems.append('%s: og:image 指向的文件不存在: %s（跑 tools/gen_og.py）'
                                    % (page, rel))
                else:
                    size = image_size(disk)
                    if size is None:
                        problems.append('%s: 认不出的图片格式: %s' % (page, rel))
                    else:
                        w, h, mime = size
                        declared = (metas.get(('property', 'og:image:width')),
                                    metas.get(('property', 'og:image:height')))
                        if declared != (str(w), str(h)):
                            problems.append('%s: 声明 %sx%s，实际 %dx%d（%s）'
                                            % (page, declared[0], declared[1], w, h, rel))
                        if metas.get(('property', 'og:image:type')) != mime:
                            problems.append('%s: og:image:type=%r，实际 %s'
                                            % (page, metas.get(('property', 'og:image:type')),
                                               mime))

        # ------------------------------------------------------- JSON-LD
        scripts = LD_RE.findall(block)
        if not noindex_expected:
            if len(scripts) != 1:
                problems.append('%s: 结构化数据 %d 段（期望 1 段 @graph）'
                                % (page, len(scripts)))
            else:
                try:
                    data = json.loads(scripts[0])
                except ValueError as exc:
                    # 少一个逗号 = 整段被爬虫丢弃，而页面毫无变化
                    problems.append('%s: JSON-LD 解析失败: %s' % (page, exc))
                    data = None
                if isinstance(data, dict):
                    if data.get('@context') != 'https://schema.org':
                        problems.append('%s: JSON-LD @context 不是 schema.org' % page)
                    types = [e.get('@type') for e in data.get('@graph', [])]
                    want = expected_types(page, posts)
                    if types != want:
                        problems.append('%s: @graph=%s，期望 %s' % (page, types, want))
                    # 所有 url / @id 都必须是绝对地址（相对地址爬虫常拒绝解析）
                    for node in data.get('@graph', []):
                        for key, value in node.items():
                            if key in ('url', '@id', 'item', 'mainEntityOfPage'):
                                value = value.get('@id') if isinstance(value, dict) else value
                                if isinstance(value, str) and not value.startswith('https://'):
                                    problems.append('%s: JSON-LD %s 不是绝对地址: %s'
                                                    % (page, key, value))
                    # 文章：日期必须与内容源一致（页面上写 3 月、结构化数据说别的，
                    # 是那种谁都不会去看的错）
                    if 'BlogPosting' in types:
                        slug = page.split('/')[1]
                        want_date = posts.get(slug)
                        got_date = next((n.get('datePublished') for n in data['@graph']
                                         if n.get('@type') == 'BlogPosting'), None)
                        if want_date and not str(got_date).startswith(want_date):
                            problems.append('%s: datePublished=%r，内容源里是 %s'
                                            % (page, got_date, want_date))

        rows.append((page, seo.page_url(page) or '(noindex)', image or '-'))

    # ------------------------------------------------------------ 跨页一致性
    # canonical 撞车（两页声明同一个正式地址）是复制内容问题的根源
    for url, pages_with_it in sorted(canonicals.items()):
        if len(pages_with_it) > 1:
            problems.append('canonical 重复: %s 被 %s 同时声明'
                            % (url, ', '.join(pages_with_it)))

    # -------------------------------------------------------------- robots.txt
    robots_path = os.path.join(ROOT, 'robots.txt')
    if not os.path.exists(robots_path):
        problems.append('robots.txt 不存在（跑 tools/build_seo.py）')
    else:
        text = open(robots_path, encoding='utf-8').read()
        if not re.search(r'(?m)^User-agent:\s*\*\s*$', text):
            problems.append('robots.txt 里没有 `User-agent: *`')
        if not re.search(r'(?m)^Allow:\s*/\s*$', text):
            problems.append('robots.txt 里没有 `Allow: /`')
        if re.search(r'(?m)^Disallow:\s*/\s*$', text):
            problems.append('robots.txt 里有 `Disallow: /` —— 那等于整站不让抓')
        want = '%s/sitemap.xml' % seo.SITE_URL
        if not re.search(r'(?m)^Sitemap:\s*%s\s*$' % re.escape(want), text):
            problems.append('robots.txt 的 Sitemap 行不是 %s' % want)

    # ------------------------------------------------------------- sitemap.xml
    sm_path = os.path.join(ROOT, 'sitemap.xml')
    if not os.path.exists(sm_path):
        problems.append('sitemap.xml 不存在（跑 tools/build_seo.py）')
    else:
        try:
            root = ET.parse(sm_path).getroot()
        except ET.ParseError as exc:
            problems.append('sitemap.xml 解析失败: %s' % exc)
            root = None
        if root is not None:
            ns = '{http://www.sitemaps.org/schemas/sitemap/0.9}'
            if root.tag != ns + 'urlset':
                problems.append('sitemap.xml 根元素是 %s，期望 urlset' % root.tag)
            locs = [e.findtext(ns + 'loc') for e in root.findall(ns + 'url')]
            dupes = sorted({x for x in locs if locs.count(x) > 1})
            if dupes:
                problems.append('sitemap.xml 有重复 loc: %s' % ', '.join(dupes))
            # 与页面清单双向对账：漏一页 / 多一页都要报
            want = sorted(seo.page_url(p) for p in pages if p not in NOINDEX_PAGES)
            if sorted(locs) != want:
                problems.append('sitemap 与页面清单不一致：漏 %s / 多 %s'
                                % (sorted(set(want) - set(locs)),
                                   sorted(set(locs) - set(want))))
            # canonical 与 sitemap 必须指同一个集合（两处各错一半就会自相矛盾）
            if sorted(canonicals) != sorted(locs):
                problems.append('canonical 集合与 sitemap 不一致：差 %s'
                                % sorted(set(canonicals) ^ set(locs))[:3])
            for loc in locs:
                if loc and not loc.startswith(seo.SITE_URL + '/'):
                    problems.append('sitemap loc 不在本站主机下: %s' % loc)
            for e in root.findall(ns + 'url'):
                for child in e:
                    if child.tag not in (ns + 'loc', ns + 'lastmod'):
                        # priority / changefreq 被 Google 与 Bing 明说忽略，
                        # 加回来只是噪音（见 tools/seo.py 顶部的说明）
                        problems.append('sitemap 里有无效元素 <%s>' % child.tag[len(ns):])

    if not quiet:
        print('pages (%d):' % len(rows))
        for page, url, image in rows:
            print('  %-46s %-52s %s' % (page, url, image))
        print()
        print('og images (%d):' % len(og_images))
        for rel, used in sorted(og_images.items()):
            size = image_size(os.path.join(ROOT, rel))
            print('  %-52s %sx%s  %d page(s)'
                  % (rel, size[0] if size else '?', size[1] if size else '?', len(used)))
        print()

    if problems:
        print('PROBLEMS:')
        for p in problems:
            print('  !', p)
        return 1
    print('ok — %d pages, canonical/og/JSON-LD 齐备，robots + sitemap 与页面清单一致'
          % len(pages))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quiet', action='store_true', help='只输出问题与汇总')
    args = ap.parse_args()
    return check(quiet=args.quiet)


if __name__ == '__main__':
    sys.stdout.reconfigure(line_buffering=True)
    sys.exit(main())
