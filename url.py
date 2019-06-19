#!/usr/bin/env python
# encoding:utf-8

"""
Watch_Dogs-Client
路由配置
"""

from handlers import *


# 路由配置
HANDLERS = [
    (r'/v', TestHandler),  # version
    (r'.*', NotFoundHandler)  # 404
]
