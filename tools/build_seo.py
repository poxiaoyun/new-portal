#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 robots.txt 与 sitemap.xml（第 7 个生成器，跑在页面流水线的最后）。

为什么把这两份也做成生成器，而不是手写两个静态文件
--------------------------------------------------
`robots.txt` 里的 Sitemap 行与 `sitemap.xml` 里的每条 `<loc>` 都含**规范主机**，
而主机名已经集中定义在 `tools/seo.py`（`SITE_URL`）。手写这两个文件等于把主机名
又抄了 15 遍 —— 换域名时会漏改，而漏改的症状是「sitemap 把爬虫引到一个不存在的
域上」，本地怎么测都是绿的。生成器的另一个好处是**页面清单自动跟上**：加一个产品
页 / 一篇动态，这里不用改。

页面清单从 `qa/links.py` 的 `discover_pages()` 取，不自己再走一遍目录 ——
那份清单是链接体检的判据，sitemap 与它必须指同一批页面，两个实现放一起才能保证
一致（`qa/seo.py` 会拿两边对账）。

lastmod 的取舍见 `tools/seo.py` 顶部「未做 / 不打算做的」那段：只给有真实内容
日期的页面写，宁缺毋滥。

用法：
    python3 tools/build_seo.py
"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import seo  # noqa: E402
import build_blog  # noqa: E402
from qa.links import discover_pages  # noqa: E402

ROBOTS = os.path.join(ROOT, 'robots.txt')
SITEMAP = os.path.join(ROOT, 'sitemap.xml')

# 不进 sitemap 的页面。404 页对爬虫要反过来说话（head 里是 noindex），
# 把它列进 sitemap 等于一边说「别收录」一边说「来收录」。
EXCLUDED = {'404.html'}

ROBOTS_HEADER = '''# 破晓石科技官网 · https://www.poxiaoshi.cn
#
# 整站都对外开放：没有登录墙、没有付费墙、也没有需要屏蔽的目录，所以这里只有
# 一条 Allow。**刻意不写 Disallow** —— 写了就得维护一份「哪些不该抓」的清单，
# 而这份站点的每一页都是给人看的。
#
# 本文件由 tools/build_seo.py 生成，别手改（重跑会覆盖）。

User-agent: *
Allow: /
'''

MISS = []
applied = {}


def sitemap_urls(pages):
    """[(loc, lastmod 或 None), …]，与 pages 一一对应。

    lastmod 只给博客：
      * 详情页 —— 内容源 frontmatter 里的 `date`
      * 列表页 —— 最新一篇的 date（列表页的内容确实随新文章而变）
    其余页面不写。理由见 tools/seo.py 顶部。
    """
    posts = build_blog.load_posts()
    by_slug = {p['slug']: p['date'] for p in posts}
    newest = max(p['date'] for p in posts)

    out = []
    for out_rel in pages:
        loc = seo.page_url(out_rel)
        if loc is None:
            continue                        # 404 之类没有自己 URL 的页
        lastmod = None
        if out_rel == 'blog/index.html':
            lastmod = newest
        elif out_rel.startswith('blog/') and out_rel.endswith('/index.html'):
            slug = out_rel.split('/')[1]
            lastmod = by_slug.get(slug)
            if lastmod is None:
                MISS.append('blog/%s/index.html 在内容源里找不到对应 slug' % slug)
        out.append((out_rel, loc, lastmod))
    # 排序只为了好读：sitemap 是给人复核「有没有漏页」用的清单，首页排在最前面、
    # 其余按 URL 顺排，扫一眼就知道多了或少了谁。爬虫不看顺序。
    out.sort(key=lambda e: (e[0] != 'index.html', e[1]))
    return out


def build():
    pages = discover_pages(ROOT)
    if not pages:
        MISS.append('discover_pages() 一个页面都没找到')
        return
    entries = sitemap_urls([p for p in pages if p not in EXCLUDED])
    applied['pages discovered'] = len(pages)
    applied['sitemap entries'] = len(entries)

    # ---------------------------------------------------------- robots.txt
    robots = ROBOTS_HEADER + '\nSitemap: %s/sitemap.xml\n' % seo.SITE_URL

    # --------------------------------------------------------- sitemap.xml
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for _out_rel, loc, lastmod in entries:
        lines.append('  <url>')
        lines.append('    <loc>%s</loc>' % loc)
        if lastmod:
            lines.append('    <lastmod>%s</lastmod>' % lastmod)
        lines.append('  </url>')
    lines.append('</urlset>')
    sitemap = '\n'.join(lines) + '\n'

    # -------------------------------------------------------------- 守卫
    # 期望值不取自刚生成的这两份文本，而是各问一次「另一个方向」：
    #   * loc 必须绝对、必须在本站主机下（拿 SITE_URL 比）
    #   * loc 之间不许重复（重复的 <loc> 是最常见的 sitemap 事故，爬虫会
    #     把同一页当两个 URL，正好抵消掉 canonical 的作用）
    #   * 磁盘上每个页面对应一条，且每条都能落回磁盘上的一个文件
    locs = [loc for _r, loc, _m in entries]
    if len(set(locs)) != len(locs):
        dupes = sorted({x for x in locs if locs.count(x) > 1})
        MISS.append('sitemap 里有重复 loc: %s' % ', '.join(dupes))
    for out_rel, loc, _m in entries:
        if not loc.startswith(seo.SITE_URL + '/'):
            MISS.append('loc 不是本站绝对地址: %s (来自 %s)' % (loc, out_rel))
        # 落回磁盘时补成 index.html：目录存在不等于页面存在
        # （`os.path.exists('about/')` 对空目录也成立）。
        disk = loc[len(seo.SITE_URL) + 1:]
        if disk.endswith('/') or disk == '':
            disk += 'index.html'
        if not os.path.exists(os.path.join(ROOT, disk)):
            MISS.append('loc 在磁盘上找不到对应文件: %s (来自 %s)' % (loc, out_rel))
    expected = sorted(seo.page_url(p) for p in pages if p not in EXCLUDED)
    if sorted(locs) != expected:
        MISS.append('sitemap 覆盖与页面清单不一致：缺 %s / 多 %s'
                    % (sorted(set(expected) - set(locs)), sorted(set(locs) - set(expected))))

    if MISS:
        print('ISSUES:')
        for m in MISS:
            print('  !', m)
        return 1

    with open(ROBOTS, 'w', encoding='utf-8') as fh:
        fh.write(robots)
    with open(SITEMAP, 'w', encoding='utf-8') as fh:
        fh.write(sitemap)

    print('wrote robots.txt (%d B) + sitemap.xml (%d B, %d urls)'
          % (len(robots), len(sitemap), len(entries)))
    print('applied:')
    for k, v in applied.items():
        print('  + %s x%s' % (k, v))
    for _out_rel, loc, lastmod in entries:
        print('  %-58s %s' % (loc, lastmod or '-'))
    print('ok')
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(line_buffering=True)
    sys.exit(build())
