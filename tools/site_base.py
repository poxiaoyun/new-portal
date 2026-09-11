#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把发布产物里的**站内根相对**链接（href/src = "/xxx"）注入部署前缀。

为什么需要这一层
----------------
站点的全部生成器（reshape_home / build_about / build_blog / build_contact /
build_products）以及体检脚本 qa/links.py，共享同一个假设：

    **站点根 == 域名根**

于是它们产出 `href="/products/rune/"`、`href="/contact"` 这种根相对链接 ——
数量是 807 条，每一页的导航与页脚都带。这个假设在有些部署下成立，有些不成立：

    https://www.poxiaoshi.cn/                  <- 绑了自定义域名，站点在域名根  ✓
    https://poxiaoyun.github.io/new-portal/    <- 项目页，站点根在子路径      ✗

子路径下浏览器把 `/products/rune/` 解析成 `poxiaoyun.github.io/products/rune/`，
807 条链接全部 404。而本地预览（`tools/preview.py` 起在站点根）和 qa/links.py
的断言**都是绿的** —— 失败点落在「产物之外」，没人检查。

**当前部署形态**：绑了自定义域名 `www.poxiaoshi.cn`，站点在**域名根**，所以
workflow 里的 `SITE_BASE` 是**空字符串**，本脚本当前是空操作（走下面的空分支）。
2026-09-11 傍晚曾部署在项目页子路径，那时 `SITE_BASE=/new-portal`。
两种形态的切换只需要改 workflow 里那**一个**变量 —— 但也正因为只是改一个变量，
忘改过一次（绑域名后没同步清空，产物里仍带 `/new-portal/`，线上首页打得开、
点任何链接都 404），所以 workflow 里补了「Assert SITE_BASE matches the Pages host」
那步守卫，两个方向都查。

修法选择：**不动源码语义，只在发布前改写产物**
--------------------------------------------
三个候选：
  A. 全站改相对路径      —— 彻底，但 13 页 + 5 个生成器 + 断言全改，回归面极大
  B. 源码里写死前缀      —— 本地预览立刻坏掉，且日后换域名要翻遍源码
  C. 发布前改写产物      <- 本文件的方案

C 的好处是前缀只在一处（workflow 的 SITE_BASE），源码继续表达「站点根 =
域名根」这个更简单的语义；本地预览、qa/links.py、构建期断言全都零改动。
代价是「改写后的产物」之前没人验过 —— 所以本脚本自带注入后自查（见下）。

幂等与自查（两个都不能省）
------------------------
* **重复注入守卫**：产物里若已存在 `href="{base}/"`，说明这个 dist 被改写过了，
  直接报错退出。否则二次运行会得到 `/new-portal/new-portal/...`。
* **注入后残留自查**：改写完**重新扫一遍磁盘上的产物**，凡仍有根相对引用的
  一律报错。这条断言与「替换了多少条」无关 —— 它不比对期望清单，而是问
  「现在的产物里还有没有会让线上 404 的链接」。两者同源就等于自证：
  （2026-09-11 审查吃过一次亏，见 docs/CODE-REVIEW-2026-09-11.md）。

用法：
    python3 tools/site_base.py dist                 # 根部署（当前）：空操作，只打印说明
    SITE_BASE=/new-portal python3 tools/site_base.py dist
    python3 tools/site_base.py dist --base /new-portal
"""

import argparse
import os
import re
import sys

# 只认 href / src。产物的 HTML 里根相对引用**只有**这两种属性（807 + 47 条，
# 2026-09-11 实测）；content / action / srcset / poster / canonical / og:url
# 一个都没有。以后生成器新增了别的属性、或加了 canonical，这里要同步扩。
# 探针在 qa 里没有位置（那时还没注入），所以扩属性时请一并加断言。
ATTR_RE = re.compile(r'\b(?P<attr>href|src)="(?P<url>/[^"]*)"')

# CSS 里的根相对 url()。**只报告不阻断**：换牌时搬过来的那份 vendor.css 里
# 原本有 3 处 url(/<上游资源目录>/…)（对应的选择器 .tf-hero-card-side-dither /
# .tf-about-team-image 全站无人使用，是死代码），已在 2026-09-11 的品牌清理里
# 连同那两条 background-image 声明一起摘掉，目前为 0 处。但站内 CSS 一旦真的
# 引用了根相对资源，子路径下同样 404 —— 所以这个探针留着，至少要让它能被看见。
CSS_URL_RE = re.compile(r'url\(\s*[\'"]?(/[^\'")]*)')


def normalize_base(raw):
    """把各种写法收敛成 '/prefix' 或 ''（空 = 根部署）。"""
    base = (raw or '').strip()
    if base in ('', '/'):
        return ''
    if not base.startswith('/'):
        base = '/' + base
    return base.rstrip('/')


def rewrite(text, base):
    """返回 (新文本, 替换条数)。已带前缀的 URL 不动（幂等）。"""
    hits = []

    def sub(m):
        url = m.group('url')
        # `//host/path` 是协议相对外链，不是站内引用 —— 一律放过。
        if url.startswith('//'):
            return m.group(0)
        # 已经带前缀：说明改写过了，交给调用方去报「重复注入」。
        if url == base or url.startswith(base + '/'):
            return m.group(0)
        hits.append(url)
        return '%s="%s%s"' % (m.group('attr'), base, url)

    return ATTR_RE.sub(sub, text), len(hits)


def collect_html(dist):
    out = []
    for root, _dirs, files in os.walk(dist):
        for name in files:
            if name.endswith(('.html', '.htm')):
                out.append(os.path.join(root, name))
    return sorted(out)


def residual(text, base):
    """产物里仍然会 404 的根相对引用（排除已注入前缀的）。"""
    bad = []
    for m in ATTR_RE.finditer(text):
        url = m.group('url')
        if url.startswith('//'):
            continue
        if base and (url == base or url.startswith(base + '/')):
            continue
        bad.append('%s="%s"' % (m.group('attr'), url))
    return bad


def main():
    ap = argparse.ArgumentParser(description='注入部署前缀到发布产物')
    ap.add_argument('dist', help='待改写的产物目录（如 dist/）')
    ap.add_argument('--base', default=None,
                    help='部署前缀，如 /new-portal；默认读环境变量 SITE_BASE，空=根部署')
    args = ap.parse_args()

    sys.stdout.reconfigure(line_buffering=True)

    base = normalize_base(args.base if args.base is not None
                          else os.environ.get('SITE_BASE', ''))

    if not os.path.isdir(args.dist):
        print('ERROR: 产物目录不存在: %s' % args.dist)
        return 1

    if not base:
        # 根部署：根相对引用**本来就是要的形态**，不需要「残留检查」——
        # 这里唯一的价值是把「空操作」说清楚，避免和「守卫被我改坏了、
        # 静默什么都没做」混在一起。
        #
        # 注意这段不能反过来写成「检查有没有根相对链接」：那在根部署下
        # 必然报错（708 条全都合法）。2026-09-11 首版就这么写错了，
        # 用例 1 一跑就现形。
        print('SITE_BASE 为空 —— 站点发布在域名根，根相对链接无需改写，空操作。')
        return 0

    print('部署前缀: %s' % base)

    pages = collect_html(args.dist)
    if not pages:
        print('ERROR: %s 下没有 HTML 文件，发布清单可能错了' % args.dist)
        return 1

    # --- 第一遍：重复注入守卫 ---------------------------------------------
    # 必须在改写**之前**查：查到就说明 dist 是二次改写的产物，改写下去会
    # 叠成 /new-portal/new-portal/。留在改写后查是查不出来的（那条会被
    # 当作「本来就有前缀」而放过）。
    doubled = []
    for path in pages:
        with open(path, encoding='utf-8') as f:
            text = f.read()
        if '="%s/' % base in text:
            doubled.append(path)
    if doubled:
        print('ERROR: 以下产物已带 %s/ 前缀，二次运行会把前缀叠起来：' % base)
        for path in doubled[:10]:
            print('  %s' % path)
        print('  提示：dist/ 应由构建从零生成（rm -rf dist && ...），不要复用旧目录。')
        return 1

    # --- 第二遍：改写 ------------------------------------------------------
    total, touched, changed_files = 0, 0, []
    for path in pages:
        with open(path, encoding='utf-8') as f:
            text = f.read()
        new_text, n = rewrite(text, base)
        if n:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_text)
            total += n
            touched += 1
            changed_files.append((os.path.relpath(path, args.dist), n))

    if total == 0:
        # 一条都没改 = 正则和产物的形态对不上了（生成器改了写法？）。
        # 不能当成功放过 —— 那等于这次发布 807 条链接全 404 而 CI 全绿。
        print('ERROR: 一条都没改写 —— ATTR_RE 与产物形态不匹配，'
              '发布出去会全站 404。请核对生成器产出的链接写法。')
        return 1

    print('改写 %d 条，涉及 %d 个页面：' % (total, touched))
    for name, n in changed_files[:8]:
        print('  %-48s %4d' % (name, n))
    if len(changed_files) > 8:
        print('  … 另有 %d 个页面' % (len(changed_files) - 8))

    # --- 第三遍：注入后残留自查 -------------------------------------------
    # 独立判据：重新读盘，问「还有没有会让线上 404 的根相对引用」。
    # 不是拿 total 去对比一个期望值 —— 那会与改写逻辑同源。
    leftover = []
    for path in pages:
        with open(path, encoding='utf-8') as f:
            for item in residual(f.read(), base):
                leftover.append('%s: %s' % (os.path.relpath(path, args.dist), item))
    if leftover:
        print('ERROR: 注入后仍残留 %d 条根相对引用：' % len(leftover))
        for item in leftover[:15]:
            print('  %s' % item)
        return 1

    # --- CSS 里的根相对 url()：报告不阻断 ---------------------------------
    css_hits = []
    for root, _dirs, files in os.walk(args.dist):
        for name in files:
            if not name.endswith('.css'):
                continue
            path = os.path.join(root, name)
            with open(path, encoding='utf-8', errors='replace') as f:
                for url in CSS_URL_RE.findall(f.read()):
                    if url.startswith('//') or url.startswith(base + '/'):
                        continue
                    css_hits.append('%s: %s' % (os.path.relpath(path, args.dist), url))
    if css_hits:
        print('WARN: CSS 里还有 %d 处根相对 url()，子路径下会被解析到站点根之外：'
              % len(css_hits))
        for item in sorted(set(css_hits))[:10]:
            print('  %s' % item)

    print('site_base ok: %s ← %d 条链接' % (base, total))
    return 0


if __name__ == '__main__':
    sys.exit(main())
