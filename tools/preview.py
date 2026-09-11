#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""本地预览：静态服务 + **强制不缓存**。

为什么不用 `python3 -m http.server`
-----------------------------------
它不发 `Cache-Control`，浏览器就按启发式缓存（大体是 Last-Modified 至今的 10%）
自行决定新鲜期。于是「改了 CSS / HTML → 刷新 → 还是旧样子」，很容易被误判成
「改动没生效」而去翻代码。

2026-09-11 就为此白查了一轮：about 页的页首间距明明已经写进 `about.css`
（服务器返回的文件 md5 与磁盘逐字节一致、含 5 处 `padding-top`），浏览器拿到的
却是缓存副本，看起来像「只有 about 页没生效」。同一次改动里 contact 页之所以
「对了」，只是因为它是个新页面、浏览器里没有它的旧副本。

这里统一发 `Cache-Control: no-store`，改完刷新即最新。**只用于本地预览**；
线上不能这么干（每次都重下全部资源）。

用法
----
    python3 tools/preview.py                 # 起在 8899
    python3 tools/preview.py --port 9000
    python3 tools/preview.py --bind 127.0.0.1
"""

import argparse
import functools
import http.server
import os
import socketserver
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    """静态文件服务，但把所有响应标记成不可缓存。"""

    def end_headers(self):
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()

    def log_message(self, fmt, *args):
        # 默认实现每请求打一行，跑页面时刷屏；只留错误。
        if args and str(args[1]).startswith(('4', '5')):
            sys.stderr.write('  %s %s\n' % (self.address_string(), fmt % args))


class ReusableTCPServer(socketserver.ThreadingTCPServer):
    allow_reuse_address = True
    daemon_threads = True


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--port', type=int, default=8899)
    ap.add_argument('--bind', default='127.0.0.1')
    ap.add_argument('--root', default=ROOT)
    args = ap.parse_args()

    handler = functools.partial(NoCacheHandler, directory=args.root)
    with ReusableTCPServer((args.bind, args.port), handler) as httpd:
        print('preview  http://%s:%d/  (Cache-Control: no-store)' % (args.bind, args.port))
        print('root     %s' % args.root)
        print('Ctrl-C to stop.')
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print('\nstopped.')


if __name__ == '__main__':
    main()
