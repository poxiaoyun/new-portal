# new-portal · 破晓石科技官网

[www.poxiaoshi.cn](https://www.poxiaoshi.cn/) 的源码。

静态站，没有前端框架、没有打包器、没有任何 npm 依赖：**14 个产物（13 个 `index.html`
+ `404.html`）全部由 `tools/` 下的 Python 生成器派生，产物直接入库**，CI 每次 push 到
`main` 重跑一遍生成器再发布到 GitHub Pages。

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
assets/css/*.css      vendor.css（换牌时搬来的编译产物，含整套设计令牌与组件族）
                      custom.css 及各页样式表（自己写的部分）
assets/js/main.js     全站唯一的脚本：导航 / 滚动 / 乱码动效 / 对话回放 / 地图
assets/img/*          图标、栅格纹理、客户 logo
content/blog/*.md     博客内容源（frontmatter + 正文，本站自持）
tools/*.py            页面生成器与公共库
tools/ref/*.html      首页的 pristine 快照 —— reshape_home.py 的输入，别删
tools/qa/            体检脚本（静态两支 + 浏览器三支）
docs/                 设计评审与历史留档，**不上线**
```

## 构建

```bash
python3 tools/build_all.py          # 全量重建 + 静态体检（顺序是硬依赖）
python3 tools/build_all.py --check  # 只跑静态体检，不重建
```

流水线顺序不能调：`reshape_home.py` 先产出首页，另外五个生成器都从**已定稿的
首页**里整篇取站芯（head / nav / 移动抽屉 / footer），并且会在写盘前断言首页一个
字节都没被改动。顺序错了会得到站芯漂移的页面，而且是静默的。

凭据在构建期从环境变量注入，未配置时只用占位符并打 WARN，不会失败：

| 变量 | 用途 | 缺失后果 |
| --- | --- | --- |
| `WEB3FORMS_ACCESS_KEY` | 联系页表单 | 表单渲染正常但提交被拒 |
| `TENCENT_MAP_KEY` | 联系页地图 | 退到降级卡 |
| `SITE_BASE` | 部署前缀，见下文 | 默认按域名根 |

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
```

浏览器那两支要自己起服务，不进 `build_all`（CI 里没跑，`cdp.mjs` 是它们共用的会话层）：

```bash
python3 tools/preview.py --port 8899 &
node tools/qa/reshape.mjs http://127.0.0.1:8899/index.html    # 首页结构 / 交互断言
node tools/qa/page.mjs    http://127.0.0.1:8899/index.html    # 零报错 / 资源 / 四档视口溢出
node tools/qa/page.mjs    http://127.0.0.1:8899/index.html --shots tmp/shots
```

## 部署

`.github/workflows/deploy-pages.yml`，push 到 `main` 触发。**四步顺序都不能动：**

1. **Guard** —— 扫源码里有没有明文凭据。必须在 Build **之前**（构建会把凭据写进产物）。
2. **Build** —— `python3 tools/build_all.py`，用 Secret 注入凭据。
3. **Stage** —— 只把可发布的目录复制进 `dist/`。清单是**白名单 + 反向自查**：
   正向清单漏项的表现是「什么都没发生」，所以还要反过来问一次「仓库里每个页面，
   在清单里吗」。`tools/ content/ docs/` 绝不上线。
4. **Inject** —— `python3 tools/site_base.py dist` 给站内根相对链接注入 `SITE_BASE`
   前缀。夹在 Stage 与 upload 之间：早于 Stage 时 `dist/` 还不存在，晚于 upload 时
   artifact 已经打包好了。

`SITE_BASE` 必须与 Pages 域名配置一致，workflow 里有一条断言**两个方向都查**（绑了
自定义域名却留着前缀、没绑域名却清空了前缀，症状都是「点任何链接都 404」）。期望值
取自 Pages API 而不是产物本身 —— 产物自证不了自己的域名。

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
