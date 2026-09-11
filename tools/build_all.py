#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""跑完整条页面流水线，一条命令。**顺序是硬依赖，不是偏好。**

    index.html            <- reshape_home.py   （从 tools/ref 的 pristine 快照派生）
      ├─ about/index.html   <- build_about.py
      ├─ blog/…             <- build_blog.py
      ├─ contact/index.html <- build_contact.py
      ├─ products/*/index.html <- build_products.py
      └─ 404.html           <- build_404.py    （全站兜底页 + 旧前缀兼容层）

后五个都用 portal_page.derive() 从**已定稿的 index.html** 取站芯（head / nav /
移动抽屉 / footer），并且 derive() 会在写盘前断言 index.html 一个字节都没被改动。
所以 index.html 必须先就位、且中途不能动 —— 顺序错了会得到站芯漂移的页面，
而且是静默的。products/ 的深度是 2（products/<slug>/index.html），比 about /
blog / contact 深一层，derive(depth=2) 负责把相对资产路径加够两层；404.html 在
站点根，depth=0。

凭据在构建期从环境变量注入（GitHub Secret -> CI env，见 build_contact.py 顶部）：
    WEB3FORMS_ACCESS_KEY    未设置时 form 用占位符，只 WARN 不失败
    TENCENT_MAP_KEY         未设置时地图退到代理模式，只 WARN 不失败
本地想用真值预览，写进仓库根 .env.local（已 gitignore）。

用法：
    python3 tools/build_all.py            # 全量重建 + 静态体检
    python3 tools/build_all.py --check    # 只跑静态体检，不重建
"""

import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# 顺序即依赖：第一个产站芯，其余五个消费它。
PIPELINE = ['reshape_home.py', 'build_about.py', 'build_blog.py', 'build_contact.py',
            'build_products.py', 'build_404.py']

# 静态体检：不用浏览器、不用起服务，直接在产物上跑。都必须在生成之后执行。
CHECKS = [
    os.path.join('qa', 'links.py'),     # 站内链接闭环 + 路径深度
    os.path.join('qa', 'classes.py'),   # 幽灵类（vendor.css 里没有的工具类）
]


def run(script, *args):
    path = os.path.join(HERE, script)
    print('=' * 72)
    print('> %s %s' % (script, ' '.join(args)))
    print('=' * 72)
    result = subprocess.run([sys.executable, path] + list(args), cwd=ROOT)
    return result.returncode


def static_checks():
    """跑完全部体检，返回失败的清单。"""
    return [script for script in CHECKS if run(script) != 0]


def main():
    # 子进程直接往同一终端写，父进程的 print 在管道里是块缓冲 —— 不改成行缓冲的话
    # 输出会被拆散（`| tail` 时 banner 掉到最后、跑到 build 输出后面去）。
    sys.stdout.reconfigure(line_buffering=True)

    if '--check' in sys.argv:
        sys.exit(1 if static_checks() else 0)

    failed = []
    for script in PIPELINE:
        if run(script) != 0:
            failed.append(script)
            # 站芯没生成，后面三个必然全崩 —— 直接停在第一个失败点，
            # 否则会刷一屏「missing index.html」把真正的错误埋掉。
            break

    if failed:
        print('\nFAILED: %s' % ', '.join(failed))
        sys.exit(1)

    bad = static_checks()
    if bad:
        print('\nFAILED: %s' % ', '.join(bad))
        sys.exit(1)

    print('\npipeline ok: %d generators + %d static checks'
          % (len(PIPELINE), len(CHECKS)))


if __name__ == '__main__':
    main()
