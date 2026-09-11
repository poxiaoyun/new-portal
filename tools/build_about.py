#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 about/index.html —— 「关于我们 / 公司简介」页。

设计取舍
--------
原站（换牌前的那套模板，下同）的 about 页正文是一段 Webflow 片段（113 KB）
加一份 538 KB 的 Webflow 样式表，两者用的是
`page-wrapper` / `section-container` / `w-variant-<uuid>` 这套命名。直接把它们
搬进来等于在本站里并存第二套设计系统：多 650 KB 资源、多一套命名、多一份要跟着
上游演进的维护面。

所以这里只借原站 about 页的**版式语言**（Hero + 编号特性列表 + 关键数字带 +
团队卡与招聘条 + 荣誉网格 + 历程节点 + 收尾 CTA，区块之间用 code divider 分隔），
实现落在本站已有的 `.tf-section-*` 骨架与 `--tf-*` 调色板上。首页的那套皮肤本来
就是对原站首页换牌来的，两者同源，所以关于页放进站内是同一个视觉家族。

站芯复用
--------
外壳（`<head>` / nav / 移动抽屉 / footer / 脚本）不重写，而是从已经生成好的
`index.html` 里整篇取来，只换 head 的 title / description、追加 about.css、
替换 `<main>` 内容、把资产路径加深一级。这套派生逻辑与守卫的公共部分在
`tools/portal_page.py`（同一套也给 blog 页用）。导航与页脚因此永远和首页一致；
首页改了导航，重跑本脚本即可同步，不需要在两处改同一段标记。

内容来源
--------
https://www.poxiaoshi.cn/about/ ，逐字取自线上页面。四处轻微编辑：
  * 发展历程 2023 线上原文是「成立破晓石公司成立。」，重复了「成立」，改为
    「破晓石公司成立。」
  * 三个特色卡只有两张有线上原文（使命与愿景 / 开源生态），第三张
    「全栈自研与信创兼容」的正文取自本站首页 FAQ 02 已发布的表述
  * 荣誉计数写「16 张证书」（线上原文说「荣誉星环」，实际是 16 张软著证书；
    侧栏「关键数字」已用「项软件著作权」，同页不重复同措辞）
  * 特色列表表头由「三个立足点」改为「技术选型的三把尺子」（原表头与侧栏
    overline 重复）
四处都在汇报里标注，方便回退。
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from portal_page import (ARROW_S, Ctx, brand_action, code_divider, derive, esc, ext,  # noqa: E402
                         finish, overline, reveal, upstream_brand)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT = os.path.join(ROOT, 'about', 'index.html')
OUT_REL = 'about/index.html'
ABOUT_CSS = 'about.css'


# ============================================================ 板块外壳
def board(sid, order, overline_text, title, copy, body, panel=None, split=True):
    """一个板块外壳。有 panel 时走首页那套左右分栏（侧栏吸顶），否则整宽。

    骨架类名与首页一致（.tf-section / .tf-section-inner / .tf-section-frame /
    .tf-section-split / .tf-section-sidebar），样式全部来自 vendor.css。
    """
    sidebar = (
        '<div class="tf-section-sidebar">%s'
        '<h2 class="tf-section-title mt-5">%s</h2>'
        '<p class="tf-section-copy">%s</p></div>'
        % (overline(overline_text), esc(title), copy))
    if split and panel:
        inner = '<div class="tf-section-split">%s%s</div>' % (sidebar, panel)
    else:
        inner = ('<div class="tf-section-heading">%s'
                 '<h2 class="tf-section-title mt-5">%s</h2>'
                 '<p class="tf-section-copy">%s</p></div>%s'
                 % (overline(overline_text), esc(title), copy, body))
        body = ''
    return (
        '<section id="%s" class="tf-section scroll-mt-[90px] text-white tf-motion-section" '
        'style="--tf-motion-order: %d;">'
        '<div class="tf-section-inner tf-section-frame">%s%s</div></section>'
        % (sid, order, inner, body))


# ============================================================ 内容
COMPANY = {
    'name': '成都破晓石科技有限公司',
    'short': '破晓石科技',
    'slogan': '原生无界 · 破晓时刻',
    'address': '四川省成都市高新区银泰悦坊17号楼9层',
    'mail': 'support@xiaoshiai.cn',
    'intro': '成都破晓石科技有限公司致力于云原生、开源产品与 AI 智算平台的自主研发。'
             '我们为企业提供覆盖容器云、混合云、AI 智算云及 AI 能力应用的全栈解决方案。',
}

# 产品总览的落点。以前这个常量叫 PRODUCTS_URL，值指旧站的 `products/` 首页 ——
# 而旧站正是本站在替换的东西，2026-09-11 晚随「全站不再指向旧站」一起收回站内首页。
# 名字也一起改了：它现在指的是首页，再叫 PRODUCTS_URL 会让人以为站内真有 products/ 页。
HOME_URL = '/'
DOCS_URL = 'https://docs.poxiaoshi.cn'
GITHUB_URL = 'https://github.com/kubegems'

# 商务落点。2026-09-11 晚（十三）用户要求「预约演示 / 联系我们 / 进入控制台」全站
# 一律跳 /contact：本页那两处 `brand_action('联系我们', …)` 原本是 `mailto:`，
# 现在跟着改 —— 站内有了联系页，邮件按钮就该让位给它（联系页上也照旧列出邮箱，
# 想发邮件的人不会被挡住）。公司邮箱本身仍出现在正文与收尾 CTA 的文本里，那是信息，
# 不是入口。
CONTACT_PAGE = '/contact'

# 三张特色卡。前两张逐字来自线上 about 页，第三张复用首页 FAQ 02 的既有表述。
PILLARS = [
    ('01', '使命与愿景', '以云原生为统一基座，打造面向未来的 AI 原生基础设施。',
     [('使命', '让企业以最短路径拥抱云原生与 AI。'),
      ('愿景', '成为企业数智化进程中的长期技术伙伴。')]),
    ('02', '开源生态', 'KubeGems 等自研开源项目已在多个行业落地，构建完善的社区、培训与联合创新机制。',
     [('开源', 'KubeGems 容器云平台与社区生态持续演进。'),
      ('协作', '社区、培训与联合创新机制一并开放。')]),
    ('03', '全栈自研与信创兼容', '平台全栈采用 Golang，兼容国产服务器、操作系统与算力芯片，可完全私有化交付。',
     [('自研', '从容器云到 AI 智算，核心组件全部自研。'),
      ('信创', '适配国产软硬件栈，支持离线安装与升级。')]),
]

# 关键数字：每个数字都来自线上正文，没有新造指标。
STATS = [
    ('2021', '从开源容器云起步', '启动 KubeGems 开源容器云设计，云原生基座由此定型。'),
    ('16', '项软件著作权', '覆盖容器云、AI 智算、多云管理与运营平台，均由中华人民共和国国家版权局颁发。'),
    ('2', '位核心创始成员', '累计十余年云计算与 AI 平台建设经验，主导过多项云平台与模型训练项目。'),
    ('2025', '业务走向海外', '入局中东业务，为能源行业提供云原生 SaaS 化服务。'),
]

TEAM = [
    ('马', '马青', '创始人 · KubeGems 发起人',
     '曾任达闼机器人云平台负责人，主导云平台与 AI 平台建设及模型训练项目，拥有十余年云计算经验。'),
    ('张', '张李昆', '联合创始人 · KubeGems 架构师',
     '主攻云基础设施方向，取得多项专利，擅长云原生架构与 AI 基础平台设计与落地。'),
]

HONOR_ISSUER = '中华人民共和国国家版权局'
HONORS = [
    ('晓石 AI 平台', '2024'),
    ('晓石容器云平台', '2024'),
    ('魔哈 AI 仓库平台', '2024'),
    ('晓石云模型服务平台', '2025'),
    ('晓石混合云管理平台', '2025'),
    ('晓石应用管理平台', '2025'),
    ('晓石云平台网关中间件', '2025'),
    ('晓石云应用实时监控插件', '2025'),
    ('晓石应用商店平台', '2025'),
    ('晓石数据库管理平台', '2025'),
    ('晓石多云运营管理平台', '2025'),
    ('晓石多租户应用运维平台', '2025'),
    ('晓石 XMOP 安卓版APP', '2025'),
    ('晓石 MPOP 安卓版APP', '2025'),
    ('晓石 XMOP 苹果版APP', '2025'),
    ('晓石 MPOP 苹果版APP', '2025'),
]

MILESTONES = [
    ('2021', '启动 KubeGems 开源容器云设计。'),
    ('2023', '破晓石公司成立。'),
    ('2024', '推出 XPAI 智算平台，构建模型全生命周期能力。'),
    ('2025', '入局中东业务，为能源行业全面提供云原生 SaaS 化服务。'),
]


# ============================================================ 板块渲染
def hero():
    # is-motion-visible 直接写在 section 上：首屏不该等 IntersectionObserver
    # 才显形（首页 #home 也是这么做的），内层 reveal 仍然负责渐入。
    # 垂直间距**不要**写在这串类名里 —— vendor.css 是上游 Tailwind 的编译产物，
    # 上游用过什么才有什么，`pt-4` / `pb-16` / `md:pb-20` 一个都不在里面（写了
    # 等于没写，顶部内边距实际是 0，页首直接贴住 fixed 顶栏）。改在 about.css 的
    # `.tf-about-hero` 里用真 CSS 写，那里还能用 clamp() 做连续响应式。
    # tools/qa/classes.py 会拦这类幽灵类。
    return (
        '<section class="tf-about-hero tf-motion-section is-motion-visible px-6 '
        'md:px-8 lg:px-20" style="--tf-motion-order: 0;">'
        + reveal(
            '<div class="mx-auto flex max-w-[920px] flex-col items-center text-center">'
            + overline('关于破晓石_')
            + '<h1 class="mt-6 max-w-[1080px] text-[3.1rem] font-semibold leading-[0.98] '
              'tracking-[-0.04em] text-white md:text-[4.65rem] lg:text-[4.55rem] '
              'lg:leading-[1.02] xl:text-[4.85rem]">'
              '<span class="block">以技术驱动成长</span></h1>'
            + '<p class="mt-5 max-w-[760px] text-base leading-8 text-white/62 md:text-lg">'
            + COMPANY['intro'] + '</p>'
            + '<div class="mt-7 flex flex-wrap items-center justify-center gap-3">'
            + brand_action('联系我们', CONTACT_PAGE)
            + brand_action('了解产品', HOME_URL, 'secondary')
            + '</div>'
            + '<p class="tf-about-hero-meta">'
              '<span>成都 · 高新区</span><i aria-hidden="true"></i>'
              '<span>云原生 · AI 智算</span><i aria-hidden="true"></i>'
              '<span>私有化交付</span></p>'
            '</div>', delay=0.05)
        + '</section>')


def pillars():
    rows = ''.join(
        '<div class="tf-about-pillar"><span class="tf-about-pillar-index">%s</span>'
        '<div><h3>%s</h3><p>%s</p><dl>%s</dl></div></div>'
        % (idx, esc(title), copy,
           ''.join('<div><dt>%s</dt><dd>%s</dd></div>' % (esc(k), v) for k, v in items))
        for idx, title, copy, items in PILLARS)
    panel = ('<div class="tf-about-pillars" aria-label="我们的立足点">'
             '<p class="tf-about-pillars-head">技术选型的三把尺子</p>%s</div>' % rows)
    return board('why', 1, '我们的立足点', '以云原生为基座，做 AI 原生的基础设施。',
                 '从开源容器云起步，我们把同一套底座延伸到 AI 智算、资产仓库、AI 聚合网关与运营平台。'
                 '下面三件事，是我们判断每一个技术选择的尺子。', '', panel)


def numbers():
    cells = ''.join(
        '<li class="tf-about-stat"><p class="tf-about-stat-value">%s</p>'
        '<h3>%s</h3><p class="tf-about-stat-copy">%s</p></li>' % (esc(v), esc(t), esc(c))
        for v, t, c in STATS)
    body = ('<ol class="tf-about-stats" aria-label="关键数字">%s</ol>' % cells)
    # 走分栏：右列 756px 正好放 2×2，比全宽 4 列更耐读
    return board('numbers', 2, '关键数字_', '每一步都有据可查。',
                 '下面每一个数字都来自公开可核验的事实：开源项目、著作权证书、'
                 '团队履历与已交付的行业项目。', '', body)


def team():
    cards = ''.join(
        '<li class="tf-about-member">'
        '<span class="tf-about-member-mark" aria-hidden="true"><b>%s</b></span>'
        '<div class="tf-about-member-copy"><h3>%s</h3>'
        '<p class="tf-about-member-role">%s</p>'
        '<p class="tf-about-member-bio">%s</p></div></li>' % (esc(mark), esc(name), esc(role), esc(bio))
        for mark, name, role, bio in TEAM)
    hiring = (
        '<div class="tf-about-hiring">'
        '<span class="tf-about-hiring-tag"><i aria-hidden="true"></i>WE\'RE HIRING.</span>'
        '<p class="tf-about-hiring-copy">我们在找愿意把复杂系统做简单的人。%s</p>'
        '<a class="tf-about-hiring-link" href="mailto:%s">发送简历 %s</a>'
        '</div>' % (COMPANY['slogan'], COMPANY['mail'], ARROW_S))
    member_block = ('<ul class="tf-about-team" aria-label="核心团队">%s</ul>%s'
                    % (cards, hiring))
    # 全宽：两位创始人的卡片铺满一行，招聘条压在下面
    return board('team', 3, '核心团队', '一支把产品做进生产环境的团队。',
                 '创始成员来自云平台与 AI 平台一线，既写过调度器，也陪客户跑过训练任务。'
                 '我们相信长期的工程纪律，比短期的功能密度更重要。', member_block)


def honors():
    items = ''.join(
        '<li class="tf-about-honor"><span class="tf-about-honor-index">%02d</span>'
        '<h3>%s</h3><p>%s · %s</p></li>' % (i + 1, esc(name), HONOR_ISSUER, year)
        for i, (name, year) in enumerate(HONORS))
    # 星环与光晕放进独立 stage：.tf-section-inner 本身就是 .tf-section-frame，
    # 直接给它加 overflow:hidden 会切掉四个角标（见 about.css 的注释）
    ring = ('<div class="tf-about-honors-stage" aria-hidden="true">'
            '<div class="tf-about-honors-glow"></div>'
            '<div class="tf-about-orbit"><span></span><span></span><span></span></div></div>')
    body = ('%s<p class="tf-about-honors-count"><b>%d</b> 张证书</p>'
            '<ul class="tf-about-honors-grid" aria-label="公司荣誉">%s</ul>'
            % (ring, len(HONORS), items))
    return ('<section id="honors" class="tf-section tf-about-honors scroll-mt-[90px] '
            'text-white tf-motion-section" style="--tf-motion-order: 4;">'
            '<div class="tf-section-inner tf-section-frame">'
            '<div class="tf-section-heading">%s'
            '<h2 class="tf-section-title mt-5">认证证书由官方单位颁发。</h2>'
            '<p class="tf-section-copy">我们用一组「荣誉星环」记录每一次技术与信任的跃迁：'
            '每一张证书对应一款自研平台，发行方均为中华人民共和国国家版权局。</p></div>'
            '%s</div></section>'
            % (overline('公司荣誉'), body))


def milestones():
    nodes = ''.join(
        '<li class="tf-about-milestone"><span class="tf-about-milestone-dot" '
        'aria-hidden="true"></span><p class="tf-about-milestone-year">%s</p>'
        '<p class="tf-about-milestone-copy">%s</p></li>' % (esc(year), esc(copy))
        for year, copy in MILESTONES)
    body = ('<div class="tf-about-milestone-track"><ol class="tf-about-milestones" '
            'aria-label="发展历程">%s</ol></div>' % nodes)
    # 全宽：四个年份排成一行，连线才有意义（分栏时每列只剩 171px）
    return board('history', 5, '发展历程_', '从开源容器云，走到 AI 智算。',
                 '我们没有换过赛道，只是把同一套云原生底座，一年一年往上层推。', body)


def closing():
    return (
        '<section class="tf-contact-cta-section text-white tf-motion-section" '
        'style="--tf-motion-order: 6;">'
        '<div class="tf-contact-cta-structure" aria-hidden="true">'
        '<span class="is-crossline"></span><span class="is-bottomline"></span></div>'
        '<div class="tf-contact-cta-shell"><div class="tf-contact-cta-card">'
        '<div class="tf-contact-cta-primary">'
        '<img src="../assets/img/cta-dither.webp" alt="" width="566" height="140" '
        'aria-hidden="true" loading="lazy" decoding="async">'
        '<div class="tf-contact-cta-primary-content">'
        '<h2>想聊聊您的 <strong>云与 AI 底座？</strong></h2>'
        '<p>从容器云到 AI 智算，我们可以先聊架构，再谈交付。</p>'
        + brand_action('联系我们', CONTACT_PAGE)
        + '</div></div>'
        '<div class="tf-contact-cta-secondary">'
        '<p>%s<br>%s</p>'
        '<div class="tf-about-cta-links">'
        '<a href="%s"%s>产品总览 %s</a>'
        '<a href="%s"%s>开发者文档 %s</a>'
        '<a href="%s"%s>KubeGems 开源 %s</a></div>'
        '</div></div></div></section>'
        % (COMPANY['name'], COMPANY['address'],
           HOME_URL, ext(HOME_URL), ARROW_S,
           DOCS_URL, ext(DOCS_URL), ARROW_S,
           GITHUB_URL, ext(GITHUB_URL), ARROW_S))


def main_markup():
    divider = code_divider('https://api.poxiaoshi.cn/about', 1)
    return (hero()
            + divider
            + pillars()
            + divider
            + numbers()
            + divider
            + team()
            + divider
            + honors()
            + divider
            + milestones()
            + closing())


# ============================================================ 装配
def main():
    ctx = Ctx()
    doc, home, home_md5 = derive(
        ctx,
        out_rel=OUT_REL,
        title='关于我们 | ' + COMPANY['short'],
        # head 的 description 直接复用 COMPANY['intro']（也就是 hero 正文那句）。
        # 早期版本在这里另写了一份措辞略有不同的硬编码文案（「…自主研发，为企业提供…」
        # vs 正文的「…自主研发。我们为企业提供…」，差 6 字节），同一句话存两份定义。
        # 抽公共库时一并统一为 COMMPANY['intro']，产物 md5 因此从 775b9873… 变为
        # 2c560828…（字节数 61690 → 61696）。改的是 meta，页面上看不到。
        description=COMPANY['intro'],
        extra_css=ABOUT_CSS,
        main_markup=main_markup(),
        main_label='main body -> 关于我们板块',
        nav_label='nav active state -> 关于我们',
    )

    # ------------------------------------------------------- 本页专属守卫
    # 板块与内容计数。前半段断的是「生成器 ↔ 产物」一致（builder 漏渲染一条就报错），
    # 后半段的绝对条数断的是「内容本身」：线上 about 页就是 16 张软著证书、2 位核心
    # 成员、4 个年份，删改要显式改这里的期望值，不能悄悄少一条。
    for name, want in (('PILLARS', 3), ('STATS', 4), ('TEAM', 2),
                       ('HONORS', 16), ('MILESTONES', 4)):
        got = len(globals()[name])
        if got != want:
            ctx.miss.append('%s: %d entries, expected %d' % (name, got, want))
    checks = [('tf-about-pillar"', len(PILLARS), 'pillars'),
              ('tf-about-stat"', len(STATS), 'stats'),
              ('tf-about-member"', len(TEAM), 'team cards'),
              ('tf-about-honor"', len(HONORS), 'honor chips'),
              ('tf-about-milestone"', len(MILESTONES), 'milestones')]
    for needle, want, label in checks:
        got = doc.count(needle)
        if got != want:
            ctx.miss.append('%s: got %d, want %d' % (label, got, want))
    # 每个 id 只应出现一次
    for sid in ('why', 'numbers', 'team', 'honors', 'history'):
        if doc.count('id="%s"' % sid) != 1:
            ctx.miss.append('section id="%s" should appear exactly once, got %d'
                            % (sid, doc.count('id="%s"' % sid)))
    # 章节顺序：hero < why < numbers < team < honors < history < cta < footer
    order = ['tf-about-hero', 'id="why"', 'id="numbers"', 'id="team"', 'id="honors"',
             'id="history"', 'tf-contact-cta-section', 'tf-reference-footer']
    pos = [doc.find(x) for x in order]
    if -1 in pos:
        ctx.miss.append('section order anchor missing: '
                        + ', '.join(x for x, p in zip(order, pos) if p < 0))
    elif pos != sorted(pos):
        ctx.miss.append('sections are out of order: ' + str(list(zip(order, pos))))
    # 站内不该出现的旧品牌 / 上游残留
    for leftover in ('api.example.com', 'Building AI Infrastructure', 'Loki Wong',
                     'Nia Park', 'WE ARE HIRING', 'src="assets/'):
        if leftover in doc:
            ctx.miss.append('leftover / bad path: ' + leftover)
    if upstream_brand(doc):
        ctx.miss.append('leftover: 上游品牌名（见 portal_page.UPSTREAM_BRAND_RE）')
    # 星环必须画在 stage 里：直接给 .tf-section-inner 加 overflow:hidden 会切掉
    # .tf-section-frame 那四个 -1px 的角标（差点就这么发了）
    css_path = os.path.join(ROOT, 'assets', 'css', ABOUT_CSS)
    css_bare = (re.sub(r'/\*.*?\*/', '', open(css_path, encoding='utf-8').read(), flags=re.S)
                if os.path.exists(css_path) else '')
    if re.search(r'\.tf-about-honors\s+\.tf-section-inner\s*\{', css_bare):
        ctx.miss.append('about.css must not style .tf-section-inner directly '
                        '(overflow would clip the frame corners)')
    if 'tf-about-honors-stage' not in doc:
        ctx.miss.append('the honour rings lost their clipping stage')
    # 商务出口（2026-09-11 晚（十三））：两处 `brand_action('联系我们')` 都指 /contact。
    # `tf-brand-action` 是本页的主按钮样式，全页三处用它（这两条 + 「了解产品」），
    # 所以按「指 /contact 的 brand-action 恰好 2 条」咬 —— 少一条是有人把它改回 mailto，
    # 多一条是又加了个商务按钮而没想清楚落点。
    # 另一处 `tf-about-hiring-link`（发送简历）是邮箱语义，**不算**商务按钮，保持 mailto。
    got = doc.count('href="%s" class="tf-brand-action' % CONTACT_PAGE)
    if got != 2:
        ctx.miss.append('「联系我们」主按钮应有 2 处指向 %s，实得 %d' % (CONTACT_PAGE, got))

    finish(ctx, doc, OUT, OUT_REL, len(home), home_md5)


if __name__ == '__main__':
    main()
