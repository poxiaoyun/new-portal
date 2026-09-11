# AGENTS.md · new-portal

给在本仓库里干活的编码代理看的规则。**照着做，别即兴发挥。**

## 0. 一句话

静态站，14 个产物由 `tools/` 的 Python 生成器派生后入库；改站点 = 改生成器 + 重跑，
CI 重跑生成器后发布到 GitHub Pages。

## 1. 红线

| 不许 | 因为 |
| --- | --- |
| 手改 `index.html` / `404.html` / `<page>/index.html` | 下次跑生成器会被整体覆盖；产物是「编译结果」，不是源码 |
| 手改 `assets/css/vendor.css` 里**与我们无关**的规则 | 它是上游 Tailwind 编译产物，改动面越大越难证等价；只改被引用到的那些（现在是 `pxs-*` 类与 `--pxs-*` 令牌） |
| 绕开 `tools/build_all.py` 单独跑某个生成器后提交 | 顺序是硬依赖，且 `--check` 的两支静态体检会漏跑 |
| 改 `SITE_BASE` 而不动 Pages 域名配置（或反之） | 症状是「首页能开、点任何链接都 404」，极具迷惑性；workflow 里有断言拦，但别指望它替你想 |
| 未经用户明确授权 `git commit` / `push` / 建 PR | 用户要求：改完停在工作区并汇报，等指令 |

## 2. 开工前

读这三处，它们定义了「什么算改对」：

- `tools/build_all.py` 顶部 —— 流水线顺序与为什么是这个顺序
- `tools/portal_page.py` 顶部 —— 站芯派生模型（所有内容页共用首页的 head/nav/footer）
- `tools/reshape_home.py` 顶部 —— 首页是从 `tools/ref/index.before-reshape.html`
  这份 pristine 快照**用锚定替换重新派生**的，不是手改出来的

## 3. 标准工作流

```bash
# 改生成器或样式 → 
python3 tools/build_all.py            # 重建 + 静态体检；必须看到 pipeline ok
python3 tools/preview.py --port 8899  # 要人工看效果时（强制不缓存）
node tools/qa/reshape.mjs http://127.0.0.1:8899/index.html
node tools/qa/page.mjs    http://127.0.0.1:8899/index.html
```

改动分三类，别混：

| 改什么 | 改哪里 |
| --- | --- |
| 首页结构 / 文案 | `tools/reshape_home.py` 的 stage 函数与常量（锚定替换，幂等可重跑） |
| 内容页（about / blog / contact / products / 404） | 对应的 `tools/build_*.py`；公共派生逻辑进 `portal_page.py` |
| 样式 | `assets/css/custom.css` 或各页样式表；`pxs-*` 类与 `--pxs-*` 令牌在 `vendor.css` |
| 博客正文 | `content/blog/<slug>.md`，然后 `python3 tools/build_blog.py` |

## 4. 自证：改完怎么证明没改坏

- **产物是「不可手改」的，所以改动必须由生成器解释得了。** 改完重跑一次
  `build_all.py`，产物字节不应再变（幂等）。变了说明有手改残留。
- **纯重命名类改动**（改类名 / 改令牌命名空间）的等价判据：把新旧两侧各自归一化成
  同一个占位符再比字节 —— 结构变化会露出来，重命名会被抹平。逐页比对时用
  `difflib` 按 token（`<[^>]*>|[^<]+`）对齐，不要按行 diff：产物正文挤在一行里。
- **期望值不能取自被检查对象。** 判断「产物里的值对不对」，参照物必须来自产物
  **之外**（Pages API、源码常量、另一份独立清单）。用产物里的值去断言产物，永远绿。
- **守卫比注释可靠。** 每条踩过的坑都要落成可运行断言；只写注释一定会在某次重构里
  被绕过（实测发生过：`SITE_BASE` 的注释没拦住「绑域名后忘清空前缀」那个 bug）。

## 5. 命名空间与品牌清理

- `pxs-*` / `--pxs-*`：从上游样式表搬来的 vendor 组件与设计令牌。
- `tf-*` / `--tf-*`：自己写的组件与调色板。
- **仓库里不允许出现上游品牌痕迹**（类前缀、令牌、URL、注释、文档引言，全部）。
  换牌清理 2026-09-11：`pipellm-*` → `pxs-*`、`--pl-*` → `--pxs-*`、
  `tools/build.py` + 两份上游快照删除。
- 只留一条回归哨兵：`tools/portal_page.py` 的 `UPSTREAM_BRAND_RE`
  （`reshape_home.py`、`qa/reshape.mjs` 各有一份等价实现）。它是**正则不是字面量**，
  故意如此：既咬得住品牌名被拆成两个词的变体，也让这个名字在仓库里归零。
  **不要把它换成字面量。**
- 注意 `pl-1`…`pl-11` 是 Tailwind 的 `padding-left` 工具类，不是品牌令牌；批量改名
  时别用「看到 `pl-` 就换」这种判据。

## 6. 守卫清单（动到相关区域时必须一起更新）

| 位置 | 管什么 |
| --- | --- |
| `tools/reshape_home.py` 的 `stage_guards()` | 首页：必须出现的文案/类、必须消失的旧文案/旧类、div 配平 |
| `tools/build_*.py` 各自的 `guard` / `miss()` | 本页结构、区块顺序、站外链接、`leftover` 残留 |
| `tools/portal_page.py` 的 `finish*()` | 站芯指纹 `chrome_fingerprint()` 与首页逐字节比对 |
| `tools/qa/links.py` | 768 条站内链接闭环 + 路径深度 |
| `tools/qa/classes.py` | 幽灵类（HTML 用了、样式表里没有） |
| `tools/qa/reshape.mjs` / `page.mjs` | 浏览器侧结构与运行时（CI 里没跑） |

**加断言时的两个坑：**

1. **计数型守卫会被新结构误伤。** 一条文案在「乱码动效」的三段式钩子里会出现三次
   （占位 / 动效宿主 / 无障碍副本）。所有「这条文案出现 N 次」的断言都要先把重复
   副本剥掉再数，否则一加动效就红。
2. **豁免名单会掩盖死代码。** 曾有豁免条目声称某类名是 main.js 的钩子，实际 main.js
   里 0 次命中 —— 那个死类名因此被瞒了很久。豁免条目一律要求附上**依据文件**，
   由脚本打开核对。

## 7. 部署

见 `README.md`「部署」。四步顺序（Guard → Build → Stage → Inject → upload）都不能动；
`Stage` 是白名单 + 反向自查（「仓库里每个页面在清单里吗」），加目录时**对着
`ls -1d */` 逐个核**，别凭记忆维护这张清单 —— 曾经漏掉 `products/`，而全站有 269 条
链接指向它。

## 8. 工具陷阱

- **BSD/macOS 的 `grep` 不支持 BRE 里的 `\|`**：`grep -n "a\|b" file` 是找字面量
  `a|b`，会静默返回空 —— 这个假阴性在本项目里已踩过 7 次，误判过「残留引用已清空」。
  **一律用 `grep -E`**，或直接用编辑器/专用搜索工具。
- `grep -r` 找本地服务响应时记得带 `-L`：`/contact` 这类是 301，不带 `-L` 拿到空响应体。
- 判断「产物里的 URL 能否在磁盘上找到对应文件」时，不要真去起服务（沙箱里
  `python urllib` 走代理会 502）；把 URL 直接映射到文件系统路径核对更稳。
- `assets/js/main.js` 的动效钩子是**自发现**的：它扫 `.tf-scramble-label` 再
  `closest('a, button')`，不再维护容器类白名单。所以新增标签只需给钩子，不用改 JS。

## 9. 待办（用户已知，尚未拍板）

- 页脚 21 条标签是否保留乱码动效（当前保留，范围是上一轮我自己扩的）
- 全站 `晓石云` → `破晓石科技` 的剩余 16 处文案是否统一
- 页脚巨型 wordmark 的字号仍按旧的 7 字调（现为 5 字，居中留白偏大）
- SEO 资产缺失：`robots.txt` / `sitemap.xml` / `og:` 图
- Pages 的 **Enforce HTTPS** 尚未勾选（`http://` 不跳 `https://`）
- 各页守卫密度不均
