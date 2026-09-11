#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成 4 个产品子页：/products/{rune,moha,ai-router,boss}/index.html

它们对应顶栏「产品」下拉里的四个板块（Rune 智算 / Moha 资产 / AIRouter · AI聚合网关
/ BOSS 运营）。在此之前，那四个入口都指向旧站（`www.poxiaoshi.cn/products/rune/`
之类）或直接指向控制台 —— 站内没有产品页，导航一出去就回不来了。

版式语言
--------
参照原站 `/runtime` 那一页：左侧文案 + 右侧深色控制台面板，mono 小标签，
居中 story 标题。**组件不新造**：vendor.css 里本就有整套 `tf-runtime-*`（42 个类）
与 `tf-section-*` / `tf-overline` / `tf-brand-action` / `tf-contact-cta-*`，
本脚本只是把它们按那页的顺序拼起来。本页家族自己的少量样式（页首双栏与内边距、
预览面板内层）在 `assets/css/products.css`。

正文只剩一块（2026-09-11 晚（九）（十）（十一））
-----------------------------------------------
顺序是：**页首**（定位 + 控制台预览）→ **代码分隔线**。

到此为止删过三轮，都是用户点名删的，别再往回加：

| 轮次 | 删掉的段落 |
| --- | --- |
| 晚（九） | 四项关键能力 `#capabilities` / 能力清单 `#detail` / 能力边界 `#boundary` / 同一个内核的其他三块 `#siblings` |
| 晚（十） | 一次全过程 `#flow`（各页名字不同：部署全过程 / 上传与分发 / 请求选路 / 交班巡检） |
| 晚（十一） | 收尾 CTA 整段（「想在您的环境里跑 X？」那张卡片，见下） |

晚（十一）删的是**函数不是数据**：收尾 CTA 是四页共用的 `closing(p)`，`PRODUCTS` 里
没有对应字段。删掉之后四页正文只剩页首 —— 最后一屏不再是 CTA 卡，而是那条代码分隔线
加页脚。**分隔线留着**（它不在用户点名范围内，位置也没动）：删段不该顺带把版面往前
挪一格，它去留是视觉决定，等被点名。

被删内容里唯一有长期价值的是**产品口径**（AIRouter 与 BOSS 没有在线充值与扣费闭环、
Rune 资源池不含调度、Rune Harness 仍是规划），原文归档在
`docs/CODE-REVIEW-2026-09-11.md` §15.3 与 §16.3；晚（十）那四段与晚（十一）这段都是
**先留档再删**的，逐字原文（含 `closing()` 源码与恢复步骤）在
`docs/archive/products-deleted-sections-2026-09-11.md`。

`--tf-motion-order` 现在只剩 0（页首）/ 1（分隔线）—— 它是**错峰出场的槽位**，不是
序号，删段后刻意不重排：重排会改掉页首的出场节奏，而用户要的是「删掉那一段」，不是
「整页动效重来」。收尾那段原本占着 6，这个值随它一起消失（不是改成 2）。
谁要动这些数字，先想清楚这是在改视觉。

内容来源
--------
四页的正文事实**全部来自本机仓库**，不是从旧站复制的营销文案：

  Rune        rune/README.md、rune/docs/{workspace,cluster,flavor,resourcepool,quota,
              product,observability}/、rune/pkg/cloud/llmgateway/、storagevolume/
  Moha        XiaoShi-Moha/{CONTEXT.md,pkg/hub/*,docs/design/*}、moha-sdk/{README,cli.py}
  AIRouter    airouter/{README.md,AGENTS.md,docs/guide/*,docs/design/*,internal/domain/*}
  BOSS        boss-homepage-redesign-2026-07-23.md、XiaoShi-Rune-Console/src/routes/{navs,
              sections}/boss.tsx、cn/{navbar,gateway}.json

写作纪律（都写进了守卫，别绕过去）
----------------------------------
* **AIRouter 没有充值 / 扣费闭环**：只讲用量计量、费用快照与周期配额，不把支付与
  结算写成能力。「充值 / 扣费 / 余额」三个词在四页上一律不得出现（PROJECT-MEMORY.md
  的口径）。这原先是「能力边界」那一栏里的一句声明，栏删了之后口径从「恰好一次」
  收紧成「一次都不许」—— 免得那句话没了之后，有人把「在线充值」当能力写进正文。
* **Rune Harness 仅为愿景**：出现「Rune Harness」的地方必须同时写「规划 / 尚未」。
  这条守卫目前在本文件里**碰不到东西**（四页正文一次都没提过 Harness，它只出现在
  首页站芯的导航条与首页正文，由 `reshape_home.py` 的 required 串守着）—— 留着是
  条件式不变量：一旦有人把它写进产品页，这条就会开始咬。
* **调度不作为已完整交付的能力**：资源池只做容量汇总与健康视图，**不包含调度**。
  晚（十）之前这条在页面上靠「一次全过程」里的「调度链路」「选择资源池 · 容量与健康」
  两个标签**反向**呼应，那一段删掉之后，页面上已经没有能被误读成「平台负责调度」的
  说法了 —— 但规则本身仍然生效：正文里不许把调度写成已交付能力。
* 面板里的数字一律标注「示意数据」，不编造真实指标。

路径与深度
----------
产物是 `products/<slug>/index.html`，比首页深**两级**，所以 `derive(depth=2)`，
主内容里的资源写站点根相对路径 `assets/…`（由 derive 统一加 `../../`），
不要在 markup 里手写 `../` —— 这是 build_blog.py 定下的约定。
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import seo  # noqa: E402
# 晚（十一）删掉收尾 CTA 之后，ARROW_S 与 ext 在这个文件里再没有使用者：ARROW_S 只被
# `closing()` 的链接组用，ext 只被 `closing()` 与 `brand_action()` 用 —— 后者内部自己
# 调，不需要这里传入。留着就是两个没人引用的 import。
from portal_page import (Ctx, PRODUCT_NAV_GROUP, brand_action, code_divider,  # noqa: E402
                         derive, esc, finish_many, overline, upstream_brand)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

DEPTH = 2
PRODUCTS_CSS = 'products.css'
SITE_NAME = '破晓石科技'
DOCS_URL = 'https://docs.poxiaoshi.cn'

# 商务落点只有一个（2026-09-11 晚（十三），用户要求「预约演示 / 联系我们 / 进入控制台」
# 一律跳 /contact）。这里原先有 `MAIL` 与 `CONSOLE_URL` 两个常量：页首第一个按钮发邮件、
# 第二个按钮直连控制台。两个都改指 /contact 之后它们再无引用，所以一起删掉 ——
# 留着就是在邀请下一个人「给某个 CTA 加回一个直连控制台的理由」。
CONTACT_PAGE = '/contact'

# 页首按钮组**允许**的落点白名单。写成与 `PRODUCTS[*]['actions']` 无关的常量是
# 有意的 —— 期望值若从被检查的数据里算出来，篡改那份数据就等于篡改断言（见 guards()
# 里「商务出口」那段的注释）。Moha 页的次按钮是文档站，是四页里唯一的结构差异，
# 所以 DOCS_URL 也在名单里。
ACTION_HREFS = (CONTACT_PAGE, DOCS_URL)


# ============================================================ 内容
PRODUCTS = [
    {
        'slug': 'rune',
        'name': 'Rune',
        'sub': '智算',
        'accent': 'var(--tf-rune)',
        'card': '多租户 AI 平台控制面：集群、工作空间、资源规格、配额与推理服务注册。',
        # `'badge'` 字段（「核心产品 · Rune 智算」）与页首那枚胶囊徽标一起在晚（十二）
        # 按用户要求删除 —— 四条数据、CSS、守卫三处都跟着清了。
        # 留档 + 恢复步骤：docs/archive/products-deleted-sections-2026-09-11.md。
        'overline': 'Rune 智算_',
        'title': '训练与推理，一套控制面管到底。',
        'lede': 'Rune 是晓石云的多租户 AI 平台控制面：接入集群、隔离工作空间、定义资源规格、'
                '下发配额，把模型服务注册到网关。上层是训练、微调、推理与应用实例，'
                '下层是 Kubernetes —— 中间不再需要一套自研的编排胶水。',
        'meta': ['K8s 原生', '多租户隔离', '私有化 / 离线交付'],
        # 两个按钮同指 /contact，文字不同是有意的：`联系我们` 是主按钮（想找人聊），
        # `预约演示` 是次按钮（想看东西）。它们不是两条不同的路，是同一件事的两种说法
        # —— 用户 2026-09-11 晚拍板把原来的「进入控制台」改成这个措辞，与首页品牌带、
        # 页尾那条统一（首页那两条本来就写着「预约演示」）。
        'actions': [('联系我们', CONTACT_PAGE, 'primary'),
                    ('预约演示', CONTACT_PAGE, 'secondary')],
        'preview': {
            'label': 'rune · control-plane',
            'status': '运行中',
            'rows_title': '工作空间上下文',
            'rows': [('Workspace', 'ws-dev-a'), ('Flavor', 'nvidia-h100.2'), ('状态', 'Running')],
            'line': '$ rune apply -f workspace.yaml',
            'steps': [('0 1', '提交规格'), ('0 2', '选资源池'), ('0 3', '实例就绪')],
            'footer': [('集群', 'cluster-a 已连接'), ('资源池', 'h100-pool'),
                       ('配额', '8 / 20 卡')],
            'note': '界面示意：字段取自平台真实对象，数值为示意值，非实时数据。',
        },
    },
    {
        'slug': 'moha',
        'name': 'Moha',
        'sub': '资产',
        'accent': 'var(--tf-moha)',
        'card': '私有化 AI 资产仓库：模型、数据集、镜像与 Space 的统一元数据与版本治理。',
        'overline': 'Moha 资产_',
        'title': '模型、数据集与镜像，一个仓库管到底。',
        'lede': 'Moha 是私有化的 AI 资产仓库：四类仓库（模型 / 数据集 / 镜像 / Space）'
                '共用一个元数据面，版本用 Git 语义，大文件走 LFS 直连对象存储，'
                '镜像与 OCI 生态兼容，需要保密的上传即加密。',
        'meta': ['Git + LFS', 'OCI 兼容', '信封加密'],
        # 这一页的次按钮是「开发者文档」（指文档站，站外开新窗），**不是**商务按钮，
        # 所以它留 DOCS_URL 不动 —— Moha 页因此只有一条 /contact 入口，另三页两条。
        # 这是四个页首里唯一的结构差异，别为了「四页对齐」把它改成 /contact。
        'actions': [('联系我们', CONTACT_PAGE, 'primary'),
                    ('开发者文档', DOCS_URL, 'secondary')],
        'preview': {
            'label': 'moha · registry',
            'status': '已同步',
            'rows_title': '仓库上下文',
            'rows': [('仓库', 'demo/ocr-lora'), ('版本', 'v2.1.0'), ('体积', '142.0 GB')],
            'line': '$ moha upload model demo/ocr-lora ./ckpt',
            'steps': [('0 1', '分片上传'), ('0 2', '元数据索引'), ('0 3', '打标签发布')],
            'footer': [('类型', 'model'), ('可见性', 'internal'), ('加密', 'AES-256-CTR')],
            'note': '界面示意：字段取自 Moha 的真实模型与 CLI 参数，数值为示意值。',
        },
    },
    {
        'slug': 'ai-router',
        'name': 'AIRouter',
        'sub': 'AI聚合网关',
        'accent': 'var(--tf-airouter)',
        'card': 'AI聚合网关：协议翻译、策略路由、配额限流与用量计量，收口所有模型调用。',
        'overline': 'AIRouter · AI聚合网关_',
        'title': '多家上游，一个 OpenAI 兼容入口。',
        'lede': 'AIRouter 把集群内自建推理服务与公有云模型收成同一个入口：'
                '调用方用 OpenAI 或 Claude 风格说话，网关负责认证、审核、选路、限额，'
                '再按上游方言转发。控制面管配置与落库，数据面只管转发。',
        'meta': ['OpenAI 兼容', 'Claude 兼容', '控制面 / 数据面分离'],
        'actions': [('联系我们', CONTACT_PAGE, 'primary'),
                    ('预约演示', CONTACT_PAGE, 'secondary')],
        'preview': {
            'label': 'airouter · data-plane',
            'status': 'healthy',
            'rows_title': '本次请求',
            'rows': [('模型', 'deepseek-v3.2'), ('渠道', 'vllm-a100'), ('选路', 'priority')],
            'line': '$ curl -X POST /v1/chat/completions',
            'steps': [('0 1', '认证与审核'), ('0 2', '选出渠道'), ('0 3', '转发计量')],
            'footer': [('回退', '最多再试 2 条'), ('限流', 'RPM · TPM · 并发'),
                       ('用量', 'usage_id 幂等')],
            'note': '界面示意：字段取自网关真实对象与响应头，延迟为示意值。',
        },
    },
    {
        'slug': 'boss',
        'name': 'BOSS',
        'sub': '运营',
        'accent': 'var(--tf-boss)',
        'card': '智算中心运营控制台：租户、配额、网关运营、资产与审计的跨域值班视图。',
        'overline': 'BOSS 运营_',
        'title': '平台是否健康，30 秒内说得清。',
        'lede': 'BOSS 是平台的后台运营与治理面。它不重建 Rune、Moha、AIRouter 的事实，'
                '而是把它们汇总成一张值班视图：风险待办、容量水位、网关质量、'
                '资产与账号概览，以及下一步该去哪里处置。',
        'meta': ['多租户运营', '配额与计量', '值班视图'],
        'actions': [('联系我们', CONTACT_PAGE, 'primary'),
                    ('预约演示', CONTACT_PAGE, 'secondary')],
        'preview': {
            'label': 'boss · overview',
            'status': '巡检正常',
            'rows_title': '当班摘要',
            'rows': [('待办', '3 项待处理'), ('数据源', '5 / 10 已接入'),
                     ('容量', 'GPU 78% 已分配')],
            'line': '$ boss overview --window 24h',
            'steps': [('0 1', '看风险'), ('0 2', '看容量'), ('0 3', '看质量')],
            'footer': [('租户', '28 个在管'), ('请求', '3.8M · 24h'), ('成功率', '99.2%')],

            'note': '界面示意：字段取自平台真实对象，数值为示意值，非实时数据。',
        },
    },
]


def product_href(slug):
    return '/products/%s/' % slug


def divider_for(slug):
    """页首与收尾之间那条代码分隔线。URL 里的 /products/<slug> 与旧站产品页路径同形，
    所以守卫查「旧站外链」时要先把这段装饰性文本摘掉（见 guards）。"""
    return code_divider('https://api.poxiaoshi.cn/products/' + slug, 1)


# ============================================================ 板块渲染


def hero(p):
    v = p['preview']
    actions = ''.join(brand_action(label, href, kind) for label, href, kind in p['actions'])
    meta = ''.join('<span>%s</span>%s' % (esc(x), '<i></i>' if i < len(p['meta']) - 1 else '')
                   for i, x in enumerate(p['meta']))
    rows = ''.join('<div><dt>%s</dt><dd>%s</dd></div>' % (esc(k), esc(val))
                   for k, val in v['rows'])
    steps = ''.join('<li><b>%s</b>%s</li>' % (esc(idx), esc(label)) for idx, label in v['steps'])
    footer = ''.join('<span><b>%s</b>%s</span>' % (esc(k), esc(val)) for k, val in v['footer'])
    preview = (
        '<div class="tf-runtime-console tf-product-preview">'
        '<div class="tf-runtime-console-bar">'
        '<div class="tf-runtime-console-dots"><span></span><span></span><span></span></div>'
        '<span>%s</span>'
        '<span class="tf-runtime-console-status">%s</span></div>'
        '<div class="tf-product-preview-body">'
        '<p class="tf-runtime-label">%s</p>'
        '<dl class="tf-product-preview-rows">%s</dl>'
        '<p class="tf-product-preview-line"><i>$</i>%s</p>'
        '<ol class="tf-product-preview-steps">%s</ol>'
        '<p class="tf-product-preview-note">%s</p>'
        '</div>'
        '<div class="tf-runtime-console-footer">%s</div>'
        '</div>'
        % (esc(v['label']), esc(v['status']), esc(v['rows_title']), rows,
           esc(v['line'].lstrip('$ ')), steps, esc(v['note']), footer))
    return (
        '<section class="tf-product-hero tf-motion-section is-motion-visible px-6 md:px-8 lg:px-20" '
        'style="--tf-motion-order: 0;">'
        '<div class="tf-product-hero-shell mx-auto max-w-[1180px]">'
        # 徽标胶囊（`tf-product-hero-badge`）与它下面那层 `<div class="mt-6">` 包装在
        # 2026-09-11 晚（十二）**一起**删除 —— 那个 mt-6 唯一的职责就是「小标与徽标之间
        # 的间距」，徽标没了它就是一段没有服务对象的空白（原来的注释也是这么写的）。
        # 小标现在直接作为左栏第一行，仍然不要自己的类名：写过但没有任何规则的类会被
        # tools/qa/classes.py 当幽灵类拦下，而为绕过它补一条空规则，等于把一个
        # 「其实没样式」的事实藏起来。
        '<div class="tf-product-hero-copy">%s'
        '<h1 class="tf-product-hero-title">%s</h1>'
        '<p class="tf-product-hero-lede">%s</p>'
        '<div class="tf-product-hero-actions">%s</div>'
        '<p class="tf-product-hero-meta">%s</p>'
        '</div>%s</div></section>'
        % (overline(p['overline']), esc(p['title']),
           esc(p['lede']), actions, meta, preview))




# 收尾 CTA（`closing()`）在 2026-09-11 晚（十一）按用户要求整段删除 —— 就是「想在您的
# 环境里跑 X？」那张卡片（用户的原话是「删除『进入控制台』的区域」，澄清后确认为整段）。
# 它走后，产品页上的控制台入口只剩**页首按钮组**里那一条（Rune / AIRouter / BOSS 三页
# 的 `actions` 第二项；Moha 页页首是「开发者文档」，本来就没有）。
#
# 2026-09-11 晚（十三）：那一条也改指 /contact 了，按钮文字从「进入控制台」改成
# 「预约演示」。**至此四个产品页上再没有 console.poxiaoshi.cn 链接**，全站唯一还在
# 提「控制台」的地方是产品页预览面板的示意界面（那是插图，不是入口）。
# 逐字原文与恢复步骤：docs/archive/products-deleted-sections-2026-09-11.md。


def main_markup(p):
    divider = divider_for(p['slug'])
    # 强调色**只在这里给一次**，各段靠继承拿（`--tf-product-accent` 是自定义属性，
    # 继承链与 DOM 一致）。改之前每个 section 各自内联了一遍同一个值（当时是七个）
    # —— 加一个板块就要记得再抄一次，而漏抄的那一段不会有任何报错，只是颜色悄悄变了。
    #
    # 这条规则就是 .tf-products-page 存在的理由（assets/css/products.css）。没有它，
    # 这个类就是个幽灵类，tools/qa/classes.py 会拦；而绕过检查的办法不该是删规则。
    #
    # 2026-09-11 晚（九）删掉「四项关键能力 / 能力清单 / 能力边界 / 同一个内核的其他
    # 三块」，晚（十）删掉最后一块正文「一次全过程」，晚（十一）连收尾 CTA 也整段删了
    # —— 正文至此只剩页首一块。
    #
    # **分隔线留着**（原本三条里的第一条，位置没动）：三轮删段都没点名它，而它原本是
    # 页首与下一段之间的过渡 —— 后面现在没有段落了，它就一路接页脚。删段不该顺带把版面
    # 往前挪一格；要不要连它一起去掉，是个视觉决定，等被点名。
    return ('<div class="tf-products-page" style="--tf-product-accent: %s;">' % p['accent']
            + hero(p)
            + divider
            + '</div>')


# ============================================================ 装配 + 守卫
# 已删除的段落。它们不该以任何形态复活 —— 段落标签、容器类、卡片类都算。
# 分三轮：晚（九）删了四段正文，晚（十）删了最后一段「一次全过程」，晚（十一）删了
# 收尾 CTA。用户点名删过的东西，下一轮改版最容易「从旧产物里粘一段回来」，所以每一轮
# 都要留下反向断言。
# （`SECTION_IDS` 那条「id 唯一」的断言随晚（十）一起没了：正文里已经不剩任何带 id
# 的段落，留着就是一个遍历空元组的循环 —— 看着像检查，其实什么都不做。）
RETIRED_IDS = ('flow', 'capabilities', 'detail', 'boundary', 'siblings')
RETIRED_CLASSES = ('tf-capability-card', 'tf-products-boundary', 'tf-products-sibling',
                   # 晚（十）：「一次全过程」那段的容器与它的注脚。上游 runtime 页的
                   # showcase 组件本身还在 vendor.css 里，只是本页家族不再用它 ——
                   # 这一段被粘回来时，这两个类是最先出现的形态。
                   'tf-runtime-showcase', 'tf-products-note',
                   # 晚（十一）：收尾 CTA。`tf-contact-cta-*` 是 vendor.css 里的通用
                   # 组件族（首页与 /about 都还在用），**不是**本页家族的东西，所以
                   # 不能靠「幽灵类」检查发现它复活 —— 只能在这里点名。整族一起拦：
                   # 只写 -section 的话，把卡片挪进另一个 <section> 就绕过去了。
                   'tf-contact-cta-', 'tf-products-cta-links',
                   # 晚（十二）：页首徽标胶囊。它是**本页自己定义的类**（规则刚从
                   # products.css 删掉），幽灵类检查这回能抓 —— 但只在「类写回来而
                   # 规则没补」时抓；两样一起粘回来它就一声不响，所以照样点名。
                   'tf-product-hero-badge')
# 被删段落的可见标题。id 与类名答的是「代码回来了没有」，这几条答的是「读者还看得见
# 那几个标题吗」—— 比如整段被重写成不带 id 的 <div> 时，只有它们会响。
RETIRED_TITLES = ('一次部署的全过程', '一次上传与分发', '一次请求的选路', '一次交班巡检',
                  # 晚（十一）：收尾 CTA 的 h2。它是这一段唯一一句人话标题；卡片被
                  # 重排成别的结构、类名全换掉时，只有这条会响。
                  '想在您的环境里跑',
                  # 晚（十二）：页首徽标那四条文本的共同前缀（四条都是「核心产品 · …」）。
                  # 取前缀不取全文：四页各写一个全串要维护四份，而漏掉的那一页永远不会
                  # 报错 —— 前缀一条顶四条，且「核心产品」这个词只出现在徽标上。
                  '核心产品 · ')


def guards(ctx, p, doc, main_html):
    slug = p['slug']
    # 分隔线里的 fetch URL 与旧站产品页路径同形，但它只是装饰性代码，先摘掉再查。
    # 摘之前的原件留一份：正文现在只有两块，下面那句 `<section` 计数要数上分隔线才算
    # 得对（摘掉之后只剩页首一条，计数就没有意义了）。
    raw_main = main_html
    main_html = main_html.replace(divider_for(slug), '')
    def miss(msg):
        ctx.miss.append('%s: %s' % (slug, msg))

    # --- 内容逐字落盘（builder 漏渲染一个字段就能立刻发现） --------------
    # （`badge` 这条随徽标一起在晚（十二）删除：字段没了，断言留在元组里会直接
    # `KeyError`，而"把断言注掉"是这类改动最常见的半拉子收尾。）
    for label, needle in (('title', p['title']), ('lede', p['lede']),
                          ('overline', p['overline'])):
        if esc(needle) not in doc:
            miss('hero field lost: %s' % label)
    # --- 条数 -----------------------------------------------------------
    for needle, want, label in (
            ('tf-product-preview-steps"', 1, 'hero preview step list'),
            ('class="tf-product-hero ', 1, 'hero')):
        got = doc.count(needle)
        if got != want:
            miss('%s: got %d, want %d' % (label, got, want))
    # 页首那组编号步骤（0 1 / 0 2 / 0 3）用 <li> 数。全过程那段删掉后，数是全页
    # 唯一的编号列表 —— 所以这条断言也顺手看着「没人往页首里塞第四步」。
    m = re.search(r'<ol class="tf-product-preview-steps">(.*?)</ol>', doc, re.S)
    if not m or m.group(1).count('<li>') != 3:
        miss('hero preview should carry exactly 3 numbered steps')
    # --- 章节顺序 -------------------------------------------------------
    # 正文只剩两块，顺序即全部结构。`tf-faq-code-divider` 是那条代码分隔线（站芯里的
    # 通用组件），它必须留在页首之后 —— 谁把分隔线挪到页首之前，页面就变成「先一条
    # 装饰线、再标题」，那是排版事故。
    # 晚（十一）删掉收尾 CTA，`tf-contact-cta-section` 这个锚点随之去掉：留着它，守卫
    # 会在「CTA 确实没了」的正常状态下天天报 anchor missing —— 那是把删除当故障。
    order = ['tf-product-hero', 'tf-faq-code-divider', 'tf-reference-footer']
    pos = [doc.find(x) for x in order]
    if -1 in pos:
        miss('section order anchor missing: '
             + ', '.join(x for x, q in zip(order, pos) if q < 0))
    elif pos != sorted(pos):
        miss('sections are out of order: %s' % list(zip(order, pos)))
    # 正文的块数就是全部结构：晚（十一）之后只剩「页首 + 分隔线」。这条比顺序锚点更早
    # 发现问题 —— 有人加回第三段时，锚点数组里没有它，顺序依然成立，只有计数会响。
    # （`raw_main` 是没摘掉分隔线的原件；加段落时这条与 docstring 要一起改。）
    got = raw_main.count('<section')
    if got != 2:
        miss('正文应有 2 块（页首 + 分隔线），实得 %d' % got)
    # --- 删掉的段落不许复活 ---------------------------------------------
    # 「删板块」这种改动最容易在下次改版里被半路加回来（改了 markup 忘了 css，或者从
    # 旧产物里直接粘一段回来），所以删完要留下反向断言：段落 id、容器类、可见标题各
    # 查一遍。正文里也不该再有指向其他产品页的互链 —— 三张姊妹卡是它唯一的来源
    # （nav 里那份在站芯上，不算 main）。
    for sid in RETIRED_IDS:
        if 'id="%s"' % sid in doc:
            miss('已删段落回来了: id="%s"' % sid)
    for cls in RETIRED_CLASSES:
        if cls in doc:
            miss('已删板块的类回来了: ' + cls)
    for title in RETIRED_TITLES:
        if title in doc:
            miss('已删段落的标题还在页面上: ' + title)
    for q in PRODUCTS:
        if 'href="%s"' % product_href(q['slug']) in main_html:
            miss('main 里不该再有产品页互链（姊妹卡已删）: ' + q['slug'])
    # --- 商务出口（晚十三）-----------------------------------------------
    # 页首按钮组的落点逐条核。**期望值不能从 `p['actions']` 里算出来**：
    #
    # 第一版写的是
    #     want = sum(1 for _, href, _ in p['actions'] if href == CONTACT_PAGE)
    #     got  = main_html.count('href="/contact"')
    # 那是「拿被检查的数据算期望」。把某页次按钮的目标改成 /about（模拟改错目标），
    # `actions` 一改，markup 真的渲染成 /about，于是 got 与 want 一起变成 1 ——
    # 断言一声不响地通过，2026-09-11 审查时实测确认 MISS=0。
    # `reshape_home.py` 的 `CONTACT_RETARGET` 在同一轮踩的是同一个坑（§19.6 记了
    # 那条教训），但只修了那处，这里漏了。
    #
    # 现在把「允许的落点」写成与 actions 无关的白名单常量（ACTION_HREFS），再按
    # 渲染顺序逐条核 —— 篡改 actions 里的目标会落在白名单之外，当场咬住。
    # 只写「恰好 N 条 /contact」不够：Moha 页只有一条，而且条数对不代表目标对。
    btns = re.findall(r'<a href="([^"]*)"[^>]*class="tf-brand-action[^"]*">', main_html)
    if len(btns) != len(p['actions']):
        miss('页首按钮数 %d，actions 声明 %d' % (len(btns), len(p['actions'])))
    for href in btns:
        if href not in ACTION_HREFS:
            miss('页首按钮落在允许的落点之外: %s（只允许 %s）'
                 % (href, ' / '.join(ACTION_HREFS)))
    if CONTACT_PAGE not in btns:
        miss('页首按钮组里没有一条指向 %s' % CONTACT_PAGE)
    if 'mailto:' in main_html:
        miss('产品页正文不该再有 mailto（商务出口统一到 /contact），实得 %d 处'
             % main_html.count('mailto:'))
    # 控制台直达在晚（十一）随收尾 CTA 删掉、晚（十三）连页首那条也改指 /contact，
    # 至此产品页一个都不该剩。预览面板里的「控制台」是插图文字，不含域名 ——
    # 所以这条按域名咬，不按「控制台」三个字咬（咬了会把插图也判违规）。
    if 'console.poxiaoshi.cn' in main_html:
        miss('产品页正文不该再有控制台直达')
    # --- 写作纪律（产品口径，不是排版） ----------------------------------
    # 「充值 / 扣费 / 余额」在四个产品页上一律不得出现。网关与运营页原本靠「能力边界」
    # 那一栏显式声明「没有在线充值与扣费闭环」，该栏按用户要求删除后，这句话在页面上
    # 已无处可放 —— 于是口径从「恰好一次、且必须在边界栏」收紧成「一次都不许」，
    # 免得删栏之后有人顺手把「在线充值」当成能力写进正文（PROJECT-MEMORY.md：
    # AIRouter 只做用量计量与费用快照，不得暗示计费闭环）。
    for word in ('充值', '扣费', '余额'):
        n = main_html.count(word)
        if n:
            miss('口径：%r 出现 %d 次，产品页上一律不得出现（不得暗示计费闭环）' % (word, n))
    for m in re.finditer(r'Rune Harness', main_html):
        near = main_html[m.start():m.start() + 60]
        if '规划' not in near and '尚未' not in near:
            miss('口径：提到 Rune Harness 必须同时写明是规划中的形态')
    # --- 不残留旧站的产品页链接（本轮正是要把它们换掉） ------------------
    for old in ('poxiaoshi.cn/products/rune', 'poxiaoshi.cn/products/moha',
                'poxiaoshi.cn/products/ai-router'):
        if old in main_html:
            miss('main 里仍有旧站产品链接: ' + old)
    # --- 资源与结构 -----------------------------------------------------
    if re.search(r'(?:src|href)="(?<!\.\./\.\./)assets/', doc):
        miss('bare assets/ path survived')
    # 只查开标签前缀，不带 `>`：页根容器上现在挂着 --tf-product-accent 的内联
    # style，写死闭合尖括号会让这条守卫在「变量搬家」时假报「容器丢了」——
    # 2026-09-11 把强调色从七个 section 收拢到根容器时就是这么踩的。
    if '<div class="tf-products-page"' not in doc:
        miss('page container lost')
    else:
        m2 = re.search(r'<main\b[^>]*>', doc)
        if doc.find('tf-products-page') < m2.end():
            miss('page container must sit inside <main>')
    # 强调色只在根容器上给一次，各段靠继承。计数 = 1：变多了是有人又把同一个值抄回
    # 段级，变少了是根容器那条没了（整页强调色会一起失效）。删掉姊妹卡之前这里是 4
    # —— 那三张卡各自反向覆盖成对方的颜色，是页根继承链唯一的例外；例外没了，计数
    # 就该跟着回到 1，而不是留着一个永远碰不到的大数字。
    got = doc.count('--tf-product-accent: var(--tf-')
    if got != 1:
        miss('--tf-product-accent 应只有 1 处（页根容器），实得 %d' % got)
    for tag in re.findall(r'<section\b[^>]*>', doc):
        if '--tf-product-accent' in tag:
            miss('section 不该内联 --tf-product-accent: ' + tag[:90])
    # --- head -----------------------------------------------------------
    if '<title>%s</title>' % esc('%s %s | %s' % (p['name'], p['sub'], SITE_NAME)) not in doc:
        miss('<title> not rewritten')
    if upstream_brand(doc):
        miss('upstream leftovers')


def main():
    ctx = Ctx()
    pages = []
    home_len = home_md5 = 0
    for p in PRODUCTS:
        markup = main_markup(p)
        out_rel = 'products/%s/index.html' % p['slug']
        doc, home, home_md5 = derive(
            ctx,
            out_rel=out_rel,
            title='%s %s | %s' % (p['name'], p['sub'], SITE_NAME),
            description=p['card'],
            extra_css=PRODUCTS_CSS,
            main_markup=markup,
            active_group=PRODUCT_NAV_GROUP,
            main_label='main body -> %s 产品页' % p['name'],
            nav_label='nav active state -> 产品',
            depth=DEPTH,
            # 每个产品一张自己的 og 卡片：产品名 + 定位 + 该板块强调色。
            # 用默认图也不算错，但四个产品页分享出去是同一张图，等于白费。
            seo_extra=dict(image=seo.og_image('product', p['slug'])),
        )
        home_len = len(home) if not home_len else home_len
        guards(ctx, p, doc, markup)
        pages.append((os.path.join(ROOT, 'products', p['slug'], 'index.html'), out_rel, doc))

    finish_many(ctx, pages, home_len, home_md5,
                extra_lines=['products: %s' % ', '.join(product_href(p['slug'])
                                                       for p in PRODUCTS)])


if __name__ == '__main__':
    main()
