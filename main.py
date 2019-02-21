#!/usr/bin/env python
# encoding:utf-8

"""
Watch_Dogs
基于Flask的远程监控客户端

- 来源验证
- 异步响应
"""

# todo 1. setting&log 2. 异步

from flask import Flask, request

app = Flask('Watch_Dogs-Client')

ALLOWED_REQUEST_ADDR = []


def request_source_check(func):
    """装饰器 - 请求地址识别"""
    global ALLOWED_REQUEST_ADDR

    def wrapper(*args, **kw):
        # 验证请求地址
        if request.remote_addr not in ALLOWED_REQUEST_ADDR or "0.0.0.0" in ALLOWED_REQUEST_ADDR:
            return "", 403
        result = func(*args, **kw)
        return result

    return wrapper


@app.route('/')
@request_source_check
def hello_world():
    # print request.remote_addr
    return 'Hello World!'


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=8000,
        debug=True
    )
