# 产品子页删除的段落：原文留档（2026-09-11）

这四段是 2026-09-11 晚（十）按用户要求从 `/products/*/index.html` 删除的
「一次全过程」板块 —— `tools/build_products.py` 里 `PRODUCTS[*]['flow']` 四个数据块
的**逐字原文**。删之前先留档，是因为上一轮（晚（九））删掉「四项关键能力 / 能力清单 /
能力边界 / 同一个内核的其他三块」时没有留，等想归档已经无据可查了；那四段的**口径**
条目侥幸留在 `docs/CODE-REVIEW-2026-09-11.md` §15.3，逐字版则永久丢失。

**留档目的是「能加回来」，不是「留着好看」。** 谁要把某一段恢复到页面上：
把下面某个 `'flow'` 块整段粘回 `PRODUCTS` 里对应产品的 `'preview'` 之后、`'slug'` 之前，
然后在 `guards` 里把该段从 `RETIRED_IDS` / `RETIRED_CLASSES` / `RETIRED_TITLES`
三张名单里摘掉（不然构建会直接报「已删段落回来了」）—— 那三条断言就是干这个的。

| slug | 面板标题（`flow.overline`） | 页首标题（仍在页面上） |
| --- | --- | --- |
| `rune` | 一次部署的全过程 | 训练与推理，一套控制面管到底。 |
| `moha` | 一次上传与分发 | 模型、数据集与镜像，一个仓库管到底。 |
| `ai-router` | 一次请求的选路 | 多家上游，一个 OpenAI 兼容入口。 |
| `boss` | 一次交班巡检 | 平台是否健康，30 秒内说得清。 |

---


## rune · 一次部署的全过程

```python
        'flow': {
            'overline': '一次部署的全过程',
            'title': '从一份规格，到一条可用的推理端点。',
            'copy': '用户只表达「要什么规格、跑哪个模板」，剩下的选池、拉起、注册由控制面完成。'
                    '下面这条路是每个工作空间实例都会走的。',
            'console_label': 'rune · workspace apply',
            'console_title': 'POST /workspaces/ws-dev-a/instances',
            'console_status': 'succeeded',
            'request_label': '提交（规格与模板）',
            'request_pre': 'apiVersion: ai.xiaoshiai.cn/v1\n'
                           'kind: WorkspaceInstance\n'
                           'metadata:\n'
                           '  workspace: ws-dev-a\n'
                           '  cluster: cluster-a\n'
                           'spec:\n'
                           '  product: vllm\n'
                           '  flavor: nvidia-h100.2\n'
                           '  replicas: 1',
            'protocols': ['Helm Chart', 'vLLM', 'SGLang', 'llama.cpp', 'K8s Job'],
            'result': '✔ 实例就绪：ws-dev-a / vllm-7d9f · 2 × H100',
            'route_meta': ('调度链路', 'avg 42 s'),
            'steps': [
                ('shield', '校验规格', '配额与可见性'),
                ('layers', '选择资源池', '容量与健康'),
                ('server', '拉起实例', '模板渲染'),
                ('route', '注册服务', '同步到网关'),
            ],
            'trace': ['namespace ws-dev-a', 'flavor nvidia-h100.2', 'pool h100-pool',
                      'quota 8/20 卡', 'gateway registered'],
            'footer': [('集群', 'cluster-a（已连接）'), ('配额', '租户级 + 工作空间级两层'),
                       ('可观测', '指标 / 日志 / 告警')],
            'note': '示意流程：字段与步骤取自平台真实对象，用时为示意值，非实测指标。',
        },
```


## moha · 一次上传与分发

```python
        'flow': {
            'overline': '一次上传与分发',
            'title': '大文件直传对象存储，只留一个指针在 Git 里。',
            'copy': '小文件走 Git，大文件转 LFS 指针直连对象存储 —— 仓库本身保持轻量，'
                    '克隆与分支切换不会被权重文件拖慢。',
            'console_label': 'moha · git-lfs push',
            'console_title': 'moha upload model demo/ocr-lora ./ckpt',
            'console_status': 'pushed',
            'request_label': '提交（CLI / SDK / Git）',
            'request_pre': '$ moha create model demo/ocr-lora\n'
                           '$ moha upload model demo/ocr-lora ./ckpt --revision v2.1.0\n'
                           '\n'
                           '# 非交互场景用 REST：\n'
                           'POST /api/v1/repos/demo/ocr-lora/uploads\n'
                           '  { "revision": "v2.1.0", "kind": "lfs" }',
            'protocols': ['Git', 'Git-LFS', 'OCI Distribution v3', 'Multi-arch', 'Trivy'],
            'result': '✔ 已提交：v2.1.0 · 142.0 GB · 分片直传对象存储',
            'route_meta': ('上传链路', '4 个分片并行'),
            'steps': [
                ('key', '校验引用', '引用名与权限'),
                ('database', '分片上传', 'LFS → S3'),
                ('scan', '元数据索引', 'Safetensors 识别'),
                ('git-branch', '打标签发布', '版本可检索'),
            ],
            'trace': ['lfs pointer 4.2 KB', 'objects → S3', 'head 88 tensors',
                      'stats ready', 'audit push/commit'],
            'footer': [('可见性', 'public / internal / private'),
                       ('检索', '元数据 + 全文'), ('审计', '/v1/audits')],
            'note': '示意流程：字段与接口取自 Moha 的真实模型与 CLI 子命令，数值为示意值。',
        },
```


## ai-router · 一次请求的选路

```python
        'flow': {
            'overline': '一次请求的选路',
            'title': '调用方只写模型名，去哪台机器由网关决定。',
            'copy': '认证、审核、选路、限额都在热路径上完成；配置由控制面经 gRPC 推送，'
                    '数据面只读缓存与内存，不碰业务库。',
            'console_label': 'airouter · request lifecycle',
            'console_title': 'POST /v1/chat/completions',
            'console_status': '200 stream',
            'request_label': '入站请求',
            'request_pre': 'POST /v1/chat/completions HTTP/1.1\n'
                           'Authorization: Bearer sk-***\n'
                           'X-Tenant: tenant-a\n'
                           '\n'
                           '{"model":"deepseek-v3.2","stream":true, ...}',
            'protocols': ['OpenAI Chat', 'Claude Messages', 'OpenAI Responses',
                          'Embeddings', 'Rerank'],
            'result': '✔ 200 stream · upstream vllm-a100 · TTFT 218 ms',
            'route_meta': ('选路结果', 'priority · 候选 3 条'),
            'steps': [
                ('shield', '认证与审核', '凭证 + 内容策略'),
                ('layers', '选出渠道', '可见性 → 匹配 → 选择'),
                ('server', '转发并计量', '按上游方言'),
                ('route', '写出用量', 'usage_id 幂等'),
            ],
            'trace': ['moderation pass', 'channel vllm-a100', 'fallback 0/2',
                      'quota 滚动 7 天', 'usage_id usg_018f…'],
            'footer': [('数据面', '只读 Redis 缓存 + gRPC 回源'),
                       ('配置下发', '控制面经 gRPC 热更新'),
                       ('观测', '三层日志 + Prometheus + OTel')],
            'note': '示意流程：字段取自网关真实对象与响应头，延迟为示意值，非实测指标。',
        },
```


## boss · 一次交班巡检

```python
        'flow': {
            'overline': '一次交班巡检',
            'title': '不重算事实，只把事实摆到同一屏。',
            'copy': '每个域的事实源仍在自己那里：算力在 Rune、用量在 AIRouter、'
                    '资产在 Moha、身份在 IAM。BOSS 做的是汇总、比对与分派。',
            'console_label': 'boss · platform overview',
            'console_title': 'GET /api/v1/platform/overview?window=24h',
            'console_status': '3 项待处理',
            'request_label': '巡检请求',
            'request_pre': 'GET /api/v1/platform/overview?window=24h\n'
                           'X-Tenant: tenant-a\n'
                           '\n'
                           '# 返回：风险待办 / 容量水位 / 网关质量 /\n'
                           '#       账号安全 / 资产概览',
            'protocols': ['风险待办', '容量水位', '网关质量', '账号安全', '资产概览'],
            'result': '✔ 3 项待处理 · 1 项高风险（渠道健康度下降）',
            'route_meta': ('汇总来源', '5 个产品域只读'),
            'steps': [
                ('list', '看风险', '待办与告警'),
                ('server', '看容量', '集群与配额'),
                ('activity', '看质量', '成功率与延迟'),
                ('users', '分派处置', '跳到对应产品'),
            ],
            'trace': ['resources → rune', 'metering → airouter', 'assets → moha',
                      'identity → iam', 'license ok'],
            'footer': [('事实来源', '各域只读汇总'), ('角色', 'SRE · 网关运营 · 安全合规 · FinOps'),
                       ('范围', '不含财务结算')],
            'note': '示意界面：字段取自 BOSS 的真实模块，数值为示意值，非实际运营数据。',
        },
```

---

# 收尾 CTA 整段：原文留档（2026-09-11 晚（十一））

晚（十一）删的是**页尾那一整块 CTA**（`.tf-contact-cta-section`），不是它里面的
「进入控制台」链接。起因是用户说「删除『进入控制台』的区域」——「区域」指的正是这张
卡片；澄清时用户把它描述成「想在您的环境里跑 xxx 的那个区域」，于是整段删掉。

它和上面四段 `'flow'` 不一样：**它不是数据块，是一个渲染函数**。`PRODUCTS` 里没有
它的内容，四页共用同一个 `closing(p)`，只有 `<h2>` 里的产品名随 `p['name']` 变。

```
删掉它之后，四页正文只剩：页首（hero）+ 页尾那条代码分隔线（tf-faq-code-divider）。
分隔线是上一轮刻意保留的，本轮也没点名，所以留着了 —— 它原本的语义是「页首与收尾之间的
过渡」，现在后面已经没有段落了。要不要连它一起去掉，是视觉决定，等被点名。
```

## 1. `tools/build_products.py` 里的 `closing()`（逐字原文）

```python
def closing(p):
    links = [('开发者文档', DOCS_URL), ('开源项目', 'https://github.com/kubegems')]
    link_html = ''.join('<a href="%s"%s>%s %s</a>' % (href, ext(href), esc(label), ARROW_S)
                        for label, href in links)
    return (
        '<section class="tf-contact-cta-section text-white tf-motion-section" '
        'style="--tf-motion-order: 6;">'
        '<div class="tf-contact-cta-structure" aria-hidden="true">'
        '<span class="is-crossline"></span><span class="is-bottomline"></span></div>'
        '<div class="tf-contact-cta-shell"><div class="tf-contact-cta-card">'
        '<div class="tf-contact-cta-primary">'
        '<img src="assets/img/cta-dither.webp" alt="" width="566" height="140" '
        'aria-hidden="true" loading="lazy" decoding="async">'
        '<div class="tf-contact-cta-primary-content">'
        '<h2>想在您的环境里跑 <strong>%s</strong>？</h2>'
        '<p>%s</p>%s</div></div>'
        '<div class="tf-contact-cta-secondary">'
        '<p>%s</p>'
        '<div class="tf-products-cta-links">%s</div>'
        '<a class="tf-contact-cta-console" href="%s"%s>%s %s</a>'
        '</div></div></div></section>'
        % (esc(p['name']),
           esc('可以先聊架构，再谈交付：我们有容器云与智算平台的完整私有化经验，'
               '也可以只交付您缺的那一块。'),
           brand_action('联系我们', 'mailto:' + MAIL),
           esc('成都破晓石科技有限公司 · ' + MAIL),
           link_html, CONSOLE_URL, ext(CONSOLE_URL), esc('进入控制台'), ARROW_S))
```

调用点在 `main_markup()`：

```python
    return ('<div class="tf-products-page" style="--tf-product-accent: %s;">' % p['accent']
            + hero(p)
            + divider
            + closing(p)          # ← 这一行删掉
            + '</div>')
```

## 2. 产物里那一段（`/products/rune/`，逐字）

四页只有产品名不同：`rune` 段里 `<strong>Rune</strong>`，另三页分别是 `Moha` /
`AIRouter` / `BOSS`；其余字节完全相同。

```html
<section class="tf-contact-cta-section text-white tf-motion-section" style="--tf-motion-order: 6;"><div class="tf-contact-cta-structure" aria-hidden="true"><span class="is-crossline"></span><span class="is-bottomline"></span></div><div class="tf-contact-cta-shell"><div class="tf-contact-cta-card"><div class="tf-contact-cta-primary"><img src="../../assets/img/cta-dither.webp" alt="" width="566" height="140" aria-hidden="true" loading="lazy" decoding="async"><div class="tf-contact-cta-primary-content"><h2>想在您的环境里跑 <strong>Rune</strong>？</h2><p>可以先聊架构，再谈交付：我们有容器云与智算平台的完整私有化经验，也可以只交付您缺的那一块。</p><a href="mailto:support@xiaoshiai.cn" class="tf-brand-action tf-button tf-button-primary"><span class="tf-brand-action-label" aria-hidden="true"><span style="--tf-brand-char:0">联</span><span style="--tf-brand-char:1">系</span><span style="--tf-brand-char:2">我</span><span style="--tf-brand-char:3">们</span></span><span class="sr-only">联系我们</span><i class="tf-brand-action-corner is-top-left" aria-hidden="true"></i><i class="tf-brand-action-corner is-top-right" aria-hidden="true"></i><i class="tf-brand-action-corner is-bottom-left" aria-hidden="true"></i><i class="tf-brand-action-corner is-bottom-right" aria-hidden="true"></i></a></div></div><div class="tf-contact-cta-secondary"><p>成都破晓石科技有限公司 · support@xiaoshiai.cn</p><div class="tf-products-cta-links"><a href="https://docs.poxiaoshi.cn" target="_blank" rel="noopener noreferrer">开发者文档 <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-arrow-right h-3.5 w-3.5" aria-hidden="true"><path d="M5 12h14"></path><path d="m12 5 7 7-7 7"></path></svg></a><a href="https://github.com/kubegems" target="_blank" rel="noopener noreferrer">开源项目 <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-arrow-right h-3.5 w-3.5" aria-hidden="true"><path d="M5 12h14"></path><path d="m12 5 7 7-7 7"></path></svg></a></div><a class="tf-contact-cta-console" href="https://console.poxiaoshi.cn" target="_blank" rel="noopener noreferrer">进入控制台 <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="lucide lucide-arrow-right h-3.5 w-3.5" aria-hidden="true"><path d="M5 12h14"></path><path d="m12 5 7 7-7 7"></path></svg></a></div></div></div></section>
```

（`.tf-contact-cta-*` 全套类与 `cta-dither.webp` 都来自 vendor 与 `assets/img/`，
**没有被删**：`/about` 页仍在用同一套组件，所以删产品页这一段不涉及 vendor 与图片。）

## 3. 怎么加回来

> **2026-09-11 晚（十三）补充**：那一轮把商务出口全部收口到 `/contact`，`build_products.py`
> 里的 `MAIL` 与 `CONSOLE_URL` 两个常量因此成了死常量、被删掉了，`CONTACT_PAGE = '/contact'`
> 取而代之。所以按下面第 1 步粘回 `closing()` 时，函数体里的 `'mailto:' + MAIL` 与
> `CONSOLE_URL` **必须换成新的落点**（要么写死 `CONTACT_PAGE`，要么自己重新定义这两个
> 常量）—— 否则会得到 `NameError`。归档里那份逐字原文是**当时**的样子，不是现在该有的
> 样子；这也顺带说明：一条链接的落点会随产品口径改变，而「删掉一段」留下的原文不会。

1. 把上面 `closing()` 函数整段粘回 `tools/build_products.py`（位置在原处：`hero()` 与
   `main_markup()` 之间），并在 `main_markup()` 的 `+ divider` 之后补 `+ closing(p)`。
2. 文件顶部的 import 要一起补回来：`ARROW_S`（`from portal_page import …`）与 `ext`
   —— 函数体里 `ext` 用两处、`ARROW_S` 用一处，缺一个都是 `NameError`。
   （`brand_action` / `esc` 是删不掉的，`hero()` 仍在用。）
3. `assets/css/products.css` 里补回 `.tf-products-cta-links*` 三条规则（原文见
   `docs/CODE-REVIEW-2026-09-11.md` §17，或直接照 `about.css` 的
   `.tf-about-cta-links*` 抄一份改前缀）。
4. `guards()` 里把该段的守卫反过来：从 `RETIRED_CLASSES` / `RETIRED_TITLES` 里摘掉
   `tf-contact-cta-*` 与「想在您的环境里跑」，并把 `order` 锚点数组补回
   `'tf-contact-cta-section'`（位置在 `tf-faq-code-divider` 之后）。
5. `--tf-motion-order: 6` 这个槽位值按原文恢复 —— 它是错峰出场的槽位，不是序号，
   别顺手改成 2。

---

# 页首徽标 `tf-product-hero-badge`：原文留档（2026-09-11 晚（十二））

用户原话：「删除四个子产品的 tf-product-hero-badge」。它不是一个段落，是页首左栏
最上面那个 mono 小胶囊（例：`核心产品 · Rune 智算`，右侧一个强调色圆点）——
上游原站 /runtime 页左上角那个 chip 的位置。

## 1. 渲染代码（`tools/build_products.py` 的 `hero()`，逐字）

```python
        '<div class="tf-product-hero-copy">'
        '<span class="tf-product-hero-badge"><i aria-hidden="true"></i>%s</span>'
        # 小标只有「与徽标的间距」这一件事要做，而 mt-6 就是它 —— 不要为这一行再起
        # 一个类名：写过但没有任何规则的类会被 tools/qa/classes.py 当幽灵类拦下，
        # 而为了绕过它去补一条空规则，等于把一个「其实没样式」的事实藏起来。
        '<div class="mt-6">%s</div>'
        '<h1 class="tf-product-hero-title">%s</h1>'
```

`%s` 的第一项是 `esc(p['badge'])`，第二项是 `overline(p['overline'])`。
晚（十二）删掉徽标后，`<div class="mt-6">` 这个包装也一并去掉（它唯一的职责就是
「与徽标的间距」，理由写在上面那段注释里），overline 直接作为 `hero-copy` 的第一行。

## 2. 四条数据（`PRODUCTS[*]['badge']`）

```python
        'badge': '核心产品 · Rune 智算',
        'badge': '核心产品 · Moha 资产',
        'badge': '核心产品 · AIRouter · AI聚合网关',
        'badge': '核心产品 · BOSS 运营',
```

## 3. 产物里那一段（`/products/rune/`，逐字）

```html
<span class="tf-product-hero-badge"><i aria-hidden="true"></i>核心产品 · Rune 智算</span><div class="mt-6"><span class="tf-overline">Rune 智算_</span></div>
```

## 4. CSS（`assets/css/products.css`，逐字）

```css
/* 徽标：mono 大写小胶囊，左侧一个强调色圆点（上游 runtime 页左上角那个 chip 的位置） */
.tf-product-hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.42rem 0.72rem;
  border: 1px solid var(--tf-line-strong);
  border-radius: var(--pxs-radius-pill, 999px);
  background: #ffffff0a;
  color: rgba(255, 255, 255, 0.66);
  font-family: var(--font-mono);
  font-size: 0.66rem;
  letter-spacing: 0.16em;
  text-transform: uppercase;
}
.tf-product-hero-badge i {
  width: 0.4rem;
  height: 0.4rem;
  border-radius: 50%;
  background: var(--tf-product-accent, #9fe9ff);
  box-shadow: 0 0 12px var(--tf-product-accent, #9fe9ff);
}
```

注意：**`--tf-product-accent` 的继承链没有因为删徽标而失守** —— 圆点 `i` 只是它的
使用者之一，页首光晕（`.tf-product-hero:before` 的 `color-mix`）、预览面板的终端提示符
（`.tf-product-preview-line i`）与编号步骤（`.tf-product-preview-steps b`）都还在用。
页根容器那条「强调色只写一次」的守卫不受影响。

## 5. 怎么加回来

1. `hero()` 里在 `<div class="tf-product-hero-copy">` 之后补回上面那两行（徽标 span +
   `<div class="mt-6">` 包装），并把 `%` 参数序列改回去：`p['badge']` 要排在
   `overline(p['overline'])` **之前**（位置错一格会静默把徽标文字渲染成小标）。
2. `PRODUCTS` 四条各自补回 `'badge'` 字段（`'slug'` 附近即可）。
3. `assets/css/products.css` 补回上面两条规则（位置在 `.tf-product-hero-copy` 与
   `.tf-product-hero-title` 之间）。
4. `guards()` 里两处反过来：把 `tf-product-hero-badge` 从 `RETIRED_CLASSES` 摘掉、
   把「核心产品 · 」从 `RETIRED_TITLES` 摘掉，并把 `('badge', p['badge'])` 那条逐字
   落盘断言补回 `for label, needle in (…)` 元组里。

