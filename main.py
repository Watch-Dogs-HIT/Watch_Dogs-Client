#!/usr/bin/env python
# encoding:utf-8

"""
Watch_Dogs
基于Flask的远程监控客户端

- 来源验证
- 异步响应
"""

import getpass
import functools
from flask import Flask, request, jsonify

from setting import Setting

from Core.sys_monitor import SysMonitor
from Core.process_manage import ProcManager
from Core.process_monitor import ProcMonitor

app = Flask("Watch_Dogs-Client")

# 全局资源及变量
setting = Setting()
logger = setting.logger
ALLOWED_REQUEST_ADDR = setting.ALLOWED_REQUEST_ADDR_LIST
LINUX_USER = getpass.getuser()
system_monitor = SysMonitor()
process_monotor = ProcMonitor()
process_manager = ProcManager()
# 初始化监控数据
system_monitor.calc_cpu_percent()
system_monitor.calc_cpu_percent_by_cores()
system_monitor.calc_net_speed()

# log
logger.error("Watch_Dogs-Clinet@" + str(system_monitor.get_intranet_ip()) + "start at" + setting.get_local_time())


# 在flask使用装饰器是,需要使用functools.wraps({func_name})以使函数的属性顺利传递给外层的@app.route()
# reference : https://segmentfault.com/a/1190000006658289
# reference : https://stackoverflow.com/questions/31900579/view-function-mapping-is-overwriting-an-existing-endpoint-function-when-using-a

def request_source_check(func):
    """装饰器 - 请求地址识别"""
    global ALLOWED_REQUEST_ADDR

    @functools.wraps(func)
    def wrapper(*args, **kw):
        # 验证请求地址
        if request.remote_addr not in ALLOWED_REQUEST_ADDR and "0.0.0.0" not in ALLOWED_REQUEST_ADDR:
            return jsonify({"Error": "Unknown request addr - " + str(request.remote_addr)}), 403
        try:
            res = func(*args, **kw)
        except Exception as e:
            return jsonify({"Error": str(e)}), 500
        return res

    return wrapper


# -----index-----
@app.route("/")
@request_source_check
def index():
    global LINUX_USER
    res = {
        "user": LINUX_USER,
        "time": setting.get_local_time(),
        "nethogs env": process_monotor.is_libnethogs_install()
    }
    return jsonify(res)


# -----sys------
@app.route("/sys/info")
@request_source_check
def sys_info():
    global system_monitor
    return jsonify(system_monitor.get_sys_info())


@app.route("/sys/loadavg")
@request_source_check
def sys_loadavg():
    global system_monitor
    return jsonify(system_monitor.get_sys_loadavg())


@app.route("/sys/uptime")
@request_source_check
def sys_uptime():
    global system_monitor
    return jsonify(system_monitor.get_sys_uptime())


@app.route("/sys/cpu/info")
@request_source_check
def sys_cpu_info():
    global system_monitor
    return jsonify(system_monitor.get_cpu_info())


@app.route("/sys/cpu/percent")
@request_source_check
def sys_cpu_percent():
    global system_monitor
    return str(system_monitor.calc_cpu_percent())


@app.route("/sys/cpu/percents")
@request_source_check
def sys_cpu_percents():
    global system_monitor
    return jsonify(system_monitor.calc_cpu_percent_by_cores())


@app.route("/sys/mem/info")
@request_source_check
def sys_mem_info():
    global system_monitor
    return jsonify(system_monitor.get_mem_info())


@app.route("/sys/mem/size")
@request_source_check
def sys_mem_size():
    global system_monitor
    return str(system_monitor.get_sys_total_mem())


@app.route("/sys/mem/percent")
@request_source_check
def sys_mem_percent():
    global system_monitor
    return str(system_monitor.calc_mem_percent())


@app.route("/sys/net/devices")
@request_source_check
def sys_net_devices():
    global system_monitor
    return jsonify(system_monitor.get_all_net_device())


@app.route("/sys/net/default_device")
@request_source_check
def sys_net_defaultdevice():
    global system_monitor
    return system_monitor.get_default_net_device()


@app.route("/sys/net/ip")
@request_source_check
def sys_net_ip():
    global system_monitor
    res = {
        "intranet_ip": system_monitor.get_intranet_ip(),
        "extranet_ip": system_monitor.get_extranet_ip()
    }
    return jsonify(res)


@app.route("/sys/net/percent")
@request_source_check
def sys_net_percent():
    global system_monitor
    return jsonify(system_monitor.calc_net_speed())


@app.route("/sys/disk/stat")
@request_source_check
def sys_disk_stat():
    global system_monitor
    return jsonify(system_monitor.get_disk_stat())


# -----manage-----
@app.route("/proc/search/<string:key_word>")
@request_source_check
def proc_search(key_word):
    global process_manager
    search_type = "contain"
    if request.args.has_key("type"):
        search_type = request.args.get("type")
    return jsonify(process_manager.search_pid_by_keyword(key_word, search_type))


@app.route("/proc/kill/<int:pid>")
@request_source_check
def proc_kill(pid):
    global process_manager
    kill_child = False
    kill_process_gourp = False
    if request.args.has_key("kill_child"):
        kill_child = request.args.get("kill_child")
    if request.args.has_key("kill_process_gourp"):
        kill_process_gourp = request.args.get("kill_process_gourp")
    if not kill_child and kill_process_gourp:
        process_manager.kill_process(pid)
    else:
        process_manager.kill_all_process(pid, kill_child, kill_process_gourp)


@app.route("/proc/start/<string:execute_file_full_path>")
@request_source_check
def proc_start(execute_file_full_path):
    global process_manager
    pid = process_manager.start_process(execute_file_full_path)
    return str(pid)


# -----log-----
@app.route("/log/exist")
@request_source_check
def log_exist():
    global process_manager
    if request.args.has_key("path"):
        path = request.args.get("path").encode('utf-8')
        return jsonify(process_manager.is_log_exist(path))
    return jsonify({"ERROR": "NO PATH"})


@app.route("/log/head")
@request_source_check
def log_head():
    global process_manager
    if request.args.has_key("path"):
        path = request.args.get("path").encode('utf-8')
        n = 100
        if request.args.has_key("n"):
            n = int(request.args.get("n").encode('utf-8'))
        return jsonify(process_manager.get_log_head(path, n))
    return jsonify({"ERROR": "NO PATH"})


@app.route("/log/tail")
@request_source_check
def log_tail():
    global process_manager
    if request.args.has_key("path"):
        path = request.args.get("path").encode('utf-8')
        n = 100
        if request.args.has_key("n"):
            n = int(request.args.get("n").encode('utf-8'))
        return jsonify(process_manager.get_log_tail(path, n))
    return jsonify({"ERROR": "NO PATH"})


@app.route("/log/last_update_time")
@request_source_check
def log_last_update_time():
    global process_manager
    if request.args.has_key("path"):
        path = request.args.get("path").encode('utf-8')
        return str(process_manager.get_log_last_update_time(path))
    return jsonify({"ERROR": "NO PATH"})


@app.route("/log/keyword_lines")
@request_source_check
def log_keyword_lines():
    global process_manager
    if request.args.has_key("path") and request.args.has_key("key_word"):
        path = request.args.get("path").encode('utf-8')
        kw = request.args.get("key_word").encode('utf-8')
        return jsonify(process_manager.get_log_keyword_lines(path, kw))
    return jsonify({"ERROR": "NO path & key_word"})


# -----process-----

@app.route("/proc/<int:pid>/")
@request_source_check
def process_all_info(pid):
    """进程所有信息汇总"""
    return str(pid)


@app.route("/proc/all_pid/")
@request_source_check
def proc_all_pid():
    global process_manager
    return jsonify(process_manager.get_all_pid())


@app.route("/proc/all_pid_name/")
@request_source_check
def proc_all_pid_name():
    global process_manager
    return jsonify(process_manager.get_all_pid_name())


@app.route("/proc/<int:pid>/info")
@request_source_check
def proc_pid_info(pid):
    global process_manager
    return jsonify(process_manager.get_process_info(pid))


#
#
# @app.route("/sys/disk/stat")
# @request_source_check
# def sys_disk_stat():
#     global system_monitor
#     return jsonify(system_monitor.get_disk_stat())
#
#
# @app.route("/sys/disk/stat")
# @request_source_check
# def sys_disk_stat():
#     global system_monitor
#     return jsonify(system_monitor.get_disk_stat())


if __name__ == "__main__":
    app.run(
        host="0.0.0.0",
        port=setting.PORT,
        debug=True,
        threaded=True
    )
