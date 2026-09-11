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

# 本来就**没有** CSS 规则的名字（精确匹配）：{名字: (为什么它不需要 CSS, 依据文件)}
#
# 「依据」是这里的防呆核心，别填成一个顺手看起来对的文件名。
# 这些条目免掉的是幽灵类检查，而幽灵类检查是全仓**唯一**会追问「这个 class 到底
# 有没有人用」的地方 —— 豁免一旦基于错误的前提，死类名就能在它下面长期潜伏。
#
# 2026-09-11 实证：`hover-scramble` 以「main.js 的打字机效果钩子」被登记到这里
# （理由看着完全合理），而 main.js 里从来没有这个字符串。它的真身只是生成器写在
# 页脚链接上的一个空壳 —— 21 条链接带着它，动效从未实现，hover 时只有颜色变化。
# 它一路安然无恙，因为唯一会追问的检查被它自己的豁免挡住了，直到用户报
# 「下拉和页脚的文字不动」才被翻出来。
#
# 所以每条都必须写明名字真正出现在哪个文件，脚本会打开那个文件核对。
# 只登记**当前页面上真的用到**的钩子：命不中的条目会一直报 stale。
EXACT_HOOKS = {
    # 生成器给 hero 终端的 SVG 画的那个 circle。它没有 CSS 规则，也没有任何 JS
    # 引用 —— 名字在这里出现只是为了给那个元素一个语义标记，样式全由内联属性
    # (stroke / fill) 承担。真要让它动起来，改的是生成器里的内联属性或另加 CSS，
    # 不要指望这个 class。
    'tf-thinking-track': ('生成器写死的 SVG 装饰标记，无 CSS 也无 JS 引用',
                          'tools/reshape_home.py'),
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


def verify_hooks(root):
    """核对每条豁免的依据：名字必须真的出现在它声称的那个文件里。

    理由是**写下的那句**（「main.js 的钩子」）与实际不符时，这里就会响 ——
    而不是等到几个月后有人发现某个动效从来没生效过。
    """
    problems = []
    for name, (note, source) in sorted(EXACT_HOOKS.items()):
        try:
            with open(os.path.join(root, source), encoding='utf-8') as fh:
                text = fh.read()
        except OSError as exc:
            problems.append('%s: 依据文件读不到 —— %s（%s）' % (name, exc, source))
            continue
        if name not in text:
            problems.append('%s: 依据是 %s，那个文件里却没有这个名字。'
                            '登记的理由是「%s」—— 理由与事实不符，'
                            '这个豁免掩盖的是不是真问题？' % (name, source, note))
    return problems


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
    # 还有人命中的豁免也要查依据：命中只说明「产物里写了这个 class」，
    # 不说明「它真的有人用」—— 死类名照样会被命中。
    unbacked = verify_hooks(root)

    if problems or stale or unbacked:
        print('PROBLEMS:')
        for rel, ghosts in problems:
            print('  ! %s' % rel)
            for token in ghosts:
                print('       %s' % token)
        for name in stale:
            print('  ! stale hook whitelist entry: %s — 没有任何 class 命中它' % name)
        for msg in unbacked:
            print('  ! 豁免的依据对不上: %s' % msg)
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
        if unbacked:
            print('  豁免的依据必须是**真的**：写「main.js 的钩子」就得能在那个文件里')
            print('  找到这个名字。名字只在生成器里出现、却在产物里到处挂着，说明它')
            print('  没有使用者 —— 要么给它真实现（CSS 或 JS），要么把 class 摘掉。')
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
