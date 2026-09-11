# new-portal 前端代码 review（2026-09-11）

首页版式定稿后的一次结构与重复度体检，目标只有一句话：**把该复用的抽出来，别让下一个页面再抄一遍。**

## 1. 审查范围

`new-portal` 只有 `index.html` 一个产物，其余都是手写源码。按三层 + QA 看：

| 层 | 文件 | 角色 |
| --- | --- | --- |
| 生成器 | `tools/reshape_home.py` | 从 pristine 快照派生 `index.html`（唯一真源） |
| 样式 | `assets/css/custom.css` | overrides（`vendor.css` 按约定只读） |
| 交互 | `assets/js/main.js` | 无框架，约 360 行 |
| QA | `tools/qa/*` | 回归断言 |
| 资源生成 | `tools/gen_icons.py` 等 | SVG/图标产物 |

审查判据（硬约束）：**视觉已定稿，本轮只允许等价改动**。
- `index.html`：改动前后 **md5 必须逐字节相同**（`679acda5…`）
- `custom.css`：把 `var()` 展开后与改动前逐条比对 —— 最终差异**只有 6 组刻意删除的死规则**，无任何取值变化
- 死代码判定：类名在 `index.html` + `main.js` 中 **零命中**
- 不做浏览器实跑（当前环境 headless Chrome 不可用，且用户要求不自动验证）

## 2. 发现与处理

| # | 问题 | 影响 | 处理 |
| --- | --- | --- | --- |
| 1 | 子容器填充手工拼切片 `body[:open_tag_end(a)] + items + body[b-6:]`，**4 处**；`-6` 硬编码了 `</div>` 长度 | 容器换成 `<section>`/`<span>` 立刻切错标记，且是静默错误 | 抽 `fill_children()`；偏移改由标签自身推导 |
| 2 | 外链属性串 `target="_blank" rel="noopener noreferrer"` 手写 **8 处** | 漏一处就是行为不一致 | 抽 `ext(href)` |
| 3 | 板块外壳（section→frame→split→sidebar）AIRouter / BOSS **各手拼一遍** | 改一次排版要改两处；做 `/products/*` 落地页会变成第三处 | 抽 `board_section()`，node-id 通过参数带过 |
| 4 | 四个产品的名称/href 在 **4 处**重复：nav 下拉、hero pills、control-plane lanes（4 段手写 `lane()`）、footer 产品列 | 改一个产品名/链接要翻 4 个地方，且容易漏 | 建 `PRODUCTS` 注册表；tabs、lanes、pills、页脚全部由它派生 |
| 5 | 定价卡 4 张 × 3 槽位 = **13 次 `need()`**（约 40 行） | 加第五张卡要再写三段 | 建 `PRICING_CARDS` 表 + 槽位循环（8 行） |
| 6 | 板块色 `#9fe9ff/#d7c5ff/#8affc1/#ffb36b` 在 CSS 里 **22 处、18 种取值**；高频中性色（`#ffffff1a`、`#ffffff6b` 等）另 18 处 | 加第五个板块要重抄一遍色值族 | `:root` 调色板 23 个 token、38 处引用；**四个板色族的内联字面量已归零** |
| 7 | `main.js` 里 `GW` 云平台 tab 组、复制按钮、replay-step 监听：目标选择器 **全页 0 命中**（`#gateway` 板块早已删除） | 死代码 78 行，读代码时要逐个确认「这段还在用吗」 | 删除；另清掉从未被调用的 `cm()` 高亮函数 |
| 8 | `custom.css` 有 6 组选择器在产物 + JS 中零命中（`.tf-gateway-code`、`.tf-reveal/.is-in`、`.tf-block-overline`、`.tf-managed-api-intro` 的两处逗号列表、`.tf-gateway-decision b`） | 死样式让人误判「这个类还在用」 | 删除，并在原处留一行说明；现在全表零死选择器 |
| 9 | `tools/qa/` 12 个脚本，**每个都抄一份 CDP 启动样板**（spawn → 轮询 target → WebSocket → rpc），各有各的端口/profile | 改一次启动参数要改 12 处；`verify2.mjs` 断言的是已删除的 `#gateway` 板块，早已失效 | 抽 `tools/qa/cdp.mjs`（`session()`：导航 + 等水合 + 错误收集 + 截图）；合并/删除 9 个失效脚本 |
| 10 | 跨文件重复串无人看管：`main.js` 重抄了 4 个 lane 类名与 2 条 lucide 路径；`custom.css` 必须留着一条「抵消 vendor 把描边归零」的规则 | 今天已经因此出过一次事故（产品下拉图标全隐形） | `stage_guards()` 新增跨文件断言（含反向自测） |

## 3. 验证方式（都可复跑）

```bash
cd new-portal

# 1) 产物逐字节不变 + 守卫全绿（含跨文件断言）
python3 tools/build_all.py              # 总入口：四个生成器 + links.py，末尾必须打印 pipeline ok
md5 -q index.html                      # 679acda5200afc9ca1475cc303fcf3da  ← 见第 8 节，此值已随改动更新

# 2) CSS 只做了等价替换：展开 var() 后与改动前逐条比对
#    结论：差异只有 6 组刻意删除的死规则，无取值变化（23 token / 38 引用全部能还原）

# 3) 死代码判定：类名在 index.html + main.js 中零命中
#    结果：custom.css 已无零命中选择器

# 4) JS 语法
for f in tools/qa/*.mjs assets/js/main.js; do node --check "$f"; done

# 5) 反向自测（改坏即报错）
#    - 改 main.js 的 'tf-control-boss' -> 守卫报 "no longer drives"
#    - 改任一共享 lucide 片段     -> 守卫报 "lost the shared glyph fragment"
#    - 删 custom.css 的描边覆盖   -> 守卫报 "lost the 产品 dropdown stroke override"

# 6) 浏览器回归（当前环境未跑，需要时手动执行）
python3 -m http.server 8899 &
node tools/qa/reshape.mjs http://127.0.0.1:8899/index.html   # 结构 + 交互断言
node tools/qa/page.mjs    http://127.0.0.1:8899/index.html   # 错误/资源/四档视口溢出
node tools/qa/page.mjs    http://127.0.0.1:8899/index.html --shots tmp/shots
```

## 4. 刻意没做的（及原因）

1. **`main.js` 里仍有一份产品数据**（`CONTROL[].title/desc`、`AUDIT` 四条记录）。它和 Python 的 `PRODUCTS` / `ICON_*` 是同一份信息的第二份拷贝，理想做法是把这些抽成 `assets/data/*.json`，由生成器内联成 `<script type="application/json">`，`main.js` 同步读取（不引入 `fetch`，`file://` 下也能用）。**本轮没做：当前环境跑不了 headless Chrome，改交互逻辑无法验证。** 反过来说，只要它能被验证，这是下一步收益最大的一处去重。
2. **`vendor.css` 内的死规则**（`.tf-managed-api-*`、`.tf-footer-status`、`.tf-gateway-code`、`.tf-advantage-*`、`.tf-harness-*`）保持原样。它是编译产物，按既有约定不手改。
3. **`data-page-node-id` 常量**：散在替换里，可提成命名表，但改动面大、收益一般（node id 只在本脚本内闭合使用）。
4. **`stage_harness()` / `stage_xcmp()` 已是空壳**：前者只剩「把定价区排到 blog 之前」，后者只剩一次 `cut_section`。名字与内容不符，建议改名或并入 `stage_pricing()`；本轮保留原样以免打乱既有调查路径。

## 5. 给后续开发的用法（做 `/products/*` 落地页时）

- 新增板块 → 只写数据：`PRODUCTS` 加一条（名称/文案/`page` 站内路径/口径色），nav、hero、control-plane、页脚自动跟上。（2026-09-11 晚更新：字段由「旧站 href」改为「站内 `page`」，见第 13 节。晚（九）+晚（十）又删掉了 `caps` / `detail` / `boundary` / `flow` 四个字段与那份「图标 key」—— 现在一条产品只剩 `slug / name / sub / accent / card / badge / overline / title / lede / meta / actions / preview`，见第 16 节的页面形态说明。）
- 产品子页的正文只剩两块（页首 / 代码分隔线，见 `build_products.py` 的 `main_markup`；
  2026-09-11 晚（十一）起连收尾 CTA 也删了，见 §17）。要加回内容是正常需求，但**先把
  `guards()` 里的 `RETIRED_IDS` / `RETIRED_CLASSES` / `RETIRED_TITLES` 三张名单里对应
  那条摘掉，并把 `main_markup` 里那句「正文应有 2 块」的计数一起改掉**，否则构建直接报
  「已删段落回来了」/「正文应有 2 块」；被删段落的逐字原文（含 `closing()` 源码）在
  `docs/archive/products-deleted-sections-2026-09-11.md`。
- 新增整块版面（首页）→ 用 `board_section(id, order, overline, title, copy, link, panel, ...)`，不要从 `index.html` 复制再改。（这是首页 `reshape_home.py` 的用法；产品页没有这个函数。）
- 新增颜色 → 加进 `:root` 调色板，不要在规则里写裸 hex。
- 改完必须 `python3 tools/build_all.py`（总入口，按依赖顺序跑五个生成器 + 静态体检；
  顺序不能颠倒，后四个生成器都从 `index.html` 取站芯）。`md5` 变化说明改动真的落进了产物；守卫报错一律先修再说。
- **接第三方服务**（表单托管、地图、统计）→ 走「占位符 + 环境变量 + 降级」三件套，别把 key 写死：
  读 `os.environ`，回落占位符，CI 从 Secret 注入。见 `build_contact.py` 的
  `WEB3FORMS_ACCESS_KEY` / `TENCENT_MAP_KEY` 与 `.github/workflows/deploy-pages.yml`
  里的 guard 步骤（那条 `grep -rIl` 会拦住任何把真值抄进源码目录的提交）。
- **改站芯上的东西（nav / footer）时先数出现位置**：一个导航组通常有「桌面下拉 +
  移动抽屉 + 页脚」三份，每份 node-id 都不同。见 9.1。

## 6. 仍未确认的老问题（与本轮无关，等你拍板）

1. ~~`AiIRouter · AI聚合网关` 里多出的 `i` 是否笔误~~ —— **已确认是笔误，2026-09-11 已修正**。
   实际只有两处：`tools/reshape_home.py` 的板块数据常量与 `stage_guards()` 的 required 断言
   （原判「`assets/css` 也有」不准，那里本就没有这个串）。产物是派生的，重跑即同步。
   `AiIRouter` 现已进 `stage_guards()` 的 leftover 列表，改回去会被守卫咬。另加一条同源断言见第 7 节。
2. ~~全站仍有多处 `AIRouter 网关` / 旧品牌字样是否统一改名~~ —— **2026-09-11 用户拍板：
   统一为 `AIRouter · AI聚合网关`，已全站落地，见第 8 节。**
3. 四板块编号不统一（Rune 无编号，Moha/03/04 有）。
4. CTA 用「构建」、正文用「构筑」是否统一。

## 7. 2026-09-11 晚：博客卡封面同源 + `AiIRouter` 笔误修正

### 7.1 封面同源（首页 ↔ `/blog` 详情页）

之前首页三张卡的封面是换牌时自造的 `assets/img/blog/cover-*.png`（近黑底线稿），
而 `/blog` 详情页用的是内容源 `cover:` 指向的 `assets/img/news/*`（线上原图），
同一个站点两处各说各话。

现在首页不再自己写图名：`tools/reshape_home.py` 新增 `post_cover(slug)`，从
`content/blog/<slug>.md` 的 `cover:` 读——与 `tools/build_blog.py` 同一个来源。
**这是结构性的同源，不是靠两处对齐出来的**：改一次 md，首页与详情页同时变。
已实测（把 cover 换成同目录另一张真实图，重跑两个生成器，两处都跟着换了；恢复后回原状）。

顺带归位了图片框的处理档位：前两张卡补上 `.is-wide-art`（`scale(1.04)` +
`object-position:center`），与第三张一致。换牌时三张是**为这个容器程序化生成的
近黑底亮线稿**（见 `tools/gen_blog.py` 文件头），默认档 `scale(1.3)` 那种强放大
裁切对线稿是加分；现在是实拍照片与品牌图，构图本身有意义、不该被裁。

### 7.2 一并调整了封面在首页的处理档位（`custom.css`）

`tools/gen_blog.py` 的文件头记着一件事：`.tf-blog-image-frame img` 的
`opacity:.38 + grayscale + contrast(.9) + brightness(1.1) + scale(1.3)` 会把
「中间调的图」变成 *a featureless grey smear* —— 那批线稿正是为此才生成成近黑底的。
封面图源换掉之后这一档就不再合适，`custom.css` 末尾按「照片」重新定档
（`opacity:.5` + `brightness(.5)`，压低而不是抬亮）。**这一处只有静态推算，需要目视确认。**

### 7.3 验证

新增守卫（`stage_guards` / `stage_blog_cards`）：`assets/img/blog/` 与 `AiIRouter`
进 leftover 列表；产物里三张封面必须是内容源声明的那三张；`src="assets/img/news/`
恰好 3 处；`is-wide-art` 恰好 3 个。反向自测（子进程 + 真实改内容源）：
内容源被删 / 缺 `cover:` 字段 / cover 指向不存在的文件 → 各自报错并带出连锁的
leftover 断言；`AiIRouter` 改回去 → 报 `leftover copy: AiIRouter`。

### 7.4 后续

`assets/img/blog/` 三张旧封面（688 KB）已于当日 16:50 按用户确认删除，目录一并移除。
`tools/build.py` 里那三条资源映射保留无害：该脚本的输入 `dom.html` 与输出
`../xiaoshi-cloud/` 都已不存在，是条彻底失效的历史流水线（输出目录也不在 new-portal，
它对应的是更早的换牌目录），那三条是死引用。
**（2026-09-11 晚补记：`tools/build.py` 连同它读的两份上游快照
`tools/ref/dom.html` / `tools/ref/<上游样式表>.css` 已在品牌清理里整体删除，
这条「保留无害」的结论随之作废 —— 死引用没有了，死管道也没有了。）**

## 8. 2026-09-11 晚（二）：AIRouter 品牌写法统一

### 8.1 决定

用户拍板：AIRouter 的定位词统一为 **`AIRouter · AI聚合网关`**。此前四种说法并存
（`AIRouter 网关` / `AIRouter · 模型网关` / `AIRouter 统一网关` / `AIRouter 统一模型网关`），
`assets/js/main.js` 里还有第五种 `AIRouter 统一模型入口`。

### 8.2 分类处理（关键：这不是一次全字符串替换）

` · ` 在这套设计里是**标签用的主副分隔符**。正文句子里直接塞进去会和句读打架，
所以按两类处理：

| 语境 | 写法 | 位置 |
| --- | --- | --- |
| 标签 / 品牌串 | `AIRouter · AI聚合网关` | title、meta、hero pill、控制平面 lane、板块 overline、footer 产品列、nav 下拉描述、console 下拉、`main.js` tab 描述 |
| 正文句子 | `AIRouter` + 定位词的自然语序 | story 并列句（`AIRouter 聚合网关`）、`AIR_COPY`（`AIRouter 是晓石云的 AI聚合网关：`）、FAQ（`AIRouter 聚合网关，`）、定价（`AI聚合网关随订阅开通`） |

另外 **title 与跑马灯的四板块并列串把分隔符从 `·` 改成了 `/`**：

```
旧：Rune 智算 · Moha 资产 · AIRouter 网关 · BOSS 运营
新：Rune 智算 / Moha 资产 / AIRouter · AI聚合网关 / BOSS 运营
```

否则分层作用会被淹没——五个 ` · ` 连成的串会被读成五个板块，与「四大核心板块」的
既定叙事打架。`/` 只在这两处出现，职责是「`/` 分板块、` · ` 分主副」。

### 8.3 改动点（产物是派生的，源码只动了这些）

- `tools/reshape_home.py`：`PRODUCTS` 的 AIRouter 条目（`sub`/`desc`/`short`/`pill`/`lane`）
  加 `stage_head` / `stage_story` / `stage_faq` / `stage_pricing` / `AIR_COPY` / docstring
- `assets/js/main.js`：控制平面 tab 描述
- `tools/build_about.py`：about 页「…延伸到 AI 智算、资产仓库、AI 聚合网关与运营平台。」
- `tools/qa/reshape.mjs`：5 条期望值同步（footer 产品列 / hero pills / 板块正文 /
  定价正文 / 标题），并把标题断言从「含 Rune Harness」加强为**逐字相等**

关键杠杆：`pill[0]` 同时喂 hero pills 与 footer 产品列（`:466` / `:974`），
`name`+`desc` 喂 nav 下拉、`short` 喂 console 下拉 —— 所以改一处等于四处同步。

### 8.4 验证

- 首页产物 `AIRouter · AI聚合网关` 恰好 **16 处**：title 1 + meta 1 +
  跑马灯 10（无缝滚动把一条文案复制成 10 份）+ hero pill 1 + 控制平面 lane 1 +
  板块 overline 1 + footer 产品列 1 → 已固化成**计数断言**（`got != 16` 即报错）
- 每个内页 11 处（跑马灯 10 + footer 产品列 1）——站芯变化经重建传导到全部内页
- 旧写法全站残留 **0**（含 `AiIRouter`、`模型网关`、`统一模型网关`、`统一模型入口`）
- 新增 leftover 守卫 6 条：`AIRouter 网关` / `AIRouter · 模型网关` / `AIRouter 统一网关` /
  `AIRouter 统一模型网关` / `统一模型网关` / `统一模型入口`。注意 `AIRouter 网关`（空格）
  与正式写法 `AIRouter · AI聚合网关`（点号）不是子串关系，能咬住回退
- 三生成器幂等通过；`links.py` 8 pages / 218 in-site links / no broken；
  `node --check assets/js/main.js` 通过。**未做浏览器验证。**

### 8.5 仍待办

首页与内页 footer 里 `AIRouter · AI聚合网关` 的链接仍指向旧站外链
`https://www.poxiaoshi.cn/products/ai-router/`（全站 ×5）。等新站自建 `/products/*`
落地页时这里要一并换掉——与第 6 节第 3、4 项无关，是链接迁移问题，不是改名问题。

## 9. 2026-09-11 晚（三）：导航「关于我们」三项调整 + 新建 `/contact`

用户要求：①「开源项目」改为跳转 https://www.kubegems.io/ ；②删除「加入我们」栏目；
③按原站（换牌前的参考站）的 /contact 样式完善「联系我们」栏目，内容取自
https://www.poxiaoshi.cn/contact/ ，表单用 web3forms、地图用腾讯地图。

### 9.1 导航下拉：两份都要改

「关于我们」下拉在页面上有**两份**：桌面下拉（`.tf-nav-company-dropdown`）与移动抽屉
（`「关于我们」` 标题下那个 `.grid.gap-2`），各有自己的内联图标与 `data-page-node-id`。

做法是**定向修补**而不是重写整个下拉（`reshape_home.py` 的 `stage_nav_company`）：
五个 item 各带自己的图标，重写等于把图标全搬一遍，还会丢掉那条被其他 stage 用来
精确落位的 DOM 血缘。定位一律用 node-id 而不是文本——这次改的正是文本。

* 开源项目：`/affiliates` → `https://www.kubegems.io/`，站外自动补
  `target="_blank" rel="noopener noreferrer"`
* 加入我们：整项移除（含图标）。招聘入口本来就在 about 页的招聘条上，
  导航里指着一个不存在的 `/careers` 没有意义

**页面外的两处连带**（用户没明说，做了并在此标出，可否决）：
页脚社交区的「联系我们」图标原先指向旧站 `https://www.poxiaoshi.cn/contact/`，
站内页建好后改指 `/contact`；否则同名的「联系我们」在两个域名下打架。

**两个差点翻车的点**：

1. `match_close()` 返回的是「闭合标签**之后**」的索引（看它的 docstring）。
   删项时若照着别处的习惯再 `find('>')` 一次，终点就会越过紧随其后的
   `<a …>` 开标签，把下一项也吃掉 —— 症状是「联系我们」凭空消失，
   而 `/careers` 计数归零、看着像是改对了。现在守卫逐项断言八个 node-id，
   专门咬这种情况。
2. node-id 是大小写敏感的。`gqYzTmgj4gK6ap8EQFrzhA` 里的 `F` 我抄成了 `f`，
   守卫报缺项、肉眼比对字符串看不出来，最后靠逐字符 hex 比对才定位。

连带修正：`portal_page.py` 的导航图标计数断言从 9 改为 8（产品 4 + 关于我们 4），
它是所有内容页共用的站芯指纹的一部分。`tools/qa/links.py` 的 `NOT_BUILT_YET`
移出 `/contact`（它开始受正式检查保护）。

### 9.2 `/contact` 页：样式几乎全现成

原站的 /contact 实际返回的是首页（原站没有独立联系页），但**版式不用猜**：
vendor.css 里已经躺着整套 company 组件族 —— `.tf-company-contact-layout`
（`minmax(0,1.35fr) minmax(18rem,.65fr)` 两栏）、`-form`、`-aside`、`-message`、
`.tf-company-form-success` / `-error`、`.tf-company-kicker` / `-section` 全都有规则，
最初来源就是原站那份样式表（`tools/ref/` 里的备份已在 2026-09-11 品牌清理时删除）。
这是「换牌站点的 vendor.css 里可能已有现成组件」
的又一例：写页面前第一件事就是 grep vendor.css。

于是新增的只有三块（`assets/css/contact.css`）：
1. 把原站的品牌橙换成本站调色板（`.tf-company-contact-form button` 从实心橙
   改成白底深字，对齐 `.tf-button-primary`；aside 渐变改成 `--tf-rune-4`）
2. 补 vendor 没覆盖的：页首、联系方式行、地图容器、地图降级卡
3. 表单的校验态与结果槽位

三件套：
* `tools/build_contact.py` —— 页面生成器（复用 `portal_page.py`，depth=1）
* `assets/css/contact.css` —— 6.7 KB
* `assets/js/contact.js` —— 表单提交 + 地图初始化

内容逐字取自旧站 contact 页：标题「与我们对话未来云与 AI」、副标题、五个表单字段
（姓名/公司/邮箱/电话/需求描述）连各自的 placeholder、三条联系方式。邮箱在线上被
Cloudflare 邮箱保护混淆成 `[email protected]`，解码后取回 `support@xiaoshiai.cn`。

### 9.3 两个外部凭据：走 GitHub Secret，构建期注入

两个都是**前端凭据**——注定出现在产物的 HTML 里。web3forms 靠收件方校验、腾讯地图
靠 key 白名单兜底，**不是靠把 key 藏起来**。所以纪律是「不进源码」，而不是
「不影响产物」：仓库里永远只有占位符，真值在 GitHub Secret，CI 构建时注入。

| 用途 | 环境变量 / Secret 名 | 未注入时 |
| --- | --- | --- |
| web3forms 表单收件 | `WEB3FORMS_ACCESS_KEY` | 回落占位符，只 WARN 不失败；提交被 web3forms 拒收，错误落到 `.tf-company-form-error`（**不静默丢单**） |
| 腾讯地图 | `TENCENT_MAP_KEY` | 回落 `_TMapSecurityConfig` **代理模式**（本机预览可用），线上走降级卡 |

解析优先级：**进程环境变量 > 仓库根 `.env.local`（已 gitignore）> 占位符**。
两个 Secret 已写入 `poxiaoyun/new-portal`；名字与上游 `poxiaoyun/portal` 的
`NEXT_PUBLIC_*` 版**故意不同**，因为本站不是 Next.js，`NEXT_PUBLIC_` 前缀会误导
人以为有构建期插值机制。

**腾讯地图两种模式互斥**（`build_contact.py: inject_scripts()`）：

- **直连**（有 `TENCENT_MAP_KEY`）：SDK 带 `key=` 参数从官方 CDN 加载，
  **不挂** `_TMapSecurityConfig` —— 两者并存会得到一张空白地图。
- **代理**（无 key）：`_TMapSecurityConfig` 必须在 SDK 之前，SDK 不带 key 参数，
  `__WB_HTTP_PORT__` / `__WB_TMAP_SECRET__` 两个占位符**原样保留**，由本机预览层
  运行时替换。`serviceHost` 指向 `127.0.0.1`，线上必然连不上，所以线上必须走直连。

两种模式都失败时 `contact.js` 退到降级卡（地址文字 + 腾讯地图网页版链接）。降级是
**设计好的，不是故障**：SDK `onerror` 打标 + `typeof TMap === 'undefined'` 两条判定，
任一条成立就切卡，页面不会留一块空白。地图容器也不传 `mapStyleId`（自定义样式需在
控制台单独开通，默认 key 用不了）。

坐标取 `30.540905, 104.05972`（GCJ-02），与旧站 `<meta name="ICBM">` 里的那一对
完全一致——**不做 WGS-84 转换**，腾讯地图本来就用 GCJ-02。

⚠️ **本地产物默认是占位符**：这样提交进仓库的那份 HTML 不含凭据。想在本地看到真地图
/ 真提交，把两个值写进 `.env.local` 再跑一次构建即可（同一份生成器，只是喂了真值）。

### 9.4 部署：`.github/workflows/deploy-pages.yml`

本站是「**生成器 + 提交产物**」的静态站，所以 CI 不能只 upload 目录，必须在云端
**重跑生成器**才能把 Secret 注进页面。工作流三步，缺一不可：

1. **Guard**（排在 build **之前**）——`grep -rIl` 扫 `tools assets content docs`，
   命中任一个 Secret 的真值就 fail。顺序不能反：构建会把凭据写进
   `contact/index.html`，之后再扫必然命中。只扫源码目录，不扫生成产物
   （产物里带 key 是设计如此）。
2. **Build** —— `python3 tools/build_all.py`。这是本轮新增的总入口，
   把四个生成器的**顺序**收在一处（`index.html` 必须先就位，后三个都靠
   `portal_page.derive()` 从它取站芯，且 `derive()` 会断言首页一字节未改）。
   跑完接 `qa/links.py` 静态体检。
3. **Stage + upload** —— 只把 `index.html .nojekyll assets about blog contact`
   拷进 `dist/` 上传。`tools/` `content/` `docs/` **不上线**（否则
   `docs/CODE-REVIEW-2026-09-11.md` 会变成公开可下载）。

配套改动：

- 新增 `.gitignore`：`.env.local`、`dist/`、`.DS_Store`。此前仓库没有 gitignore。
- 启用 Pages（`build_type=workflow`，无 CNAME）：`https://poxiaoyun.github.io/new-portal/`。
  **未设置 CNAME** —— `www.poxiaoshi.cn` 目前仍由 `poxiaoyun/portal`（Next.js）提供服务，
  两个仓库不能同时声明同一个域名。
- 触发条件只有 `main` + `workflow_dispatch`。**注意**：`workflow_dispatch` 的入口
  只有在工作流文件落到默认分支之后才会出现在 Actions 里，所以合并到 `main` 之前
  一次也跑不起来。

### 9.5 验证

四生成器加 contact 全部幂等通过（跑两遍 md5 一致）；`links.py` **9 pages /
214 in-site links / no broken**，`/contact` 从「not built yet」转为正式检查；
`node --check` 通过 contact.js 与 reshape.mjs；导航改动的反向自测做过
（把「加入我们」的 node-id 改成「联系我们」的，守卫报出 4 条：leftover `/careers`、
两个 node-id 缺项、`/contact` 计数不符）。

本轮新增的三条验证：

1. **两种地图模式各构建一次**：直连模式断言「SDK 带 key 且无 `_TMapSecurityConfig`
   且无代理占位符」，代理模式断言「有 `_TMapSecurityConfig` 且 SDK 不带 key」——
   互为反向，改坏任一边都会报。凭据缺失时只 WARN，构建照常成功。
2. **`.env.local` 回落**：写入两个值但不 export 环境变量，构建同样走直连模式；
   `git check-ignore -v .env.local` 确认被 `.gitignore` 第 3 行拦住。
3. **白名单腐化守卫**（`qa/links.py`）：临时把 `/careers` 加回 `NOT_BUILT_YET`
   再跑，报 `stale whitelist entry: /careers (加入我们) — nothing links to it any more`。
   这条是新加的：白名单里留着没人引用的条目，会让汇总行继续谎称「这些还没建」。

**未做浏览器验证**（按既定纪律，等明确要求）。

### 9.6 仍待办

1. ~~web3forms access_key~~ / ~~线上腾讯地图 key~~ → 已进 GitHub Secret（见 9.3）
2. 合并到 `main` 后手动触发一次 `Deploy to GitHub Pages`，确认两边凭据都注进去了
   （看产物里 SDK 是否带 `key=`、表单 `access_key` 是否非占位符）
3. 到 web3forms 后台把 `poxiaoshi.cn` 域名加进白名单，到 lbs.qq.com 给这个 key
   配域名白名单——**这才是这两个前端凭据真正的防线**
4. 降级卡里那个 `map.qq.com` 带参链接没有实际点开验证过——它不带 key，
   但腾讯网页版对参数的容忍度需要目视确认
5. 页脚「公司」列还有两条指向旧站：`https://www.poxiaoshi.cn/about/`（站内已有
   `/about`）与 `mailto:` 那两条联系方式。本轮没动，等你定
6. **是否切域名**：新站现在挂在 `poxiaoyun.github.io/new-portal/`，`www.poxiaoshi.cn`
   还在旧的 Next.js 站上。要切换得先摘掉旧仓的 CNAME，再给新仓配上

## 10. 2026-09-11 晚（四）：页首贴住顶栏 —— 「幽灵类」修复 + 新的静态守卫

### 10.1 症状与真因

`/about` 与 `/contact` 的页首，`.tf-overline` 胶囊（「关于破晓石_」「联系我们_」）
视觉上压住了 fixed 顶栏。

真因**不是间距给少了，是写的间距根本没生效**。两页的 hero 类串一样：

    px-6 pb-16 pt-4 md:px-8 md:pb-20 lg:px-20

其中 **`pt-4` / `pb-16` / `md:pb-20` 三个在 vendor.css 里一条规则都没有**。
vendor.css 是上游 Tailwind 的**编译产物** —— 上游用过什么类，才有什么类；我们
手写的工具类不在其中。于是：

* 水平方向一直正常 —— `px-6` / `md:px-8` / `lg:px-20` 都存在（且写的是
  `padding-inline`，与垂直方向的 `padding-top` 不打架）
* 垂直方向 padding 全是 0 —— 页首直接贴住顶栏。顶栏 `fixed` 只为它留了
  116px 占位，紧贴看起来就像压上去

**为什么光看页面发现不了规律**：首页与 `/blog` 页一个幽灵类都没有。所以这不是
「整体设计偏紧」，而是这两页独有的缺陷 —— 只有把 HTML 里的类名逐个拿去样式表里
比对才看得出来。

全站扫描结果：产物里 23 个类没有对应规则，其中 **19 个是 `lucide-*`**（图标库靠
SVG 自身属性画，本来就不该有 CSS）、2 个是 JS 钩子（`hover-scramble`、
`tf-thinking-track`），**真缺陷只有那 3 个**。

### 10.2 修法：把垂直间距从类名挪进 CSS

`pt-4` / `pb-16` / `md:pb-20` 三个类从两个生成器的 hero 类串里删掉，改在两页各自的
CSS 里用真规则写：

```css
/* assets/css/about.css 与 contact.css，各自对同名 hero 选择器 */
.tf-about-hero {
  position: relative;
  overflow: hidden;
  padding-top: clamp(2rem, 4.2vw, 3.5rem);     /* 32 → 56px */
  padding-bottom: clamp(4rem, 6vw, 5rem);      /* 64 → 80px */
}
```

三个理由：

1. **不再依赖「上游恰好编译过这个类」**。写 `clamp()` 还能拿到连续响应式，
   比 `md:` 断点跳变更平滑。
2. **不出优先级问题**。`px-*` 用的是 `padding-inline`（逻辑属性），
   我们设 `padding-top` / `padding-bottom`，方向不重叠；两页 CSS 又都排在
   `vendor.css` 之后加载，同特异性下后写者胜。
3. **`:before` 装饰层不受影响**。页首的径向光晕是 `position:absolute; top:-14rem`
   定位的，不是 `inset:0`，padding 变化不会让它错位。

`custom.css` 里没有任何 `.tf-*-hero` 规则，无第三方覆写风险。

### 10.3 新增守卫：`tools/qa/classes.py`

这类缺陷**不报错、不 WARN、纯静态可查**，正适合做成门禁。新脚本把产物 body 段的
class token 逐个做 CSS 转义，查 `.<转义后>` 是否出现在任一样式表里（assets/css/**
全部 + 各页内联 `<style>`）。

白名单是**必要**的而非图省事 —— 图标库与 JS 钩子本来就没有 CSS 规则：

```python
EXACT_HOOKS = {'hover-scramble', 'tf-thinking-track'}
PREFIX_HOOKS = ('lucide', 'is-')
```

同 `links.py` 的 `NOT_BUILT_YET` 一样，白名单里**长期没人命中的条目也会报错**
（stale）—— 避免它退化成「把报错压下去的地方」。第一版白名单写了 `group` /
`peer` / `js-` 三条「预防性」豁免，一跑就全报 stale，正好证明这条检查有效；
那条设计也顺势改成了「只登记当前真的用到」。

接进 `tools/build_all.py` 的统一体检（`CHECKS`），`--check` 与全量构建都会跑：

```
ok — 9 pages, 1838 class token, 510 distinct
ok — 9 pages, no ghost class, 4 hook pattern(s) still live
pipeline ok: 4 generators + 2 static checks
```

### 10.4 验证

* 幂等：`about` `3fbe4fa6…`、`contact` `67b69c19…`，复跑不变；`index.html`
  `ed8f1398…` **未受影响**（站芯没动）
* `links.py` 9 pages / 214 links / no broken；`classes.py` 0 幽灵类
* **反向自测两条**：往产物 hero 里塞回 `pt-4` → 报 `about/index.html: pt-4`；
  给白名单加一条假豁免 → 报 `stale hook whitelist entry: zzz-no-such-hook`
* **未做浏览器验证**（按既定纪律）

改动文件：`tools/build_about.py`、`tools/build_contact.py`（删幽灵类）、
`assets/css/about.css`、`assets/css/contact.css`（补真 padding）、
`tools/qa/classes.py`（新增）、`tools/build_all.py`（接入体检）。

### 10.5 遗留

**同一类坑可能还在别处**：这次只查了「间距类」，`classes.py` 目前是全量查的，
但白名单是按前缀放的 —— 哪天在生成器里写了个不存在的字号/颜色类，它会报，
按提示补 CSS 即可。**真正要记住的判断是**：`vendor.css` 里没有的 Tailwind 类，
写了等于没写；发现样式「明明写了却不生效」，第一件事是把类名拿去 vendor.css
里搜一下。

### 10.6 后续（同一晚）：一次被缓存误导的排查

改完请用户目视复核，反馈「contact 页对了，about 页还是没对」。两页的 CSS 规则、
link 顺序、HTML 结构都是等价的，于是先算清三件事：

| 文件 | `.tf-about-hero` | `.tf-contact-hero` |
| --- | --- | --- |
| `vendor.css` | 1 条（position / overflow / `border-top` / `border-bottom`） | **0 条** |
| 本页 CSS | position / overflow + `padding-top` / `padding-bottom` | 同一组声明，**逐字相同** |

垂直 padding 两页逐字相等 → 代码侧不可能产生差异。再核服务器侧：
`curl` 回的 `about.css` md5 与磁盘一致（含 5 处 `padding-top`），`/about/` 返回的
hero class 也已无 `pt-4`。**结论：浏览器拿的是缓存副本。**

为什么只有 about 页中招：它是既有页面，浏览器里早就存着旧 HTML + 旧 CSS；
contact 是新页面，第一次访问。同一次改动两页表现不同，纯粹是缓存命中的偶然。

排查中又踩一次老坑：`grep -n "padding-top\|padding-bottom"` 返回**空**，一度以为
服务器内容不对 —— 其实是 BSD grep 单文件模式不认 `\|`（记过的坑）。换成
`grep -c "padding-top"` 立刻得到 5。

### 10.7 顺带修掉的根因：本地预览服务不禁缓存

`python3 -m http.server` 不发 `Cache-Control`，浏览器按启发式缓存（大致是
Last-Modified 至今的 10%）自行决定新鲜期 —— 改完刷新看到旧样子，就会去翻代码，
白费一轮。新增 `tools/preview.py`：同一个 `SimpleHTTPRequestHandler`，但统一发
`Cache-Control: no-store, no-cache, must-revalidate, max-age=0` + `Pragma: no-cache`
+ `Expires: 0`，并且只打印 4xx / 5xx 日志。**只用于本地预览**，线上不能这么干。

```bash
python3 tools/preview.py --port 8899      # 也就换掉原来的 python3 -m http.server
```

换服务只对新请求生效：浏览器里已有的旧副本要**硬刷新一次**才会被换掉
（`Cmd+Shift+R`），之后 `no-store` 接管，改完刷新即最新。

### 10.8 未动的一处不对称 + 一个线上隐患

**`about` 页在 `vendor.css` 里比 contact 页多一条 `border-top`**（1px / 10% 白）。
它落在 section 顶边、也就是顶栏底线上，与顶栏自己的
`box-shadow: 0 1px #ffffff14` 叠在一起。判断是 vendor 给「完整版 hero」（带
`-shell` / `-copy` / `-graphic` 网格那套）留的，我们的简化版 hero 用不到。
`border-bottom` 画在 hero 底部，截图里可见，像是想要的区块分隔线，**所以没动**。
要不要去掉 `border-top`（让两页 hero 完全对称）等你定。

**线上隐患**：GitHub Pages 默认给资源发 `max-age=600`，而 CSS / JS 的 URL 不带版本
串 —— 以后改样式上线，10 分钟内回访的用户会看到旧样式。彻底解法是在
`portal_page.py` 生成 link 时追加 `?v=<内容短哈希>`，但那会牵动
`chrome_fingerprint` 的「站芯逐字节相等」不变量（首页与内页都得一起变），
需要单独一轮做。本轮未动。

## 11. 2026-09-11 晚（五）：顶层菜单「解决方案」改指演示站

### 11.1 改动

「解决方案」原本指向旧站的 `https://www.poxiaoshi.cn/products/`（新站没有这个
路径）。改为 `https://ppt.poxiaoshi.cn/#slide-1`（演示站第一页，已确认返回 200）。

它是**顶层菜单项**（`.tf-nav-menu-link`）而不是下拉项，`reshape_home.py` 里为此
新增 `NAV_MENU_RETARGET` + `stage_nav_menu()`，复用上一轮为「关于我们」写的
`retarget_nav_item()`（按 node-id 定位、校验旧 href、站外自动补
`target`/`rel`）。执行序列里插在 `stage_nav` 之后。

| 位置 | node-id | 结果 |
| --- | --- | --- |
| 桌面顶层 | `YR7a557saso22RZ5nfXC1O` | ✅ 指向演示站，开新窗 |
| 移动抽屉 | `Woje1sxC8xj3MiPZ2Cg9sr` | ✅ 同上 |

### 11.2 改之前先确认「只改这一处」

裸 `https://www.poxiaoshi.cn/products/` 在 nav 里**恰好 2 处**（就是上面这两处）；
另外 9 处是 `products/rune/`、`products/moha/`、`products/ai-router/` 这类**带子
路径**的（产品下拉 + console 下拉 + 抽屉产品组），不是同一个 href。
守卫按**带引号的精确形态** `www.poxiaoshi.cn/products/"` 断言旧值归零 ——
换成不带引号的 `products/` 会把那 9 处也一起咬住，误报。

### 11.3 顺带核对的两件事

* `ext()` 对 `http` 开头的 href 自动补 `target="_blank" rel="noopener noreferrer"`，
  桌面项原本没有 target（上游顶层项是同窗口跳转、抽屉项带 target，本身就不一致），
  现在两处统一为开新窗 —— **这条你没明说，可否决**。
* 四个内页的站芯派生自首页，改完重建后每页都是 2 处链接（`index` / `about` /
  `blog` / `contact` 各 2），无需逐页改。

### 11.4 验证

* 幂等：`index` `213c7d3c…`、`about` `d32440b6…`、`blog` `459c0410…`、
  `contact` `30c5f457…`
* 体检全绿：`9 pages / 214 in-site links / no broken` + `no ghost class`
* 反向自测：把抽屉侧 node-id 改成不存在的值 → 守卫报 4 条（锚点缺失、1/2 未生效、
  链接实得 1 处、旧 href 残留），能咬住「只改看得见的那一份」
* 新增 QA 探针 `navMenu` + 1 条断言（`tools/qa/reshape.mjs`）
* **未做浏览器验证**（按纪律）

### 11.5 探针踩到的两个坑（写探针时踩的，不是页面问题）

1. `.tf-nav-menu-link` 这个类**同时用在 `<a>` 与 `<button>`** 上（产品、关于我们
   两个下拉 trigger 都是 button），所以探针取到的 7 项里有 2 项 `href` 为 `null`；
   断言必须**按 label 查找**而不是按索引，否则上游增删一项就漂。
2. 标签外面套着 `tf-scramble-label` 的三重 span（measure / live / sr-only 各存一份
   同样的文案），`textContent` 会得到「解决方案解决方案解决方案」—— 探针只取
   `.tf-scramble-measure` 那一层。

### 11.6 仍未动的旧站外链（本轮只动了 nav 里那一个）

`about` 页正文里还有 2 处「产品总览」按钮指向 `poxiaoshi.cn/products/`
（hero 下方与页尾 CTA 各一），页脚「公司」列还有 `poxiaoshi.cn/about/` 等。
都不在本次要求范围内，未动。

## 12. 2026-09-11 晚（六）：nav logo 两条 mark 顶部对齐

### 12.1 改动

`assets/img/logo.svg` 的两条 mark 原来是这样（画布 150×28）：

| | 顶部 | 底部 | 高度 |
| --- | --- | --- | --- |
| 左（长条） | y=2 | y=26 | 24 |
| 右（短条） | **y=6** | y=21 | 15 |

短条比长条低 4 —— 视觉上是「悬在长条中间偏上」。用户要求两条**顶部对齐**，
于是短条 `y 6 -> 2`（高度 15 不变，新范围 y 2..17），渐变
`lg-mono` 的 `y1/y2` 同步 `6/21 -> 2/17`（否则色阶整体偏下）。

画布尺寸、左条、文字都没动，所以 **nav 布局零影响**（`h-7 w-auto` 不变，
`<img>` 的 bbox 由画布决定）。产物 md5 四个页面全部不变 —— logo 是静态资产，
HTML 只存路径。

### 12.2 为什么改生成器而不是直接改文件

`logo.svg` 是 `tools/gen_icons.py` §10 的产物，直接改文件会让生成器成为谎言。
但**不能重跑全量生成器**：先 diff 了一遍，发现

```
DIFF  icon-hex.svg
```

`assets/img/icon-hex.svg` 被手工微调过（整个六边形上移 1 行），**生成器没有跟上**。
直接 `python3 tools/gen_icons.py assets/img` 会静默回退那次手调。
所以流程是：改生成器 → 生成到临时目录 → **只拷 `logo.svg`**
（同日改 `icon-mark.svg` 时同一套流程，只是拷的文件换成它）。

> 这条状态是历史遗留，本次未动：`icon-hex.svg` 的产物与生成器仍不一致，
> 谁重跑全量谁就会覆盖它。要么把那次手调回写进生成器，要么接受产物归生成器管。

### 12.3 新增断言（`tools/qa/reshape.mjs`）

纯视觉对齐的约定**不报错、也不 WARN**，而且旧坐标看着也挺正常，最容易被人
「顺手改回去」。所以钉两条：

```js
eq('nav logo bars share one top edge', /* 两条 <rect> 的 y 必须相等 */, true)
eq('nav logo short bar gradient tracks the bar', /* y1 == rect.y && y2 == rect.y + rect.h */, true)
```

第一条咬住对齐本身；第二条咬住「渐变跟着矩形走」（这条对旧值也成立 —— 它管的
是不变量，不是具体数值）。已用 node 单独验过判定：新 logo `topAligned: true`、
旧 logo `topAligned: false`。

### 12.4 `icon-mark.svg` 一并改为顶部对齐（同日追加）

上一版这里写的是「未动」，因为当时判断 nav 是「锁版 logo」、hero 是「展示图形」，
对齐规则可以不同。用户次日回话要求一并改，**已改**。

`assets/img/icon-mark.svg`（60×60）短条 `y 14 → 6`（高 30 不变，新范围 6..36），
渐变 `mk-violet` 的 `y1/y2` 同步 `14/44 → 6/36`。长条（`y 6..54`）与画布都没动。

改动后两份 mark **重新回到严格 0.5× 同形**（长条 48→24、短条 30→15、顶部 6→2），
也就是把上一版「刻意打破同比」的决定撤销了。生成器里 §6 与 §10 的注释已同步改写：
两处 bar 不允许各自漂移，改一边必须改另一边。

**为什么布局零影响**：`icon-mark.svg` 有三个使用点 —— favicon、hero hub
（`.tf-icon-hero.center img`）、Harness 带标（`.tf-control-harness-mark img`），
三处都是**正方形 `<img>` + `object-fit: contain`** 装一张正方形 60×60 画布，
且长条仍占满 `y 6..54`（即包围盒没变），所以移动短条不可能挪动任何布局。
四个页面产物 md5 全部不变。

### 12.5 新增断言（`tools/qa/reshape.mjs`）

纯视觉对齐的约定**不报错、也不 WARN**，而且旧坐标看着也挺正常，最容易被人
「顺手改回去」。所以钉三条（前两条对 nav lockup，后三条对 brand mark）：

```js
eq('nav logo bars share one top edge',        /* 两条 <rect> 的 y 必须相等 */, true)
eq('nav logo short bar gradient tracks the bar', /* y1 == rect.y && y2 == rect.y + rect.h */, true)
eq('brand mark bars share one top edge',      /* 同上，读 icon-mark.svg */, true)
eq('brand mark short bar gradient tracks the bar', /* 同上，查 mk-violet */, true)
eq('the two marks keep the same bar geometry at 2:1', /* hub 的 height 恒为 nav 的 2 倍 */, true)
```

前两条咬住对齐本身；渐变那两条咬住「渐变跟着矩形走」（对旧值也成立 —— 它管的
是不变量，不是具体数值）。最后一条是**把两个文件绑在一起**：只改一边的高度就会
在这里断，也就是「同一份素材只声明一次」这条纪律的可执行版本。

用 node 单独验过判定：新 `icon-mark` 三条全 `true`，把旧坐标拼回去喂同一函数得
`topAligned: false`（能咬住）。注意「2:1」那条对旧值也成立 —— 它管的是两文件
的绑定关系，不是对齐，职责不同。

## 13. 2026-09-11 晚（七）：四个产品子页 + 产品目录收归站内

> 本节记录的是**当晚（七）那个时点**的状态。其后的第（八）轮（§14）把「五处目录型
> 入口」扩成六处（加定价卡）、把首页的控制台直达全部收回、并把旧站链接清零 ——
> 本节里「保留 3 处控制台直达」「旧站只留 XCMP 与 chatbox」等说法**已被 §14 取代**。

用户原话：

> 现在为顶部栏产品下面的4个子产品生产独立的子页面，样式参考
> 原站的 /runtime 页面，保持样式，内容根据你对 Rune 大产品的理解来填充。
> （引文里的参考站域名已随 2026-09-11 品牌清理隐去，本文件内其余同类引文同此处理。）

### 13.1 产物与工具链

| 文件 | 角色 |
| --- | --- |
| `products/{rune,moha,ai-router,boss}/index.html` | 四个子页，深度 2 |
| `tools/build_products.py` | 生成器，data-driven（`PRODUCTS` 四条数据 + 18 个内联 lucide 图形） |
| `assets/css/products.css` | 只补 vendor 里没有的四块（页首双栏与内距、页首预览面板内层、能力边界两栏、姊妹卡） |
| `tools/portal_page.py` | 新增 `PRODUCT_NAV_GROUP` 常量（产品子页把 `is-active` 挪到「产品」触发键） |
| `tools/build_all.py` | `PIPELINE` 加 `build_products.py`（必须在 `reshape_home.py` 之后，它也从 `index.html` 取站芯） |

**版式不是新写的**：原站 /runtime 那一页的组件族本就在 `vendor.css` 里
（`tf-runtime-*` 42 个类 + `tf-capability-*` 卡片族 + `tf-section-*` 版面壳），
生成器只按那页的顺序把它们拼起来 —— 做新产品页的第一件事是 `grep` 组件族，
不是先写 CSS。

**正文事实来自本机仓库**，不是旧站营销文案：`rune/`、`XiaoShi-Moha/`、
`airouter/`、`XiaoShi-Rune-Console/` 与 `boss-homepage-redesign-2026-07-23.md`。
四条产品口径纪律（AIRouter 无充值/扣费闭环、Rune Harness 必带「规划/尚未」、
资源池不含调度、面板数字标「示意值」）全部写进 `guards()`，违反即构建失败。

### 13.2 产品目录的五个落点（20 条，一次改完）

改之前，四个产品名在**五处**都指向旧站 `www.poxiaoshi.cn/products/*`（BOSS 那条
指向控制台）。这五处是同一次改动，所以做法是把 `PRODUCTS` 的字段从旧站 `href`
换成站内 `page`，五处一起跟着变：

| 入口 | 条数 | 生成位置 |
| --- | --- | --- |
| 桌面「产品」下拉 | 4 | `stage_nav()` |
| 桌面「预约演示」下拉（`选择产品_`） | 4 | `stage_nav()` |
| 移动抽屉产品组 | 4 | `stage_nav()` |
| 控制平面四条 lane 的「进入 X」 | 4 | `lane()` |
| 页脚「产品」列 | 4 | `stage_footer_cta()` |

根相对路径 `/products/<slug>/`，所以 `ext()` 不会再加 `target="_blank"` ——
**站内跳转开新窗是错的**，而在此之前这 16 条每一条都带着。守卫专门查这一点：
产物里凡是 `href="/products/…/"` 后面跟 `target=` 就报错。

### 13.3 去「用」的入口**保持不动**（判断，可否决）

| 位置 | 目标 | 为什么不动 |
| --- | --- | --- |
| 品牌带 CTA | `console.poxiaoshi.cn` | 去「用」的入口 |
| BOSS 深潜板块 CTA | `console.poxiaoshi.cn` | 同上 |
| 页尾 CTA | `console.poxiaoshi.cn` | 同上 |
| AIRouter 深潜板块「了解 AIRouter」 | 文档站 | 同上 |

**规则**：产品页承接「了解」，控制台承接「用」。所以产品目录里不应再有直连
控制台的条目（BOSS 那一条原来就是），但首页必须留着**一条不经过营销页就能进
控制台的路** —— 全删掉是另一种错。产物里 console 直达从 8 处降到 3 处，守卫按
这个数咬住。

附带一处同类修正：页脚「产品总览」原来指旧站首页（`www.poxiaoshi.cn/`），
即本站正在替换的那个站，改指 `/`。

### 13.4 新增守卫（`stage_guards()`）

```
每个产品恰好 5 处 href="/products/<slug>/"      （漏改=4，改重=6）
旧站同名路径 href="https://www.poxiaoshi.cn/products/<slug>/" 必须为 0
旧站 products/ 路径总数 == 2（只剩页脚 XCMP 与 chatbox，且各恰好 1 条）
console.poxiaoshi.cn 恰好 3 处
href="/products/…/" 后面不得跟 target=
```

`build_products.py` 侧另有 7 条计数 + 章节顺序 + 三张姊妹卡互链 + 口径三条 + 无
`assets/` 残留 + 页容器在 `<main>` 内 + `<title>` 重写。

### 13.5 反向自测揪出的一个守卫 bug（教训值得留）

第一版是这样反推「禁止值」的：

```python
stale = 'href="https://www.poxiaoshi.cn%s"' % p['page']       # ✗
```

把 Rune 那条 `page` 改回旧站的绝对 URL 去自测 —— 只有「总数」那条报，逐条这条
一声不响。因为 `page` 已是绝对 URL 时，拼出来的是
`href="https://…/https://…"` 这个四不像，**恰好漏掉这轮最该抓的回归**。

改成从路径末段取 slug（旧站与站内的 slug 同名，这是稳定事实）：

```python
slug = p['page'].strip('/').split('/')[-1]                    # ✓
stale = 'href="https://www.poxiaoshi.cn/products/%s/"' % slug
```

**教训**：从「期望值」反推「禁止值」的守卫，在期望值本身出错时会**同时失效** ——
两个方向必须各自锚在独立事实上，不能是同一条数据的两种写法。

### 13.6 幽灵类体检带出的一次收拢

`classes.py` 拦下两个没有任何规则的类：

- `tf-product-hero-overline` —— 只是个带 `mt-6` 的包装 div（内层 `<span
  class="tf-overline">` 才是样式本体）。**删类**，留 `mt-6`。
- `tf-products-page` —— 页根容器。让它真的承担一件事：强调色
  `--tf-product-accent` 原本在**七个 section 各自内联一遍**，现在只写在页根容器上
  一次，各段靠继承；姊妹产品卡是唯一反向覆盖的地方（每张卡显示对方的颜色）。
  顺带七份重复的内联变量变成一份。

**教训**：幽灵类体检给出的两条出路里，「补一条空规则」和「加进白名单」都是
掩盖；第三个选项 —— 让这个类真的承担一件事 —— 才是修复。这次选的正是第三个。

### 13.7 验证

```
python3 tools/build_all.py
  -> 5 generators + 2 static checks
  -> qa/links.py:  13 pages, 531 in-site links, no broken link
     四个 products/*/index.html  inbound=56（不再是孤儿页）
  -> qa/classes.py: 13 pages, 2799 class token, 566 distinct, no ghost class

反向自测（改坏即报错，验完即还原）：
  - 把 Rune 的 page 退回旧站 URL -> 「产品目录仍指向旧站」+「旧站路径应只剩 2 条，实得 7」
  - 撤掉页根容器的强调色       -> 「--tf-product-accent 应只有 4 处，实得 3」×4 页
```

浏览器通道（`tools/qa/reshape.mjs`）本轮**未跑**，沿用「不自动做本地验证」的纪律。

### 13.8 待拍板 / 未做

1. ~~三处 console 直达要不要也改指产品页~~ —— **已办，见 §14**：首页三处全部收回站内，
   控制台入口改由产品页承接。
2. ~~nav「价格与服务」仍指旧站根~~ —— **已办，见 §14**：改指 `/#pricing`。
3. ~~定价区 6 处 `https://www.poxiaoshi.cn/`~~ —— **已办，见 §14**：四张卡 → 各自产品页，
   两条文案链接 → `/contact`。
4. `products.css` 的 `clamp()` 松紧、四页在真实浏览器里的观感需目视确认。（仍未做）


## 14. 2026-09-11 晚（八）：全站不再指向旧站 + 首页收回控制台直达

用户原话：

> 全部要指向到新页面，同时你看下全站指向到旧站根的 https://www.poxiaoshi.cn/，全部要指向到本站

这句是对 §13.8 里第 1–3 条待拍板的回复：三条都改。改动集中在 `tools/reshape_home.py`
（站芯 nav + 页脚 + 首页正文）与 `tools/build_about.py`（about 正文两处）。

### 14.1 结果

产出的 13 个页面里，`https://www.poxiaoshi.cn/…` **出现 0 次**（改前 7 页各 2–8 处）。

| 位置 | 原指向 | 现指向 | 依据 |
| --- | --- | --- | --- |
| 桌面 / 抽屉「价格与服务」 | 旧站首页 | `/#pricing` | 首页定价区自带 `id="pricing"`（上游就有） |
| 定价卡 ×4（Rune/Moha/AIRouter/BOSS） | 旧站首页 | 各自 `/products/<slug>/` | 四张卡就是四个产品 |
| 定价区「查看完整报价」「查看商务条款」 | 旧站首页 | `/contact` | 站内没有报价页，报价与条款是商务动作 |
| 品牌带 CTA、页尾 CTA（文字都是「预约演示」） | 控制台 | `/contact` | 按钮写着预约演示，却直连控制台 |
| BOSS 深潜板块「进入 BOSS」 | 控制台 | `/products/boss/` | 现在有 BOSS 产品页了 |
| 页脚 混合云 / 智算中心 / XCMP 云管理 | 旧站 solutions、旧站 xmcp | `/products/rune/` | 云智算内核与它的多云底座都在这一页 |
| 页脚 教育行业 / 能源制造 | 旧站 cases | `/blog/` | 站内交付故事（马基努油田那篇正是能源） |
| 页脚 AI 应用 | 旧站 chatbox | `/products/ai-router/` | AI 应用统一经聚合网关接入 |
| 页脚 关于我们 | 旧站 about | `/about` | 站内有这一页 |
| about 页「了解产品」「产品总览」×2 | 旧站 products/ | `/` | 首页就是四大板块的总览 |

**顺带纠正一个认知**：页首那两处「预约演示」按钮的落点一直是控制台，不是文案写的那样 ——
只读代码看不出来，得把按钮文字和 href 放在一起看。

### 14.2 保留的站外出口（有意，不是漏改）

| 域名 | 条数 | 为什么留 |
| --- | --- | --- |
| `docs.poxiaoshi.cn` | 142 | 独立文档站，站内没有替代内容 |
| `ppt.poxiaoshi.cn/#slide-1` | 26 | 顶层菜单「解决方案」的落点（§11 定的） |
| `console.poxiaoshi.cn` | 产品页 7 处 | 见下 |
| `kubegems.io` / `github.com/poxiaoyun` | 各页页脚 | 外部开源项目 |

**控制台直达**：首页那 3 处已全部收回，但**产品页里保留了 7 处**（每页两个「进入控制台」
按钮，moha 页只有一个 —— 见 14.5）。链路因此变成 **首页 → 产品页 → 控制台**。

### 14.3 四条工程笔记

**一、断言从「逐条名单」换成「主域零出现」。** 上一轮的守卫是「旧站路径应只剩 XCMP 与
chatbox 两条」+ 按名保住这两条。这轮两条也收回了，继续写名单就会漏掉新加的那一条。
改成 `re.findall(r'https://www\.poxiaoshi\.cn/[^"]*', body)` 必须为空。
三个含 `poxiaoshi.cn` 但不是旧站的域名（`api` / `docs` / `ppt`）都不是 `www.` 开头，
所以精确到 `www.` 就够，不会误伤。

**二、`ext()` 只回答「该加」，不回答「该删」。** 页脚那六条原标签都写着
`target="_blank" rel="noopener noreferrer"`。`retarget_nav_item` 那种只换 href 的写法会
留下它们，得到「站内链接开新窗」。新增的 `retarget_link` 在目标为站内时把这两个属性
一起摘掉。**两个方向要分开写**，别指望一个函数包圆。

**三、`new_href in body` 是伪断言。** 第一版守卫写的是「定价区 X 的新落点 Y 不在页面里
就报」—— 而四张卡指向的是产品页，那些链接在页面上到处都是，**这条几乎永远为真**。
反向自测把 Moha 定价卡退回旧站时它一声不响。改成按 `data-page-node-id` 把标签捞出来
核 `href` 才咬得住。通则：**断言要落在「这一个元素」上，别落在「页面上存在某个字符串」上。**

**四、按来源计数，别按总量。** 上一轮是「每个产品恰好 5 处入口」，这轮加了定价卡、
页脚又多出三条指向 Rune 的别名（混合云 / 智算中心 / XCMP），总量就成了「每加一条入口
都要跟着改的数」，而且它分不清「某处漏改」和「另一处被删」。改成按 `<a>` 的 class 片段
逐来源数（产品下拉 / 预约演示下拉 / 抽屉 / lane / 页脚 / 定价卡 各 1 条）。

### 14.4 验证

```
python3 tools/build_all.py
  -> 5 generators + 2 static checks
  -> qa/links.py:  13 pages, 659 in-site links, no broken link
     /#pricing 被解析到 index.html（ok，13 page(s)）
  -> qa/classes.py: 13 pages, 2799 class token, 566 distinct, no ghost class

产物全量扫描：www.poxiaoshi.cn 出现 0 次；首页 console 直达 0 处

反向自测（改坏即报错，验完即还原）：
  A/B/C 页脚一条 + 定价卡一条 + nav「价格与服务」退回旧站
      -> 「定价卡：Moha 应有 1 条指向 /products/moha/，实得 0」
      -> 「本站仍有指向旧站的链接 4 条」
      -> 「「价格与服务」应有 2 处指向首页定价区，实得 0」
      -> 「页脚两条行业案例应指 /blog/，实得 1」
  D     撤掉 retarget_link 的 target/rel 摘除
      -> 「产品页入口不应开新窗，实得 3 处带 target」
      -> 「站内链接不应开新窗，实得 6 处」
```

浏览器通道（`tools/qa/reshape.mjs`）本轮**未跑**，沿用「不自动做本地验证」的纪律。

### 14.5 待拍板 / 未做

1. **moha 产品页少一个「进入控制台」**：另外三页 hero 区都有
   （`actions` 里写了 `('进入控制台', CONSOLE_URL, 'secondary')`），moha 只写了「联系我们」。
   看起来是遗漏，但不在本轮范围内，没动。
2. 产品页里的 7 处控制台直达是否也要收回（本轮判断：保留，它是「用」的入口）。
3. `products.css` 的 `clamp()` 松紧、四页在真实浏览器里的观感需目视确认。

## 15. 2026-09-11 晚（九）：产品页删掉四段，一页只讲一件事

用户原话：

> 4个产品子页面，删除"四项关键能力"，"能力边界"，"能力清单"和"同一个内核的其他三块"的区域

### 15.1 删了什么、剩下什么

| 段落 | 原 id | 内容 | 处置 |
| --- | --- | --- | --- |
| 四项关键能力 | `#capabilities` | 4 张 `.tf-capability-card`（图标 + 索引 + 标题 + 说明 + 文档链接） | 删 |
| 一次全过程 | `#flow` | 全宽 console：请求 / 选路双栏 + 4 个编号步骤 + trace | **留** |
| 能力清单 | `#detail` | 左侧文案 + 右侧 10 行对象表 | 删 |
| 能力边界 | `#boundary` | 「已经交付 / 有明确边界」两栏 | 删 |
| 同一个内核的其他三块 | `#siblings` | 3 张产品互链卡 | 删 |

现在每页是：hero（左文案 + 右 console 预览）→ 代码分隔线 → 全过程 console → 收尾 CTA。
页高 59.4 KB → **48.1 KB**（正文 9.7 KB），`products.css` 393 → **262 行**。

一起删掉的还有三样东西 —— 漏掉任何一样都会留下「半截改动」：

1. `PRODUCTS` 里的 `caps` / `detail` / `boundary` 三个字段（四条产品各一组，共 12 块）
2. 渲染函数 `capabilities()` / `detail_section()` / `boundary_section()` /
   `siblings_section()` / `mark_strong()`（最后一个只被 boundary 用）
3. `products.css` 里对应的规则块（boundary 全部、sibling 全部、能力卡图标槽），
   以及三条只为它们而设的响应式 / hover 规则

用 AST 复查过：无「定义未调用」的函数，无「导入未使用」的名字。

### 15.2 守卫的四处改写

1. **id 与顺序锚点**：`SECTION_IDS` 五个 → `('flow',)`；`order` 八项 → 四项。
   id 唯一性断言在新形态下仍然有意义 —— 谁把删掉的段落加回来，计数立刻变 2。
2. **条数**：删掉 capability cards / boundary 两栏 / sibling cards 三条计数。
3. **新增「删掉的四段不许复活」**（`RETIRED_IDS` / `RETIRED_CLASSES`）：逐项查
   `id="…"` 与三个类名前缀，外加「main 里不该再有产品页互链」—— 姊妹卡是它唯一的来源。
   **删除动作本身也要有断言**：否则它会在下次改版时被半路加回来，「改了 markup 忘了
   css」和「从旧产物里粘一段回来」都是常见形态。
4. **强调色计数 4 → 1**：三张姊妹卡是页根继承链唯一的例外（每张卡反向覆盖成对方颜色），
   例外删了，计数就必须跟着回到 1 —— 数字型断言最容易这样烂掉：改完主体忘了改数字，
   守卫从此变成一条永远碰不到的旧阈值。

### 15.3 被删段落里的口径条目（原文归档）

这四段里有些是**产品口径**而不是文案，删段之后它们在整个页面上没有落点了。原文留档，
以后要在别处重新表达时照这个写：

**Rune**（原 `#boundary` 右栏）

- 资源池只做容量汇总与健康视图，**不包含调度**，也不是队列或算力权益池
- 调度域仍在演进（Volcano / HyperNode 等首期约束），不作为已完整交付的能力对外承诺
- Rune Harness 云智算内核目前是**规划中的形态**，尚未提供实现
- 模型、数据集与镜像的仓库不在 Rune 内，由 Moha 提供，Rune 只做编排与代理

**Moha**（原 `#boundary` 右栏）

- 不提供面向用户的 AK/SK：认证走 OIDC、本地账号、SSH 公钥、Webhook 或反向代理请求头
- Space 的集群、规格与模板由 Rune 提供并转交部署，Moha 不自持算力信息
- Moha 是仓库与元数据的事实源；配额、计量与运营视图不在它这一层
- 仓库 README 里还留着早期代号 ModelX，产品对外的名字统一用 Moha

**AIRouter**（原 `#boundary` 右栏，逐字残留一句）

- **没有在线充值与扣费闭环**：网关不对接支付渠道，额度由管理端登记，结算与余额闸门默认关闭

**BOSS**（原 `#boundary` 右栏，逐字残留一句）

- **不提供在线充值与扣费闭环**，也没有余额账户、收入与毛利口径

上面 Rune / Moha 两页是完整两栏；AIRouter / BOSS 那两句是改写前 grep 抓到的原句，
**同名栏目的其余条目未及留存**（改写完才想起归档，本地无备份、仓库里也从未提交过）。
语义要点已在上表，逐字版本要另找。

顺带记两处「口径在页面上的替代落点」：BOSS 页的全宽 console 页脚仍写着
`范围 · 不含财务结算`；AIRouter 页现在只剩 `转发计量` / `用量 usage_id 幂等` /
`quota 滚动 7 天` 这类事实描述，没有任何计费闭环的暗示。

### 15.4 口径守卫从「恰好一次」收紧成「零次」

原断言：「充值 / 扣费 / 余额」在 AIRouter 与 BOSS 页各出现一次、且必须落在边界栏里。
现在四页一律 **0 次** —— 边界栏没了，「显式声明没有」这句话无处可放，留着旧断言只会
变成一条永远失败的守卫；更糟的是有人为了让它过，把「在线充值」当成一条能力写进去。
（`Rune Harness` 那条不变：出现就必须同时写「规划 / 尚未」。）

### 15.5 验证

```
python3 tools/build_all.py
  -> 5 generators + 2 static checks
  -> qa/links.py:   13 pages, 647 in-site links（改前 659），no broken link
  -> qa/classes.py: 13 pages, 2722 class token / 551 distinct（改前 2799 / 566），no ghost class

四个产物：无 id="capabilities|detail|boundary|siblings"，无 tf-capability-card /
tf-products-boundary / tf-products-sibling，无「四项关键能力 / 能力清单 / 能力边界 /
同一个内核的其他三块」任何字样
products.css：22 个选择器逐个能在四个产物里找到（头部注释里点名的 tf-panel 除外）

反向自测（一次造三类故障，验完即还原）：
  A 把 id="boundary" + class="tf-products-sibling" 塞回正文
      -> 四页各报「已删段落回来了: id="boundary"」+「已删板块的类回来了: tf-products-sibling」
  B 把「在线充值」写进 flow 文案
      -> rune: 口径：'充值' 出现 1 次，产品页上一律不得出现（不得暗示计费闭环）
  C 撤掉页根容器的强调色
      -> 四页各报「--tf-product-accent 应只有 1 处（页根容器），实得 0」
```

浏览器通道（`tools/qa/reshape.mjs`）本轮**未跑**，沿用「不自动做本地验证」的纪律。

### 15.6 待拍板 / 未做

1. **（晚（十）已解决，见 §16）口径条目「页面上无处可放」** —— 见 15.3。当时最担心的
   是 Rune：全宽 console 里还有 `调度链路`、`选择资源池 · 容量与健康` 这类标签，删掉
   「资源池不含调度」那句之后容易被读成「平台负责调度」。那一段（连同这两个标签）在
   晚（十）被整段删除，页面上再没有能被那样读的字。口径本身没放松，仍然写在
   `build_products.py` 文件头的「写作纪律」里。
2. **moha 页 hero 少一个「进入控制台」**（另三页 hero 都有），§14.5 就挂着，仍未动。
3. `products.css` 的 `clamp()` 松紧与四页真实浏览器观感需目视确认。

## 16. 2026-09-11 晚（十）：产品页删掉最后一段正文，只剩页首与收尾

用户原话：

> 删除rune产品页的一次部署的全过程的区域，删除moha产品页的一次上传与分发的区域，
> 删除airouter产品页的一次请求的选路的区域，删除boss页面的一次交班巡检的区域

四条指令就是同一件事：删掉 `#flow`（「一次全过程」）那一段，各页只是标题不同。
它是晚（九）之后正文里唯一的段落，删完产品页正文就只剩**页首**与**收尾 CTA** 两块。

### 16.1 结果

```
                        改前            改后
页高                    48.1 KB         44.4 KB
正文（main）            13.6 KB         6.0 KB
tools/build_products.py 644 行          463 行
assets/css/products.css 262 行          256 行
```

现在每页：页首（定位 + 控制台预览）→ 代码分隔线 → 收尾 CTA。四页正文的可见文字只剩
badge / overline / h1 / lede / 两个按钮 / meta 行 + 右栏预览面板。

**分隔线留着，是刻意的**（原本三条里的第一条，位置没动）。它不在用户点名的两段里；
页首是一块深色大面板、收尾是另一块深色卡片，中间没有这行代码会直接贴上。要不要连它
一起去掉是个视觉决定，没被点名就不动 —— 与晚（九）「删段不该顺带把版面往前挪一格」
同一条规矩。`--tf-motion-order` 也照旧是 0 / 1 / 6，不重排。

### 16.2 一起删的四样（漏一样就是半截改动）

| # | 删了什么 | 位置 |
| --- | --- | --- |
| 1 | `PRODUCTS[*]['flow']` 四个数据块（共 123 行） | 每个产品的 `'preview'` 之后 |
| 2 | `flow_section()` / `story_heading()` / `icon()` 三个渲染函数 | 后两个只被 `flow_section` 用 |
| 3 | `_ICON_PATH` 图标表（18 个内联 lucide，47 行） | 只被 `icon()` 用 |
| 4 | `products.css` 的 `.tf-products-note` 规则 | 全宽 console 的注脚，删段后无引用 |

第 2、3 条是这个仓库特有的连带面：**数据段删掉之后，为它服务的那一整条渲染链会一起
变成死代码**，而它们分散在文件的不同位置（图标表在最上面、渲染函数在中段、数据在中段
偏上）。AST 复查过：无「定义未调用」的函数、无「未使用」的导入。顺手还删掉一个从创建
起就没被用过的常量 `BY_SLUG`（模块级常量不在上面两项检查的覆盖范围里，是手工数的）。

### 16.3 被删段落里的口径条目（原文归档）

逐字原文另存 `docs/archive/products-deleted-sections-2026-09-11.md`（含四段完整 payload）。
口径上值得单独记的：

| 产品 | 那一段里唯一有长期价值的说法 |
| --- | --- |
| Rune | `调度链路` / `选择资源池 · 容量与健康` 两个标签 —— **删掉它们反而修掉了 §15.6.1 记的那个语义空档**：页面上再没有能被读成「平台负责调度」的字 |
| Moha | 可见性三档 `public / internal / private`、审计入口 `/v1/audits` |
| AIRouter | `quota 滚动 7 天`、`usage_id` 幂等、数据面「只读 Redis 缓存 + gRPC 回源」 |
| BOSS | 页脚 `范围 · 不含财务结算`（连同它，BOSS 页上再没有一句提结算） |

计数口径：`充值 / 扣费 / 余额` 依旧是四页一律 0 次（晚（九）收紧的），本轮没有放松。

### 16.4 守卫的四处改写

1. **`SECTION_IDS` 连同「id 唯一」那条断言一起删掉。** 正文里已经没有任何带 id 的
   段落了，留着一个遍历空元组的循环，是**看着像检查、其实什么都不做**的东西 ——
   比没有断言更糟。删段落的替代保障是下面第 2 条。
2. **`RETIRED_TITLES` —— 三条名单之外再加一层「读者还看得见吗」。** 原来的
   `RETIRED_IDS`（查 `id="…"`）和 `RETIRED_CLASSES`（查容器类）答的都是「代码有没有
   回来」；如果那一段被重写成不带 id 的普通 `<div>`，两条都问不出来。于是把四个被删的
   可见标题也列成名单，直接查字符串。**名单里的四个串逐一与删前的留档原文比对过** ——
   拼错一个字节，这条断言就会永不触发（这正是「名单型断言」最危险的失效方式）。
3. **`RETIRED_CLASSES` 加两项：`tf-runtime-showcase` / `tf-products-note`。**
   没有把 `flow_section` 用到的 13 个 `tf-runtime-*` 全列进去：那是**上游 vendor 的
   组件族**，将来别的页要用是合理的，全列等于把 vendor 的能力也判成违禁。只挑了两个
   真正的钩子 —— 那一段的**外层容器**（整段被粘回来时它必然出现）与**本页自己的注脚类**
   （它一并进了 CSS 删除名单，回来就必须连 CSS 一起回）。
4. **顺序锚点 `id="flow"` → `tf-faq-code-divider`。** 正文只剩三块，顺序就是全部结构：
   页首 → 分隔线 → 收尾。这条同时保证没人把分隔线挪到页首之前（变成「先一条装饰线、
   再标题」的排版事故）。

### 16.5 验证

```
python3 tools/build_all.py
  -> 5 generators + 2 static checks
  -> qa/links.py:   13 pages, 647 in-site links, no broken link
  -> qa/classes.py: 13 pages, 2630 class token / 530 distinct（改前 2722 / 551）, no ghost class

四产物扫描：无 id="flow" / tf-runtime-showcase / tf-products-note / tf-runtime-step /
  tf-runtime-request / tf-runtime-route / tf-runtime-story，无四个已删标题任何字样
products.css：20 个选择器逐个能在四页产物里找到（`tf-section` 与 `tf-about-cta-links`
  两个「未命中」出自文件头注释，不是规则）
AST 复查：无「定义未调用」的函数、无未使用的导入

反向自测（一次造三类故障，验完即还原）：
  A 把 id="flow" + class="tf-runtime-showcase" + tf-products-note 塞回正文
      -> 四页各报「已删段落回来了: id="flow"」+ 两条「已删板块的类回来了」
  B 把「一次部署的全过程」写回页首标题
      -> rune: 已删段落的标题还在页面上: 一次部署的全过程
  C 把分隔线挪到页首之前
      -> 四页各报「sections are out of order: [('tf-product-hero', 31560),
         ('tf-faq-code-divider', 31393), …]」
```

浏览器通道（`tools/qa/reshape.mjs`）本轮**未跑**，沿用「不自动做本地验证」的纪律。

### 16.6 待拍板 / 未做

1. **页首与收尾之间那条分隔线留不留。** 现在它两侧各一块深色面板；删掉页面会变成
   两块直接相接。留是默认（见 16.1），要删就一句话。
2. **页面已经很短了** —— 四页正文 6 KB，滚一屏到底。要不要在页首与收尾之间放回一点
   内容（比如只放其中一个被删段落，或加一段纯文字的「适用场景」），由你定；留档里
   四个段落随时可以加回来。
3. **moha 页 hero 少一个「进入控制台」**（另三页 hero 都有），§14.5 挂到现在。页面越
   短这个不一致越显眼。
4. `products.css` 的 `clamp()` 松紧与四页真实浏览器观感需目视确认。

## 17. 2026-09-11 晚（十一）：产品页删掉收尾 CTA（「想在您的环境里跑 X？」）

用户原话：

> 4个产品子页面 删除"进入控制台"的区域

「进入控制台」在四页上有两处，先问了一次「删哪一处」，用户答：

> 「想在您的环境里跑 xxx」的那个区域

于是删的是**页尾那一整块 CTA**（`.tf-contact-cta-section`），不是它里面的那个链接。
先行确认这一步是必要的：只按字面删「进入控制台」，会得到三种都说得通的结果
（页尾那条链接 / 页首那个按钮 / 整段 CTA），删错要重来。

### 17.1 结果

```
                        改前            改后
页高                    44.4 KB         41.8 KB
正文（main）            6.0 KB          3.4 KB
正文段落                3 块            2 块（页首 + 分隔线）
tools/build_products.py 463 行          461 行
assets/css/products.css 256 行          244 行
motion-order            0 / 1 / 6       0 / 1
```

四页现在只剩页首一块正文（+ 那条代码分隔线）。**页首按钮组没动**：Rune / AIRouter /
BOSS 的页首仍有「进入控制台」（`PRODUCTS[*]['actions']` 第二项），Moha 页页首是
「开发者文档」。所以本站指向 `console.poxiaoshi.cn` 的链接从 11 条降到 3 条
（首页 0、产品页 3），商务出口（页首「联系我们」+ 页脚）未受影响。

### 17.2 连带面：这次删的是**函数**，不是数据块

前两轮删段落改的是 `PRODUCTS` 里的字段（`caps` / `detail` / `boundary` / `flow`），
这一轮的收尾 CTA **没有数据字段** —— 它是四页共用的渲染函数 `closing(p)`，`PRODUCTS`
里一个字都不用改。连带面因此和前两轮不同：

| # | 面 | 具体动作 |
| --- | --- | --- |
| 1 | 渲染函数 | 删 `closing()`（整段，含它的 `links` 构造） |
| 2 | 调用点 | `main_markup()` 去掉 `+ closing(p)` |
| 3 | import | `ARROW_S`、`ext` 在本文件随之失去使用者（`ARROW_S` 只被它用；`ext` 只被它与 `brand_action` 用，而后者内部自己调）→ 从 `portal_page` 的 import 里摘掉 |
| 4 | 本页 CSS | 删 `.tf-products-cta-links*` 三条规则 —— 这是整段里**唯一**写在本页样式表的规则 |
| 5 | 守卫 | order 锚点去掉 `tf-contact-cta-section`；`RETIRED_CLASSES` 加 `tf-contact-cta-`，`RETIRED_TITLES` 加「想在您的环境里跑」；新增「正文块数 = 2」断言 |

**没动的**：`.tf-contact-cta-*` 全套类与 `cta-dither.webp` 都还在 vendor.css / `assets/`
里 —— 首页与 `/about` 页仍在用同一套组件（首页 main 内 9 处、about 页 7 处），
删产品页这一段不涉及 vendor 与图片。`DOCS_URL`、`CONSOLE_URL`、`MAIL` 三个常量也都要
留：前两个还被 `PRODUCTS[*]['actions']` 引用（Moha 的「开发者文档」用 `DOCS_URL`），
`MAIL` 用于四页的「联系我们」。**删函数时最容易顺手删掉一个仍被别处用的常量。**

### 17.3 守卫的三处改写

1. **order 锚点去掉 `tf-contact-cta-section`。** 留着它会天天报 `anchor missing` ——
   把一个**已经按要求删掉**的段落当故障。锚点数组描述的是「当前该有的段落」，不是
   「历史上出现过的段落」。
2. **`RETIRED_CLASSES` 里写的是 `tf-contact-cta-`（带尾横线的前缀，拦整族），不是
   单个 `-section`。** 理由有两条：只写 `-section` 的话，把卡片挪进另一个
   `<section>`、或者干脆改成 `<div class="tf-contact-cta-card">` 就绕过去了；
   而这族类是 **vendor 的通用组件**，幽灵类检查（`tools/qa/classes.py`）永远抓不到
   它复活 —— 幽灵类抓的是「用了但样式表里没有」，vendor 里样式一直都在。
   这两条合起来：这一族只能靠 RETIRED 名单点名。
3. **新增「正文块数 = 2」断言**（数的是 `raw_main`，即未摘掉分隔线的原件）。它比
   order 锚点更早发现问题：有人加回第三段时，锚点数组里没有它，顺序依然成立，
   只有计数会响。顺带因此把 `main_html` 的「摘掉分隔线」改成了留一份 `raw_main`。

### 17.4 验证

```
python3 tools/build_products.py     -> 4 页重建，守卫全绿（0 miss），首页 md5 未变
python3 tools/qa/classes.py         -> ok — 13 pages, no ghost class, 4 hook pattern(s) still live
产物核对                            -> 四页 main 各 2 个 <section>，motion-order 0/1，
                                       tf-contact-cta 计数 0；首页/about 各自计数不变
反向自测（只调 guards()，不落盘）:
  A 把收尾 CTA 整段加回正文
      -> 四页各命中 3 条：「正文应有 2 块（页首 + 分隔线），实得 3」+
         「已删板块的类回来了: tf-contact-cta-」+「已删段落的标题还在页面上: 想在您的环境里跑」
  B 类名全换掉、只把那句标题塞进页首
      -> 只有 RETIRED_TITLES 命中（正是它存在的理由）
  正对照：未篡改时 baseline_miss = 0（四页）
```

浏览器通道（`tools/qa/reshape.mjs`）本轮**未跑**，沿用「不自动做本地验证」的纪律。

本次反向自测没改任何源文件：把 `build_products.py` 当模块 import，构造篡改后的 doc
喂给 `guards()` 看它报不报。这样比「改源文件再 `git checkout` 还原」安全 ——
`finish_many()` 是**先写盘再报错**的，跑失败态构建会把坏产物写进 `products/`。

### 17.5 留档

逐字原文（`closing()` 源码 + 产物 HTML + 五步恢复说明）在
`docs/archive/products-deleted-sections-2026-09-11.md`。这是连着第二轮「先留档再删」。

### 17.6 待拍板 / 未做

1. **页尾那条分隔线现在悬空了。** 它原本是「页首 ↔ 收尾」之间的过渡，收尾没了之后
   它直接接页脚。留是默认（三轮删段都没点名它，且删段不该顺带把版面往前挪一格）；
   要删就一句话。**注意删它之后正文只剩页首一块**，`guards` 里那条「块数 = 2」的
   断言与 `order` 数组都要跟着改（守卫跟着结构走，别留一条永远碰不到的断言）。
2. **页首按钮组仍不一致**：三页第二按钮是「进入控制台」，Moha 是「开发者文档」。
   §14.5 挂到现在。删掉页尾那条之后，页首这个是本站仅存的控制台入口，要不要统一
   （补 Moha / 或反过来全删）请拍板。
3. **四页正文现在只有页首一块**（3.4 KB）。要不要放回一点内容由你定，留档里
   `closing()` 与四个 `flow` 段随时可加回。
4. `products.css` 的 `clamp()` 松紧与四页真实浏览器观感需目视确认（老问题，仍未目视）。

## 18. 2026-09-11 晚（十二）：删掉页首徽标 `tf-product-hero-badge`

用户原话：

> 删除四个子产品的tf-product-hero-badge

删的是页首左栏最上面那枚 mono 小胶囊（`核心产品 · Rune 智算`，右侧一个强调色圆点；
上游 runtime 页左上角 chip 的位置）。用户直接给了类名，**没有歧义，不需要澄清** ——
与前两轮「XX 的区域」不同，这次是精确定位。

### 18.1 结果

```
                        改前            改后
页高                    41.8 KB         41.7 KB
tools/build_products.py 461 行          458 行
assets/css/products.css 244 行          232 行
页首左栏首元素          badge 胶囊      小标（tf-overline）
```

四页 `tf-product-hero-badge` / `核心产品` / `class="mt-6"` 计数**全部为 0**。

### 18.2 连带面：删「页内元素」比删「整段」小得多，但有两处容易漏

| # | 面 | 具体动作 |
| --- | --- | --- |
| 1 | 数据字段 | 四条 `PRODUCTS[*]['badge']` |
| 2 | 渲染 | `hero()` 里的徽标 `<span>` **与它下面那层 `<div class="mt-6">` 包装** |
| 3 | 参数序列 | `%` 元组里 `esc(p['badge'])` 去掉后，后面的参数整体前移一格 |
| 4 | 本页 CSS | `.tf-product-hero-badge` 与 `.tf-product-hero-badge i` 两条规则 |
| 5 | 守卫 | `RETIRED_CLASSES` / `RETIRED_TITLES` 各加一条；**同时删掉 `('badge', p['badge'])` 那条逐字落盘断言** |

两处容易漏的：

- **第 2 面里的 mt-6。** 它不是徽标的一部分，而是一层包装 div，`hero()` 里原本的注
  释就写着「小标只有『与徽标的间距』这一件事要做，而 mt-6 就是它」。徽标删了、包装
  留着，页面上就多出一段**没有服务对象的空白**，而注释还在说它服务谁 —— 比多一行
  DOM 更糟的是注释开始说谎。所以一起删，并把理由写回新注释。
  判据：**删掉一个元素时，问一句「哪一层是只为它存在的」**（间距包装、分隔符、
  `aria-hidden` 的装饰、只为它渲染的辅助函数）。
- **第 5 面里的逐字断言。** `for label, needle in (…, ('badge', p['badge']), …)` 这条
  断言会在字段删除后直接 `KeyError`。而这类改动的常见半拉子收尾是**把断言注掉**
  （而不是删掉）—— 于是列表里留下一条永远不跑的检查。删字段就要删这条断言。

### 18.3 `RETIRED_TITLES` 用共同前缀：一条顶四条

四条徽标文本是 `核心产品 · Rune 智算` / `核心产品 · Moha 资产` /
`核心产品 · AIRouter · AI聚合网关` / `核心产品 · BOSS 运营`。**没有**写四个全串，
而是写了共同前缀 `'核心产品 · '`：

- 四页各写一个全串要维护四份，而**漏掉的那一页永远不会报错**（名单型断言最危险的
  失效方式）；
- 前缀成立的前提是「这个词只出现在被删对象上」—— 落盘前 grep 了一遍全部产物，
  `核心产品` 在四页正文中只出现在徽标里（标题、lede、meta 行都没有这个词）。
- 代价是**过度匹配**（未来某处若合法地用了「核心产品」会误报）。这个代价可以接受：
  真要再用，改名单即可，而漏检是不可发现的。

### 18.4 顺手复核：强调色继承链没失守

徽标圆点 `.tf-product-hero-badge i` 曾是 `--tf-product-accent` 的使用者之一。删完
在样式表里数了一遍还剩谁在用：`.tf-product-hero:before`（光晕的 `color-mix`）、
`.tf-product-preview-line i`（终端提示符）、`.tf-product-preview-steps b`（编号步骤）
—— **还有三个**，所以页根容器那条规则（以及守卫「强调色恰好 1 处」）不受影响。
若这里数出来是 0，`--tf-product-accent` 整条链就该一起删，那才是真的连带面。

### 18.5 验证

```
python3 tools/build_products.py     -> 4 页重建，守卫全绿（0 miss）
python3 tools/qa/classes.py         -> ok — 13 pages, no ghost class, 4 hook pattern(s) still live
产物核对                            -> badge / 核心产品 / class="mt-6" 计数全 0，
                                       hero 左栏首元素是 <span class="tf-overline">
反向自测（只调 guards()，不落盘）:
  A 徽标原样加回（类 + 文本）
      -> 四页各命中 2 条：「已删板块的类回来了: tf-product-hero-badge」+
         「已删段落的标题还在页面上: 核心产品 · 」
  B 只把文本塞回去（一个类名都不写）
      -> 只剩 RETIRED_TITLES 命中（正是它存在的理由）
  正对照：未篡改时 baseline_miss = 0
```

浏览器通道与 `qa/*.mjs` 本轮**未跑**，沿用「不自动做本地验证」的纪律。

### 18.6 留档

逐字原文（渲染代码 + 四条数据 + 产物 HTML + CSS 两条规则 + 四步恢复说明）在
`docs/archive/products-deleted-sections-2026-09-11.md`。第三轮「先留档再删」。

### 18.7 待拍板 / 未做

1. **页首左栏现在以小标开头**（`Rune 智算_` 这行 mono 小字直接顶在左栏第一行）。
   徽标在时它是被胶囊压着的一行；现在它与页首上内边距之间的视觉重量需要目视确认 ——
   如果觉得太贴，加回一点间距是一句话的事（`hero-copy` 首个元素的 `margin-top`；
   但**不要**把它写成 `mt-6` 复活那一层空包装，直接写在 `.tf-product-hero` 的
   padding-top 或小标所在的 `tf-overline` 上更合适）。
2. 页尾那条代码分隔线仍悬空（§17.6.1）。
3. 页首按钮组仍不一致：三页「进入控制台」/ Moha「开发者文档」（§14.5 起挂着）。
4. 四页正文现在只有页首一块 + 一条分隔线（§17.6.3）。

---

## 19. 2026-09-11 晚（十三）：三类商务入口全部收口 `/contact`

### 19.1 需求与两个澄清

用户原话：「将所有的『预约演示』『联系我们』『进入控制台』都自动跳转到 /contact 页面」

先把全站这三个文案的 `<a>` 全部枚举出来（13 页 × 每个标签的可见文本 + href），发现
**它们分布在两个源头**，而且指向三个不同的地方：站内 `/contact`、`mailto:`、控制台。
逐条改之前有两处歧义会直接决定改法，所以问了一次 —— 两问都答了：

| 问题 | 用户的选择 |
| --- | --- |
| 「进入控制台」改指 `/contact` 后，与旁边那个「联系我们」按钮目标完全重复 | **文字改成「预约演示」，保留按钮** |
| 导航栏与页脚的「联系销售」（同样 `mailto:`，13 页都有，不在点名的三类里） | **一起改指 `/contact`** |

### 19.2 两个源头

| 源头 | 覆盖范围 | 改了什么 |
| --- | --- | --- |
| `tools/reshape_home.py`（**站芯**） | 全部 13 页的 nav / 移动抽屉 / footer | 新增 `stage_contact_retarget()`：4 条 `mailto:` → `/contact` |
| `tools/build_products.py` | 4 个产品页页首按钮组 | 4 条「联系我们」`mailto:` → `/contact`；3 条「进入控制台」→ 文字改「预约演示」、目标改 `/contact` |
| `tools/build_about.py` | about 页两处 `brand_action` | `mailto:` → `/contact` |

站芯那一处是最省力的部分，也是**唯一能一次性覆盖 13 页**的位置：`portal_page.derive()`
从定稿的 `index.html` 里取 nav / 抽屉 / footer，所以首页改 4 条 = 全站 13 页 × 4 条一起变。
反过来说，这也是它们此前长期不一致的原因 —— 站芯是派生源，只改产品页的按钮永远动不了它。

四条站芯链接（node-id 见 `CONTACT_RETARGET`）：导航条右侧 CTA「联系销售」、移动抽屉
「联系销售」、页脚「公司」列的「联系我们」与「联系销售」。

### 19.3 改完之后的链接账（全部实测）

| 项 | 改后 |
| --- | --- |
| 首页 `href="/contact"` | **11**（改前 7，净增 4 = 页脚「联系我们」「联系销售」+ nav CTA「联系销售」+ 抽屉「联系销售」） |
| 其余 12 页 | 每页同增 4：产品页 9 / 9 / 9 / 8（Moha 只有 1 条页首入口，故 8）、about 9、blog 与 contact 各 7 |
| 全站 `href="/contact"` | **104** |
| 「预约演示 / 联系我们 / 联系销售」链接 | **89** 条（5 / 45 / 39），落点全部为 `/contact`，0 例外；「进入控制台」**0** 条 |
| `console.poxiaoshi.cn` | 全站 **0**（三页页首那三条改指后归零） |
| 旧站 `www.poxiaoshi.cn` | 全站 **0** |
| 全站 `mailto:` | 每页只剩 1 条（页脚邮箱图标）；about 多「发送简历」、contact 多两条邮箱显示 |

顺带清掉两个**死常量**：`build_products.py` 的 `MAIL` 与 `CONSOLE_URL` 在改动后
再无引用，一起删了（`CONTACT_PAGE` 取而代之）。留着就是在邀请下一个人「给某个 CTA
加回一个直连控制台的理由」。`reshape_home.py` 的 `CONSOLE_HREF` **留着**：它仍作为
两处 `retarget_link` 的 old 值（品牌带、页尾 CTA）—— 那是「只删除这一个方向」的写法。

### 19.4 三条保留决策

1. **页脚那枚邮箱图标不动**（`aria-label="邮箱"`）。它答的是「怎么发邮件给我们」，
   与「怎么联系我们」（`/contact` 表单）是两件事。改成 `/contact` 不是收口，
   是把一个邮箱地址按钮变成表单入口 —— 而用户没点名删它。
2. **Moha 页不加按钮**。它页首第二条本来就是「开发者文档」（指文档站），没有
   「进入控制台」可改。三个兄弟页变两个按钮、它保持一个，是**正确的不一致**
   （§14.5 挂了三轮的那个「Moha 少一个按钮」，到此不再是缺陷：另三页那条现在
   与「联系我们」同目标，Moha 没有它反而更清爽）。
3. **about 页的「发送简历」保持 `mailto:`**。它是招聘动作，不是商务出口。

### 19.5 守卫：这轮新增的断言与它们抓什么

`reshape_home.stage_guards()`：
- `/contact` 计数 7 → **11**（每加一条入口就得跟着改，所以注释里写明这 11 条是谁）；
- 4 条 node-id **逐条**核 href，期望值写死 `CONTACT_PAGE`（不读名单里的 `new_href`）；
- `CONTACT_RETARGET` **名单长度必须为 4**；
- 站芯 `mailto:` **恰好剩邮箱图标那 1 条**（`mails != [CONTACT_MAIL]` 即报）。

`build_products.guards()`：页首指向 `/contact` 的条数 == `p['actions']` 里落在
`/contact` 的项数（**不写死 2**，Moha 是 1）；正文不得出现 `mailto:`；不得出现
`console.poxiaoshi.cn`（按域名咬，不按「控制台」三个字咬 —— 预览面板里的「控制台」
是插图文字）。

`build_about.guards()`：`href="/contact" class="tf-brand-action` 恰好 2 条。

`tools/qa/reshape.mjs`（**浏览器通道**）：补了 1 条断言 —— 导航条右侧 CTA 的 href
必须是 `/contact`。它复用现有采集字段 `navMenu`（该字段本来就收 `.tf-nav-menu-link`，
里面既有「联系销售」也有「解决方案」），**没有**动采集逻辑。本轮按纪律没跑这条通道，
这条断言因此只是「写下了、语法通过」，未经运行验证；页脚两条与抽屉那条**没有**在
浏览器侧重复实现一遍（`data-page-node-id` 的语义只有 Python 侧知道）。

`link_href_of()` 这轮从 `stage_guards` 的中段**提到函数最上面**：它现在有三处调用者
（商务收口 / 定价区 / 页脚回收）。

### 19.6 反向自测：一个自证陷阱

做法沿用上轮（import 模块喂篡改 doc，不落盘；`reshape_home.py` 是脚本不是模块，
所以用 `exec(源码.replace(写盘那行, '_kept = body'))` 执行）：

```text
A 对照（未篡改）                        MISS=0
B 页脚「联系我们」退回 mailto            MISS=3  （总数+逐条+mailto 三条都响）
C 漏改抽屉那条（名单少一条）              MISS=3  （多一条「名单应为 4 条」）
D 整张名单清空（stage 空转）              MISS=3
E nav CTA 目标改成 /about               MISS=2  （逐条那条第一次没响 —— 见下）
F 页脚「联系销售」旧值写错                MISS=4  （retarget_link 的匹配分支报错）
G 抽屉 node-id 抄错                     MISS=4  （锚点丢失 + 逐条「链接没了」）
```

**E 用例揭穿了一个自证陷阱**，值得单独记：第一版的逐条断言写的是
`got_href != new_href`，而 `new_href` 读的就是被篡改的那张名单 —— 把某条目标改成
`/about` 时，期望值跟着一起变了，于是逐条断言一声不响，只剩总数那条在报（说不清是
哪一条）。改成「期望值写死 `CONTACT_PAGE`」之后 E 才咬住。**断言与它检查的数据是同一份
数据源时，篡改数据源等于同时篡改断言。**

C 用例暴露的是另一类缺口：逐条断言只看得见**名单里**的条目，删掉某项时它对该项静默
—— 所以补了「名单长度必须为 4」。数字型断言要追「这个数是谁算出来的」，否则只防手滑。

### 19.7 核验

```text
python3 tools/build_all.py          -> pipeline ok: 5 generators + 2 static checks
                                        （13 页 / 708 条站内链接闭环 / 0 幽灵类）
三类文案逐条枚举（带 assert）         -> 89 条，落点全部 /contact，0 条例外
console.poxiaoshi.cn / 旧站域名       -> 全站均 0
首页 md5                            -> 未变（products 页 derive 断言通过）
```

浏览器通道与 `qa/*.mjs` 本轮**未跑**（沿用「不自动做本地验证」纪律）。

### 19.8 待拍板

1. **同区重复**：页脚「公司」列现在是「联系我们 / 联系销售 / 关于我们」，前两条
   相邻且同指 `/contact`；移动抽屉里同样是「联系我们」（列表项）+「联系销售」（按钮）
   两条同目标。要我合并成一条（或把其中一条改成别的落点），说一声。
2. **`/contact` 页的页脚「联系我们」是自链**（点它刷新当前页）。站芯一致性的代价，
   无害但冗余；要单独处理就得在 `build_contact.py` 里拆掉那一条，与「站芯永远和首页
   一致」的原则相抵 —— 我倾向不动。
3. 产品页页首两按钮现在同目标（`联系我们` primary + `预约演示` secondary）。文字不同、
   落点相同是中性的，但如果你希望次按钮承担别的动作（比如去文档站），这是它的位置。
4. §18.7 的前三条（页首左栏视觉重量 / 页尾分隔线悬空 / 四页正文只剩一块）仍未处理。

---

## 20. 2026-09-11 晚（十四）：对整条流水线做一轮独立审查

这一轮不改需求，只找问题。审查面是**工作区里全部未提交的改动**（20 个已跟踪文件改动
+ 33 项未跟踪新增 + 13 个产物页），方法是读源码 + 对产物做枚举式实测，不跑浏览器通道。

### 20.1 已修（四条，都是「静态检查本该抓到但没抓到」的）

| # | 问题 | 影响 | 修法 |
| --- | --- | --- | --- |
| 1 | **`products/` 不在 Pages 部署清单里** | 四个产品子页永远不会上线。全站 **269 条**站内链接指向 `/products/*/`（导航下拉 + 页脚在**每一页**上各 20 条，首页正文另 9 条）—— 线上全部 404 | `deploy-pages.yml` 的 staging 循环补 `products` |
| 2 | `tools/__pycache__/*.pyc` 未被忽略 | 生成器之间互相 import（`portal_page` / `mdrender`），一跑就落 `.pyc`；`git add .` 会把 3 个字节码文件提交进仓库 | `.gitignore` 加 `__pycache__/` 与 `*.py[cod]` |
| 3 | **资源路径「少一层」无人检查** | `../assets/`（depth=2 时应为 `../../assets/`）线上 404。原三条正则一条都不命中：`portal_page` 与 `links.py` 的「bare」那条用 `(?<![\w/])` 把前面是 `/` 的情况排除了，正好放过 `../assets/`；「too_deep」只抓更深的；`links.py` 的存在性分支要求 `ref.startswith('../../')`，少一层直接 `continue` | 两处都改为**按层数核**：把 `src="…assets/"` 的前缀层数收成集合，必须等于 `depth` |
| 4 | **`build_products` 的 `/contact` 断言是自证陷阱** | `want = sum(1 for _, href, _ in p['actions'] if href == CONTACT_PAGE)` 拿**被检查的数据**算期望。把某页次按钮改成 `/about`，markup 真的渲染成 `/about`，`want` 与 `got` 一起变成 1 → 断言静默通过（实测 MISS=0）。§19.6 记的就是这个坑，但当时只修了 `reshape_home.py` 那处 | 新增与 `actions` 无关的白名单常量 `ACTION_HREFS`，按渲染顺序逐条核按钮落点 |

反向自测（不落盘）：资源层数三条 —— 少一层 `[1]`、裸 `[0]`、多一层 `[3]`，正对照 `[]`；
`links.py` 端到端造一个只有 `../assets/` 的假站点 → 返回码 1 并指名
`asset path depth [1], want 2`。按钮落点 —— 四页 × 三种篡改（改 `/about` / 控制台 /
mailto）全部咬住；另加一条反面用例「actions 声明 1 条而 markup 渲染 2 个按钮」也被抓。

### 20.2 待拍板（按建议优先级）

0. **部署在子路径，但站内链接全是根相对 —— 这一条最伤，建议先定**。
   GitHub Pages 的实际配置是 `html_url: https://poxiaoyun.github.io/new-portal/`、
   `cname: null`（`gh api repos/poxiaoyun/new-portal/pages`），也就是站点跑在
   **`/new-portal/` 子路径**下。而产物里的站内链接全是**根相对**：

   | 顶层路径 | 条数 |
   | --- | --- |
   | `/products/…` | 269 |
   | `/blog/…` | 216 |
   | `/contact` | 104 |
   | `/` | 54 |
   | `/#pricing` | 26 |
   | `/about` | 39 |
   | **合计** | **708** |

   `href="/products/rune/"` 在 `poxiaoyun.github.io/new-portal/` 下会解析成
   `poxiaoyun.github.io/products/rune/` —— 全部 404。**资源路径不受影响**（`../assets/`
   这类相对引用按目录层级解析，与部署子路径无关，所以页面样式是好的），**只有站内
   链接会断**。

   这不是本轮引入的（`main` 上也有 17 条 `/about` `/blog` `/contact` `/affiliates`
   `/careers`），但本轮把它从 17 条放大到 708 条，并且第一次让「12 个子页 + 站芯里
   每一页都有的导航/页脚链接」全部踩在这个假设上。**`qa/links.py` 抓不到**，因为它的
   `resolve()` 直接拿 `href` 去磁盘根找文件 —— 体检与产物共享同一个「站点根 = 域名根」
   的假设，自洽地全绿。

   三条出路，我倾向 A（反正最终要切到 `www.poxiaoshi.cn`）：
   * **A. 加 `CNAME` 用自定义域名做根部署**。一次性解决，且与「替换 poxiaoshi.cn」
     的目标一致。注意记忆里那条：`poxiaoyun/portal`（Next.js）现在服务着
     `www.poxiaoshi.cn`，**两仓不能同时声明同域**，切换前要先摘旧仓 CNAME、调 DNS。
   * **B. 站内链接全改相对**（按页面深度算 `../products/rune/`）。彻底 base-agnostic，
     代价是 708 条 + `links.py` / 各守卫的 `resolve()` 都要跟着改。
   * **C. 构建期注入 base 前缀**（一个 `SITE_BASE` 常量拼在每个根相对 href 前）。
     改动最小，但产物与部署路径绑定 —— 切域名时要重跑，忘了就是个静默 404 源。

   在你定之前我不动链接形态；**另一个建议**：不管选哪条，`qa/links.py` 都该补一条
   「部署形态」断言（例如读 `SITE_BASE`，或直接断言根相对链接数 == 0），否则这个假设
   永远是隐式的。

1. **口径不对称（建议优先看）**。规则里有两类词待遇不同：
   * 产品页守卫**硬禁**「充值 / 扣费 / 余额」（0 次）
   * 但首页正文有 **11 处「出账」+ 2 处「计费」**：「计量与出账」「按月出账并可导出」
     「✓ 出账已生成」「待出账 0 已全部核销」「计量计费」，且
     `qa/reshape.mjs` 用 `eq('BOSS names its three operating steps', v.bossSteps,
     ['开户与授权', '配额与调度', '计量与出账'])` 把其中一处**锁死**——按口径改文案
     会让浏览器通道报错。

   口径原文说的是「AIRouter 仅计量计价、无充值/扣费闭环，首页不得暗示计费闭环」，
   BOSS 的「出账」可以解释成「报表生成」而非「收钱」，所以这**未必**是违规。问题在于
   两套规则从没在一处对照过，而一处被硬禁、另一处的近义词被断言固化。要么统一收紧
   （首页改写并同步断言），要么在 `PROJECT-MEMORY.md` 里写清「出账 / 计费」属于允许
   词汇及其边界。**在你定之前我不动首页文案，也不动那条断言。**

2. **`build_about.py` 的守卫最弱**：406 行、9 条断言；同期建的 `build_blog.py` 452 行
   26 条、`build_contact.py` 466 行 30 条，产品页另有一套 `guards()`（含三张
   `RETIRED_*` 名单与口径词检查）。about 页是最早建的，没有「段落计数 / 顺序锚点」
   之外的机制。要不要照产品页那套补上口径与结构断言。

3. **站点级 SEO 资产全缺**：`robots.txt`、`sitemap.xml`、`404.html`、
   `favicon.ico`（只有 `icon-mark.svg`）、`site.webmanifest` 都不存在；产物 head 里
   没有 `og:` / `twitter:` 标签，也没有 `canonical`。对一个要替换 `poxiaoshi.cn`
   的官网来说，分享卡片无图、搜索引擎无地图、旧链接无处跳转（404 只会是 Pages
   默认页）。要补的话是新增三个静态文件 + 在 `stage_head` 里加 `og:` 元信息。

4. **`finish_many()` 是先写盘再报错**：`portal_page.py` 的 docstring 写「不会留下
   『一半新一半旧』的目录」，但实现是 `for …: 写盘` → 然后才 `if ctx.miss: raise`。
   守卫确实在调用前跑完了，所以判断是对的、**动作顺序反了** —— 守卫失败时脏产物
   已经覆盖了 `products/`。修法是把 `if ctx.miss` 那段提到写盘循环之前（`finish()`
   同理）。改动会改变「失败时还能看产物」的调试体验，所以等你点头。

5. **`mdrender.py` 的两处不设防**（内容目前自持，属边界问题）：
   * 「以 `<` 开头的行整块透传」+ `_HTML_TAG` 原样保留 —— 是**有意设计**（注释里写了），
     但意味着 `content/blog/*.md` 一旦接受外部供稿就变成注入口；
   * `[文](javascript:…)` 这类链接不做协议白名单，`esc_attr()` 只转义 `&<>"`。
   建议：给链接协议加白名单（`http/https/mailto//`），并把「内容必须自持」写进
   `content/blog/README.md`。

6. **contact 表单在 Secret 缺失时静默降级**：未注入 `WEB3FORMS_ACCESS_KEY` 时产物里
   是 `REPLACE_WITH_YOUR_WEB3FORMS_ACCESS_KEY`，CI 只打 `::warning::` 不失败 ——
   线上会出现一个「提交必然失败」的表单，而没人被通知。建议把这条 warning 升级成
   `::error::`（或至少在部署摘要里显眼提示）。

7. **体积**：`vendor.css` 307KB 未压缩、全站每页都加载（Pages 会 gzip，实际传输
   约 40KB，尚可）；`assets/img/news/20251215-hygon-{cpu,dcu}.webp` 252KB / 239KB、
   `20250724-1.jpg` 136KB 是最大的三张（blog 详情页用），可考虑压到 ~100KB。

8. **陈旧脚本**：`tools/gen_logos.py`（33 行）、`tools/gen_tex.py`（137 行）全仓库无
   任何引用；`tools/gen_blog.py`（129 行）只被本文档提到过；`tools/qa/sbs.py`、
   `qa/slice.py` 是当时做视觉对比的图片拼接/切片脚本，依赖 PIL 且已无用。要么删，
   要么在文件头写清「保留原因」。

9. **`.github/` 整个目录还是未跟踪**：这套 Pages 工作流从未在 Actions 上跑过一次，
   包括那步凭据守卫。第一次推上去时值得盯一眼（另外 `grep -- "$value"` 用的是 BRE，
   建议改 `grep -F`，避免将来 key 里出现正则元字符时误报）。

### 20.3 两条工程教训（本轮踩到的，比修掉的那四条更值钱）

**一、守卫体系的盲区在产物之外。** 这一轮开头，13 个页面全绿：708 条站内链接闭环、
0 幽灵类、5 个生成器的断言全过。但同一个工作区里同时躺着两个会让线上整站不可用的
问题 —— 四个产品页**根本不会被部署**（不在 staging 清单），以及 708 条站内链接在
**实际部署路径下全部 404**（根相对 ↔ 子路径）。

两者都不是「代码写错了」，而是「关于交付的假设没人验证」：

| 断言覆盖的 | 断言没覆盖的 |
| --- | --- |
| 产物内部：链接在磁盘上能解析、类名有 CSS、段落没复活、口径词没出现 | 产物之外：它会被发布吗？发布到哪个路径？`.gitignore` 会不会把 `.pyc` 一起带上？Secret 有没有真的注入？ |

而且 `qa/links.py` 的 `resolve()` 与产物共享同一个「站点根 = 域名根」假设，所以
体检查得越细，越会给人「已经查透了」的错觉。**结论：生成器守卫保护内容，流程守卫
保护交付，两类都要有，且后者的期望值必须来自产物之外**（CI 配置、Pages API、
staging 清单），不能来自被检查的那份假设。

**二、并行编辑同一个文件会丢改动。** 这一轮我给 `build_products.py` 发的两个编辑是在
**同一条消息里并行**发出的（一个加常量、一个改守卫），工具都回了 success，但只有
前一个落地 —— 后一个被基于同一份旧内容的前者覆盖。表现是「自测里 `ACTION_HREFS`
读得到、守卫却仍是旧逻辑且静默通过」，查了三轮才定位到是编辑竞态而不是断言逻辑错。
**同一文件的多次改动必须串行发**；跨文件的并行不受影响（本轮 `.gitignore` +
`deploy-pages.yml`、`portal_page.py` + `links.py` 两批并行都完整落地）。

### 20.4 核验

```text
python3 tools/build_all.py             -> pipeline ok: 5 generators + 2 static checks
                                          （13 页 / 708 条站内链接闭环 / 0 幽灵类）
资源层数断言（derive + links.py）       -> 少一层/裸/多一层三种篡改全部命中，正对照 0
按钮落点断言                            -> 四页 × 三种目标篡改全部命中，反面用例命中
.gitignore                              -> git check-ignore 现在认得 tools/__pycache__
部署清单                                -> products 已列入（站点根六个可发布目录齐全）
gh api .../new-portal/pages             -> html_url 含 /new-portal/、cname 为 null
                                          （§20.2 第 0 条的事实依据）
```

浏览器通道与 `qa/*.mjs` 本轮**未跑**（沿用「不自动做本地验证」纪律）。

## 21. 2026-09-11 晚（十五）：顶部导航 hover 动效加长 + 下拉选项补动效

用户原话：「顶部首页，产品，解决方案，价格与服务，文档中心，关于我们，联系销售，
预约样式的按钮，鼠标浮动上去有个动效，这个动效的时间有点短，加长一点。另外下拉选项
里面的按钮应该也有动效。」

### 21.1 先看清楚「那个动效」是什么

顶部导航的 hover 反馈**不止一层**，加长之前得先分层，否则很容易只改了最显眼的那层：

| 层 | 载体 | 原时长 | 说明 |
| --- | --- | --- | --- |
| 文字乱码跳动 | `main.js` 的 `scramble()` | **0.23–0.29s** | `setInterval(…, 26)`，帧数 = 2 × 字数，逐字还原。四字词 9 帧 ≈ 0.23s。**这才是最显眼的那一层** |
| 颜色过渡 | `.tf-nav-menu-link` 的 `transition` | **0.18s** | `--motion-fast` |
| 按钮按下感 | `.tf-button:hover { transform: scale(.98) }` | 0.4s | 「预约演示」走 `--transition-control` |
| 下拉项背景/边框 | `.tf-nav-dropdown-item` | **无（`transition:none`）** | 见 21.2 |
| 下拉面板淡入 | `.tf-nav-dropdown` | 0.32s | `--motion-base` |

### 21.2 下拉「没有动效」是真的没有，不是错觉

`vendor.css` 在换成 #111 深色面板的那版下拉上写死了：

```css
.tf-nav-product-menu .tf-nav-dropdown         { transition: none; }
.tf-nav-company-dropdown                      { transition: none; }
.tf-nav-product-menu .tf-nav-dropdown-item    { transition: none; transform: none; }
.tf-nav-company-dropdown .tf-nav-dropdown-item { transition: none; transform: none; }
```

即：鼠标划过去时**背景与边框是瞬变的**，连 vendor 通用档
（`.tf-nav-dropdown-item:hover { transform: translate(.25rem) }`）的位移也被这两条作用域
压成了 `none`。上游那版设计是有意为之（原站风格），但用户现在要的就是把它打开。

另有一处同样静默：`main.js` 里 scramble 的绑定选择器只有
`'.tf-nav-menu-link, .tf-footer-link'` —— **下拉项不在里面**，所以「关于我们」下拉里
那四项（带 `.tf-scramble-label`）hover 时文字是死的。这是「下拉里的按钮也该有动效」
这句话的直接答案。

### 21.3 改动

| 文件 | 动作 |
| --- | --- |
| `assets/js/main.js` | 帧间隔 `26` → 常量 `SCRAMBLE_FRAME_MS = 48`（四字 0.23s → 0.43s，五字 0.29s → 0.53s）；绑定选择器补 `.tf-nav-dropdown-item`、`.tf-nav-console-item`；整段包在 `prefers-reduced-motion` 判断里 |
| `assets/css/custom.css` | 新增一节（含注释约 85 行）：`--tf-nav-hover: .45s` + 菜单项 / 触发器 svg / 预约按钮 / 下拉项 / 弹层项 / 两块面板的过渡覆写 + 一条 `prefers-reduced-motion` 把变量降到 `1ms` |

两个文件都是**站芯资产**（13 页共用），改一次全站生效，不需要重跑生成器。
产物 HTML 一行未动。

**`prefers-reduced-motion` 这轮顺手补上了**（skill 里本就有「动效一律补减弱动态效果」
的约定，这次加长动效正好是触发点）：CSS 侧把 `--tf-nav-hover` 降到 `1ms`
（不用 `none`，语义保持「有过渡、只是瞬时」），JS 侧整段不绑事件 —— 只做 CSS 的话，
过渡没了但文字乱码照跳。

### 21.4 两处刻意的取舍

1. **曲线一起换**：`.tf-nav-menu-link` 原来用 `--motion-ease-standard`（对称曲线），
   改成 `--motion-ease-out`。时长拉到 0.45s 后，对称曲线在中段会「停」一下；
   ease-out 起步缓、收尾快，慢而不拖。两个变量是配着改的。
2. **「预约演示」按钮只改时长，不加位移**：`.tf-button:hover` 已经写了
   `transform: scale(.98)`，再叠位移会与 vendor 的 `:where(...)` 那条打架；
   顶部这排按钮的基准语言就是「微缩」。位移只加在下拉项上（`.2rem`，
   比 vendor 通用档的 `.25rem` 稍收 —— 两处下拉是 270px 定宽 + 20px 图标对齐，
   位移再大右侧说明文字会贴边）。

### 21.5 核验：这轮改动全靠「同形选择器 + custom 后加载」压 vendor，必须静态证一遍

`custom.css` 里这些覆写全部是**同特异性**决胜（`.tf-nav-menu-link` 对 `.tf-nav-menu-link`、
`.tf-nav-company-dropdown .tf-nav-dropdown-item` 对同名…），一旦哪条 vendor 规则特异性
更高，覆写就**静默失效**，页面照常渲染、没有任何报错。所以写了个脚本把两张样式表里
命中同一元素、同一声明的规则都列出来，按 `(特异性, 来源序)` 排序看谁赢：

```text
菜单项基础态        OK  CUSTOM   color/opacity var(--tf-nav-hover)
产品下拉开          OK  CUSTOM   opacity/transform var(--tf-nav-hover)
产品下拉项          OK  CUSTOM   background/border/border-radius/color/transform
产品下拉项 hover    OK  CUSTOM   transform: translate(.2rem)
公司下拉项          OK  CUSTOM   background/border/border-radius/color/transform
公司下拉项 hover    OK  CUSTOM   transform: translate(.2rem)
预约按钮基础态      OK  CUSTOM   border/background/color/transform
弹层项基础态        OK  CUSTOM   border/background/color/transform
弹层项箭头          OK  CUSTOM   transform var(--tf-nav-hover)
两类面板 transition OK  CUSTOM   （vendor 那两条分别是 none / --motion-base）
```

（菜单项 `:hover` 的 `color` 仍由 vendor 决定 —— 那是**应该**的：我只改时长，
不改 hover 后的颜色。）

其余：`node --check assets/js/main.js` 通过；两份样式表括号配平；
`python3 tools/build_all.py` 全绿（13 页 / 0 幽灵类）。

### 21.6 待拍板

1. **产品下拉那四项仍然只有 CSS 过渡、没有文字乱码** —— 它们的标题里根本没有
   `.tf-scramble-label`，要有文字动效得改 HTML 结构（给标题套 label）。
   现状：四项 hover 有背景/边框/位移过渡，没有乱码。要不要补？
2. **页脚链接的乱码节奏跟着一起变慢了**（同一个 `SCRAMBLE_FRAME_MS`，页脚链接
   也在绑定列表里）。要不要给页脚单独一档节奏？
3. **移动端抽屉里的按钮没动**（用户点名的是顶部那排）。抽屉里的「联系我们 /
   联系销售」用的是另一套类，要不要一起。
4. 0.45s / 48ms 这两个数是我定的（原来 0.18s / 26ms）。看完实机觉得还要再慢或
   该收一点，说一声 —— 两个数分别在 `custom.css` 的 `--tf-nav-hover` 与
   `main.js` 的 `SCRAMBLE_FRAME_MS`，都是一行。
5. 下拉项那 `.2rem` 位移是我加的（vendor 把通用档的 `.25rem` 压成了 `none`）。
   如果觉得「选项在动」比「只有背景变化」更晃眼，去掉那两条 `:hover` 规则即可。

