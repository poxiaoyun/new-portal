#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""渲染站点的分享图与图标（og 卡片 / favicon / Organization logo）。

产物**入库**，和 assets/img/*.webp 一样是产物而不是源码：

    assets/img/og-default.png              全站默认 1200x630（首页 / about / blog / contact）
    assets/img/og/blog-<slug>.png          5 篇公司动态各一张（带封面）
    assets/img/og/product-<slug>.png       4 个产品各一张（带该板块强调色）
    assets/img/favicon-96.png              96x96  透明（搜索结果里的站点图标）
    assets/img/apple-touch-icon.png        180x180 透明
    assets/img/icon-512.png                512x512 透明（JSON-LD 里 Organization 的 logo）

为什么用无头 Chrome 而不是画图库
--------------------------------
三件事凑一起才是这个选择：
  1. 卡片要的是**真字体 + 真 CSS**：Geist 与 PingFang 的混排、字重、行高要和站内
     一致。用 PIL 手排中文还得自己找字体、自己算断行，而本机（和 CI）都没有
     Pillow，也不该为一个静态站的配图给构建链加一个 Python 依赖。
  2. 卡片里的封面是 webp（assets/img/news/*.webp），社交平台对 webp 的支持参差，
     所以必须**转成 PNG** —— 交给浏览器解码比自己写解码器稳。
  3. Chrome 本来就是本仓库的渲染器（tools/qa/cdp.mjs 那套）。

两个必需的 Chrome 参数（都踩过）
--------------------------------
  --no-sandbox   本机沙箱里 Chrome 自己的 sandbox 初始化会失败，症状是
                 `Failed to initialize sandbox` + `GPU process isn't usable. Goodbye.`
                 截图一张都不出。关掉它的沙箱才能起。
  --virtual-time-budget=…
                 字体是网络请求。默认的截图时机在字体到位**之前**，会拍到 fallback
                 字形的卡片 —— 图看着「有字」，但字体是错的，而且每次都换个样子。
                 这个参数让 Chrome 按虚拟时间推进到异步资源就绪再截。
  --force-device-scale-factor=1
                 不加的话 Retina 上出的是 2x 图（2400x630）。OG 卡的尺寸必须是
                 声明出去的那个数。

刻意不进 build_all.py
--------------------
它要起浏览器，CI 里没有（浏览器侧体检本来也不在 CI 里跑）。所以：

  * 新增一篇文章 / 一个产品之后，手工跑一次，把 PNG 一起提交；
  * `tools/qa/seo.py` 会检查「页面引用的 og 图在磁盘上是否存在」以及尺寸是否为
    1200x630，漏跑生成器会在体检里报出来，而不是等社交平台静默不显示。

用法：
    python3 tools/gen_og.py             # 全部重渲染
    python3 tools/gen_og.py --list      # 只列会渲染哪些，不跑浏览器
    python3 tools/gen_og.py --only blog # 只渲染某一类（default/blog/product/icon）
"""

import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

import seo  # noqa: E402
import build_blog  # noqa: E402
import build_products  # noqa: E402

CHROME = os.environ.get('CHROME') or \
    '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'

# 临时 HTML 落在 tmp/ 下（已 gitignore、且不在发布清单里）。**必须在仓库里**：
# 卡片要按相对路径引用 assets/img 下的封面与纹理，file:// 页面跨目录取本地资源
# 不可靠，同树内相对路径才稳。
TMP = os.path.join(ROOT, 'tmp', 'og')

# 卡片 HTML 在 tmp/og/ 下，所以引 assets/ 要往上退两级。**这一条漏了不会报错**：
# 封面 <img> 拿到 404 就静默不画，卡片照出，只是右边空一块 —— 第一版就是这么
# 交出来的（article 卡右侧全空），所以补了 qa/seo.py 里那条「og 图非空且尺寸对」
# 之外的目视复核，以及这里显式算前缀而不是手写 '../..'。
ASSETS = os.path.relpath(ROOT, TMP).replace(os.sep, '/') + '/'

# ---------------------------------------------------------------- 设计令牌
# 与 assets/css/custom.css 的 :root 同一套。取的是**字面值**而不是 var()：
# 卡片是一张独立渲染的图，不引站内的样式表（引了会把整个 vendor.css 拖进来）。
PLATE = '#0d0e10'
LINE = '#ffffff1a'
LABEL = '#ffffff6b'
DITHER = 'assets/img/dither-bg-01.webp'
MARK_SVG = 'assets/img/icon-mark.svg'
OG_W, OG_H = 1200, 630
PAD = 72
# 有封面时正文栏的内容宽度；封面栏吃掉剩下那一条，保证 456 + 600 + 2*72 = 1200。
COVER_TEXT_W = 600
COVER_W = OG_W - (COVER_TEXT_W + 2 * PAD)

FONT_STACK = ("Geist, Inter, 'PingFang SC', 'Hiragino Sans GB', "
              "'Microsoft YaHei', -apple-system, sans-serif")
MONO_STACK = ("'Geist Mono', ui-monospace, SFMono-Regular, Menlo, "
              "'PingFang SC', monospace")


def css_var(name):
    """从 assets/css/custom.css 的 :root 里取一个 --tf-* 的字面值。

    产品的强调色在产品注册表里写成 `var(--tf-rune)`。卡片没有 CSS 变量上下文，
    所以要把那层间接解开 —— 但**不在这里再抄一份色值**，否则调色板一改，卡片
    还停在旧颜色上，而且没人会发现（图是不会报错的产物）。
    """
    text = open(os.path.join(ROOT, 'assets', 'css', 'custom.css'), encoding='utf-8').read()
    m = re.search(re.escape(name) + r'\s*:\s*(#[0-9a-fA-F]{3,8})\s*;', text)
    if not m:
        raise SystemExit('custom.css 里找不到 %s 的字面色值' % name)
    return m.group(1)


def resolve_color(value):
    """`var(--tf-rune)` -> `#9fe9ff`；已经是字面值就原样返回。"""
    m = re.fullmatch(r'var\(\s*(--tf-[a-z0-9-]+)\s*\)', value.strip())
    return css_var(m.group(1)) if m else value


# --------------------------------------------------------------- 文案排布
def text_units(text, latin=0.55):
    """把一段中英混排折成「相当于几个中文字宽」。"""
    return max(1.0, sum(latin if ord(c) < 0x2E80 else 1.0 for c in text))


def fit_size(text, box_w, box_h, base=66, floor=38, line_height=1.26, latin=0.55):
    """估一个能把 text 塞进 box 的字号。

    两个约束取小：
      * 单行放得下      size <= box_w / units
      * 折行后高度够    size <= sqrt(box_w * box_h / (line_height * units))
        （由「总行宽 units*size 折成 N 行、N*line_height*size <= box_h」解出）

    这只是**估算**，CSS 那边还有 `overflow-wrap` 与行数上限兜底 —— 估偏了是
    「字略小/略大」，不是「字跑出画面」。
    """
    units = text_units(text, latin)
    by_width = box_w / units
    by_area = (box_w * box_h / (line_height * units)) ** 0.5
    return int(max(floor, min(base, by_width, by_area)))


def ellipsis(text, limit):
    """字符截断，且**不切断拉丁词**。

    截到一半的 `（NVIDIA I…` 比少说一句更难看，也更像 bug。
    """
    text = re.sub(r'\s+', ' ', str(text)).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit - 1].rstrip()
    # 收尾若落在拉丁词中间（前一个字符是字母、后面还有字母），退到这个词的词首
    while cut and (cut[-1].isascii() and cut[-1].isalnum()) and \
            len(cut) < len(text) and text[len(cut)].isalnum():
        cut = cut[:-1].rstrip()
    return (cut or text[:limit - 1]) + '…'


# 新闻稿开头的电头：`成都，2024 年 11 月 1 日 —— `。卡片的正文只有两三行，
# 这一截对读者没有信息量（日期在卡片右下角已经有了），去掉它才能把版面让给
# 真正的正文。只认「城市 + 日期 + 破折号」这一种形态，不做通用解析。
DATELINE_RE = re.compile(
    r'^[^，。；]{0,14}，\s*\d{4}\s*年\s*\d{1,2}\s*月\s*\d{1,2}\s*日\s*(?:——|--|—)\s*')


def strip_dateline(text):
    return DATELINE_RE.sub('', str(text), count=1)


def clip_sentences(text, limit):
    """按**句子边界**截断：宁可少说一句，也不在半句中间切出省略号。

    卡片正文只有两三行，硬切会切在「此次适配围绕设…」这种地方 —— 读者看到的是
    一个断掉的词。先按句号分句，能整句放下就整句放下；第一句本身就超限时
    （长句很常见）才退回字符截断。
    """
    text = re.sub(r'\s+', ' ', str(text)).strip()
    if len(text) <= limit:
        return text
    best = ''
    for part in re.split(r'(?<=[。！？])', text):
        if len(best) + len(part) > limit:
            break
        best += part
    return best or ellipsis(text, limit)


def esc(text):
    return (str(text).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;'))


# ------------------------------------------------------------------ 卡片
def card_html(*, title, kicker='', sub='', meta='', accent='#9fe9ff', cover=None,
              dots=(), mode='card'):
    """一张 1200x630 的卡片。

    dots 是 [(标签, 颜色), …]：首页卡片底部那排「四大板块」，每个前面一个色点 ——
    比再写一遍四个产品名更省地方，也顺手把板块色带进图里。
    """
    title_box_w = COVER_TEXT_W if cover else 1000
    title_size = fit_size(title, title_box_w, 268, base=66, floor=38)
    # 副标题与标题同处一栏，所以宽度一起收窄。有封面时正文栏更窄，但纵向
    # 富余（正文区约 300px 高、行高 1.5*23≈35px），放宽字符上限反而更划算 ——
    # 让 clip_sentences 能多收一句完整的话，而不是早早退回半句加省略号。
    sub_size = 25 if not cover else 23
    sub_limit = 96 if cover else 74

    layers = ['<div class="bg"><div class="grid"></div><div class="glow"></div>'
              '<div class="dither"></div></div>']
    if cover:
        layers.append('<div class="cover"><img src="%s%s" alt=""></div>'
                      % (ASSETS, esc(cover)))

    mark = open(os.path.join(ROOT, MARK_SVG), encoding='utf-8').read()
    # 内联进来（600 多字节），省一次本地文件请求 —— file:// 下唯一会出问题的
    # 就是这类子资源
    mark = re.sub(r'<svg([^>]*?)width="[^"]*"\s+height="[^"]*"',
                  r'<svg\1width="52" height="52"', mark, count=1)

    foot_left = '<span class="mono domain">www.poxiaoshi.cn</span>'
    foot_right = '<span class="mono">%s</span>' % esc(meta) if meta else ''

    body = ['<h1 style="font-size:%dpx">%s</h1>' % (title_size, esc(title))]
    if sub:
        body.append('<p style="font-size:%dpx">%s</p>'
                    % (sub_size, esc(clip_sentences(sub, sub_limit))))
    if dots:
        body.append('<ul class="dots">%s</ul>' % ''.join(
            '<li><i style="background:%s"></i>%s</li>' % (esc(c), esc(t)) for t, c in dots))

    return ('''<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>%s</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Geist:wght@300;400;500;600;700&family=Geist+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
%s
.wrap{position:absolute;top:0;left:0;right:0;bottom:0;z-index:2;display:flex;
  flex-direction:column;padding:%dpx;--accent:%s}
/* 有封面时收成两栏：正文栏占左侧，封面独占右侧。
   不这么做的话页头那颗 kicker 会压在封面右上角，而那张区域常常是亮的
   （实测「生态计划」四个字在 NVIDIA 那张卡上几乎看不见）。 */
.wrap--cover{right:auto;width:%dpx}
.cover{position:absolute;top:0;right:0;width:%dpx;height:%dpx;overflow:hidden;z-index:1}
.cover img{width:100%%;height:100%%;object-fit:cover}
.cover::before{content:'';position:absolute;inset:0;
  background:linear-gradient(0deg,%s 0%%,rgba(13,14,16,.72) 20%%,rgba(13,14,16,0) 46%%)}
.cover::after{content:'';position:absolute;inset:0;
  background:linear-gradient(90deg,%s 0%%,%s 16%%,rgba(13,14,16,.72) 46%%,rgba(13,14,16,.14) 82%%,rgba(13,14,16,0) 100%%)}
header{display:flex;align-items:center;justify-content:space-between;gap:24px}
.brand{display:flex;align-items:center;gap:16px}
.brand span{font-size:27px;font-weight:600;letter-spacing:.4px}
.kicker{font-family:%s;font-size:17px;letter-spacing:2.4px;
  color:var(--accent);white-space:nowrap;text-align:right}
.body{flex:1;display:flex;flex-direction:column;justify-content:center;gap:22px;
  %s}
h1{margin:0;font-weight:600;line-height:1.26;letter-spacing:-.4px;
  max-width:1000px;overflow-wrap:break-word;word-break:break-word}
.body p{margin:0;color:rgba(255,255,255,.66);line-height:1.5;max-width:1000px}
.dots{list-style:none;margin:8px 0 0;padding:0;display:flex;flex-wrap:wrap;gap:14px 30px}
.dots li{display:flex;align-items:center;gap:10px;font-size:20px;
  color:rgba(255,255,255,.78)}
.dots i{width:11px;height:11px;border-radius:50%%;display:block}
footer{display:flex;flex-direction:column;gap:20px}
.rule{height:1px;background:linear-gradient(90deg,var(--accent),%s 42%%,transparent)}
.foot{display:flex;align-items:center;justify-content:space-between;gap:24px}
.mono{font-family:%s;font-size:17px;letter-spacing:1.1px;color:%s}
.domain{color:rgba(255,255,255,.82)}
</style></head>
<body>
%s
<div class="wrap%s">
  <header><div class="brand">%s<span>破晓石科技</span></div>
    <div class="kicker">%s</div></header>
  <div class="body">%s</div>
  <footer><div class="rule"></div>
    <div class="foot">%s%s</div></footer>
</div>
</body></html>''' % (
        esc(title), base_css(accent), PAD, esc(accent),
        COVER_TEXT_W + 2 * PAD, COVER_W, OG_H,
        # ::before 的底部遮挡（让页脚那行 mono 字压在图上仍然读得清），
        # 然后是 ::after 的左右渐隐（把封面左缘化进底板）
        PLATE, PLATE, 'rgba(13,14,16,.88)',
        MONO_STACK, cover_clamp(cover),
        LINE, MONO_STACK, LABEL,
        ''.join(layers), ' wrap--cover' if cover else '',
        mark, esc(kicker), ''.join(body),
        foot_left, foot_right))


def cover_clamp(cover):
    """正文栏的最大宽度：有封面时收窄到封面左边，否则让标题用满整幅。"""
    return 'max-width:%dpx;' % (COVER_TEXT_W if cover else 1000)


def base_css(accent):
    """卡片的基础样式。与站内同一套观感：深色底板 + 细网格 + 板块色辉光 + 抖动纹理。"""
    return '''
*{box-sizing:border-box}
html,body{margin:0;padding:0;width:%(w)dpx;height:%(h)dpx;overflow:hidden}
body{background:%(plate)s;color:#fff;font-family:%(sans)s;
  -webkit-font-smoothing:antialiased;text-rendering:geometricPrecision}
.bg{position:absolute;inset:0;z-index:0}
.grid{position:absolute;inset:0;opacity:.5;
  background-image:linear-gradient(90deg,rgba(255,255,255,.045) 1px,transparent 1px),
    linear-gradient(180deg,rgba(255,255,255,.045) 1px,transparent 1px);
  background-size:64px 64px}
.glow{position:absolute;inset:0;
  background:radial-gradient(820px 560px at 8%% -16%%,%(glow)s 0%%,transparent 64%%)}
.dither{position:absolute;inset:0;opacity:.19;
  background:url(%(dither)s) center/cover no-repeat;
  -webkit-mask-image:radial-gradient(120%% 90%% at 50%% 0%%,#000 0%%,transparent 78%%);
  mask-image:radial-gradient(120%% 90%% at 50%% 0%%,#000 0%%,transparent 78%%)}
''' % {'w': OG_W, 'h': OG_H, 'plate': PLATE, 'sans': FONT_STACK,
       'dither': ASSETS + DITHER,
       'glow': hex_alpha(accent, 0.26)}


def hex_alpha(hex_color, alpha):
    """`#9fe9ff` + 0.2 -> `rgba(159,233,255,.2)`。"""
    h = hex_color.lstrip('#')
    if len(h) == 3:
        h = ''.join(c * 2 for c in h)
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return 'rgba(%d,%d,%d,%s)' % (r, g, b, alpha)


def icon_html(size, padding_ratio=0.0):
    """正方形、**透明底**的图标 HTML。Chrome 侧还要配 --default-background-color=0。"""
    mark = open(os.path.join(ROOT, MARK_SVG), encoding='utf-8').read()
    inner = int(size * (1 - padding_ratio))
    mark = re.sub(r'<svg([^>]*?)width="[^"]*"\s+height="[^"]*"',
                  r'<svg\1width="%d" height="%d"' % (inner, inner), mark, count=1)
    # 把 viewBox 收到图形本身的包围盒（横 10..46、纵 6..54）。原始画布 60x60 里
    # 图形并不是居中的 —— 右边留白比左边少 2 个单位，照 60 的画布摆，放大到 512
    # 会有 15px 的偏心，窗口标题栏和书签栏上一眼能看出来。
    mark = mark.replace('viewBox="0 0 60 60"', 'viewBox="10 6 36 48"', 1)
    return ('''<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;width:%dpx;height:%dpx;background:transparent;overflow:hidden}
body{display:flex;align-items:center;justify-content:center}</style></head>
<body>%s</body></html>''' % (size, size, mark))


# ------------------------------------------------------------------ 卡片表
BLOG_ACCENT = '#9fe9ff'


def build_cards():
    """按真实数据算出所有卡片。数据来自**内容的真源**，不是这里另抄一份。

    两个消费方都直接 import 对应的生成器（它们都有 `if __name__` 守卫）：
      build_blog.load_posts()   —— 文章标题/日期/分类/封面，且会校验内容源本身
      build_products.PRODUCTS   —— 产品名/定位/强调色
    这样加了文章或产品，两边自动跟上。
    """
    cards = []

    # 1) 全站默认卡：首页用。四个板块的色点也画在这张上。
    dots = [(('%s %s' % (p['name'], p['sub'])).strip(), resolve_color(p['accent']))
            for p in build_products.PRODUCTS]
    cards.append(dict(
        name='og-default', out=seo.DEFAULT_OG_IMAGE, kind='default',
        html=card_html(
            # 品牌只在左上出现一次（logo 里的字就是「破晓石科技」），所以右上
            # 那颗 kicker 给的是**定位**而不是再把公司名写一遍 —— 同一张图上
            # 同一个名字出现两次，等于浪费了最贵的那块版面。
            kicker='AI 智算平台 · 私有化交付',
            title='Rune Harness 云智算内核',
            # 四个板块名已经在下面那排色点里了，正文不再复述一遍 —— 否则
            # 一行字被 ellipsis() 截成半句，白白浪费一行。
            sub='四大板块共享同一个云智算内核，为企业提供私有化的 AI 智算平台'
                '与云管理能力。',
            accent=BLOG_ACCENT,
            dots=dots,
        ), size=(OG_W, OG_H)))

    # 2) 每篇公司动态一张，带它自己的封面
    for post in build_blog.load_posts():
        cards.append(dict(
            name='blog ' + post['slug'], kind='blog',
            out=seo.og_image('blog', post['slug']),
            html=card_html(
                kicker=post['tag'],
                title=post['title'],
                # 摘要开头的电头（`成都，2026 年 3 月 27 日 —— `）在卡片上没有
                # 信息量，去掉它版面才够说一句完整的话（日期在右下角已经有了）。
                sub=strip_dateline(post['summary']),
                meta=post['date'],
                accent=BLOG_ACCENT,
                cover=post['cover'],
            ), size=(OG_W, OG_H)))

    # 3) 每个产品一张，用该板块的强调色
    for p in build_products.PRODUCTS:
        cards.append(dict(
            name='product ' + p['slug'], kind='product',
            out=seo.og_image('product', p['slug']),
            html=card_html(
                kicker='%s · %s' % (p['name'], p['sub']),
                title=p['title'],
                sub=p['card'],
                accent=resolve_color(p['accent']),
            ), size=(OG_W, OG_H)))

    # 4) 图标。三个尺寸三种用途，都是透明底。
    cards.append(dict(name='favicon', kind='icon', out='assets/img/favicon-96.png',
                      html=icon_html(96, 0.06), size=(96, 96), transparent=True))
    cards.append(dict(name='apple-touch', kind='icon', out='assets/img/apple-touch-icon.png',
                      html=icon_html(180, 0.12), size=(180, 180), transparent=True))
    cards.append(dict(name='org-logo', kind='icon', out=seo.ORG_LOGO,
                      html=icon_html(512, 0.10), size=(512, 512), transparent=True))
    return cards


# ------------------------------------------------------------------ 渲染
def render(card, quiet=False):
    os.makedirs(TMP, exist_ok=True)
    out = os.path.join(ROOT, card['out'])
    os.makedirs(os.path.dirname(out), exist_ok=True)
    html_path = os.path.join(TMP, re.sub(r'[^\w.-]', '_', card['name']) + '.html')
    with open(html_path, 'w', encoding='utf-8') as fh:
        fh.write(card['html'])

    w, h = card['size']
    cmd = [CHROME, '--headless=new', '--no-sandbox', '--disable-gpu',
           '--hide-scrollbars', '--force-device-scale-factor=1',
           '--window-size=%d,%d' % (w, h),
           # 字体是网络请求：不等它就截，拍到的是 fallback 字形
           '--virtual-time-budget=8000',
           '--screenshot=' + out]
    if card.get('transparent'):
        cmd.append('--default-background-color=00000000')
    cmd.append('file://' + html_path)
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    if not os.path.exists(out) or os.path.getsize(out) < 400:
        print('  ! %s 渲染失败' % card['out'])
        print(proc.stdout.decode('utf-8', 'replace')[-800:])
        return False
    if not quiet:
        print('  + %-44s %7d B  %dx%d' % (card['out'], os.path.getsize(out), w, h))
    return True


def png_size(path):
    """从 PNG 头里读真实宽高（IHDR 的字节 16..24）。

    不引第三方库；这也是**独立判据**：卡片声明的尺寸是估算出来的，到底出了多大
    只能量文件本身。OG 卡尺寸不对是会让平台拒收的。
    """
    with open(path, 'rb') as fh:
        head = fh.read(33)
    if head[:8] != b'\x89PNG\r\n\x1a\n' or head[12:16] != b'IHDR':
        return None
    return (int.from_bytes(head[16:20], 'big'), int.from_bytes(head[20:24], 'big'))


def main():
    sys.stdout.reconfigure(line_buffering=True)
    only = None
    if '--only' in sys.argv:
        only = sys.argv[sys.argv.index('--only') + 1]
    listing = '--list' in sys.argv

    cards = build_cards()
    if only:
        cards = [c for c in cards if c['kind'] == only]
    if not cards:
        raise SystemExit('没有匹配的卡片（--only %s）' % only)

    if listing:
        for c in cards:
            print('%-8s %-34s %s' % (c['kind'], c['name'], c['out']))
        return 0

    if not os.path.exists(CHROME):
        raise SystemExit('找不到 Chrome: %s\n（可用环境变量 CHROME 指定，'
                         '或从 tools/qa/cdp.mjs 的 CHROME 常量看它默认在哪）' % CHROME)

    print('渲染 %d 张卡片 -> ' % len(cards), end='')
    print(', '.join(sorted({os.path.dirname(c['out']) or '.' for c in cards})))
    failed = [c['out'] for c in cards if not render(c)]

    # 渲染完按真实像素复核一遍。写死期望值在这里是可以的：尺寸是**这个脚本自己
    # 要求**的（og 卡必须 1200x630），不是从产物里读出来的。
    bad = []
    for c in cards:
        path = os.path.join(ROOT, c['out'])
        if not os.path.exists(path):
            continue
        got = png_size(path)
        if got != c['size']:
            bad.append('%s 实际 %s，期望 %s' % (c['out'], got, c['size']))
    if bad or failed:
        print('\nFAILED:')
        for m in bad:
            print('  !', m)
        for m in failed:
            print('  !', m, '未生成')
        return 1
    print('\nok — %d 张图，尺寸全部复核通过' % len(cards))
    return 0


if __name__ == '__main__':
    sys.exit(main())
