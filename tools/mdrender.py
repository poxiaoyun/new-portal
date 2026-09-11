#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""blog 正文的 Markdown -> HTML 渲染器（本站需要的那一小块子集）。

为什么不引第三方库
------------------
1. `content/blog/*.md` 是本站自己维护的内容源，渲染结果要进守卫断言的字节流，
   行为必须**可预测且被我读得完**——一个 300 行的自研子集比 5000 行的通用实现
   更好审。哪天需要新语法，加一条分支比调库的开关便宜。
2. Python 环境不保证能装包（沙箱 offline），生成器必须能在裸环境跑。

支持的块级语法
--------------
    标题        # ## ### #### ##### ######
    段落        连续非空行（软换行直接拼接，中文不需要插空格）
    无序列表    - / * / +
    有序列表    1. 2. …
    引用        >
    分隔线      --- / *** / ___
    围栏代码    ``` … ```
    表格        GFM 风格（第二行是 |---|---| 分隔行）
    HTML 块     以 `<` 开头的行，原样透传
    图片段      独立成行的 ![alt](src) 渲染成 <figure><img></figure>

支持的行内语法
--------------
    **粗**  __粗__  *斜*  _斜_  `代码`  [文](url)  ![图](src)
    内嵌 HTML 标签（白名单外的也保留，但不解析其中内容）

不支持（用不到就不做，避免半吊子实现）
--------------------------------------
    嵌套列表、列表项内的多段落、引用内的列表、标题锚点、脚注、
    定义列表、任务列表、自动链接、setext 标题（`===` 下划线式）。
    遇到 `1)` 这样的非标准有序标记会当成普通段落——这是有意的，
    宁可原样输出也不要错误解析。
"""

import re

__all__ = ['render', 'render_inline', 'esc', 'esc_attr']

# 行内解析：先把「不能被转义/不能被强调正则误伤」的东西抽成占位符，最后还原。
# 占位符用 \x00N\x00 —— 正文里不可能出现 NUL，且不含 * ` [ ] 等标记字符。
_PLACEHOLDER = '\x00%d\x00'

_ESCAPABLE = re.compile(r'\\([\\`*_{}\[\]()#+\-.!|>~])')
_CODE_SPAN = re.compile(r'`([^`]+)`')
_IMAGE = re.compile(r'!\[([^\]]*)\]\(([^)\s]+?)(?:\s+"([^"]*)")?\)')
_LINK = re.compile(r'\[([^\]]*)\]\(([^)\s]+?)(?:\s+"([^"]*)")?\)')
_HTML_TAG = re.compile(r'</?[a-zA-Z][\w-]*(?:\s[^<>]*?)?/?>')
_STRONG = re.compile(r'\*\*(?=\S)(.+?)(?<=\S)\*\*', re.S)
_STRONG_ALT = re.compile(r'__(?=\S)(.+?)(?<=\S)__', re.S)
_EM = re.compile(r'(?<!\*)\*(?=\S)([^*]+?)(?<=\S)\*(?!\*)')
_EM_ALT = re.compile(r'(?<![\w_])_(?=\S)([^_]+?)(?<=\S)_(?![\w_])')


def esc(text):
    """HTML 文本转义。中文标点（含「」“”）不需要动。"""
    return (str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


def esc_attr(text):
    return esc(text).replace('"', '&quot;')


def _is_external(href):
    """站外链接（http/https）开新窗口；站内（/、.、#、mailto）保持同窗。"""
    return href.startswith('http://') or href.startswith('https://')


def render_inline(text):
    """解析一行/一段的行内标记，返回已转义的 HTML 片段。"""
    store = []

    def stash(html):
        store.append(html)
        return _PLACEHOLDER % (len(store) - 1)

    # 1. 反斜杠转义：\* 想输出字面 *，先藏起来，免得被下面的强调正则吃掉
    text = _ESCAPABLE.sub(lambda m: stash(esc(m.group(1))), text)

    # 2. 行内代码：内容不解析任何标记，但仍然要转义
    text = _CODE_SPAN.sub(lambda m: stash('<code>%s</code>' % esc(m.group(1))), text)

    # 3. 图片与链接。链接文字递归走一遍行内解析（此时图片/代码已被抽出，不会递归爆炸）
    text = _IMAGE.sub(lambda m: stash(
        '<img src="%s" alt="%s"%s>'
        % (esc_attr(m.group(2)), esc_attr(m.group(1)),
           ' title="%s"' % esc_attr(m.group(3)) if m.group(3) else '')), text)
    text = _LINK.sub(lambda m: stash(
        '<a href="%s"%s>%s</a>'
        % (esc_attr(m.group(2)),
           ' target="_blank" rel="noopener noreferrer"' if _is_external(m.group(2)) else '',
           render_inline(m.group(1)))), text)

    # 4. 内嵌 HTML 标签原样保留（如单元格里的 <br>）
    text = _HTML_TAG.sub(lambda m: stash(m.group(0)), text)

    # 5. 剩下的才是纯文本，转义
    text = esc(text)

    # 6. 强调。粗体必须先于斜体，否则 **x** 会被 * 的规则先咬一口。
    text = _STRONG.sub(r'<strong>\1</strong>', text)
    text = _STRONG_ALT.sub(r'<strong>\1</strong>', text)
    text = _EM.sub(r'<em>\1</em>', text)
    text = _EM_ALT.sub(r'<em>\1</em>', text)

    # 7. 还原占位符
    for i, html in enumerate(store):
        text = text.replace(_PLACEHOLDER % i, html)
    return text


def _split_row(line):
    """拆一行表格：去首尾竖线，按竖线切，两端去空白。"""
    s = line.strip()
    if s.startswith('|'):
        s = s[1:]
    if s.endswith('|'):
        s = s[:-1]
    return [cell.strip() for cell in s.split('|')]


def _is_table_sep(line):
    """`|---|:--:|` 这样的分隔行。至少要有一个 -。"""
    s = line.strip()
    if not s or '|' not in s and '-' not in s:
        return False
    cells = _split_row(s)
    if not cells:
        return False
    for cell in cells:
        if not re.fullmatch(r':?-{1,}:?', cell):
            return False
    return True


def _render_blocks(lines):
    out = []
    i = 0
    n = len(lines)
    while i < n:
        raw = lines[i]
        s = raw.strip()

        if not s:
            i += 1
            continue

        # ---------------------------------------------------------- 围栏代码
        if s.startswith('```'):
            lang = s[3:].strip()
            j = i + 1
            buf = []
            while j < n and not lines[j].strip().startswith('```'):
                buf.append(lines[j])
                j += 1
            if j >= n:
                # 没有闭合围栏：当普通段落，不静默吞掉后文
                out.append('<p>%s</p>' % render_inline(s))
                i += 1
                continue
            cls = ' class="language-%s"' % esc_attr(lang) if lang else ''
            out.append('<pre><code%s>%s</code></pre>' % (cls, esc('\n'.join(buf))))
            i = j + 1
            continue

        # ------------------------------------------------------------ 分隔线
        if re.fullmatch(r'(?:-{3,}|\*{3,}|_{3,})', s):
            out.append('<hr>')
            i += 1
            continue

        # -------------------------------------------------------------- 标题
        m = re.match(r'(#{1,6})\s+(.*?)\s*#*$', s)
        if m:
            lvl = len(m.group(1))
            out.append('<h%d>%s</h%d>' % (lvl, render_inline(m.group(2)), lvl))
            i += 1
            continue

        # -------------------------------------------------------------- 表格
        # 判据是「本行有竖线 + 下一行是分隔行」，比「本行像表格」可靠
        if '|' in s and i + 1 < n and _is_table_sep(lines[i + 1]):
            head = _split_row(s)
            j = i + 2
            body = []
            while j < n and lines[j].strip() and '|' in lines[j]:
                body.append(_split_row(lines[j]))
                j += 1
            rows = []
            for row in body:
                # 列数不齐时右补空，避免生成错位的表
                row = row + [''] * (len(head) - len(row))
                rows.append('<tr>%s</tr>'
                            % ''.join('<td>%s</td>' % render_inline(c) for c in row[:len(head)]))
            tbody = '<tbody>%s</tbody>' % ''.join(rows)
            if all(not c.strip() for c in head):
                # 线上用空表头表格排图片网格。GFM 语法强制第一行是表头，所以
                # Markdown 里必须写一行空的占位；产物里则不生成 <thead>，
                # 免得页面上多出一条空表头行。
                out.append('<table>%s</table>' % tbody)
            else:
                cells = ''.join('<th>%s</th>' % render_inline(c) for c in head)
                out.append('<table><thead><tr>%s</tr></thead>%s</table>' % (cells, tbody))
            i = j
            continue

        # -------------------------------------------------------------- 引用
        if s.startswith('>'):
            buf = []
            while i < n and lines[i].strip().startswith('>'):
                buf.append(re.sub(r'^\s*>\s?', '', lines[i]))
                i += 1
            # 引用内只按「段落」处理，不递归整块（本站用不到引用里的列表）
            paras = [p for p in '\n'.join(buf).split('\n\n') if p.strip()]
            out.append('<blockquote>%s</blockquote>'
                       % ''.join('<p>%s</p>' % render_inline(' '.join(p.split()))
                                 for p in paras))
            continue

        # -------------------------------------------------------------- 列表
        m = re.match(r'^([-*+]|\d+\.)\s+(.*)$', s)
        if m:
            ordered = m.group(1)[0].isdigit()
            items = []
            while i < n:
                mm = re.match(r'^([-*+]|\d+\.)\s+(.*)$', lines[i].strip())
                if not mm or mm.group(1)[0].isdigit() != ordered:
                    break
                items.append(render_inline(mm.group(2)))
                i += 1
            tag = 'ol' if ordered else 'ul'
            out.append('<%s>%s</%s>' % (tag, ''.join('<li>%s</li>' % t for t in items), tag))
            continue

        # ----------------------------------------------------------- HTML 块
        # 以 `<` 开头就整块透传（到空行为止）。这是 Markdown 的标准行为，
        # 本站用它来表达「单元格里既有图又有粗体文字」这类 GFM 表格装不下的结构。
        if s.startswith('<'):
            buf = []
            while i < n and lines[i].strip():
                buf.append(lines[i])
                i += 1
            out.append('\n'.join(buf))
            continue

        # ------------------------------------------------------ 图片独立成段
        m = re.fullmatch(r'!\[([^\]]*)\]\(([^)\s]+?)(?:\s+"([^"]*)")?\)', s)
        if m:
            cap = ('<figcaption>%s</figcaption>' % render_inline(m.group(3))
                   if m.group(3) else '')
            out.append('<figure><img src="%s" alt="%s">%s</figure>'
                       % (esc_attr(m.group(2)), esc_attr(m.group(1)), cap))
            i += 1
            continue

        # -------------------------------------------------------------- 段落
        buf = []
        while i < n and lines[i].strip():
            nxt = lines[i].strip()
            if (nxt.startswith('#') or nxt.startswith('>') or nxt.startswith('```')
                    or nxt.startswith('<') or re.fullmatch(r'(?:-{3,}|\*{3,}|_{3,})', nxt)
                    or re.match(r'^([-*+]|\d+\.)\s+', nxt)
                    or re.fullmatch(r'!\[[^\]]*\]\([^)\s]+\)', nxt)):
                break
            # 表格起始行也要断开
            if '|' in nxt and i + 1 < n and _is_table_sep(lines[i + 1]):
                break
            buf.append(nxt)
            i += 1
        if not buf:
            # 兜底：上面的 break 条件在 i 处立刻命中且没推进，强制吃掉一行防止死循环
            buf.append(lines[i].strip())
            i += 1
        out.append('<p>%s</p>' % render_inline(''.join(buf)))

    return out


def render(markdown):
    """把 Markdown 正文渲染成 HTML 片段（不含外层容器）。

    `render()` 是纯函数：同样的输入永远得到同样的字节。守卫依赖这一点。
    """
    if markdown is None:
        return ''
    text = markdown.replace('\r\n', '\n').replace('\r', '\n')
    return '\n'.join(_render_blocks(text.split('\n')))
