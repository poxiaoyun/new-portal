#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 contact/index.html —— 「关于我们 / 联系我们」页。

样式来源
--------
版式照原站（用户指定的参考站）的 company 组件族，但那套 class 换牌时已经
随 vendor.css 一起搬进本仓库了 —— 第一件事就是 grep vendor.css：
`.tf-company-contact-layout` / `-form` / `-aside` / `-message`、
`.tf-company-form-success` / `-error`、`.tf-company-kicker` / `-section` 全都有规则。
所以这页**不新造版式**，只补 vendor 没覆盖的三块（页首、联系方式行、地图），
见 assets/css/contact.css 的文件头。

内容来源
--------
https://www.poxiaoshi.cn/contact/ ，逐字取自线上页面：
  * 标题「与我们对话未来云与 AI」与副标题（「…团队将在 1 个工作日内回复。欢迎预约
    线下 Workshop 或线上方案评审。」）
  * 表单五个字段（姓名 / 公司 / 邮箱 / 电话 / 需求描述）与各自的 placeholder
  * 联系方式：邮箱 support@xiaoshiai.cn（线上被 Cloudflare 邮箱保护混淆成
    `[email protected]`，解码后取回）、地址、GitHub

线上那页没有地图，地图是本站新增（用户指定用腾讯地图），中心点取旧站
`<meta name="ICBM" content="30.540905, 104.05972">` 里的坐标（GCJ-02）。

两个外部凭据（构建期注入，源码里不留明文）
------------------------------------------
两个都是**前端凭据**：注定出现在产物的 HTML 里，这是设计如此 —— web3forms 靠收件方
校验、腾讯地图靠 key 白名单，不是靠把 key 藏起来。所以它们的纪律是「不进源码」，
而不是「不影响产物」：仓库里存的永远是占位符，真值由 CI 从 GitHub Secret 注入。

* **web3forms**（表单收件）：POST 到 https://api.web3forms.com/submit，需要 access_key。
  环境变量 `WEB3FORMS_ACCESS_KEY`（CI 从 Secret 注入）→ 用真值；
  未设置 → 回落成显式占位符，构建**不失败**，但打一行 WARN，且 submit 会被
  web3forms 拒收 —— 错误显示在 .tf-company-form-error 里，不静默丢单。
* **腾讯地图**（位置）：合规上只能用腾讯 / 高德 / 百度 / 天地图，禁止 Google /
  OSM / Mapbox。需要 key，两种模式见 inject_scripts()：
  环境变量 `TENCENT_MAP_KEY`（CI 从 Secret 注入）→ **直连模式**，SDK 带 `key=`
  参数从官方 CDN 加载，**不挂** `_TMapSecurityConfig`（两者并存会得到一张空白地图）；
  未设置 → **代理模式**，走官方 `_TMapSecurityConfig`，前端零 key，占位符
  `__WB_HTTP_PORT__` / `__WB_TMAP_SECRET__` 由本机预览层替换。
  代理只在本机预览可用；任何模式失败时 contact.js 都会退到降级卡（地址 + 网页版链接）。

本地要用真实凭据预览：把这两行写进仓库根的 `.env.local`（已 gitignore），不必每次
export。优先级是「进程环境变量 > .env.local > 占位符」。注意此时产物里就带真值了 ——
上面说过它本来也不是机密，但别把它当成能随便贴的东西。

站芯复用
--------
外壳（head / nav / 移动抽屉 / footer）从已定稿的 index.html 整篇取来，只换
title / description、追加 contact.css、替换 <main>、加深资源路径 —— 逻辑与守卫
的公共部分在 tools/portal_page.py，与 about/ blog/ 同一套。本页额外做一件事：
在 </body> 前注入地图 SDK 的配置与两个 <script>，见 inject_scripts()。
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from portal_page import (ARROW_S, Ctx, brand_action, code_divider, derive, esc,  # noqa: E402
                         ext, finish, overline, reveal, upstream_brand)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'contact', 'index.html')
OUT_REL = 'contact/index.html'
CONTACT_CSS = 'contact.css'
DEPTH = 1


# ============================================================ 外部凭据（构建期注入）
# 两个都是前端凭据 —— 产物里看得见是设计如此，靠 web3forms 收件方校验 / 腾讯地图
# key 白名单兜底，不是靠保密。纪律是「不进源码」：真值走 GitHub Secret →
# CI 环境变量 → 这里读一次，仓库里存的永远是占位符。
#
#   WEB3FORMS_ACCESS_KEY   web3forms 的 access key（UUID 形态）
#   TENCENT_MAP_KEY        lbs.qq.com 申请的地图 key（形如 AAAA-AAAA-AAAA-AAAA-AAAA-AAAA）
#
# 解析优先级：进程环境变量 > 仓库根 .env.local（gitignore）> 占位符 / 代理模式。
def _dotenv(path):
    """读一个极简 KEY=VALUE 文件。只给本地预览用，不追求完整 dotenv 语法。"""
    values = {}
    if os.path.exists(path):
        for line in open(path, encoding='utf-8'):
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


_LOCAL = _dotenv(os.path.join(ROOT, '.env.local'))


def _credential(name, fallback=''):
    return (os.environ.get(name) or _LOCAL.get(name) or fallback).strip()


WEB3FORMS_KEY = _credential('WEB3FORMS_ACCESS_KEY',
                            'REPLACE_WITH_YOUR_WEB3FORMS_ACCESS_KEY')
TENCENT_MAP_KEY = _credential('TENCENT_MAP_KEY')
WEB3FORMS_ENDPOINT = 'https://api.web3forms.com/submit'


# ============================================================ 内容
COMPANY = {
    'name': '成都破晓石科技有限公司',
    'short': '破晓石科技',
    'mail': 'support@xiaoshiai.cn',
    'address': '四川省成都市高新区银泰悦坊 17 号楼 9 层',
    'github': 'https://github.com/poxiaoyun',
    'github_label': 'github.com/poxiaoyun',
    # 与旧站 <meta name="ICBM"> 一致，GCJ-02
    'lat': '30.540905',
    'lng': '104.05972',
}

HERO_TITLE = '与我们对话未来云与 AI'
HERO_LEAD = ('填写需求表单或通过邮箱与我们联系，团队将在 1 个工作日内回复。'
             '欢迎预约线下 Workshop 或线上方案评审。')

# 表单五个字段，与线上 contact 页逐字一致（含 placeholder）
FIELDS = [
    ('contact-name', 'name', '姓名', 'text', '如：李雷', 'user'),
    ('contact-company', 'company', '公司', 'text', '如：成都破晓石科技有限公司', 'building'),
    ('contact-email', 'email', '邮箱', 'email', 'name@example.com', 'mail'),
    ('contact-phone', 'phone', '电话', 'tel', '如：138****8888', 'phone'),
]
MESSAGE = ('contact-message', 'message', '需求描述', '请描述您的云原生 / AI 相关诉求')

# 三个联系方式：与线上 contact 页同序（邮箱 / 地址 / GitHub）
CHANNELS = [
    ('Email', COMPANY['mail'], 'mailto:' + COMPANY['mail'], 'mail'),
    ('GitHub', COMPANY['github_label'], COMPANY['github'], 'github'),
    ('地址', COMPANY['address'], None, 'pin'),
]

_LUCIDE_OPEN = ('<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" '
                'viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" '
                'stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">')
ICONS = {
    'user': '<path d="M19 21v-2a4 4 0 0 0-4-4H9a4 4 0 0 0-4 4v2"/>'
            '<circle cx="12" cy="7" r="4"/>',
    'building': '<path d="M3 21h18"/><path d="M5 21V6l7-3.5L19 6v15"/>'
                '<path d="M9.5 21v-4.5h5V21"/>',
    'mail': '<rect x="2" y="4.5" width="20" height="15" rx="2"/>'
            '<path d="m22 7-10 6L2 7"/>',
    'phone': '<path d="M22 16.9v3a2 2 0 0 1-2.2 2 19.8 19.8 0 0 1-8.6-3.1 '
             '19.5 19.5 0 0 1-6-6A19.8 19.8 0 0 1 2.1 4.2 2 2 0 0 1 4.1 2h3a2 2 0 0 1 2 1.7 '
             '12.8 12.8 0 0 0 .7 2.8 2 2 0 0 1-.5 2.1L8.1 9.9a16 16 0 0 0 6 6l1.3-1.3'
             'a2 2 0 0 1 2.1-.4 12.8 12.8 0 0 0 2.8.7A2 2 0 0 1 22 16.9z"/>',
    'message': '<path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>',
    'pin': '<path d="M20 10c0 6-8 12-8 12s-8-6-8-12a8 8 0 0 1 16 0z"/>'
           '<circle cx="12" cy="10" r="3"/>',
    'github': '<path d="M15 22v-4a4.8 4.8 0 0 0-1-3.5c3 0 6-2 6-5.5.1-1.3-.3-2.5-1-3.5'
              '.3-1.2.3-2.4 0-3.5 0 0-1 0-3 1.5a13.4 13.4 0 0 0-8 0C6 2 5 2 5 2'
              'c-.3 1.2-.3 2.4 0 3.5A5.4 5.4 0 0 0 4 9c0 3.5 3 5.5 6 5.5'
              '-.4.5-.7 1-.9 1.7-.2.6-.2 1.2-.1 1.8v4"/>'
              '<path d="M9 18c-4.5 2-5-2-7-2"/>',
    'compass': '<circle cx="12" cy="12" r="10"/><path d="m16.2 7.8-2.3 6.1-6.1 2.3 '
               '2.3-6.1z"/>',
}


def icon(name):
    return _LUCIDE_OPEN + ICONS[name] + '</svg>'


# ============================================================ 板块渲染
def hero():
    """页首。与 about 页的 .tf-about-hero 同一套语言（径向光晕 + 居中标题 + 快捷键），
    is-motion-visible 直接写在 section 上 —— 首屏不该等 IntersectionObserver。"""
    chips = (
        '<div class="tf-contact-hero-chips">'
        '<a href="mailto:%s">%s%s</a>'
        '<span>%s成都 · 高新区</span>'
        '<a href="%s"%s>%s%s</a></div>'
        % (COMPANY['mail'], icon('mail'), esc(COMPANY['mail']),
           icon('pin'),
           COMPANY['github'], ext(COMPANY['github']), icon('github'), COMPANY['github_label']))
    # 同 about 页：垂直间距交给 contact.css 的 `.tf-contact-hero`，不写在这串类名里
    # —— vendor.css 里没有 pt-4 / pb-16 / md:pb-20，写了等于没写（见 qa/classes.py）。
    return (
        '<section class="tf-contact-hero tf-motion-section is-motion-visible px-6 '
        'md:px-8 lg:px-20" style="--tf-motion-order: 0;">'
        + reveal(
            '<div class="mx-auto flex max-w-[920px] flex-col items-center text-center">'
            + overline('联系我们_')
            + '<h1 class="mt-6 max-w-[1080px] text-[3.1rem] font-semibold leading-[0.98] '
              'tracking-[-0.04em] text-white md:text-[4.65rem] lg:text-[4.55rem] '
              'lg:leading-[1.02] xl:text-[4.85rem]">'
              '<span class="block">' + HERO_TITLE + '</span></h1>'
            + '<p class="mt-5 max-w-[760px] text-base leading-8 text-white/62 md:text-lg">'
            + HERO_LEAD + '</p>'
            + chips
            + '</div>', delay=0.05)
        + '</section>')


def _field(fid, name, label, kind, placeholder, ic):
    return ('<label for="%s">%s'
            '<input id="%s" name="%s" type="%s" aria-label="%s" '
            'placeholder="%s" autocomplete="off" required></label>'
            % (fid, icon(ic), fid, name, kind, esc(label), esc(placeholder)))


def contact_board(order):
    """表单 + 联系方式。骨架全部来自 vendor 的 .tf-company-contact-layout
    （`grid-template-columns: minmax(0,1.35fr) minmax(18rem,.65fr)`）。"""
    fields = ''.join(_field(*f) for f in FIELDS)
    fid, name, label, placeholder = MESSAGE
    fields += ('<label class="tf-company-contact-message" for="%s">%s'
               '<textarea id="%s" name="%s" rows="3" aria-label="%s" '
               'placeholder="%s" required></textarea></label>'
               % (fid, icon('message'), fid, name, esc(label), esc(placeholder)))

    # 蜜罐：web3forms 的标准反垃圾字段，靠 CSS 挪到视口外（见 vendor 的
    # .tf-company-contact-form .tf-contact-honeypot）。放在最末，这样第一个
    # 可见的 <label> 才是 :first-of-type，能吃到 vendor 给它的 1.55rem 上边距。
    honeypot = ('<label class="tf-contact-honeypot" aria-hidden="true">'
                '<input type="checkbox" name="botcheck" tabindex="-1" '
                'autocomplete="off"></label>')

    form = (
        '<form class="tf-company-contact-form" action="%s" method="POST" novalidate>'
        '<input type="hidden" name="access_key" value="%s">'
        '<input type="hidden" name="subject" value="官网联系表单 · %s">'
        '<input type="hidden" name="from_name" value="%s 联系我们">'
        '%s'
        '<p class="tf-company-form-error" hidden></p>'
        '<p class="tf-company-form-success" hidden></p>'
        '<button type="submit">提交需求 %s</button>%s</form>'
        % (WEB3FORMS_ENDPOINT, WEB3FORMS_KEY, COMPANY['short'], COMPANY['short'],
           fields, ARROW_S, honeypot))

    items = ''
    for title, value, href, ic in CHANNELS:
        body = ('<a href="%s"%s>%s</a>' % (href, ext(href), esc(value))
                if href else '<span>%s</span>' % esc(value))
        items += ('<li>%s<div><b>%s</b>%s</div></li>' % (icon(ic), esc(title), body))

    aside = (
        '<aside class="tf-company-contact-aside">'
        '<span class="tf-company-kicker">联系方式_</span>'
        '<h2>也可以直接找到我们。</h2>'
        '<span>工作时间内提交的需求，我们会在 1 个工作日内回复。'
        '需要方案评审或 PoC 演示，请在需求描述里注明期望的时间窗口。</span>'
        '<ul class="tf-contact-channels">%s</ul></aside>' % items)

    return (
        '<section id="reach" class="tf-company-section tf-motion-section" '
        'style="--tf-motion-order: %d;">'
        '<div class="tf-company-contact-layout">%s%s</div></section>' % (order, form, aside))


def map_board(order):
    """位置地图。腾讯地图 GL JS 需要容器有确定高度（见 contact.css 的
    .tf-contact-map），SDK 的配置与两个 <script> 由 inject_scripts() 加在
    </body> 前。"""
    fallback = (
        '<div class="tf-contact-map-fallback" hidden>'
        '<p><b>%s</b>%s</p>'
        '<a class="tf-brand-action tf-button tf-button-secondary" data-map-link '
        'href="https://map.qq.com/"%s>在腾讯地图中打开 %s</a></div>'
        % (esc(COMPANY['name']), esc(COMPANY['address']),
           ext('https://map.qq.com/'), ARROW_S))
    return (
        '<section id="visit" class="tf-contact-map-section tf-motion-section" '
        'style="--tf-motion-order: %d;">'
        '<div class="tf-contact-map-head">%s'
        '<h2>成都 · 高新区银泰悦坊</h2>'
        '<p>%s</p></div>'
        '<div class="tf-contact-map" id="contact-map" role="region" '
        'aria-label="%s位置地图"></div>%s</section>'
        % (order, overline('到访我们_'), esc(COMPANY['address']),
           esc(COMPANY['short']), fallback))


def main_markup():
    divider = code_divider('https://api.poxiaoshi.cn/contact', 1)
    return (hero()
            + divider
            + contact_board(2)
            + divider
            + map_board(3))


# ============================================================ 地图 SDK 注入
def inject_scripts(doc, ctx):
    """在 </body> 前注入腾讯地图的配置与两个 <script>。

    两种模式，由 TENCENT_MAP_KEY 决定：

    * **直连**（线上）：SDK 带 `key=` 参数。此时**不能**有 `_TMapSecurityConfig`
      —— 它和 key 参数同时用会得到一张空白地图。
    * **代理**（本机预览）：`_TMapSecurityConfig` 必须在 SDK 之前，SDK **不带**
      key 参数。`__WB_HTTP_PORT__` / `__WB_TMAP_SECRET__` 是运行时占位符，
      **必须原样保留**，不要在这里替换成具体值。

    contact.js 两种模式都排在 SDK 之后，它靠 defer 的文档顺序拿到 window.TMap。
    """
    marker = '</body>'
    if marker not in doc:
        ctx.miss.append('</body> not found, cannot inject the map scripts')
        return doc
    prefix = '../' * DEPTH
    if TENCENT_MAP_KEY:
        comment = (
            '  /* 合规：只用腾讯地图（禁止 Google / OSM / Mapbox），坐标 GCJ-02。\n'
            '     key 由构建期注入（GitHub Secret -> TENCENT_MAP_KEY），源码里不留明文。 */\n')
        sdk = ('<script src="https://map.qq.com/api/gljs?v=1.exp&key=%s" defer\n'
               '        onerror="window.__TF_TMAP_FAILED__=true"></script>\n' % TENCENT_MAP_KEY)
        mode = 'direct'
    else:
        comment = (
            '  /* 合规：只用腾讯地图（禁止 Google / OSM / Mapbox），坐标 GCJ-02。\n'
            '     本机预览走官方 key 代理 —— 前端零 key，SDK 不带 key 参数。\n'
            '     这两个占位符由 WorkBuddy 运行时替换，勿改。 */\n')
        sdk = (
            '<script type="text/javascript">\n'
            '  window._TMapSecurityConfig = {\n'
            "    serviceHost: 'http://127.0.0.1:__WB_HTTP_PORT__/_TMapService/_wbt/__WB_TMAP_SECRET__'\n"
            '  };\n'
            '</script>\n'
            '<script src="https://map.qq.com/api/gljs?v=1.exp" defer\n'
            '        onerror="window.__TF_TMAP_FAILED__=true"></script>\n')
        mode = 'proxy'
    block = ('\n<script type="text/javascript">\n' + comment + '</script>\n'
             + sdk
             + '<script src="%sassets/js/contact.js" defer></script>\n' % prefix)
    doc = doc.replace(marker, block + marker, 1)
    ctx.applied['map scripts injected (%s mode, %sassets/js/contact.js)'
                % (mode, prefix)] = 1
    return doc


# ============================================================ 装配
def main():
    ctx = Ctx()
    doc, home, home_md5 = derive(
        ctx,
        out_rel=OUT_REL,
        title='联系我们 | ' + COMPANY['short'],
        description='联系成都破晓石科技团队，预约演示、产品咨询、PoC 方案评审或项目合作。',
        extra_css=CONTACT_CSS,
        main_markup=main_markup(),
        main_label='main body -> 联系我们板块',
        nav_label='nav active state -> 关于我们',
    )
    doc = inject_scripts(doc, ctx)

    # ------------------------------------------------------- 本页专属守卫
    # 表单：字段数、收件凭据、反垃圾字段、提交出口
    for fid, _n, _l, _k, _p, _i in FIELDS:
        if 'id="%s"' % fid not in doc:
            ctx.miss.append('form field missing: ' + fid)
    if 'id="contact-message"' not in doc:
        ctx.miss.append('form textarea missing: contact-message')
    if doc.count('class="tf-company-contact-form"') != 1:
        ctx.miss.append('expected exactly one .tf-company-contact-form, got %d'
                        % doc.count('class="tf-company-contact-form"'))
    if 'action="%s"' % WEB3FORMS_ENDPOINT not in doc:
        ctx.miss.append('web3forms endpoint missing')
    if 'name="access_key" value="%s"' % WEB3FORMS_KEY not in doc:
        ctx.miss.append('web3forms access_key field missing')
    if 'name="botcheck"' not in doc:
        ctx.miss.append('web3forms honeypot (botcheck) missing')
    if doc.count('type="hidden" name=') != 3:
        ctx.miss.append('expected three hidden web3forms inputs, got %d'
                        % doc.count('type="hidden" name='))
    # 结果槽位必须两个都在：只留一个的话失败信息会没处落，静默丢单
    for slot in ('tf-company-form-success', 'tf-company-form-error'):
        if 'class="%s"' % slot not in doc:
            ctx.miss.append('result slot missing in markup: ' + slot)
    # 联系方式三条
    for _t, value, _h, _i in CHANNELS:
        if esc(value) not in doc:
            ctx.miss.append('contact channel missing: ' + value)

    # 地图：容器、降级卡、SDK 注入、模式互斥、合规红线
    if 'id="contact-map"' not in doc:
        ctx.miss.append('map container missing')
    if 'class="tf-contact-map-fallback"' not in doc:
        ctx.miss.append('map fallback card missing')
    if TENCENT_MAP_KEY:
        if 'key=%s' % TENCENT_MAP_KEY not in doc:
            ctx.miss.append('direct map mode lost the key parameter')
        if '_TMapSecurityConfig' in doc:
            ctx.miss.append('_TMapSecurityConfig must not coexist with a key parameter '
                            '(both together blank the map)')
        if '__WB_TMAP_SECRET__' in doc or '__WB_HTTP_PORT__' in doc:
            ctx.miss.append('proxy placeholder leaked into direct map mode')
    else:
        if '__WB_TMAP_SECRET__' not in doc or '__WB_HTTP_PORT__' not in doc:
            ctx.miss.append('TMap proxy placeholders were altered (they must stay verbatim)')
        if 'window._TMapSecurityConfig' not in doc:
            ctx.miss.append('proxy map mode lost _TMapSecurityConfig')
        if re.search(r'map\.qq\.com/api/gljs[^"\']*key=', doc):
            ctx.miss.append('proxy map mode must not carry a key parameter')
    if 'src="https://map.qq.com/api/gljs' not in doc:
        ctx.miss.append('TMap GL JS not loaded from the official CDN')
    # 合规硬线：禁止的服务商一个都不能出现在**资源引用**里。
    # 只看 src / href 的属性值，不看全文 —— 注入的那段脚本注释里就写着
    # 「禁止 Google / OSM / Mapbox」，全文匹配会被自己的说明文字咬到。
    for url in re.findall(r'(?:src|href)="([^"]+)"', doc):
        low = url.lower()
        for banned in ('googleapis.com/maps', 'maps.google', 'google.com/maps',
                       'openstreetmap', 'mapbox', 'leaflet', 'apple.com/maps',
                       'bing.com/maps'):
            if banned in low:
                ctx.miss.append('non-compliant map provider reference: %s in %s'
                                % (banned, url[:80]))
    sdk = re.search(r'<script src="(https://map\.qq\.com/api/gljs[^"]*)"', doc)
    if not sdk:
        ctx.miss.append('TMap SDK tag not found for the key check')
    elif TENCENT_MAP_KEY:
        if 'key=%s' % TENCENT_MAP_KEY not in sdk.group(1):
            ctx.miss.append('direct map mode: the SDK URL must carry the injected key')
    elif 'key=' in sdk.group(1):
        ctx.miss.append('proxy map mode: the SDK URL must not carry a key parameter')
    if 'mapStyleId' in doc:
        ctx.miss.append('mapStyleId must not be set (custom styles are not on the default key)')
    # 坐标：GCJ-02，与旧站 ICBM meta 同源
    js = open(os.path.join(ROOT, 'assets', 'js', 'contact.js'), encoding='utf-8').read()
    if COMPANY['lat'] not in js or COMPANY['lng'] not in js:
        ctx.miss.append('contact.js lost the office coordinates (%s, %s)'
                        % (COMPANY['lat'], COMPANY['lng']))
    if 'new TMap.Map(' not in js:
        ctx.miss.append('contact.js no longer constructs a TMap.Map')
    if 'contact-map' not in js:
        ctx.miss.append('contact.js no longer targets the #contact-map container')

    # 章节顺序：hero < 表单 < 地图 < footer
    order = ['tf-contact-hero', 'id="reach"', 'id="visit"', 'tf-reference-footer']
    pos = [doc.find(x) for x in order]
    if -1 in pos:
        ctx.miss.append('section order anchor missing: '
                        + ', '.join(x for x, p in zip(order, pos) if p < 0))
    elif pos != sorted(pos):
        ctx.miss.append('sections are out of order: ' + str(list(zip(order, pos))))
    # 站内不该出现的旧品牌 / 上游残留
    for leftover in ('src="assets/', 'ant-form', 'ant-btn'):
        if leftover in doc:
            ctx.miss.append('leftover / bad path: ' + leftover)
    if upstream_brand(doc):
        ctx.miss.append('leftover: 上游品牌名')

    # 凭据状态：缺失只 WARN 不失败 —— 本机没有 Secret 是常态，页面照常可预览。
    # 缺 web3forms key 是「表单收不到」而不是「页面坏」；缺地图 key 只是退到降级卡。
    if WEB3FORMS_KEY.startswith('REPLACE_WITH_'):
        print('WARN: web3forms access_key 未注入（当前是占位符）。')
        print('      表单能渲染、能提交，但 web3forms 会拒收。真值来源：')
        print('        GitHub Secret WEB3FORMS_ACCESS_KEY（CI 部署时自动注入），')
        print('        或本地 .env.local 里的 WEB3FORMS_ACCESS_KEY=...')
    if not TENCENT_MAP_KEY:
        print('WARN: TENCENT_MAP_KEY 未注入，地图走「代理模式」占位符。')
        print('      代理只在本机预览可用，线上会走降级卡。真值来源：')
        print('        GitHub Secret TENCENT_MAP_KEY（CI 部署时自动注入），')
        print('        或本地 .env.local 里的 TENCENT_MAP_KEY=...')

    finish(ctx, doc, OUT, OUT_REL, len(home), home_md5)


if __name__ == '__main__':
    main()
