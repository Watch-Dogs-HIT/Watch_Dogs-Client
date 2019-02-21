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
- 获取进程网络监测(基于libnethogs,需要读写net文件权限)

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
from time import time, sleep

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

    _nethogs_install = """
    有关nethogs的安装方式,请参考:
    https://github.com/Watch-Dogs-HIT/Watch_Dogs/blob/3ab4cdc46d0e91c3b427960ad7c29a838480c774/Watch_Dogs/Core/process_monitor.py#L631
    """

    def __init__(self):
        """初始化数据结构、权限信息"""
        self.__monitor_data_init__()
        self.__process_env_init__()

    def __process_env_init__(self):
        """初始化监测环境"""
        # 初始化系统监测
        self.SysMonitor = SysMontor()
        # 获取netlogs环境
        self.net_monitor_ability = self.is_libnethogs_install()
        # 初始化netlogs进程
        if not self.net_monitor_ability:
            print "netlogs monitor thread initial failed!"
        else:
            self.init_nethogs_thread()

    def __monitor_data_init__(self):
        """初始化进程监测数据结构"""
        # 用于存放所有进程信息相关的数据结构
        self.process_monitor_dict = {}
        self.process_monitor_dict["watch_pid"] = set()  # 关注的进程pid
        self.process_monitor_dict["process"] = {}  # 关注进程的相关信息
        # nethogs相关
        self.process_monitor_dict["libnethogs_thread"] = None  # nethogs进程流量监测线程
        self.process_monitor_dict["libnethogs_thread_install"] = False  # libnethogs是否安装成功
        self.process_monitor_dict["libnethogs"] = None  # nethogs动态链接库对象
        self.process_monitor_dict["libnethogs_data"] = {}  # nethogs监测进程流量数据
        # 系统内核数据
        self.MEM_PAGE_SIZE = 4  # KB
        # Libnethogs 数据
        self.LIBRARY_NAME = "libnethogs.so"  # 动态链接库名称
        self.FILTER = None  # PCAP格式过滤器 eg: "port 80 or port 8080 or port 443"
        self.nethogs_running_status = False  # nethogs进程运行状态

    def init_process_info_data(self):
        """初始化进程信息"""
        # 标准进程相关信息数据结构
        process_info_dict = \
            {
                "prev_total_cpu_time": None,  # 上次记录的CPU时间片
                "prev_process_cpu_time": None,  # 上次记录进程CPU时间片
                "prev_io_read_time": -1,  # 上次读取IO数据的时间
                "prev_io": None,  # 上次读取的IO数据
                "prev_net_data": None,  # 最近一次长期网络数据
            }
        return deepcopy(process_info_dict)

    def get_all_watched_pid(self):
        """获取所有监测的进程号"""
        return self.process_monitor_dict["watch_pid"]

    def watch_process(self, pid):
        """监测进程"""
        self.process_monitor_dict["watch_pid"].add(int(pid))
        if not str(pid) in self.process_monitor_dict["process"]:  # use [in] rather than [dict.has_key()]
            self.process_monitor_dict["process"][str(pid)] = self.init_process_info_data()

    def is_process_watched(self, pid):
        """判断该进程是否被监测"""
        return int(pid) in self.process_monitor_dict["watch_pid"]

    def remove_watched_process(self, pid):
        """移除被监测的进程"""
        if str(pid) in self.process_monitor_dict["process"]:
            self.process_monitor_dict["process"].pop(str(pid))

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

    def calc_process_cpu_percent(self, pid):
        """计算进程CPU使用率 (计算的cpu总体占用率)"""
        # 初始化 - 添加进程信息
        if pid in self.process_monitor_dict["process"]:  # 进程数据必须先被初始化
            process_info = self.process_monitor_dict["process"][str(pid)]
            if not process_info["prev_total_cpu_time"]:  # 第一次计算
                process_info["prev_total_cpu_time"] = self.SysMonitor.get_total_cpu_time()[0]
                process_info["prev_process_cpu_time"] = self.get_process_cpu_time(int(pid))
                return 0
            else:  # 非第一次计算
                current_cpu_total_time = self.SysMonitor.get_total_cpu_time()[0]
                current_process_cpu_time = self.get_process_cpu_time(int(pid))
                process_cpu_percent = round(
                    (current_process_cpu_time - process_info["prev_process_cpu_time"]) * 100.0 \
                    / (current_cpu_total_time - process_info["prev_total_cpu_time"])
                    , 2)
                process_info["prev_total_cpu_time"] = current_cpu_total_time
                process_info["prev_process_cpu_time"] = current_process_cpu_time
                return process_cpu_percent
        else:
            return -1

    @wrap_process_exceptions
    def get_path_total_size(self, path, style="M"):
        """获取文件夹总大小(默认MB)"""
        # todo : 与du -s 命令获取的结果有出入!?
        total_size = 0
        # 通过 os.walk() 获取所有文件并计算总大小
        for root, dirs, files in os.walk(path):
            try:
                total_size += sum([os.path.getsize(os.path.join(root, name)) for name in files])
            except (OSError, IOError):
                continue
        # 调整返回单位大小
        if style == "M":
            return round(total_size / 1024. ** 2, 2)
        elif style == "G":
            return round(total_size / 1024. ** 3, 2)
        elif style == "K":  # "KB"
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

    def calc_process_cpu_io(self, pid, style="M"):
        """计算进程的磁盘IO速度 (默认单位MB/s)"""
        if style == "M":  # MB/s
            io_speed_units = 1000. ** 2
        elif style == "G":  # GB/s
            io_speed_units = 1000. ** 3
        elif style == "K":  # KB/s
            io_speed_units = 1000. ** 1
        else:  # 未指定IO速度单位
            return -1, -1

        if pid in self.process_monitor_dict["process"]:  # 进程数据必须先被初始化
            process_info = self.process_monitor_dict["process"][str(pid)]
            if not process_info["prev_io"]:  # 第一次计算
                process_info["prev_io"] = self.get_process_io(int(pid))
                process_info["prev_io_read_time"] = time()
                return 0., 0.
            else:  # 非第一次计算
                current_time = time()
                current_rchar, current_wchar = self.get_process_io(int(pid))

                read_IO_speed = round(
                    (current_rchar - process_info["prev_io"][0]) / io_speed_units /
                    (current_time - process_info["prev_io_read_time"])
                    , 2)
                write_IO_speed = round(
                    (current_wchar - process_info["prev_io"][1]) / io_speed_units /
                    (current_time - process_info["prev_io_read_time"])
                    , 2)

                process_info["prev_io"] = [current_rchar, current_wchar]
                process_info["prev_io_read_time"] = current_time

                return read_IO_speed, write_IO_speed
        else:
            return -1., -1.

    @wrap_process_exceptions
    def is_libnethogs_install(self, libnethogs_path="/usr/local/lib/libnethogs.so"):
        """检测libnethogs环境是否安装"""
        return os.path.exists(libnethogs_path) and os.path.isfile(libnethogs_path)

    def signal_handler(self, signal, frame):
        """nethogs进程流量监测线程 - 退出信号处理"""
        self.process_monitor_dict["libnethogs"].nethogsmonitor_breakloop()
        self.process_monitor_dict["libnethogs_thread"] = None

    def dev_args(self, devnames):
        """
        nethogs进程流量监测线程 - 网卡参数
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

    def run_monitor_loop(self, lib, devnames):
        """nethogs进程流量监测线程 - 主循环"""
        self.nethogs_running_status = True
        # Create a type for my callback func. The callback func returns void (None), and accepts as
        # params an int and a pointer to a NethogsMonitorRecord instance.
        # The params and return type of the callback function are mandated by nethogsmonitor_loop().
        # See libnethogs.h.
        CALLBACK_FUNC_TYPE = ctypes.CFUNCTYPE(
            ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(NethogsMonitorRecord)
        )

        filter_arg = self.FILTER
        if filter_arg is not None:
            filter_arg = ctypes.c_char_p(filter_arg.encode("ascii"))

        if len(devnames) < 1:
            # monitor all devices
            rc = lib.nethogsmonitor_loop(
                CALLBACK_FUNC_TYPE(self.network_activity_callback),
                filter_arg
            )

        else:
            devc, devicenames = self.dev_args(devnames)
            rc = lib.nethogsmonitor_loop_devices(
                CALLBACK_FUNC_TYPE(self.network_activity_callback),
                filter_arg,
                devc,
                devicenames,
                ctypes.c_bool(False)
            )

        if rc != LoopStatus.OK:
            print("nethogs monitor loop returned {}".format(LoopStatus.MAP[rc]))
            self.nethogs_running_status = False
        else:
            print("exiting nethogsmonitor loop")
            self.nethogs_running_status = False

    def network_activity_callback(self, action, data):
        """nethogs进程流量监测线程 - 回调函数"""
        if data.contents.pid in self.process_monitor_dict["watch_pid"]:
            # 初始化一个新的进程网络监测数据, 并替代原来的
            process_net_data = {}
            process_net_data["pid"] = data.contents.pid
            process_net_data["uid"] = data.contents.uid
            process_net_data["action"] = Action.MAP.get(action, "Unknown")
            process_net_data["pid_name"] = data.contents.name
            process_net_data["record_id"] = data.contents.record_id
            process_net_data["str_time"] = datetime.datetime.now().strftime("%H:%M:%S")  # 这里获取的是本地时间
            process_net_data["unix_timestamp"] = time()  # unix时间戳, 单位是秒
            process_net_data["device"] = data.contents.device_name.decode("ascii")
            process_net_data["sent_bytes"] = data.contents.sent_bytes
            process_net_data["recv_bytes"] = data.contents.recv_bytes
            process_net_data["sent_kbs"] = round(data.contents.sent_kbs, 2)
            process_net_data["recv_kbs"] = round(data.contents.recv_kbs, 2)

            self.process_monitor_dict["libnethogs_data"][str(data.contents.pid)] = process_net_data

    def init_nethogs_thread(self):
        """nethogs进程流量监测线程 - 初始化"""
        # 处理退出信号
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        # 调用动态链接库
        self.process_monitor_dict["libnethogs"] = ctypes.CDLL(self.LIBRARY_NAME)
        # 初始化并创建监测线程
        monitor_thread = threading.Thread(
            target=self.run_monitor_loop, args=(self.process_monitor_dict["libnethogs"],
                                                [self.SysMonitor.get_default_net_device()],)
        )
        self.process_monitor_dict["libnethogs_thread"] = monitor_thread
        monitor_thread.start()
        monitor_thread.join(0.5)

        return

    def get_process_net_info(self, pid):
        """获取进程的网络信息(基于nethogs)"""
        if not self.net_monitor_ability and self.nethogs_running_status:
            print "Error : libnethogs is not running"
            return {"error": "libnethogs is not running"}

        if self.is_process_watched(int(pid)):
            return self.process_monitor_dict["libnethogs_data"].get(str(pid), {})
        else:
            return {"error": "No such process {}".format(str(pid))}

    def calc_process_net_speed(self, pid, speed_type="recent", long_term_sec_interval=6000):
        """
        计算进程网络上传,下载速度[Kbps, kbps]
        瞬时网络速度计算/长期(10min)网络速度计算
        """
        if self.is_process_watched(pid):
            process_info = self.process_monitor_dict["process"][str(pid)]
            if speed_type == "recent":  # 瞬时
                process_net_data = self.process_monitor_dict["libnethogs_data"].get(str(pid), {})
                if process_net_data:
                    process_info["prev_net_data"] = process_net_data
                    return process_net_data["sent_kbs"], process_net_data["recv_kbs"]
                else:
                    return 0., 0.
            else:  # 长期
                prev_net_data = process_info["prev_net_data"]
                if prev_net_data:
                    now_net_data = self.get_process_net_info(pid)
                    send_kbps = round((now_net_data["sent_bytes"] - prev_net_data["sent_bytes"]) / 1024. / \
                                      (now_net_data["unix_timestamp"] - prev_net_data["unix_timestamp"]), 2)
                    recv_kbps = round((now_net_data["recv_bytes"] - prev_net_data["recv_bytes"]) / 1024. / \
                                      (now_net_data["unix_timestamp"] - prev_net_data["unix_timestamp"]), 2)
                    if time() - prev_net_data["unix_timestamp"] > long_term_sec_interval:  # 达到长期速度计算区间
                        process_info["prev_net_data"] = prev_net_data  # 更新旧记录
                    return send_kbps, recv_kbps
                else:
                    return 0., 0.
        else:
            return -1., -1.


# 基于nethogs的进程网络流量监测实现
class Action():
    """数据动作 SET(add,update),REMOVE(removed)"""
    SET = 1
    REMOVE = 2

    MAP = {SET: "SET", REMOVE: "REMOVE"}


class LoopStatus():
    """监测进程循环状态"""
    OK = 0
    FAILURE = 1
    NO_DEVICE = 2

    MAP = {OK: "OK", FAILURE: "FAILURE", NO_DEVICE: "NO_DEVICE"}


class NethogsMonitorRecord(ctypes.Structure):
    """nethogs进程流量监测线程 - 用于进程浏览监测的数据结构
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
