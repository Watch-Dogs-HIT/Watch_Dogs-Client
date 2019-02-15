#!/usr/bin/env python
# encoding:utf-8

"""
进程监测核心功能实现 - 进程监测

主要包括
- 获取所有进程号
- 获取进程基本信息
- 获取进程CPU占用率
- 获取路径文件夹总大小
- 获取路径可用大小
- 获取进程占用内存大小
- 获取进程磁盘占用(需要root权限)
- 获取进程网络监控(基于libnethogs,需要读写net文件权限)

参考资料
reference   :   https://www.jianshu.com/p/deb0ed35c1c2
reference   :   https://www.kernel.org/doc/Documentation/filesystems/proc.txt
reference   :   https://github.com/raboof/nethogs

详细的代码与文档
code & doc  :   https://github.com/Watch-Dogs-HIT/Watch_Dogs/blob/master/Watch_Dogs/Core/process_monitor.py
"""

import os
import ctypes
import signal
import datetime
import threading
from copy import deepcopy
from time import time, sleep, localtime, strftime

from sys_monitor import SysMontor
from prcess_exception import wrap_process_exceptions

CALC_FUNC_INTERVAL = 2


class ProcMontor(object):
    """进程检测类"""

    _instance = None

    def __new__(cls, *args, **kw):
        """单例模式"""

        if not cls._instance:
            cls._instance = super(ProcMontor, cls).__new__(cls, *args, **kw)
        return cls._instance

    _note = """
    目前采用的权限问题解决思路:
    在 /usr/bin 目录下执行如下命令
    给python解释器提权 - sudo setcap cap_kill,cap_net_raw,cap_dac_read_search,cap_sys_ptrace+ep ./python2.7
    取消权限 - sudo setcap cap_sys_ptrace+ep ./python2.7
    """

    def __init__(self):
        """初始化数据结构、权限信息"""

    def __process_data_init__(self):
        """初始化进程监控数据结构"""
        # 用于存放所有进程信息相关的数据结构
        all_process_info_dict = {}
        all_process_info_dict["watch_pid"] = set()  # 关注的进程pid
        all_process_info_dict["process_info"] = {}  # 关注进程的相关信息
        all_process_info_dict["prev_cpu_total_time"] = 0  # 上次记录的总CPU时间片
        # nethogs相关
        all_process_info_dict["libnethogs_thread"] = None  # nethogs进程流量监控线程
        all_process_info_dict["libnethogs_thread_install"] = False  # libnethogs是否安装成功
        all_process_info_dict["libnethogs"] = None  # nethogs动态链接库对象
        all_process_info_dict["libnethogs_data"] = {}  # nethogs监测进程流量数据

        # 标准进程相关信息数据结构
        process_info_dict = {}
        process_info_dict["pre_time"] = 0  # 时间片(用于计算各种占用率 - 注意,这里是整个进程公用的)
        process_info_dict["prev_cpu_time"] = None
        process_info_dict["prev_io"] = None

        # 系统内核数据
        self.MEM_PAGE_SIZE = 4  # KB

        # Libnethogs 数据
        # 动态链接库名称
        LIBRARY_NAME = "libnethogs.so"
        # PCAP格式过滤器 eg: "port 80 or port 8080 or port 443"
        FILTER = None

    @wrap_process_exceptions
    def get_all_pid(self):
        """获取所有进程号"""

        def isDigit(x):
            """判断一个字符串是否为正整数"""
            try:
                x = int(x)
                return isinstance(x, int)
            except ValueError:
                return False

        return filter(isDigit, os.listdir("/proc"))

    @wrap_process_exceptions
    def get_process_info(self, pid):
        """获取进程信息 - /proc/[pid]/stat"""
        with open("/proc/{}/stat".format(pid), "r") as p_stat:
            p_data = p_stat.readline()

        p_data = p_data.split(" ")

        with open("/proc/{}/cmdline".format(pid), "r") as p_cmdline:
            p_cmdline = p_cmdline.readline().replace('\0', ' ').strip()

        return {
            "pid": int(p_data[0]),
            "comm": p_data[1].strip(")").strip("("),
            "state": p_data[2],
            "ppid": int(p_data[3]),
            "pgrp": int(p_data[4]),
            "thread num": len(os.listdir("/proc/{}/task".format(pid))),
            "cmdline": p_cmdline
        }

    @wrap_process_exceptions
    def get_process_cpu_time(self, pid):
        """获取进程cpu时间片 - /proc/[pid]/stat"""

        with open("/proc/{}/stat".format(pid), "r") as p_stat:
            p_data = p_stat.readline()

        return sum(map(int, p_data.split(" ")[13:17]))  # 进程cpu时间片 = utime+stime+cutime+cstime

    # def calc_process_cpu_percent(pid, interval=CALC_FUNC_INTERVAL):
    #     """计算进程CPU使用率 (计算的cpu总体占用率)"""
    #     global all_process_info_dict, process_info_dict
    #     # 初始化 - 添加进程信息
    #     if int(pid) not in all_process_info_dict["watch_pid"]:
    #         all_process_info_dict["watch_pid"].add(int(pid))
    #         all_process_info_dict["process_info"][str(pid)] = deepcopy(process_info_dict)  # 添加一个全新的进程数据结构副本
    #
    #     if all_process_info_dict["process_info"][str(pid)]["prev_cpu_time"] is None:
    #         all_process_info_dict["prev_cpu_total_time"] = get_total_cpu_time()[0]
    #         all_process_info_dict["process_info"][str(pid)]["prev_cpu_time"] = get_process_cpu_time(pid)
    #         sleep(interval)
    #
    #     current_cpu_total_time = get_total_cpu_time()[0]
    #     current_process_cpu_time = get_process_cpu_time(pid)
    #     process_cpu_percent = (current_process_cpu_time - all_process_info_dict["process_info"][str(pid)]["prev_cpu_time"]) \
    #                           * 100.0 / (current_cpu_total_time - all_process_info_dict["prev_cpu_total_time"])
    #
    #     all_process_info_dict["process_info"][str(pid)]["prev_cpu_time"] = current_process_cpu_time
    #     all_process_info_dict["prev_cpu_total_time"] = current_cpu_total_time
    #
    #     return process_cpu_percent

    @wrap_process_exceptions
    def get_path_total_size(self, path, style="M"):
        """获取文件夹总大小(默认MB)"""
        total_size = 0
        # 通过 os.walk() 获取所有文件并计算总大小
        for dir_path, dir_names, file_names in os.walk(path):
            for fn in file_names:
                try:
                    total_size += os.path.getsize(os.path.join(dir_path, fn))
                except (OSError, IOError):
                    continue
        # 调整返回单位大小
        if style == "M":
            return round(total_size / 1024. ** 2, 2)
        elif style == "G":
            return round(total_size / 1024. ** 3, 2)
        else:  # "KB"
            return round(total_size / 1024., 2)

    @wrap_process_exceptions
    def get_path_avail_size(self, path, style="G"):
        """获取文件夹所在路径剩余可用大小"""
        path_stat = os.statvfs(path)
        avail_size = path_stat.f_bavail * path_stat.f_frsize

        # 调整返回单位大小
        if style == "M":
            return round(avail_size / 1024. ** 2, 2)
        elif style == "G":
            return round(avail_size / 1024. ** 3, 2)
        else:  # "KB"
            return round(avail_size / 1024., 2)

    @wrap_process_exceptions
    def get_process_mem(self, pid, style="M"):
        """获取进程占用内存 /proc/pid/stat"""

        with open("/proc/{}/stat".format(pid), "r") as p_stat:
            p_data = p_stat.readline()

        # 进程实际占用内存 = rss * page size
        if style == "M":
            return round(int(p_data.split()[23]) * self.MEM_PAGE_SIZE / 1024., 2)
        elif style == "G":
            return round(int(p_data.split()[23]) * self.MEM_PAGE_SIZE / 1024. ** 2, 2)
        else:  # K
            return int(p_data.split()[23]) * self.MEM_PAGE_SIZE

    @wrap_process_exceptions
    def get_process_io(self, pid):
        """获取进程读写数据 - /proc/pid/io"""

        with open("/proc/{}/io".format(pid), "r") as p_io:
            rchar = p_io.readline().split(":")[1].strip()
            wchar = p_io.readline().split(":")[1].strip()

        return map(int, [rchar, wchar])

    # 基于nethogs的进程网络流量监控实现

    @wrap_process_exceptions
    def is_libnethogs_install(self, libnethogs_path="/usr/local/lib/libnethogs.so"):
        """检测libnethogs环境是否安装"""
        return os.path.exists(libnethogs_path) and os.path.isfile(libnethogs_path)


class Action():
    """数据动作 SET(add,update),REMOVE(removed)"""
    SET = 1
    REMOVE = 2

    MAP = {SET: "SET", REMOVE: "REMOVE"}


class LoopStatus():
    """监控进程循环状态"""
    OK = 0
    FAILURE = 1
    NO_DEVICE = 2

    MAP = {OK: "OK", FAILURE: "FAILURE", NO_DEVICE: "NO_DEVICE"}


class NethogsMonitorRecord(ctypes.Structure):
    """nethogs进程流量监控线程 - 用于进程浏览监控的数据结构
    ctypes version of the struct of the same name from libnethogs.h"""
    _fields_ = (("record_id", ctypes.c_int),
                ("name", ctypes.c_char_p),
                ("pid", ctypes.c_int),
                ("uid", ctypes.c_uint32),
                ("device_name", ctypes.c_char_p),
                ("sent_bytes", ctypes.c_uint64),
                ("recv_bytes", ctypes.c_uint64),
                ("sent_kbs", ctypes.c_float),
                ("recv_kbs", ctypes.c_float),
                )


def signal_handler(signal, frame):
    """nethogs进程流量监控线程 - 退出信号处理"""
    global all_process_info_dict
    all_process_info_dict["libnethogs"].nethogsmonitor_breakloop()
    all_process_info_dict["libnethogs_thread"] = None


def dev_args(devnames):
    """
    nethogs进程流量监控线程 - 退出信号处理
    Return the appropriate ctypes arguments for a device name list, to pass
    to libnethogs ``nethogsmonitor_loop_devices``. The return value is a
    2-tuple of devc (``ctypes.c_int``) and devicenames (``ctypes.POINTER``)
    to an array of ``ctypes.c_char``).

    :param devnames: list of device names to monitor
    :type devnames: list
    :return: 2-tuple of devc, devicenames ctypes arguments
    :rtype: tuple
    """
    devc = len(devnames)
    devnames_type = ctypes.c_char_p * devc
    devnames_arg = devnames_type()
    for idx, val in enumerate(devnames):
        devnames_arg[idx] = (val + chr(0)).encode("ascii")
    return ctypes.c_int(devc), ctypes.cast(
        devnames_arg, ctypes.POINTER(ctypes.c_char_p)
    )


def run_monitor_loop(lib, devnames):
    """nethogs进程流量监控线程 - 主循环"""
    global all_process_info_dict

    # Create a type for my callback func. The callback func returns void (None), and accepts as
    # params an int and a pointer to a NethogsMonitorRecord instance.
    # The params and return type of the callback function are mandated by nethogsmonitor_loop().
    # See libnethogs.h.
    CALLBACK_FUNC_TYPE = ctypes.CFUNCTYPE(
        ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(NethogsMonitorRecord)
    )

    filter_arg = FILTER
    if filter_arg is not None:
        filter_arg = ctypes.c_char_p(filter_arg.encode("ascii"))

    if len(devnames) < 1:
        # monitor all devices
        rc = lib.nethogsmonitor_loop(
            CALLBACK_FUNC_TYPE(network_activity_callback),
            filter_arg
        )

    else:
        devc, devicenames = dev_args(devnames)
        rc = lib.nethogsmonitor_loop_devices(
            CALLBACK_FUNC_TYPE(network_activity_callback),
            filter_arg,
            devc,
            devicenames,
            ctypes.c_bool(False)
        )

    if rc != LoopStatus.OK:
        print("nethogsmonitor loop returned {}".format(LoopStatus.MAP[rc]))
    else:
        print("exiting nethogsmonitor loop")


def network_activity_callback(action, data):
    """nethogs进程流量监控线程 - 回掉函数"""
    global all_process_info_dict
    if data.contents.pid in all_process_info_dict["watch_pid"]:
        # 初始化一个新的进程网络监控数据,并替代原来的
        process_net_data = {}
        process_net_data["pid"] = data.contents.pid
        process_net_data["uid"] = data.contents.uid
        process_net_data["action"] = Action.MAP.get(action, "Unknown")
        process_net_data["pid_name"] = data.contents.name
        process_net_data["record_id"] = data.contents.record_id
        process_net_data["time"] = datetime.datetime.now().strftime("%H:%M:%S")  # 这里获取的是本地时间
        process_net_data["device"] = data.contents.device_name.decode("ascii")
        process_net_data["sent_bytes"] = data.contents.sent_bytes
        process_net_data["recv_bytes"] = data.contents.recv_bytes
        process_net_data["sent_kbs"] = round(data.contents.sent_kbs, 2)
        process_net_data["recv_kbs"] = round(data.contents.recv_kbs, 2)

        all_process_info_dict["libnethogs_data"][str(data.contents.pid)] = process_net_data


def init_nethogs_thread():
    """nethogs进程流量监控线程 - 初始化"""
    global all_process_info_dict
    # 处理退出信号
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    # 调用动态链接库
    all_process_info_dict["libnethogs"] = ctypes.CDLL(LIBRARY_NAME)
    # 初始化并创建监控线程
    monitor_thread = threading.Thread(
        target=run_monitor_loop, args=(all_process_info_dict["libnethogs"],
                                       [get_default_net_device()],)
    )
    all_process_info_dict["libnethogs_thread"] = monitor_thread
    monitor_thread.start()
    monitor_thread.join(0.5)

    return


def get_process_net_info(pid):
    """获取进程的网络信息(基于nethogs)"""
    global all_process_info_dict

    if not all_process_info_dict["libnethogs_thread_install"]:
        all_process_info_dict["libnethogs_thread_install"] = is_libnethogs_install()
        if not all_process_info_dict["libnethogs_thread_install"]:
            print "Error : libnethogs is not installed!"
            exit(-1)

    all_process_info_dict["watch_pid"].add(int(pid))
    if not all_process_info_dict["libnethogs_thread"]:
        init_nethogs_thread()

    return all_process_info_dict["libnethogs_data"].get(str(pid), {})
