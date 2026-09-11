#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""站内链接体检：把每个页面的链接解析到磁盘，找出断链与路径深度错误。

为什么需要它
------------
这个站点的目标之一是**替换 poxiaoshi.cn** —— 页面之间必须自己闭环，不能靠跳到
线上补位。这件事在静态产物里就能查清，不需要起服务、不需要浏览器：

  * 每个 `href="/…"` 必须落到磁盘上真实存在的文件
  * 每个相对资源引用必须带**恰好等于页面深度**的 `../` 前缀（少一层 404，多一层也 404）
  * 每个内容页都必须至少被一个页面链接到（孤儿页 = 写了但没人能到）

页面是自动发现的（扫所有 `index.html`），所以新加一页不用改这里。

用法
----
    python3 tools/qa/links.py            # 查全站
    python3 tools/qa/links.py --quiet    # 只输出问题与汇总

有断链时非零退出，可以直接当门禁。
"""

import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 自动发现时应跳过的目录
SKIP_DIRS = {'.git', 'node_modules', 'tools', 'tmp', 'outputs', '.workbuddy',
             'vendor', 'dist', 'build'}

# 已经挂在站芯（nav / footer）上、但页面本身还没建的入口。
# 补齐一个就从这里删一行 —— 留着会被算作「已知未建」而不报错，删掉才会开始保护它。
#
# 2026-09-11 清空：/contact 建好了转正式检查；「关于我们」下拉里「开源项目」改指
# 站外 https://www.kubegems.io/、「加入我们」整项移除，所以原来的 /affiliates 与
# /careers 已无任何页面引用。**白名单里留着没人引用的条目是有害的** —— 它会在
# 汇总行里继续宣称「这些还没建」，让人以为站芯上还有两个死链。所以下面专门查
# 这种情况（stale whitelist），一旦某条目没有任何页面引用就报错，逼着清理。
NOT_BUILT_YET = {}

HREF = re.compile(r'href="([^"]*)"')
SRC_HREF = re.compile(r'(?:src|href)="([^"]*)"')


def discover_pages(root):
    """扫出站点里所有页面（index.html），按路径排序。"""
    pages = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS and not d.startswith('.')]
        if 'index.html' in filenames:
            rel = os.path.relpath(os.path.join(dirpath, 'index.html'), root)
            pages.append(rel)
    return sorted(pages)


def depth_of(rel_page):
    """页面相对站点根的层数：index.html=0，about/index.html=1，blog/x/index.html=2。"""
    return rel_page.count('/')


def resolve(href):
    """站内根相对链接 -> 相对站点根的磁盘路径。返回 None 表示不是站内链接。"""
    if not href.startswith('/') or href.startswith('//'):
        return None
    path = href.split('#')[0].split('?')[0].lstrip('/')
    if path == '' or path.endswith('/'):
        path += 'index.html'
    elif not os.path.splitext(path)[1]:
        path += '/index.html'
    return path


def check(root=ROOT, quiet=False):
    pages = discover_pages(root)
    problems = []
    inbound = {p: 0 for p in pages}
    root_links = {}
    counted = 0
    whitelist_seen = set()

    for page in pages:
        html = open(os.path.join(root, page), encoding='utf-8').read()
        depth = depth_of(page)
        prefix = '../' * depth

        # ---------------------------------------------------- 站内根相对链接
        for m in HREF.finditer(html):
            href = m.group(1)
            target = resolve(href)
            if target is None:
                continue
            counted += 1
            root_links.setdefault(href, set()).add(page)
            if os.path.exists(os.path.join(root, target)):
                inbound[target] = inbound.get(target, 0) + 1
            elif href.rstrip('/') in NOT_BUILT_YET:
                whitelist_seen.add(href.rstrip('/'))  # 已知未建的入口，不报
            else:
                problems.append('%s -> %s  (target missing: %s)' % (page, href, target))

        # ------------------------------------------------------- 相对资源前缀
        # 层数必须**恰好**等于页面深度。下面那条「存在性」检查对**少一层**的路径
        # 是静默跳过的（它的 continue 分支要求 ref 以完整 prefix 开头），所以层数
        # 必须单独核 —— 2026-09-11 审查发现：`../assets/` 这种（depth=2 时少一层，
        # 线上 404）在原先三条正则里一条都不命中。
        wrong = sorted({m.group(1).count('../')
                        for m in re.finditer(r'(?:src|href)="((?:\.\./)*)assets/', html)}
                       - {depth})
        if wrong:
            problems.append('%s -> asset path depth %s, want %d — 一层之差就是 404'
                            % (page, wrong, depth))
        if depth >= 1:
            for m in SRC_HREF.finditer(html):
                ref = m.group(1)
                if not ref.startswith(prefix) or '://' in ref:
                    continue
                local = ref[len(prefix):]
                # 只关心站内资产；页面之间的相对链接留给上面那条规则
                if not local.startswith(('assets/', 'content/')):
                    continue
                if not os.path.exists(os.path.join(root, local)):
                    problems.append('%s -> %s  (missing asset)' % (page, ref))

    # ------------------------------------------------------------ 孤儿页
    for page, n in sorted(inbound.items()):
        if page == 'index.html':
            continue
        if n == 0:
            problems.append('%s is an orphan — no page links to it' % page)

    if not quiet:
        print('pages (%d):' % len(pages))
        for page in pages:
            print('  %-46s depth=%d  inbound=%d' % (page, depth_of(page), inbound.get(page, 0)))
        print()
        print('in-site root-relative links (%d total):' % counted)
        for href in sorted(root_links):
            target = resolve(href)
            exists = target and os.path.exists(os.path.join(root, target))
            pending = href.rstrip('/') in NOT_BUILT_YET
            state = 'ok' if exists else ('not built yet' if pending else 'MISSING')
            print('  %-34s %-46s %-13s %d page(s)'
                  % (href, target or '-', state, len(root_links[href])))
        print()

    # 白名单腐化：条目还在，但已经没有任何页面引用它了。继续留着只会让汇总行
    # 谎称「这些还没建」，所以按错误处理 —— 要么删条目，要么把链接挂回去。
    stale = sorted(set(NOT_BUILT_YET) - whitelist_seen)
    if stale:
        print('PROBLEMS:')
        for h in stale:
            print('  ! stale whitelist entry: %s (%s) — nothing links to it any more, '
                  'drop the NOT_BUILT_YET row' % (h, NOT_BUILT_YET[h]))
        return 1

    if problems:
        print('PROBLEMS:')
        for p in problems:
            print('  !', p)
        return 1

    print('ok — %d pages, %d in-site links, no broken link'
          % (len(pages), counted))
    pending = sorted(NOT_BUILT_YET)
    if pending:
        print('  (still unbuilt, excluded from the check: %s)'
              % ', '.join('%s %s' % (h, NOT_BUILT_YET[h]) for h in pending))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quiet', action='store_true', help='只输出问题与汇总')
    args = ap.parse_args()
    return check(quiet=args.quiet)


if __name__ == '__main__':
    sys.exit(main())
