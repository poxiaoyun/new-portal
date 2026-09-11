#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 404.html —— 全站兜底页 + 旧地址兼容层。

为什么它值得有个生成器
----------------------
一般站点的 404 页是手写一次的静态文件，写完就没人再看。这一页不行，它承担两件事，
而两件事都要求它**跟着站芯走**：

1. **兜底页**。GitHub Pages 在任意未命中的路径上返回它。进错页的人看到的仍然是
   完整的导航与页脚，才有路可走 —— 所以它必须与首页共用同一份 nav / 抽屉 / 页脚。
   手写就等于把这段标记抄了第二遍，首页改了导航它不会跟。

2. **旧地址兼容层**。域名从项目页换成 www.poxiaoshi.cn 后，站点根从 `/new-portal/`
   变成了域名根，此前按 `/new-portal/xxx` 收下的地址全部失效（2026-09-11 用户报的
   就是这一类）。修法是把前缀剥掉再跳转 —— **落在 404 页上**，因为它是唯一一个
   「所有不存在的地址都会经过」的页面，一处改动即覆盖 contact / products/rune /
   blog/… 全部子页面，不需要为每页各维护一份兼容逻辑。

   这段脚本**只在域名根部署时生成**：站点发布在子路径时（项目页 /<repo>/），
   `/new-portal/xxx` 本身就是合法地址，剥前缀反而是把正确的 URL 改坏。取值来自
   环境变量 SITE_BASE（与 workflow 里注入前缀用的是同一个变量），所以两种部署
   形态各拿一份自洽的产物。

   之所以要按 SITE_BASE 分叉而不是「反正剥一下也无害」：子路径部署下，
   /new-portal/about 会被改写成 /about，而 /about 在那个部署里根本不存在 ——
   等于把 404 换成另一个 404。

站芯复用
--------
外壳从已定稿的 index.html 整篇取来（`tools/portal_page.py` 的 derive()），
本页深度是 0（产物就在站点根），所以资产路径保持 `assets/…` 不加 `../`。
导航选中态传 `active_group=None` —— 这个页面不归属任何导航组，挂在「关于我们」
或任何一个组下面都是假信息。
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from portal_page import Ctx, brand_action, derive, esc, ext, finish, upstream_brand  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, '404.html')
OUT_REL = '404.html'
PAGE_CSS = '404.css'

# 域名根部署时要剥掉的历史前缀。改这个常量前先想清楚：它描述的是**过去**的部署
# 形态，不是现在的 —— 现在的形态由 SITE_BASE 表达。
LEGACY_PREFIX = '/new-portal'

HOME_URL = '/'
CONTACT_PAGE = '/contact'

# 「站内入口」清单。这是全页唯一一张会变的表：新增产品页/内容页时加一行，
# 下面的守卫会用 len() 咬住条数，漏加会报错而不是静默少一格。
SUGGEST = [
    ('/', '首页', 'Home'),
    ('/products/rune/', 'Rune 智算', 'Product'),
    ('/products/moha/', 'Moha 资产', 'Product'),
    ('/products/ai-router/', 'AIRouter AI 聚合网关', 'Product'),
    ('/products/boss/', 'BOSS 运营', 'Product'),
    ('/about', '关于我们', 'Company'),
    ('/blog', '公司动态', 'Blog'),
    ('/contact', '联系我们', 'Contact'),
]


def legacy_redirect_script(base):
    """旧前缀剥除脚本。base 非空（子路径部署）时返回空串 —— 见模块注释。"""
    if base:
        return ''
    return (
        '<script>\n'
        '/* 旧地址兼容层：站点曾发布在 %s/ 子路径下，那批地址在域名根部署里\n'
        '   不存在。剥掉前缀再跳转，让此前收下的链接继续可用。\n'
        '   放在 head 里是为了在首屏绘制之前就跳走 —— 放进 body 会闪一下 404。 */\n'
        '(function () {\n'
        '  var LEGACY = "%s", p = location.pathname;\n'
        '  if (p.indexOf(LEGACY) === 0 &&\n'
        '      (p.length === LEGACY.length || p.charAt(LEGACY.length) === "/")) {\n'
        '    location.replace((p.slice(LEGACY.length) || "/") + location.search + location.hash);\n'
        '  }\n'
        '})();\n'
        '</script>'
        % (LEGACY_PREFIX, LEGACY_PREFIX))


# ============================================================ 板块
def hero():
    # is-motion-visible 直接写在 section 上：首屏不该等 IntersectionObserver 才显形。
    # 工具类逐条抄自 about 页的 hero（那边的组合已被 classes.py 验过存在于
    # vendor.css）；垂直间距写在 404.css 里，不写进类名。
    return (
        '<section class="tf-404-hero tf-motion-section is-motion-visible px-6 '
        'md:px-8 lg:px-20" style="--tf-motion-order: 0;">'
        '<div class="mx-auto flex max-w-[920px] flex-col items-center text-center">'
        '<p class="tf-404-code" aria-hidden="true">404</p>'
        '<h1 class="mt-6 max-w-[1080px] text-[3.1rem] font-semibold leading-[0.98] '
        'tracking-[-0.04em] text-white md:text-[4.65rem] lg:text-[4.55rem] '
        'lg:leading-[1.02] xl:text-[4.85rem]">'
        '<span class="block">这个页面不存在。</span></h1>'
        '<p class="mt-5 max-w-[760px] text-base leading-8 text-white/62 md:text-lg">'
        '地址可能拼错了，或者这个页面已经搬走。'
        '下面几个入口，从哪儿进来的都能走回去。</p>'
        '<div class="mt-7 flex flex-wrap items-center justify-center gap-3">'
        + brand_action('回到首页', HOME_URL)
        + brand_action('联系我们', CONTACT_PAGE, 'secondary')
        + '</div>'
        '<p class="tf-404-hero-meta">'
        '<span>HTTP 404</span><i aria-hidden="true"></i>'
        '<span>Page Not Found</span><i aria-hidden="true"></i>'
        '<span>破晓石科技</span></p>'
        '</div></section>')


def suggest():
    items = ''.join(
        '<li><a class="tf-404-link" href="%s"%s><b>%s</b><span>%s</span></a></li>'
        % (href, ext(href), esc(label), esc(tag))
        for href, label, tag in SUGGEST)
    return (
        '<section class="tf-404-suggest tf-motion-section" style="--tf-motion-order: 1;">'
        '<div class="tf-404-suggest-inner">'
        '<p class="tf-404-suggest-head">站内入口</p>'
        '<ul class="tf-404-links" aria-label="站内主要入口">%s</ul>'
        '</div></section>' % items)


def main_markup():
    return hero() + suggest()


# ============================================================ 装配
def main():
    base = os.environ.get('SITE_BASE', '').strip().rstrip('/')
    ctx = Ctx()
    doc, home, home_md5 = derive(
        ctx,
        out_rel=OUT_REL,
        title='页面不存在 | 破晓石科技',
        description='这个页面不存在。可以回到首页，或从站内入口继续浏览 Rune、'
                    'Moha、AIRouter、BOSS 与公司动态。',
        extra_css=PAGE_CSS,
        main_markup=main_markup(),
        active_group=None,          # 不属于任何导航组
        main_label='main body -> 404 兜底页',
        nav_label='nav active state -> 不归属任何组',
        depth=0,                    # 产物就在站点根
    )

    # head 里插旧地址兼容层。**放在 derive() 之后**：chrome_fingerprint() 逐字节比对
    # head，先插会被判成「站芯漂移」。插完自己再验一次位置，别假定标签找得到。
    script = legacy_redirect_script(base)
    if script:
        m = re.search(r'<head\b[^>]*>', doc)
        if not m:
            ctx.miss.append('<head> not found for the legacy redirect')
        else:
            doc = doc[:m.end()] + script + doc[m.end():]
            head_end = doc.find('</head>')
            if script not in doc[:head_end]:
                ctx.miss.append('legacy redirect did not land inside <head>')
            ctx.applied['legacy /new-portal redirect (%s)' % LEGACY_PREFIX] = 1
    else:
        ctx.applied['legacy redirect: skipped (SITE_BASE=%r，站点在子路径)' % base] = 1

    # ------------------------------------------------------- 本页专属守卫
    # 入口清单条数：漏加一格是「页面上少一个入口」，不会报错，所以按绝对数咬。
    if len(SUGGEST) != 8:
        ctx.miss.append('SUGGEST: %d entries, expected 8' % len(SUGGEST))
    got = doc.count('class="tf-404-link"')
    if got != len(SUGGEST):
        ctx.miss.append('tf-404-link: got %d, want %d' % (got, len(SUGGEST)))
    for href, label, _tag in SUGGEST:
        if 'href="%s"' % href not in doc:
            ctx.miss.append('entry missing from the 404 page: %s (%s)' % (href, label))
    # 两个按钮的落点写死（不拿 SUGGEST 去推——那会与数据同源，等于没断言）
    for want in (HOME_URL, CONTACT_PAGE):
        if 'href="%s" class="tf-brand-action' % want not in doc:
            ctx.miss.append('404 page lost its %s button' % want)
    # 导航不该有任何选中态：这一页不属于任何组
    if 'tf-nav-menu-link is-active' in doc:
        ctx.miss.append('404 page must not highlight a nav group')
    # 板块顺序：hero < 入口清单 < 页脚
    order = ['tf-404-hero', 'tf-404-suggest', 'tf-reference-footer']
    pos = [doc.find(x) for x in order]
    if -1 in pos:
        ctx.miss.append('section order anchor missing: '
                        + ', '.join(x for x, p in zip(order, pos) if p < 0))
    elif pos != sorted(pos):
        ctx.miss.append('sections are out of order: ' + str(list(zip(order, pos))))
    # 旧前缀脚本在两个方向上都咬：该有的时候必须有，不该有的时候必须没有。
    # 只查一个方向的话，另一种部署形态下会静默地带着一段错误的跳转上线。
    has_script = 'LEGACY = "%s"' % LEGACY_PREFIX in doc
    if base and has_script:
        ctx.miss.append('SITE_BASE=%r 是子路径部署，不该生成剥前缀脚本（会把合法 '
                        'URL 改写成另一个 404）' % base)
    if not base and not has_script:
        ctx.miss.append('域名根部署下缺少 /new-portal 兼容跳转 —— 那批旧地址会全 404')
    # 深度 0：资源引用必须是 `assets/…`，带 `../` 就是多了一层（404）
    if re.search(r'(?:src|href)="\.\./', doc):
        ctx.miss.append('depth=0 页面上出现了 ../ 前缀 —— 资源会 404')
    # 旧品牌 / 上游残留（与 about 页同一份清单，两页都从线上换牌而来）
    for leftover in ('api.example.com', 'Building AI Infrastructure', 'Loki Wong',
                     'Nia Park', 'WE ARE HIRING'):
        if leftover in doc:
            ctx.miss.append('leftover: ' + leftover)
    if upstream_brand(doc):
        ctx.miss.append('leftover: 上游品牌名')
    # 装饰性的大号 404 是本页唯一的视觉锚点，掉了页面就只剩一行标题
    if doc.count('class="tf-404-code"') != 1:
        ctx.miss.append('the decorative 404 numeral should appear exactly once')

    finish(ctx, doc, OUT, OUT_REL, len(home), home_md5)


if __name__ == '__main__':
    main()
