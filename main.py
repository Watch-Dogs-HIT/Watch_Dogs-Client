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
import traceback
from tornado.ioloop import IOLoop
from tornado.wsgi import WSGIContainer
from tornado.httpserver import HTTPServer

from flask import Flask, request, jsonify

from setting import Setting

from Core.sys_monitor import SysMonitor
from Core.process_manage import ProcManager
from Core.process_monitor import ProcMonitor
from Core.prcess_exception import NoWatchedProcess

app = Flask("Watch_Dogs-Client")

# 全局资源及变量
setting = Setting()
logger = setting.logger
ALLOWED_REQUEST_ADDR = setting.ALLOWED_REQUEST_ADDR_LIST
LINUX_USER = getpass.getuser()
system_monitor = SysMonitor()
process_monitor = ProcMonitor()
process_manager = ProcManager()
# 初始化监控数据
system_monitor.calc_cpu_percent()
system_monitor.calc_cpu_percent_by_cores()
system_monitor.calc_net_speed()
system_monitor.calc_io_speed()
# log
logger.error("Watch_Dogs-Clinet @ " + str(system_monitor.get_intranet_ip()) + " start at " + setting.get_local_time())


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
            logger.error("Unknown request addr - " + str(request.remote_addr))
            return jsonify({"Error": "Unknown request addr - " + str(request.remote_addr)}), 403
        try:
            res = func(*args, **kw)
        except Exception as e:
            logger.error("Error " + str(e.__class__) + " | " + e.message)
            logger.error("Error details : " + traceback.format_exc())
            return jsonify(
                {"Error": e.message, "Error type": str(e.__class__), "Error detail": traceback.format_exc()}), 501
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
        "nethogs env": process_monitor.is_libnethogs_install(),
        "nethogs status": process_monitor.nethogs_running_status
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


@app.route("/sys/net")
@request_source_check
def sys_net_percent():
    global system_monitor
    return jsonify(system_monitor.calc_net_speed())


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


@app.route("/sys/io")
@request_source_check
def sys_io():
    global system_monitor
    return jsonify(system_monitor.calc_io_speed())


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


# -----process all-----

@app.route("/proc/<int:pid>/")
@request_source_check
def process_all_info(pid):
    """进程所有信息汇总"""
    global process_monitor
    if process_monitor.is_process_watched(pid):
        res = process_monitor.get_process_info(pid)
        res["cpu"] = process_monitor.calc_process_cpu_percent(pid)
        res["io"] = process_monitor.calc_process_io_speed(pid)
        res["mem"] = process_monitor.get_process_mem(pid)
        if process_monitor.nethogs_running_status:
            res["net_recent"] = process_monitor.calc_process_net_speed(pid, speed_type="recent")
            res["net"] = process_monitor.calc_process_net_speed(pid, speed_type="long")
        else:  # nethogs error
            res["net_recent"] = [-2., -2.]
            res["net"] = [-2., -2.]
        return jsonify(res)
    else:
        raise NoWatchedProcess(str(pid))


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


# -----watch-----

@app.route("/proc/watch/all")
@request_source_check
def proc_watch_all():
    global process_monitor
    return jsonify(list(process_monitor.get_all_watched_pid()))


@app.route("/proc/watch/is/<int:pid>")
@request_source_check
def proc_watch_is_pid(pid):
    global process_monitor
    return str(process_monitor.is_process_watched(pid))


@app.route("/proc/watch/add/<int:pid>", )
@request_source_check
def proc_watch_add_pid(pid):
    global process_monitor
    if not process_monitor.is_process_watched(pid):
        process_monitor.watch_process(pid)
        # init process data
        process_monitor.calc_process_cpu_percent(pid)
        process_monitor.calc_process_io_speed(pid)
        if process_monitor.net_monitor_ability:
            process_monitor.calc_process_net_speed(pid)
    return str(process_monitor.is_process_watched(pid))


@app.route("/proc/watch/remove/<int:pid>")
@request_source_check
def proc_watch_remove_pid(pid):
    global process_monitor
    process_monitor.remove_watched_process(pid)
    return str(process_monitor.is_process_watched(pid))


# -----process-----

@app.route("/proc/<int:pid>/info")
@request_source_check
def proc_pid_info(pid):
    global process_monitor
    return jsonify(process_monitor.get_process_info(pid))


@app.route("/proc/<int:pid>/cpu")
@request_source_check
def proc_pid_cpu(pid):
    global process_monitor
    return jsonify(process_monitor.calc_process_cpu_percent(pid))


@app.route("/proc/<int:pid>/io")
@request_source_check
def proc_pid_io(pid):
    global process_monitor
    return jsonify(process_monitor.calc_process_io_speed(pid, style="M"))


@app.route("/proc/<int:pid>/net")
@request_source_check
def proc_pid_net(pid):
    global process_monitor
    return jsonify(process_monitor.calc_process_net_speed(pid))


@app.route("/proc/<int:pid>/mem")
@request_source_check
def proc_pid_mem(pid):
    global process_monitor
    return jsonify(process_monitor.get_process_mem(pid))


@app.route("/path/size/total")
@request_source_check
def path_size_total():
    global process_monitor
    if request.args.has_key("path"):
        path = request.args.get("path").encode('utf-8')
        return str(process_monitor.get_path_total_size(path))
    else:
        return jsonify({"ERROR": "NO path"})


@app.route("/path/size/avail")
@request_source_check
def path_size_avail():
    global process_monitor
    if request.args.has_key("path"):
        path = request.args.get("path").encode('utf-8')
        return jsonify(process_monitor.get_path_avail_size(path))
    else:
        return jsonify({"ERROR": "NO path"})


# -----404-----
@app.errorhandler(404)
def api_no_found(e):
    return jsonify(
        {"ERROR": str(request.url) + " no found! please click https://github.com/Watch-Dogs-HIT/Watch_Dogs-Client"}
    ), 404


if __name__ == "__main__":
    # 利用tornado部署flask应用
    http_server = HTTPServer(WSGIContainer(app))
    http_server.listen(setting.PORT, )
    IOLoop.instance().start()

    # flask demo
    # app.run(
    #     host="0.0.0.0",
    #     port=setting.PORT,
    #     debug=False,
    #     threaded=True
    # )
