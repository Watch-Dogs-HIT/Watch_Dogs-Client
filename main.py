#!/usr/bin/env python
# encoding:utf-8

"""
Watch_Dogs
基于Flask的远程监控客户端

- 来源验证
- 异步响应
"""

import getpass
from flask import Flask, request, jsonify

from setting import Setting

from Core.sys_monitor import SysMonitor
from Core.process_manage import ProcManager
from Core.process_monitor import ProcMonitor

app = Flask('Watch_Dogs-Client')

# 全局资源及变量
setting = Setting()
logger = setting.logger
ALLOWED_REQUEST_ADDR = setting.ALLOWED_REQUEST_ADDR_LIST
LINUX_USER = getpass.getuser()
system_monitor = SysMonitor()
process_monotor = ProcMonitor()
process_manager = ProcManager()

logger.error("Watch_Dogs-Clinet@" + str(system_monitor.get_intranet_ip()) + "start at" + setting.get_local_time())

# todo : fix return dict problem

def request_source_check(func):
    """装饰器 - 请求地址识别"""
    global ALLOWED_REQUEST_ADDR

    def wrapper(*args, **kw):
        # 验证请求地址
        if request.remote_addr not in ALLOWED_REQUEST_ADDR and "0.0.0.0" not in ALLOWED_REQUEST_ADDR:
            return "", 403
        result = func(*args, **kw)
        return result

    return wrapper


@app.route('/')
@request_source_check
def index():
    global LINUX_USER
    res = {
        "user": LINUX_USER,
        "time": setting.get_local_time(),
        "nethogs env": process_monotor.is_libnethogs_install()
    }
    return jsonify(res)


if __name__ == '__main__':
    app.run(
        host='0.0.0.0',
        port=setting.PORT,
        debug=True,
        threaded=True
    )
