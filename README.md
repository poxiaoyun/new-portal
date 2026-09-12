# new-portal · 破晓石科技官网

[www.poxiaoshi.cn](https://www.poxiaoshi.cn/) 的源码。

静态站，没有前端框架、没有打包器、没有任何 npm 依赖：**16 个产物（13 个 `index.html`
+ `404.html` + `robots.txt` + `sitemap.xml`）全部由 `tools/` 下的 Python 生成器派生，
产物直接入库**，CI 每次 push 到 `main` 重跑一遍生成器再发布到 GitHub Pages。

## 页面清单

| 路径 | 深度 | 生成器 | 说明 |
| --- | --- | --- | --- |
| `/` | 0 | `tools/reshape_home.py` | 首页：四大产品板块 + Rune Harness 云智算内核 |
| `/about/` | 1 | `tools/build_about.py` | 公司简介 |
| `/blog/` | 1 | `tools/build_blog.py` | 公司动态列表 |
| `/blog/<slug>/` | 2 | 同上 | 5 篇文章详情 |
| `/contact/` | 1 | `tools/build_contact.py` | 联系我们（web3forms 表单 + 腾讯地图） |
| `/products/{rune,moha,ai-router,boss}/` | 2 | `tools/build_products.py` | 四个产品子页 |
| `/404.html` | 0 | `tools/build_404.py` | 兜底页 + 旧地址兼容层 |

「深度」= 产物相对站点根的层数，决定站内资源前缀（`assets/` 还是 `../assets/`）。
它是 `portal_page.derive(depth=…)` 的参数，也是 `qa/links.py` 会核对的属性。

## 目录结构

```
index.html            首页产物（由 tools/ref 的 pristine 快照 + reshape_home.py 派生）
404.html about/ blog/ contact/ products/        其余 13 个产物
robots.txt sitemap.xml                          SEO 产物（tools/build_seo.py）
assets/css/*.css      vendor.css（换牌时搬来的编译产物，含整套设计令牌与组件族）
                      custom.css 及各页样式表（自己写的部分）
assets/js/main.js     全站唯一的脚本：导航 / 滚动 / 乱码动效 / 对话回放 / 地图
assets/img/*          图标、栅格纹理、客户 logo
assets/img/og/        分享图与图标（tools/gen_og.py 渲染，见「SEO」一节）
content/blog/*.md     博客内容源（frontmatter + 正文，本站自持）
content/announcements.md  顶部跑马灯的手写扩展条目（可选，见「顶部公告条」一节）
tools/*.py            页面生成器与公共库（seo.py 是 SEO 标签的唯一真源）
tools/announce.py     顶部跑马灯的内容真源（动态标题 + 手写扩展）
tools/ref/*.html      首页的 pristine 快照 —— reshape_home.py 的输入，别删
tools/qa/            体检脚本（静态三支 + 浏览器三支）
docs/                 设计评审与历史留档，**不上线**
```

## 构建

```bash
python3 tools/build_all.py          # 全量重建 + 静态体检（顺序是硬依赖）
python3 tools/build_all.py --check  # 只跑静态体检，不重建
```

流水线顺序不能调：`reshape_home.py` 先产出首页，中间五个生成器都从**已定稿的
首页**里整篇取站芯（head / nav / 移动抽屉 / footer），并且会在写盘前断言首页一个
字节都没被改动。顺序错了会得到站芯漂移的页面，而且是静默的。最后的
`build_seo.py` 要清点**全部**页面来产出 `robots.txt` / `sitemap.xml`，早于任何
页面生成器就会漏页。

一共 7 个生成器 + 3 项静态体检（`qa/links.py` / `qa/classes.py` / `qa/seo.py`），
全绿时最后一行是 `pipeline ok: 7 generators + 3 static checks`。

构建期从环境变量读入的值。**未配置一律只降级、不失败**（CI 里对每个缺失项打一条
`::warning::`，否则「站点照常发布、只是搜索引擎那边悄悄少了一半能力」这种失败在
本地完全看不见）：

| 变量 | 用途 | 缺失后果 |
| --- | --- | --- |
| `WEB3FORMS_ACCESS_KEY` | 联系页表单 | 表单渲染正常但提交被拒 |
| `TENCENT_MAP_KEY` | 联系页地图 | 退到降级卡 |
| `SITE_BASE` | 部署前缀，见下文 | 默认按域名根 |
| `SITE_URL` | canonical / `og:url` / sitemap 的规范主机，见 [SEO](#seo-与搜索引擎) | 默认 `https://www.poxiaoshi.cn` |

后两个不是凭据，但同样不该由生成器凭空编一个：`SITE_BASE` 编错是全站链接 404，
`SITE_URL` 编错是把搜索引擎指向一个不提供这份内容的主机。

站长平台的**归属验证不在这张表里** —— Google 与 Bing 都走 DNS TXT 记录，与页面产物
无关（2026-09-12 已完成），页面里不输出任何 `*-site-verification` meta。

本地想用真值预览，写进仓库根 `.env.local`（已 gitignore）。

## 本地预览

```bash
python3 tools/preview.py --port 9000
```

`preview.py` = 静态服务 + 强制 `Cache-Control: no-store`。不要用
`python3 -m http.server`：它不发缓存头，浏览器按启发式缓存，改完页面刷新看不到变化，
很容易误判「生成器没生效」。

## 体检

```bash
python3 tools/qa/links.py     # 站内链接闭环 + 路径深度（静态，已进 build_all）
python3 tools/qa/classes.py   # 幽灵类：HTML 用了、样式表里没有的类（静态，已进 build_all）
python3 tools/qa/seo.py       # 每页 title/canonical/og/JSON-LD + robots/sitemap 对账（静态，已进 build_all）
```

浏览器那两支要自己起服务，不进 `build_all`（CI 里没跑，`cdp.mjs` 是它们共用的会话层）：

```bash
python3 tools/preview.py --port 8899 &
node tools/qa/reshape.mjs http://127.0.0.1:8899/index.html    # 首页结构 / 交互断言
node tools/qa/page.mjs    http://127.0.0.1:8899/index.html    # 零报错 / 资源 / 四档视口溢出
node tools/qa/page.mjs    http://127.0.0.1:8899/index.html --shots tmp/shots
```

## 顶部公告条（跑马灯）

每一页顶部那条横向滚动的公告，内容真源是 `tools/announce.py`：

| 组成 | 来源 |
| --- | --- |
| 标签 `New:` | `announce.LABEL` |
| 公司动态的标题（最新 8 条） | `content/blog/*.md`，经 `build_blog.load_posts()` 取 |
| 手写扩展条目 | `content/announcements.md` 的 `## 条目` 一节（可选） |

自动那半**不在别处再抄一份**：改了某篇动态的 `title:`，公告条与 `/blog` 列表页一起变。
要加一条公告就编辑 `content/announcements.md`，一行一条 `- 正文 | /链接`（链接可省，
省了指向 `/blog`），然后重跑构建。格式细节与上限见该文件头部。

### 它不是「往快照里换文案」，是整条轨道重建

公告条属于**站芯**：在首页产出，13 个内容页由 `portal_page.derive()` 整篇搬走。所以
它里面不能有任何逐页差异 —— 一旦有，`chrome_fingerprint()` 会报「站芯漂移」，而那个
报错看起来像是 derive 的锅。

三条容易踩的硬约束（都由 `announce.track_html()` 算好，`announcement_guard()` 对着
产物再验一遍）：

1. **轨道必须是两个逐字节相同的半。** 动画是 `translate(0) → translate(-50%)`
   （`vendor.css` 的 `@keyframes tf-announcement-scroll`），百分比位移按元素自身宽度
   算，两个半不一致就会在循环处跳一下。
2. **半宽 ≥ 视口宽**（`.tf-announcement-viewport` 最宽 1280px），且内容宽度要盖过轨道
   自带的 `min-width:200%` —— 否则 -50% 的位移与实际内容对不上，同样错位。轨道末尾那个
   零宽 `<span>` 是给 flex 的 `gap` 补位用的，**别删**（HTML 注释代替不了它）。
3. **半宽还决定滚动速度。** 动画时长 82s 写在 vendor.css 里，速度 = 半宽 / 82 —— 条目
   从长文案换成短标题后，只按前两条取份数会让速度掉到原来的一半。所以份数还要满足
   `announce.TARGET_SPEED_PX_S`（现取 70px/s，与改前同一档）。

这三条坏掉的样子都只是「循环处看起来有点不对」或「跑马灯变懒了」，构建与三个静态体检
全都不出声，所以守卫放在首页生成器里（`announcement_guard()`）。

### 加了公告条之后，数 href 的守卫要收窄范围

公告条在每一页上重复若干份，于是同一个标题、同一批 `/blog/<slug>/` 链接会出现在**站芯**
里。凡是「这条文案 / 这个链接在页面里出现几次」的守卫，都得把轨道摘掉再数
（`reshape_home.body_without_announcement()` 与 `build_blog._main_html()`），否则会得到
两种相反的症状：**误报**（每条链接从 3 处变 7 处）或**静默失效**（标题被轨道保底，
`main` 里其实已经丢了也照样绿）。

## SEO 与搜索引擎

全站 SEO 标签的**唯一真源**是 `tools/seo.py`（站点身份常量 + 各标签的组装函数）。
改域名、改公司名、换 og 图，只改这一个文件，其余全是它的消费方：

| 产物 | 谁产出 | 在 `build_all.py` 里？ |
| --- | --- | --- |
| 各页 head 里的 SEO 块 | `tools/seo.py`，由 `reshape_home.py` 与 `portal_page.derive()` 调用 | 是 |
| `robots.txt` / `sitemap.xml` | `tools/build_seo.py` | 是 |
| `assets/img/og*.png` 等 13 张图 | `tools/gen_og.py` | **否**，见下 |

### 为什么 SEO 标签是一整块带标记的

内容页的 head 是从首页**整篇搬来**的（见「构建」一节），而 SEO 标签里有一半逐页
不同（canonical / `og:url` / `og:type` / JSON-LD / 404 还要反过来 noindex）。直接写进
站芯会立刻打破 `chrome_fingerprint()` 那条「内容页站芯必须与首页逐字节相同」的不变量。
所以它们被收进一个显式定界的块：

```html
<!--tf-seo:start--> … <!--tf-seo:end-->
```

首页连内容一起产出；`derive()` 认标记整块替换；`chrome_fingerprint()` 认标记整块剥掉
再比对。**标记写法别改** —— 改了不是静默失效，是「站芯漂移」直接报错。

### 分享图与图标

`og:image`、`favicon-96.png`、`apple-touch-icon.png`、`icon-512.png` 都由
`tools/gen_og.py` 用**无头 Chrome 渲染 HTML 卡片**得到，产物入库：

```bash
python3 tools/gen_og.py --list            # 看有哪些卡
python3 tools/gen_og.py                   # 渲染全部 13 张
python3 tools/gen_og.py --only blog       # 只渲染某一类（default/blog/product/icon）
```

它**刻意不进 `build_all.py`**：要起浏览器（CI 里没有），而图片只在改文案/换版式时
才需要重出。改完卡片记得连产物一起提交，否则线上分享图会是旧的。

三处「期望值不能取自被检查对象」的落实：canonical 主机取自 `seo.SITE_URL` 常量；
`og:image:width/height` 现读 PNG/JPEG 文件头；sitemap 与 `qa/links.py` 共用同一套
页面发现算法并**双向对账**（互查有没有对方没有的页）。

### 搜索引擎

**归属验证走 DNS TXT 记录** —— 在域名解析侧加一条，与页面产物完全解耦。Google 与
Bing 都已完成（2026-09-12），页面里**不输出**任何 `<meta name="…-site-verification">`。

这是刻意的选择，不是遗漏：DNS 验证不会因为改版、换生成器、重出产物而失效；而 meta
验证一旦某次重构漏掉那个标签，站长后台就悄悄掉回「未验证」，收录报告 / sitemap 提交
/ 抓取诊断会一起锁死 —— 那个标签只能靠「记得别删」维持。百度那条已删除（不为它做
站长平台适配，可见性走下面的被动发现）。

产物侧（`robots.txt` + `sitemap.xml` + canonical）齐备之后，只剩一件人工动作：把

```
https://www.poxiaoshi.cn/sitemap.xml
```

提交给 Google Search Console 与 Bing 网站管理员工具（Bing 也可直接从 GSC 导入）。
各家的爬虫本来就能靠 `robots.txt` 里的 sitemap 指针找到它，提交只是让收录开始得更快。

`robots.txt` **刻意不写任何 `Disallow`** —— 整站没有登录墙、付费墙，也没有不该抓的
目录，写了就得维护一份清单。它只声明 `Allow: /` 与 sitemap 地址。

**不做任何主动推送**（百度推送、IndexNow 都没有）。前者要么需要服务端 token，要么
往页面里塞一段会回连第三方的 JS；后者要求把 key 放进站点根。两者都是把「收录」的
触发权交给站外，收益不确定而维护面确定。目前走被动发现：`sitemap.xml` + 正常的
`robots.txt`，各家的爬虫会按这两者自行发现页面。

## 部署

`.github/workflows/deploy-pages.yml`，push 到 `main` 触发。**五步顺序都不能动：**

1. **Guard** —— 扫源码里有没有明文凭据。必须在 Build **之前**（构建会把凭据写进产物）。
2. **Build** —— `python3 tools/build_all.py`，用 Secret 注入凭据。
3. **Stage** —— 只把可发布的文件与目录复制进 `dist/`。清单是**白名单 + 反向自查**：
   正向清单漏项的表现是「什么都没发生」，所以还要反过来问一次「仓库里有、清单里
   没有的东西有哪些」。反向自查覆盖两类 —— 含页面的目录（按 `index.html` 找）和
   站点根的散装文件（**非 `.md`、非隐藏的都必须在清单里**，`robots.txt` /
   `sitemap.xml` 正是这一类）。`tools/ content/ docs/` 绝不上线。
4. **Assert** —— 读 Pages API 的 `cname`（产物之外），**三个方向**查域名自洽：
   `SITE_BASE` 是否与实际部署形态一致、`SITE_URL` 的主机是否就是 Pages 服务的域名、
   以及产物首页的 canonical 是否真的按 `SITE_URL` 写。三者接起来才闭合 —— 少任何
   一条，常量与实际都能各说各话而无人发现。
5. **Inject** —— `python3 tools/site_base.py dist` 给站内根相对链接注入 `SITE_BASE`
   前缀。夹在 Stage 与 upload 之间：早于 Stage 时 `dist/` 还不存在，晚于 upload 时
   artifact 已经打包好了。

`SITE_BASE` 与 `SITE_URL` 都必须与 Pages 的实际域名配置一致（第 4 步核对）。这两处
写错的症状完全不同：`SITE_BASE` 错是「点任何链接都 404」（很显眼），`SITE_URL` 错则
本地全绿、页面全好 —— 只是 canonical / `og:url` / JSON-LD 把搜索引擎指向一个不再
提供这份内容的主机。期望值取自 Pages API 而不是产物本身 —— 产物自证不了自己的域名。

**只改 `dist/`，源码语义不动。** 全部生成器与体检脚本都建立在「站点根 == 域名根」这个
假设上，产出根相对链接；一旦发布在子路径下，只在这一步改写产物。

## 内容维护（博客）

`content/blog/<slug>.md`，frontmatter 格式见 `content/blog/README.md`。

```bash
python3 tools/build_blog.py    # 重跑后列表页与详情页一起更新
```

首页三张博客预览卡的封面也从同一份内容源的 `cover:` 读，**两处不能各写一个图名**。

## 约定

- **不要手改产物。** `index.html` 是 133 KB、正文挤在一行里的巨型标记，`vendor.css`
  是上游 Tailwind 的编译产物。改结构改生成器，改文案改生成器里的常量，然后重跑。
- **命名空间**：`pxs-*` 是从上游搬来的 vendor 组件与设计令牌（`--pxs-*`），`tf-*`
  是自己写的样式。改前者要连 `vendor.css` 一起改，且改完必须让 `qa/classes.py` 依然
  全绿 —— 它正是「HTML 用的类样式表里没有」这个方向的哨兵。
- **CSS 类名与设计令牌里不允许再出现上游品牌痕迹。** 换牌清理（2026-09-11）把
  类前缀、令牌命名空间、注释与文档里的溯源表述统一换成了本站写法，只留下一条
  回归哨兵（`tools/portal_page.py` 的 `UPSTREAM_BRAND_RE`，五个内容页生成器 +
  `reshape_home.py` + `qa/reshape.mjs` 共用同一份判据）。哨兵故意写成正则而不是
  字面量：既咬得住品牌名被拆成两个词的变体，也让这个名字在仓库里彻底归零。
- **守卫优先于注释。** 每条「踩过的坑」都应该落成可运行的断言，注释记不住。
  加断言时注意**计数型守卫**会被新结构误伤（同一条文案在三段式钩子里出现三次，
  那些「出现 N 次」的断言要先把重复副本剥掉再数）。
- 未绑自定义域名时的历史包袱：`404.html` 里带一段 `/new-portal/` 前缀剥除脚本，
  且**只在域名根部署时生成**（子路径下剥前缀等于把合法 URL 改成另一个 404）。

## 相关

- 上级工作区与其余仓库的导航：`../CONTEXT-MAP.md`
- 本轮换牌清理与历次评审留档：`docs/CODE-REVIEW-2026-09-11.md`
