#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""全站 SEO 资产的单一真源：canonical / og / twitter / JSON-LD / robots / sitemap。

谁在用
------
    tools/reshape_home.py  stage_seo()     首页 head 注入这一块
    tools/portal_page.py   derive()        内容页按页整块替换
    tools/build_seo.py                     robots.txt 与 sitemap.xml
    tools/qa/seo.py                        产物静态体检

为什么是「一整块、带分隔标记」
------------------------------
每个内容页的 head 都是从已定稿的 index.html **整篇搬来的**（见 portal_page.py 顶部）。
而 SEO 标签里有一半是逐页不同的（canonical / og:url / og:title / og:description /
og:type / JSON-LD、404 还要反过来 noindex），另一半是全站一致的（og:site_name /
og:locale / og:image / theme-color）。

逐页那几个一旦直接写进站芯，portal_page.chrome_fingerprint() 那条「内容页站芯必须
与首页逐字节相同」的不变量立刻被打破 —— 而那条不变量是整个派生流程的地基（外壳
从来不是重写的，是搬过来的）。所以这里把它们收进一个**带分隔标记的块**：

    <!--tf-seo:start--> … <!--tf-seo:end-->

首页连内容一起产出；derive() 认标记整块替换；chrome_fingerprint() 认标记整块剥掉
再比对。逐页的「变」与站芯的「不变」被一条显式边界切开，而不是靠一串各改各的
正则去打听谁该动谁不该动。

规范主机
--------
canonical 一律指向 `SITE_URL`（默认 https://www.poxiaoshi.cn）。选 www 而不是裸域，
因为裸域由 GitHub Pages 301 到 www（2026-09-11 实测：https://poxiaoshi.cn/ -> 301 ->
https://www.poxiaoshi.cn/）。

这一层与 tools/site_base.py 的部署前缀注入**互不干涉**：那个管路径前缀
（`/products/` -> `/new-portal/products/`），这个管主机名。canonical 是绝对 URL，
site_base 的正则只认 `href="/…"` 这种根相对写法，两边不会互相改写。反过来说：
域名换了要改 `SITE_URL`（或设同名环境变量），workflow 里有一条断言比对 Pages 的
`cname`，两个方向都查。

站内资源在 canonical / og:image 里为什么是绝对 URL
--------------------------------------------------
og 的消费方（微信、X、Facebook、Slack 的抓取器）不保证解析相对地址，canonical
同理 —— 两者一律用绝对 URL。注意它们指向的是**生产域名**而不是当前预览环境，
这正是想要的：canonical 的意义就是「这份内容的正式地址是那个」。

未做 / 不打算做的
-----------------
* sitemap 里**不写** `<priority>` / `<changefreq>`：Google 与 Bing 都明说忽略它们，
  填了只是噪音，还容易被后来的人当成有意义的信号去调。
* sitemap 的 `<lastmod>` **只给有真实内容日期的页面**（博客文章，取自
  content/blog/<slug>.md 的 `date`）。其余页面不写。理由：lastmod 只有在「持续
  且可核实」时才会被采用，填一个构建时间等于每次发布都宣称整站刚改过。
  曾考虑「从 git log 取每个文件的最后提交日」，放弃的原因是那样每次提交之后重跑
  生成器 sitemap 都会变，本项目「重跑一次产物字节不变」的幂等判据会被噪声淹没
  （CI 的 checkout 也只有 1 层历史）。
* 不做百度主动推送。它要么需要服务端 token，要么往页面里塞一段会回连第三方的
  JS —— 后者是产品决策（性能与隐私），不替用户拍。见 README 的说明。
* 不输出站长平台的归属验证 meta（`<meta name="google-site-verification">` 那一类）。
  归属验证走 DNS TXT，与产物无关；理由与「要加回来时该改哪三处」见下面
  「站长平台的归属验证刻意不在这里」那段。
"""

import html
import json
import os
import re

# --------------------------------------------------------------- 站点身份
# 生产站点的**规范主机**。可用环境变量覆盖（本地预览、或万一换域名时不必改源码），
# 默认即线上真值。别加尾斜杠 —— abs_url() 负责拼。
SITE_URL = (os.environ.get('SITE_URL') or 'https://www.poxiaoshi.cn').rstrip('/')

SITE_NAME = '破晓石科技'
COMPANY_LEGAL = '成都破晓石科技有限公司'
LOCALE = 'zh_CN'
LOCALE_HTML = 'zh-CN'
CONTACT_EMAIL = 'support@xiaoshiai.cn'
ADDRESS = {
    'region': '四川省',
    'locality': '成都市',
    'street': '高新区银泰悦坊17号楼9层',
}

# og 图。1200x630 是各平台通用的 1.91:1；由 tools/gen_og.py 渲染，产物入库。
DEFAULT_OG_IMAGE = 'assets/img/og-default.png'
OG_IMAGE_W, OG_IMAGE_H = 1200, 630
# Organization 的 logo。Google 的知识面板要**位图**（SVG 不认），所以要一张方的。
ORG_LOGO = 'assets/img/icon-512.png'

# 分隔标记。derive() 靠它整块换、chrome_fingerprint() 靠它整块剥，
# 两处都别改写法 —— 改了这里就是「站芯漂移」而报错，不是静默失效。
SEO_START = '<!--tf-seo:start-->'
SEO_END = '<!--tf-seo:end-->'
SEO_BLOCK_RE = re.compile(re.escape(SEO_START) + r'.*?' + re.escape(SEO_END), re.S)

# 搜索结果里给爬虫的指令。
#
# `max-image-preview:large` 是**必须显式写**的：Google 的默认值不是 large，不写就
# 拿不到大图预览（这是近两年最容易漏的一条）。`max-snippet:-1` / `max-video-preview:-1`
# 同理，不写会被截断。Bing 忽略它不认识的指令，不会因此报错。
ROBOTS_INDEX = ('index, follow, max-image-preview:large, '
                'max-snippet:-1, max-video-preview:-1')
ROBOTS_NOINDEX = 'noindex, follow'

# 主题色（移动端地址栏 / 部分社交卡片的底色）。取 --tf-plate。
THEME_COLOR = '#0d0e10'

# 站长平台的**归属验证刻意不在这里**。
#
# 走的是 DNS TXT 记录（在域名解析侧加一条，与页面无关），Google 与 Bing 都已完成
# （2026-09-12）。这里曾经有一组 `<meta name="…-site-verification">` 的构建期注入，
# 已删除，两条理由：
#   1. DNS 验证与产物解耦：改版、换生成器、重出产物都不会让它失效。而 meta 验证
#      一旦某次重构漏掉那个标签，站长后台就掉回「未验证」，收录报告 / sitemap
#      提交 / 抓取诊断会一起锁死 —— 一个只能靠「记得别删」维持的标签不该承担它。
#   2. 那套机制需要三个 Secret，而「配了没配」在产物上的差别只有在站长后台看得
#      出来，本地零症状（当时只能靠在 CI 里打 warning 提醒）。
# 若将来要加回某个平台的验证标签，**三处一起改**：这里输出 + tools/qa/seo.py 的
# 必查项 + workflow 的缺失告警。只加输出不加守卫，就是把上面那个坑原样埋回去。

# JSON-LD 里跨页面互相引用的实体 id。Organization 与 WebSite 只在首页定义，
# 其余页面用 @id 指过去 —— 这是 schema.org 的标准做法，Google 会跨页解析。
ORG_ID = SITE_URL + '/#organization'
SITE_ID = SITE_URL + '/#website'


# ------------------------------------------------------------------- 小工具
def esc(text):
    """属性值与 JSON-LD 里的文本。引号也要转义 —— 它们进的是 `content="…"`。"""
    return html.escape(str(text), quote=True)


def abs_url(path):
    """站内路径 -> 绝对 URL。带不带前导斜杠都行。"""
    return SITE_URL + '/' + str(path).lstrip('/')


def page_url(out_rel):
    """产物相对路径 -> 这个页面自己的规范 URL。404 返回 None。

        index.html                     -> https://…/            （站点根）
        about/index.html               -> https://…/about/
        blog/<slug>/index.html         -> https://…/blog/<slug>/
        404.html                       -> None（它不该有 canonical）

    用 out_rel 而不是让每个调用方各写一遍 URL：out_rel 是生成器已有的参数，
    从它推导就不会出现「页面挪了位置、canonical 忘改」这种漂移。
    """
    out_rel = out_rel.replace(os.sep, '/').lstrip('./')
    if out_rel == '404.html':
        return None
    if out_rel == 'index.html':
        return SITE_URL + '/'
    if out_rel.endswith('/index.html'):
        return abs_url(out_rel[:-len('index.html')])
    return abs_url(out_rel)


def social_title(title):
    """社交卡片上的标题：去掉结尾的 ` | 破晓石科技`。

    只认**结尾**这一种形态（`endswith`），不做「按第一个 | 切」——首页标题里
    有 `晓石云 | Rune Harness …`，按第一个切割会只剩「晓石云」。
    想给某页另写一个更短的社交标题，就显式传 seo_block(og_title=…)。
    """
    suffix = ' | ' + SITE_NAME
    return title[:-len(suffix)] if title.endswith(suffix) else title


def og_image(prefix, slug):
    """某一页专属 og 图的站内路径，如 assets/img/og/blog-2026-03-27-aliyun-ppu.png。

    命名集中在这里：渲染器（tools/gen_og.py）与页面生成器必须算出**同一个**
    文件名，两边各拼一次字符串迟早会错开 —— 而错开的症状是社交卡片静默退成
    默认图（图 404 时平台只是不显示那张图，不报错、页面也没变化）。
    """
    return 'assets/img/og/%s-%s.png' % (prefix, slug)


def clamp(text, limit):
    """按字符截断，带省略号。中英混排按字符数比按字节数稳。"""
    text = re.sub(r'\s+', ' ', str(text)).strip()
    return text if len(text) <= limit else text[:limit - 1].rstrip() + '…'


# og:image 的 MIME 由扩展名推 —— 别在调用方手写 `type="image/png"`：
# 哪天某页换成 jpg 封面，写死的那份就会撒谎（社交平台会因此拒收整张图）。
_MIME = {'.png': 'image/png', '.jpg': 'image/jpeg', '.jpeg': 'image/jpeg',
         '.webp': 'image/webp', '.gif': 'image/gif', '.avif': 'image/avif'}


def image_mime(path):
    return _MIME.get(os.path.splitext(str(path))[1].lower(), 'image/png')


def jsonld_dump(obj):
    """JSON-LD 序列化。

    `json.dumps` 默认**不**转义 `<`，正文里一旦出现 `</script>` 就会提前闭合脚本
    标签（XSS 与「JSON 解析失败」两种后果）。统一转成 `\\u003c`。
    缩进一律不加：这是产物，别让每个页面多背几百字节。
    """
    raw = json.dumps(obj, ensure_ascii=False, separators=(',', ':'))
    return raw.replace('<', '\\u003c')


def _iso_datetime(date_iso):
    """`2026-03-27` -> `2026-03-27T00:00:00+08:00`。

    og 的 article:published_time 与 JSON-LD 的 datePublished 都按 ISO 8601 写。
    frontmatter 里只有日期（没有时刻），补一个本地零点 + 东八区偏移 —— 站点在成都，
    +08:00 是对的；补零点比不写时区更不容易被解析器当成 UTC 而整体前移一天。
    """
    if not date_iso:
        return None
    date_iso = date_iso.strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_iso):
        return date_iso + 'T00:00:00+08:00'
    return date_iso


# ------------------------------------------------------------ JSON-LD 实体
def organization():
    return {
        '@type': 'Organization',
        '@id': ORG_ID,
        'name': COMPANY_LEGAL,
        'alternateName': SITE_NAME,
        'url': SITE_URL + '/',
        'logo': {
            '@type': 'ImageObject',
            'url': abs_url(ORG_LOGO),
            'contentUrl': abs_url(ORG_LOGO),
            'width': 512, 'height': 512,
        },
        'email': CONTACT_EMAIL,
        'address': {
            '@type': 'PostalAddress',
            'addressCountry': 'CN',
            'addressRegion': ADDRESS['region'],
            'addressLocality': ADDRESS['locality'],
            'streetAddress': ADDRESS['street'],
        },
    }


def website():
    return {
        '@type': 'WebSite',
        '@id': SITE_ID,
        'url': SITE_URL + '/',
        'name': SITE_NAME,
        'inLanguage': LOCALE_HTML,
        'publisher': {'@id': ORG_ID},
    }


def webpage(url, title, description):
    return {
        '@type': 'WebPage',
        '@id': url + '#webpage',
        'url': url,
        'name': title,
        'description': description,
        'inLanguage': LOCALE_HTML,
        'isPartOf': {'@id': SITE_ID},
    }


def blog(url, title, description, posts=()):
    """`/blog/` 列表页。posts 是 [(url, title), …]，只引用 @id，不复述内容。"""
    entity = {
        '@type': 'Blog',
        '@id': url + '#blog',
        'url': url,
        'name': title,
        'description': description,
        'inLanguage': LOCALE_HTML,
        'isPartOf': {'@id': SITE_ID},
        'publisher': {'@id': ORG_ID},
    }
    if posts:
        entity['blogPost'] = [{'@type': 'BlogPosting', '@id': u + '#article', 'url': u,
                               'headline': t} for u, t in posts]
    return entity


def blog_posting(url, title, description, published, image, image_size, section=None):
    entity = {
        '@type': 'BlogPosting',
        '@id': url + '#article',
        'mainEntityOfPage': {'@type': 'WebPage', '@id': url + '#webpage'},
        'url': url,
        'headline': title,
        'description': description,
        'datePublished': _iso_datetime(published),
        'inLanguage': LOCALE_HTML,
        'author': {'@id': ORG_ID},
        'publisher': {'@id': ORG_ID},
    }
    if image:
        entity['image'] = {'@type': 'ImageObject', 'url': abs_url(image)}
        if image_size:
            # 宽高只在**确知**时声明：写错的宽高会让部分平台直接放弃取图。
            entity['image']['width'], entity['image']['height'] = image_size
    if section:
        entity['articleSection'] = section
    return entity


def breadcrumb(trail):
    """trail 是 [(name, url 或 None), …]，最后一项是当前页（没有 url）。

    只在**页面上真有层级线索**时才用：博客详情页 hero 里那颗分类胶囊就指回
    /blog（见 build_blog.py 的 detail_hero），层级是真实存在且可见的。
    别给没有父页面的产品页硬编一条 —— 那属于「标记了页面上不存在的东西」。
    """
    items = []
    for i, (name, url) in enumerate(trail, start=1):
        item = {'@type': 'ListItem', 'position': i, 'name': name}
        if url:
            item['item'] = url
        items.append(item)
    return {'@type': 'BreadcrumbList', 'itemListElement': items}


# --------------------------------------------------------------- SEO 块本体
def seo_block(title, description, url, *, kind='webpage', image=None, image_alt=None,
              image_size=(OG_IMAGE_W, OG_IMAGE_H), og_title=None, published=None,
              section=None, noindex=False, breadcrumb_trail=None, extra_jsonld=(),
              posts=()):
    """生成一整块（含分隔标记）的 SEO 标签。

    title / description 与 <title> / <meta name="description"> 是**同一份入参**
    （都由 derive() 传进来），所以三处不会各写各的。

    kind 决定 og:type 与 JSON-LD 的实体类型：
        website  首页           -> og:type=website，JSON-LD: Organization + WebSite
        webpage  其余静态页      -> og:type=website，JSON-LD: WebPage
        blog     博客列表页      -> og:type=website，JSON-LD: Blog
        article  博客详情页      -> og:type=article，JSON-LD: BlogPosting（+ 面包屑）

    image_size 是这张 og 图的真实像素尺寸；传 None 表示不知道、就不声明宽高
    （宽度高度写错会让部分平台放弃取图，比不写更坏）。

    noindex=True（只有 404 页用）时**不输出** canonical / og:url / og:type / JSON-LD：
    那一页没有「自己的正式地址」可言，硬指一个只会把爬虫引到 404 上。
    """
    lines = [SEO_START]
    add = lines.append

    def meta(attr, name, content):
        add('<meta %s="%s" content="%s">' % (attr, esc(name), esc(content)))

    if noindex:
        meta('name', 'robots', ROBOTS_NOINDEX)
    else:
        meta('name', 'robots', ROBOTS_INDEX)
        add('<link rel="canonical" href="%s">' % esc(url))

    meta('name', 'theme-color', THEME_COLOR)

    image = image or DEFAULT_OG_IMAGE
    # 默认 alt 描述的是「这张图是什么」（品牌卡 + 页面标题），不是再抄一遍 og:title。
    image_alt = image_alt or (SITE_NAME + ' · ' + social_title(title))
    og = og_title or social_title(title)
    desc = clamp(description, 200)

    if not noindex:
        meta('property', 'og:type', 'article' if kind == 'article' else 'website')
    meta('property', 'og:site_name', SITE_NAME)
    meta('property', 'og:locale', LOCALE)
    meta('property', 'og:title', og)
    meta('property', 'og:description', desc)
    if not noindex:
        meta('property', 'og:url', url)
    meta('property', 'og:image', abs_url(image))
    meta('property', 'og:image:type', image_mime(image))
    if image_size:
        meta('property', 'og:image:width', image_size[0])
        meta('property', 'og:image:height', image_size[1])
    meta('property', 'og:image:alt', image_alt)
    if kind == 'article' and published:
        meta('property', 'article:published_time', _iso_datetime(published))
        meta('property', 'article:author', SITE_NAME)
        if section:
            meta('property', 'article:section', section)

    # Twitter/X。site / creator 的 @handle 我们并没有，就不编 —— 缺了只是不显示
    # 署名，编错了会把别人的账号挂上去。
    meta('name', 'twitter:card', 'summary_large_image')
    meta('name', 'twitter:title', og)
    meta('name', 'twitter:description', desc)
    meta('name', 'twitter:image', abs_url(image))
    meta('name', 'twitter:image:alt', image_alt)

    # 归属验证的 meta 标签不在这里输出 —— 走 DNS TXT，见文件顶部那段说明。

    graph = []
    if not noindex:
        if kind == 'website':
            graph += [organization(), website()]
        elif kind == 'blog':
            graph.append(blog(url, title, description, posts))
        elif kind == 'article':
            graph.append(blog_posting(url, title, description, published, image,
                                      image_size, section=section))
            if breadcrumb_trail:
                graph.append(breadcrumb(breadcrumb_trail))
        else:
            graph.append(webpage(url, title, description))
    graph += [e for e in extra_jsonld if e]
    if graph:
        add('<script type="application/ld+json">%s</script>'
            % jsonld_dump({'@context': 'https://schema.org', '@graph': graph}))

    add(SEO_END)
    return '\n'.join(lines)
