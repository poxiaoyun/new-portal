# -*- coding: utf-8 -*-
"""顶部跑马灯（`.tf-announcement-bar` 里的公告轨道）的内容真源。

公告条属于**站芯** —— 它在首页上产出，13 个内容页由 `portal_page.derive()` 整篇
搬走（比对见 `chrome_fingerprint()`）。所以这里产出的每一个字节都必须与页面无关：
任何逐页差异都会被「内容页站芯与首页逐字节相同」那条不变量抓住，而且表现是
「站芯漂移」—— 看起来像是 derive 的锅，跟公告条没有半点关系。

    条目 = 自动：`content/blog/` 里全部动态的标题，按日期倒序取最新 MAX_BLOG 条
         + 手写：`content/announcements.md` 里的条目（可选，格式见那个文件）

自动那半**不去问首页的博客卡要**，而是直接读内容源（经 build_blog.load_posts()）：
首页卡片只挑了三篇，公告条要的是全部；两处各存一份列表迟早会漂 —— 2026-09-11 之前
首页与详情页的封面就是各写一份，同一篇内容两个封面。

跑马灯的无缝前提有三条，都在 track_html() 里落实：

1. **轨道必须是两个逐字节相同的半**。动画是 `translate(0) -> translate(-50%)`
   （vendor.css 的 `@keyframes tf-announcement-scroll`），百分比位移是相对元素自身
   宽度算的，所以只有两半一模一样，循环处才接得上。
2. **半宽 ≥ 视口宽**（`.tf-announcement-viewport` 最宽 1280px）。窄了会在循环中段
   从右侧露出空白。另外轨道自带 `min-width:200%`，它撑开的是**元素**而不是内容，
   而 -50% 按元素宽度算 —— 内容比 min-width 窄时，位移与实际内容对不上，同样错位。
   MIN_HALF_PX=1600 一次覆盖两条：1600 > 1280，且 2×1600=3200 > 2×1280=2560。
3. **半宽还决定滚动速度**（动画时长 82s 在 vendor.css 里写死，速度 = 半宽/82）。
   条目变短之后份数若只按前两条取，速度会悄悄掉一档 —— 见 TARGET_SPEED_PX_S。
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import build_blog  # noqa: E402
from portal_page import esc, ext  # noqa: E402

ROOT = os.path.dirname(HERE)

# 条目标签。它是**跑马灯里唯一的一处固定文案** —— 每一屏的每一条前面都挂它。
LABEL = 'New:'

# 手写扩展条目的内容源（可选文件；不存在就等于没有扩展条目）。
# SECTION 是文件里承放条目的那一节的标题 —— 它以上的部分是自由文档，以下的
# 「非空非注释非条目」行会报错。见 load_extras()。
SOURCE = 'content/announcements.md'
SECTION = '条目'
DEFAULT_HREF = '/blog'

# 自动条目取最新的多少条。公告条不是内容仓库：动态攒到几十篇之后不该整列铺上去。
# 截断是**有意的**，所以它只取一个前缀，守卫会核对第一条就是最新那篇。
MAX_BLOG = 8
# 手写条目的上限。超了直接报错而不是静默丢弃 —— 公告条就那么高，塞不下更多。
MAX_EXTRA = 8

# 轨道重复份数上限（偶数）。当前内容量（5 条）下是 8；条目多起来会降到 2~4。
MAX_REPEATS = 10

# 见模块 docstring 第 2 条。
MIN_HALF_PX = 1600

# 滚动速度。vendor.css 给轨道定的是 `animation: 82s linear infinite`（移动端 92s），
# 位移 -50% 正好是半宽 —— 所以**速度 = 半宽 / 82**。时长写死在编译产物里、改不了，
# 能调的只有「轨道多宽」，也就是重复份数。
#
# 取 70px/s 是为了与改前同一档（改前那条长文案约 77px/s，2.2 倍的落差肉眼就看得出
# 「跑马灯变懒了」）。这条**不设上限**：条目多到循环本身已经超过这个宽度时，份数退回
# 2，速度跟着变快 —— 那是内容量的自然结果，不是 bug。
#
# 顺带一提，按这个份数复现出来的轨道宽度与改前相当，标记量也相当：改前是 10 份长文案
# （每份约 250B 标记、1202px 宽），现在是 40 条短条目（每条约 66B、115px 宽）。
ANIM_S = 82.0
TARGET_SPEED_PX_S = 70.0

# ------------------------------------------------------------ 宽度估算
# `.tf-announcement-bar` 的排版事实（vendor.css）：
#   font-size: calc(.7rem + 2px)  -> 16px 根字号下 13.2px，且没有移动端覆盖
#   .tf-announcement-track        -> gap: 4.8rem
#   .tf-announcement-track a      -> gap: .7rem（<b> 与正文之间）
FONT_PX = 13.2
ITEM_GAP_PX = 4.8 * 16
BADGE_GAP_PX = 0.7 * 16

# 全角字形（CJK 及其标点、全角形式）按 1em 计，其余按 .6em。
# 与 tools/gen_og.py 的 fit_size() 同一套口径 —— 那边的用途是估字号，这里是估宽度，
# 都是「宁可高估」的方向。估歪的代价只有一个：轨道多重复两份或半宽差一点。
_WIDE = re.compile(r'[\u2e80-\u9fff\uf900-\ufaff\ufe30-\ufe4f\uff00-\uff60]')

# 零宽占位。**不是装饰**：flex 的 gap 只出现在相邻项目之间，末尾少一个项目就少一个
# gap，-50% 会与「一份」相差半个 gap（4.8rem/2 = 38px），每 82 秒在循环处跳一下。
# 补一个零宽项目让 gap 数与项目数对齐，位移就精确了。
# 不能用 HTML 注释代替 —— 注释不是 flex 项目，不产生 gap。
SPACER = '<span aria-hidden="true"></span>'


def _text_px(text):
    wide = len(_WIDE.findall(text))
    return (wide + (len(text) - wide) * 0.6) * FONT_PX


def _item_px(text):
    """一条占的宽度：标签 + 标签与正文之间的 gap + 正文。"""
    return _text_px(LABEL) + BADGE_GAP_PX + _text_px(text)


def anchor(text, href):
    """一条条目的标记。守卫拿它逐条比对产物里的轨道，所以它是唯一的构造出口。"""
    return '<a href="%s"%s><b>%s</b>%s</a>' % (esc(href), ext(href), LABEL, esc(text))


# ============================================================ 内容源
def blog_items():
    """公司动态的标题，按日期倒序取最新 MAX_BLOG 条。

    走 build_blog.load_posts() 而不是自己读 frontmatter：那一边已经管着
    「文件名 == slug」「date 是 YYYY-MM-DD」「封面存在」这些校验，也已经在按
    (date, slug) 倒序排。重写一遍排序就是给「顺序对不上」留了一扇门。
    """
    return [(p['title'], p['href']) for p in build_blog.load_posts()[:MAX_BLOG]]


def load_extras():
    """`content/announcements.md` 里的手写条目。

    分隔方式刻意选「**`## 条目` 这一节**」：它上面的说明区是自由 markdown（想写多长
    写多长），只有这一节里按条目格式解析。这样既能给这个文件写文档，又不至于让
    「写错一行」变成静默的 —— 条目区里除空行、`#` 注释、`- ` 条目外的任何一行都
    直接报错。跳过等于「写错了但什么都没发生」，而这里写错的表现是「公告条上少
    一条」，不看页面根本发现不了。

    条目格式：`- 正文 | 链接`，竖线后面的链接可省（省了指向 DEFAULT_HREF）。
    """
    path = os.path.join(ROOT, SOURCE)
    if not os.path.exists(path):
        return []
    items, in_items, seen = [], False, False
    with open(path, encoding='utf-8') as fh:
        for lineno, raw in enumerate(fh, start=1):
            line = raw.strip()
            head = re.match(r'^(#+)\s*(.*)$', line)
            if head:
                title = head.group(2).strip()
                if title == SECTION:
                    in_items, seen = True, True
                elif len(head.group(1)) <= 2:
                    in_items = False        # 同级或更高级的标题 = 条目区结束
                continue
            if not in_items or not line:
                continue
            if not line.startswith('- '):
                raise SystemExit(
                    '%s:%d: 「%s」一节里只认 "- " 开头的条目（说明请写到这一节上面，'
                    '或给它加 # 注释）: %r' % (SOURCE, lineno, SECTION, line))
            text, _, href = line[2:].partition('|')
            text, href = text.strip(), href.strip() or DEFAULT_HREF
            if not text:
                raise SystemExit('%s:%d: 条目正文是空的' % (SOURCE, lineno))
            if '|' in href:
                raise SystemExit('%s:%d: 链接里不该再有 "|"（正文本身不能含竖线）: %r'
                                 % (SOURCE, lineno, line))
            if not (href.startswith('http://') or href.startswith('https://')
                    or (href.startswith('/') and not href.startswith('//'))):
                raise SystemExit(
                    '%s:%d: 链接要写成站点根相对（如 /contact）或完整 http(s) 地址，'
                    '得到 %r —— 相对路径在站芯里是错的：同一段标记要在 depth=0/1/2 '
                    '的页面上逐字节复用' % (SOURCE, lineno, href))
            items.append((text, href))
    if not seen:
        raise SystemExit('%s: 找不到 "## %s" 这一节 —— 手写条目就写在它下面'
                         % (SOURCE, SECTION))
    if len(items) > MAX_EXTRA:
        raise SystemExit('%s: 手写条目 %d 条，超过上限 %d —— 公告条不是内容仓库，'
                         '请把长期内容放进 content/blog/' % (SOURCE, len(items), MAX_EXTRA))
    return items


def items():
    """公告条的完整条目表：公司动态（新 -> 旧）在前，手写扩展在后。"""
    out = blog_items() + load_extras()
    if not out:
        raise SystemExit('公告条没有任何条目：content/blog/ 空，%s 也没写' % SOURCE)
    return out


# ============================================================ 轨道
def cycle_px(entries):
    """一个循环（把所有条目各显示一次）的宽度估算。"""
    return sum(_item_px(text) for text, _ in entries) + ITEM_GAP_PX * len(entries)


def repeats_for(entries):
    """轨道重复几份 —— 必须是偶数（一半 = 重复份数/2 个循环）。

    取满足下面这个下限的最小偶数份数：

        半宽 ≥ max(MIN_HALF_PX, TARGET_SPEED_PX_S × ANIM_S)

    前一项是「填满视口」，后一项是「别比改前慢一档」。内容多的时候两条都自动满足，
    就是 2 份；内容少的时候是这里在决定份数。
    """
    per = cycle_px(entries)
    need = max(MIN_HALF_PX, TARGET_SPEED_PX_S * ANIM_S)
    for r in range(2, MAX_REPEATS + 1, 2):
        if (r // 2) * per >= need:
            return r
    raise SystemExit(
        '公告条内容太短（%d 条，估宽 %dpx/循环），重复 %d 份后半宽仍不足 %dpx '
        '—— 加条目，或按需下调 announce.MIN_HALF_PX / TARGET_SPEED_PX_S'
        % (len(entries), per, MAX_REPEATS, need))


def track_html():
    """`.tf-announcement-track` 的子节点：重复偶数个循环 + 一个零宽占位。"""
    entries = items()
    cycle = ''.join(anchor(text, href) for text, href in entries)
    return cycle * repeats_for(entries) + SPACER


if __name__ == '__main__':
    for text, href in items():
        print('%-4s %s' % (href, text))
