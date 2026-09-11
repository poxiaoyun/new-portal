#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""幽灵类体检：HTML 里写的 class，样式表里到底有没有对应规则。

为什么需要它
------------
`vendor.css` 是上游 Tailwind 的**编译产物** —— 上游用过什么类，才有什么类。
我们在生成器里手写的工具类未必存在；不存在的那些既不报错、也不 WARN，
只是「写了等于没写」，渲染出来是 0 或默认值。纯静态、没有运行时能替你发现。

2026-09-11 就是这么踩的：about / contact 两页的 hero 写着

    px-6 pb-16 pt-4 md:px-8 md:pb-20 lg:px-20

其中 `pt-4` / `pb-16` / `md:pb-20` 三个都不在 vendor.css 里 —— 水平内边距一直
正常（`px-6` 存在），**垂直方向全是 0**，页首的 `.tf-overline` 胶囊直接贴住
fixed 顶栏。而首页与 blog 页一个幽灵类都没有，所以只盯着页面看是发现不了规律的。

判据
----
把产物 body 段的 class token 逐个做 CSS 转义，查 `.<转义后>` 是否作为子串出现
在样式表里。不做层叠 / 优先级分析 —— 只问「有没有」这一个问题。

白名单是**必要**的，不是图省事：图标库与 JS 钩子本来就没有 CSS 规则。
往白名单里加东西之前，先确认它真的是钩子，而不是把一条真报错压下去。
反过来，白名单里长期没人命中的条目也会被报出来（stale），逼着清理 —— 和
`links.py` 里 `NOT_BUILT_YET` 的那套规矩一致。

用法
----
    python3 tools/qa/classes.py            # 查全站
    python3 tools/qa/classes.py --quiet    # 只输出问题与汇总

有问题时非零退出，可以直接当门禁。
"""

import argparse
import glob
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))

sys.path.insert(0, HERE)
from links import discover_pages  # noqa: E402  页面发现规则与 links.py 共用一套

# 本来就**没有** CSS 规则的名字（精确匹配）。
# 只登记**当前页面上真的用到**的钩子：留着命不中的条目会一直报 stale，
# 逼人做两难选择。真用到时脚本会报出来，再往这里加一行即可。
EXACT_HOOKS = {
    'hover-scramble',     # main.js 的打字机效果钩子
    'tf-thinking-track',  # main.js 的思考流进度条
}

# 同样没有 CSS 的**前缀**族
PREFIX_HOOKS = (
    'lucide',   # 图标库：图形靠 SVG 自身的属性画，不靠 class
    'is-',      # 运行时状态类（is-scrolled / is-motion-visible …）
)

# Tailwind 在 CSS 里对特殊字符做反斜杠转义，比对时要还原成同一种写法
ESCAPE_CHARS = ':.%/[]()#,!+*~<>=&$@\'"`{}|\\'

CLASS_ATTR = re.compile(r'class="([^"]*)"')
# 只体检 body —— head 里的 class 不参与渲染
BODY_START = re.compile(r'<body\b[^>]*>', re.I)
# script / style 整段跳过：前者是 JS 字符串里的假 class，后者本身就在定义样式
OPAQUE = re.compile(r'<(script|style)\b[^>]*>.*?</\1>', re.I | re.S)


def css_escape(token):
    """按 Tailwind 的写法转义一个 class token，用于在 CSS 文本里查找。"""
    return ''.join('\\' + c if c in ESCAPE_CHARS else c for c in token)


def load_styles(root):
    """把所有样式表拼成一份文本：assets 下全部 .css + 各页面内联 <style>。"""
    parts = []
    for path in sorted(glob.glob(os.path.join(root, 'assets', 'css', '**', '*.css'),
                                 recursive=True)):
        with open(path, encoding='utf-8') as fh:
            parts.append(fh.read())
    for rel in discover_pages(root):
        with open(os.path.join(root, rel), encoding='utf-8') as fh:
            doc = fh.read()
        parts.extend(re.findall(r'<style\b[^>]*>(.*?)</style>', doc, re.I | re.S))
    return '\n'.join(parts)


def page_classes(root, rel):
    """一个页面 body 段里用到的所有 class token。"""
    with open(os.path.join(root, rel), encoding='utf-8') as fh:
        doc = fh.read()
    m = BODY_START.search(doc)
    body = doc[m.end():] if m else doc
    body = OPAQUE.sub('', body)
    tokens = set()
    for attr in CLASS_ATTR.finditer(body):
        tokens.update(attr.group(1).split())
    return tokens


def hook_of(token, used):
    """命中白名单则返回那条白名单，否则 None。顺带记一次命中计数。"""
    if token in EXACT_HOOKS:
        used[token] += 1
        return token
    for prefix in PREFIX_HOOKS:
        if token.startswith(prefix):
            used[prefix] += 1
            return prefix
    return None


def check(root=ROOT, quiet=False):
    pages = discover_pages(root)
    if not pages:
        print('no page found under %s — 先生成产物再体检' % root)
        return 1

    styles = load_styles(root)
    if not styles:
        print('no stylesheet found under assets/css — 无法体检')
        return 1

    problems = []
    used = {h: 0 for h in EXACT_HOOKS}
    used.update({p: 0 for p in PREFIX_HOOKS})
    all_tokens = set()
    total = 0

    for rel in pages:
        tokens = page_classes(root, rel)
        all_tokens |= tokens
        total += len(tokens)
        ghosts = []
        for token in sorted(tokens):
            if hook_of(token, used):
                continue
            if '.' + css_escape(token) not in styles:
                ghosts.append(token)
        if ghosts:
            problems.append((rel, ghosts))

    # 白名单里没人命中的条目 = 已经过期的豁免，留着会掩盖真问题
    stale = sorted(h for h, n in used.items() if n == 0)

    if problems or stale:
        print('PROBLEMS:')
        for rel, ghosts in problems:
            print('  ! %s' % rel)
            for token in ghosts:
                print('       %s' % token)
        for name in stale:
            print('  ! stale hook whitelist entry: %s — 没有任何 class 命中它' % name)
        print()
        if problems:
            print('  上面那些 class 在任何样式表里都没有规则 —— vendor.css 是上游')
            print('  Tailwind 的编译产物，上游没用过的类不会存在，写了等于没写。')
            print('  两条出路：')
            print('    * 真需要这个样式 -> 在 assets/css/*.css 里用真 CSS 写出来')
            print('    * 它本来就是 JS / 图标库的钩子 -> 加进本文件的 EXACT_HOOKS')
            print('      （PREFIX_HOOKS 加之前先确认整族都是钩子）')
        if stale:
            print('  白名单里的 stale 条目没人用了就直接删掉 —— 留着会掩盖真报错。')
        return 1

    if not quiet:
        print('  %d pages, %d class token, %d distinct'
              % (len(pages), total, len(all_tokens)))
    print('ok — %d pages, no ghost class, %d hook pattern(s) still live'
          % (len(pages), len(used)))
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--quiet', action='store_true', help='只输出问题与汇总')
    args = ap.parse_args()
    return check(quiet=args.quiet)


if __name__ == '__main__':
    sys.exit(main())
