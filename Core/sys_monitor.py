#!/usr/bin/env python
# encoding:utf-8

"""
进程监测核心功能实现 - 系统监测

主要包括
- 总体CPU占用率
- 总体内存占用率
- 总体网络上下载速度
- 各核心CPU占用率
- 系统信息
- 系统总内存
- 系统启动时间
- 系统平均负载
- 系统磁盘占用

参考资料
reference   :   https://www.jianshu.com/p/deb0ed35c1c2
reference   :   https://www.kernel.org/doc/Documentation/filesystems/proc.txt

详细的代码与文档
code & doc  :   https://github.com/h-j-13/Watch_Dogs/blob/master/Watch_Dogs/Core/sys_monitor.py
"""

import re
import socket
import urllib2
from os import statvfs
from time import sleep, time, strftime, localtime

from prcess_exception import wrap_process_exceptions

CALC_FUNC_INTERVAL = 2  # 通用调用函数间隔(秒)
SECTOR_SIZE_FALLBACK = 512  # 默认扇区大小 512


class SysMonitor(object):
    """系统监视模块"""

    _instance = None

    def __new__(cls, *args, **kw):
        """单例模式"""

        if not cls._instance:
            cls._instance = super(SysMonitor, cls).__new__(cls, *args, **kw)
        return cls._instance

    def __init__(self):
        self.prev_cpu_work_time = 0
        self.prev_cpu_total_time = 0
        self.prev_cpu_time_by_cores = {}
        self.prev_net_receive_byte = 0
        self.prev_net_send_byte = 0
        self.prev_net_time = 0
        self.prev_disk_time = 0
        self.prev_disk_rbytes = 0
        self.prev_disk_wbytes = 0

    @wrap_process_exceptions
    def get_total_cpu_time(self):
        """获取总cpu时间 - /proc/stat"""

        with open("/proc/stat", "r") as cpu_stat:
            total_cpu_time = cpu_stat.readline().replace('cpu', '').strip()
            user, nice, system, idle, iowait, irq, softirq, steal, guest, guestnice = \
                map(int, total_cpu_time.split(' '))
            return user + nice + system + idle + iowait + irq + softirq + steal, user + nice + system

    def calc_cpu_percent(self):
        """计算CPU总占用率 (返回的是百分比)"""
        # 两次调用之间的间隔最好不要小于2s,否则可能会为0
        if self.prev_cpu_work_time == 0:  # 未初始化
            self.prev_cpu_total_time, self.prev_cpu_work_time = self.get_total_cpu_time()
            return 0.
        current_total_time, current_work_time = self.get_total_cpu_time()
        cpu_percent = round((current_work_time - self.prev_cpu_work_time) * 100.0 \
                            / (current_total_time - self.prev_cpu_total_time), 2)
        self.prev_cpu_total_time, self.prev_cpu_work_time = current_total_time, current_work_time
        return cpu_percent

    @wrap_process_exceptions
    def get_cpu_total_time_by_cores(self):
        """获取各核心cpu时间 - /proc/stat"""
        cpu_total_times = {}

        with open("/proc/stat", "r") as cpu_stat:
            for line in cpu_stat:
                if line.startswith("cpu"):
                    cpu_name = line.split(' ')[0].strip()
                    if cpu_name != "cpu":
                        user, nice, system, idle, iowait, irq, softirq, steal, guest, guestnice = \
                            map(int, line.split(' ')[1:])
                        cpu_total_times[cpu_name] = [user + nice + system + idle + iowait + irq + softirq + steal,
                                                     user + nice + system]

        return cpu_total_times

    def calc_cpu_percent_by_cores(self):
        """计算CPU各核占用率 (返回的是百分比)"""
        cpu_percent_by_cores = {}

        if not self.prev_cpu_time_by_cores:  # 未初始化
            self.prev_cpu_time_by_cores = self.get_cpu_total_time_by_cores()
            for cpu_name in self.prev_cpu_time_by_cores.keys():
                cpu_percent_by_cores[cpu_name] = 0.
        else:
            current_cpu_time_by_cores = self.get_cpu_total_time_by_cores()
            for cpu_name in current_cpu_time_by_cores.keys():
                cpu_percent_by_cores[cpu_name] = round(
                    (current_cpu_time_by_cores[cpu_name][1] - self.prev_cpu_time_by_cores[cpu_name][1]) * 100.0 / \
                    (current_cpu_time_by_cores[cpu_name][0] - self.prev_cpu_time_by_cores[cpu_name][0]), 2)
            self.prev_cpu_time_by_cores = current_cpu_time_by_cores

        return cpu_percent_by_cores

    @wrap_process_exceptions
    def get_mem_info(self):
        """获取内存信息 - /proc/meminfo"""

        with open("/proc/meminfo", "r") as mem_info:
            MemTotal = mem_info.readline().split(":")[1].strip().strip("kB")
            MemFree = mem_info.readline().split(":")[1].strip().strip("kB")
            MemAvailable = mem_info.readline().split(":")[1].strip().strip("kB")
            # 只需要前三行
            return map(int, [MemTotal, MemFree, MemAvailable])

    def calc_mem_percent(self):
        """计算系统内存占用率 (返回的是百分比)"""
        MemTotal, MemFree, MemAvailable = self.get_mem_info()
        mem_percent = round((MemTotal - MemAvailable) * 100.0 / MemTotal, 2)
        return mem_percent

    @wrap_process_exceptions
    def get_all_net_device(self):
        """获取所有网卡(不包括本地回环)"""

        # Note : 网卡命名规则
        # lo        -   本地回环
        # eth0      -   物理网卡(数字代表第几个,下同)
        # wlan0     -   无线网卡
        # br0       -   网桥
        # ens3      -   虚拟网卡 vps?
        # ppp0      -   ppp拨号
        # tpp0      -   ...

        devices = []
        with open("/proc/net/dev", "r") as net_dev:
            for line in net_dev:
                if not line.count("lo:") and line.count(":"):
                    devices.append(line.split(":")[0].strip())

        return devices

    def get_default_net_device(self):
        """获取默认网卡 - 默认选取流量最大的网卡作为默认监控网卡(本地回环除外)"""
        devices = self.get_all_net_device()
        default_net_device = "eth0"

        if default_net_device in devices:
            return default_net_device

        else:  # 获取流量最大的网卡作为默认网卡
            temp_d = ''
            max_byte = -1
            for device_name in devices:
                if max_byte < sum(self.get_net_dev_data(device_name)):
                    max_byte = self.get_net_dev_data(device_name)
                    temp_d = device_name
            return temp_d

    @wrap_process_exceptions
    def get_net_dev_data(self, device):
        """获取系统网络数据(某一网卡) -  /proc/net/dev"""
        receive_bytes = -1
        send_bytes = -1
        with open("/proc/net/dev", "r") as net_dev:
            for line in net_dev:
                if line.find(device) != -1:
                    dev_data = map(int, filter(lambda x: x, line.split(":", 2)[1].strip().split(" ")))
                    receive_bytes += dev_data[0]
                    send_bytes += dev_data[8]

        return receive_bytes, send_bytes

    @wrap_process_exceptions
    def calc_net_speed(self, device_name=None):
        """
        计算某一网卡的网络速度
        :return: [上传速度,下载速度] (单位为Kbps)
        """
        if not device_name:  # 未指定网卡
            device_name = self.get_default_net_device()
        if self.prev_net_receive_byte == 0:  # 未初始化
            self.prev_net_receive_byte, self.prev_net_send_byte = self.get_net_dev_data(device_name)
            self.prev_net_time = time()
            return 0., 0.
        current_net_receive_byte, current_net_send_byte = self.get_net_dev_data(device_name)
        current_net_time = time()
        download_speed = (current_net_receive_byte - self.prev_net_receive_byte) / 1024.0 / (
                current_net_time - self.prev_net_time)
        upload_speed = (current_net_send_byte - self.prev_net_send_byte) / 1024.0 / (
                current_net_time - self.prev_net_time)
        self.prev_net_receive_byte, self.prev_net_send_byte = current_net_receive_byte, current_net_send_byte
        self.prev_net_time = current_net_time
        return upload_speed, download_speed

    @wrap_process_exceptions
    def get_cpu_info(self):
        """系统CPU信息 - /proc/cpuinfo"""

        result = []
        c = ""
        with open("/proc/cpuinfo", "r") as cpuinfo:
            for line in cpuinfo:
                if line.startswith("processor"):
                    c = ""
                elif line.startswith("model name"):
                    c += line.split(":", 1)[1].strip() + " - "
                elif line.startswith("cpu MHz"):
                    c += line.split(":", 1)[1].strip() + "Mhz "
                elif line.startswith("siblings"):
                    c += line.split(":", 1)[1].strip() + " CPUs"
                elif line.startswith("power management"):
                    result.append(c)

        return result

    @wrap_process_exceptions
    def get_sys_info(self):
        """系统信息 - /proc/version"""

        sys_info = {"kernel": "", "system": ""}
        with open("/proc/version", "r") as version:
            sys_info_data = version.readline()
        sys_info["kernel"] = sys_info_data.split('(')[0].strip()
        sys_info["system"] = sys_info_data.split('(')[3].split(')')[0].strip()

        return sys_info

    def get_sys_total_mem(self, style="M"):
        """获取总内存大小 - /proc/meminfo"""

        style_size = 1024. ** 1  # 默认为M
        if style == 'K':
            style_size = 1024. ** 0
        elif style == 'G':
            style_size = 1024. ** 2
        return round(self.get_mem_info()[0] / style_size, 4)

    @wrap_process_exceptions
    def get_sys_loadavg(self):
        """获取系统平均负载 - /proc/loadavg"""

        la = {}
        with open("/proc/loadavg", "r") as loadavg:
            la['lavg_1'], la['lavg_5'], la['lavg_15'], la['nr'], la['last_pid'] = \
                loadavg.readline().split()

        return la

    @wrap_process_exceptions
    def get_sys_uptime(self):
        """获取系统运行时间 - /proc/uptime"""

        def second2time_str(sec):
            m, s = divmod(sec, 60)
            h, m = divmod(m, 60)
            d, h = divmod(h, 24)
            return "%d Days %d hours %02d min %02d secs" % (d, h, m, s)

        ut = {}
        cpu_core_num = len(self.get_cpu_total_time_by_cores().keys())  # 计算cpu核数
        with open("/proc/uptime", "r") as uptime:
            system_uptime, idle_time = map(float, uptime.readline().split())
            ut["system_uptime"] = second2time_str(int(system_uptime))
            ut["idle_time"] = idle_time
            ut["free rate"] = round(idle_time / system_uptime / cpu_core_num, 4)

        return ut

    @wrap_process_exceptions
    def get_disk_stat(self, style='G'):
        """获取磁盘占用情况"""

        # statvfs() http://www.runoob.com/python/os-statvfs.html
        # reference pydf - https://github.com/k4rtik/pydf/tree/c59c16df1d1086d03f8948338238bf380431deb9
        disk_stat = []

        def get_all_mount_points():
            """获取所有挂载点 - /proc/mounts"""

            mount_points = {}
            with open("/proc/mounts", "r") as mounts:
                for line in mounts.readlines():
                    spl = line.split()
                    if len(spl) < 4:
                        continue
                    device, mp, typ, opts = spl[0:4]
                    opts = opts.split(',')
                    mount_points[mp] = (device, typ, opts)

            return mount_points

        def is_remote_fs(fs):
            """test if fs (as type) is a remote one"""

            # reference pydf - https://github.com/k4rtik/pydf/tree/c59c16df1d1086d03f8948338238bf380431deb9

            return fs.lower() in ["nfs", "smbfs", "cifs", "ncpfs", "afs", "coda",
                                  "ftpfs", "mfs", "sshfs", "fuse.sshfs", "nfs4"]

        def is_special_fs(fs):
            """test if fs (as type) is a special one
            in addition, a filesystem is special if it has number of blocks equal to 0"""

            # reference pydf - https://github.com/k4rtik/pydf/tree/c59c16df1d1086d03f8948338238bf380431deb9

            return fs.lower() in ["tmpfs", "devpts", "devtmpfs", "proc", "sysfs", "usbfs", "devfs", "fdescfs",
                                  "linprocfs"]

        mp = get_all_mount_points()

        for mount_point in mp.keys():
            device, fstype, opts = mp[mount_point]

            # 过滤掉非物理磁盘
            if is_special_fs(fstype):
                continue
            try:
                disk_status = statvfs(mount_point)
            except (OSError, IOError):
                continue

            # 处理磁盘数据
            fs_blocksize = disk_status.f_bsize
            if not fs_blocksize:
                fs_blocksize = disk_status.f_frsize

            free = disk_status.f_bfree * fs_blocksize
            total = disk_status.f_blocks * fs_blocksize
            avail = disk_status.f_bavail * fs_blocksize
            used = total - free

            # 忽略系统相关挂载点(大小为0)
            if not total:
                continue

            used_percent = round(used * 100.0 / total, 4)

            # 设置返回结果单位(默认为G)
            style_size = 1024.0 ** 3
            if style == 'M':
                style_size = 1024.0 ** 2
            elif style == 'T':
                style_size = 1024.0 ** 4

            # 磁盘状态 : 设备, 文件系统, 总大小, 已用大小, 使用率, 挂载点
            disk_stat.append(
                (device,
                 fstype,
                 round(total / style_size, 4),
                 round(used / style_size, 4),
                 used_percent,
                 mount_point)
            )

        return disk_stat

    def get_local_time(self):
        """获取系统时间 - 基于python解释器"""
        return strftime('%Y-%m-%d %H:%M:%S', localtime(time()))

    def get_extranet_ip(self):
        """获取本机外网ip"""
        url = "http://ip.42.pl/raw"
        try:
            return urllib2.urlopen(url, timeout=3).read()
        except Exception as err:
            return 'time out'

    def get_intranet_ip(self):
        """获取本机内网ip"""
        try:
            csock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            csock.connect(("8.8.8.8", 80))
            (addr, port) = csock.getsockname()
            csock.close()
        except Exception as err:
            return "failed"
        return addr

    # reference:https://github.com/giampaolo/psutil/blob/ffe8a9d280c397e8fd46eb1422c2838179cfb5d9/psutil/_pslinux.py#L1052
    @wrap_process_exceptions
    def disk_io_counters(self):
        """获取磁盘IO数据"""

        """Return disk I/O statistics for every disk installed on the
        system as a dict of raw tuples.
        """

        # determine partitions we want to look for
        def get_partitions():
            partitions = []
            with open("/proc/partitions") as f:
                lines = f.readlines()[2:]
            for line in reversed(lines):
                _, _, _, name = line.split()
                if name[-1].isdigit():
                    # we're dealing with a partition (e.g. 'sda1'); 'sda' will
                    # also be around but we want to omit it
                    partitions.append(name)
                else:
                    if not partitions or not partitions[-1].startswith(name):
                        # we're dealing with a disk entity for which no
                        # partitions have been defined (e.g. 'sda' but
                        # 'sda1' was not around), see:
                        # https://github.com/giampaolo/psutil/issues/338
                        partitions.append(name)
            return partitions

        def get_sector_size(partition):
            """Return the sector size of a partition.
            Used by disk_io_counters().
            """
            try:
                with open("/sys/block/%s/queue/hw_sector_size" % partition, "rt") as f:
                    return int(f.read())
            except (IOError, ValueError):
                # man iostat states that sectors are equivalent with blocks and
                # have a size of 512 bytes since 2.4 kernels.
                return SECTOR_SIZE_FALLBACK

        retdict = {}
        partitions = get_partitions()
        with open("/proc/diskstats") as f:
            lines = f.readlines()
        for line in lines:
            # OK, this is a bit confusing. The format of /proc/diskstats can
            # have 3 variations.
            # On Linux 2.4 each line has always 15 fields, e.g.:
            # "3     0   8 hda 8 8 8 8 8 8 8 8 8 8 8"
            # On Linux 2.6+ each line *usually* has 14 fields, and the disk
            # name is in another position, like this:
            # "3    0   hda 8 8 8 8 8 8 8 8 8 8 8"
            # ...unless (Linux 2.6) the line refers to a partition instead
            # of a disk, in which case the line has less fields (7):
            # "3    1   hda1 8 8 8 8"
            # See:
            # https://www.kernel.org/doc/Documentation/iostats.txt
            # https://www.kernel.org/doc/Documentation/ABI/testing/procfs-diskstats
            fields = line.split()
            fields_len = len(fields)
            if fields_len == 15:
                # Linux 2.4
                name = fields[3]
                reads = int(fields[2])
                (reads_merged, rbytes, rtime, writes, writes_merged,
                 wbytes, wtime, _, busy_time, _) = map(int, fields[4:14])
            elif fields_len == 14:
                # Linux 2.6+, line referring to a disk
                name = fields[2]
                (reads, reads_merged, rbytes, rtime, writes, writes_merged,
                 wbytes, wtime, _, busy_time, _) = map(int, fields[3:14])
            elif fields_len == 7:
                # Linux 2.6+, line referring to a partition
                name = fields[2]
                reads, rbytes, writes, wbytes = map(int, fields[3:])
                rtime = wtime = reads_merged = writes_merged = busy_time = 0
            else:
                raise ValueError("not sure how to interpret line %r" % line)

            if name in partitions:
                ssize = get_sector_size(name)
                rbytes *= ssize
                wbytes *= ssize
                retdict[name] = (reads, writes, rbytes, wbytes, rtime, wtime,
                                 reads_merged, writes_merged, busy_time)
        return retdict

    def get_disk_io(self):
        """计算磁盘io [读取字节数,写入字节数]"""
        rbytes, wbytes = 0, 0
        io_data = self.disk_io_counters()
        for name in io_data.keys():
            rbytes += io_data[name][2]
            wbytes += io_data[name][3]

        return rbytes, wbytes

    def calc_io_speed(self):
        """计算读写速度 [读取,写入(单位MB/s)]"""
        # todo : 这里的速度要比process所计算的和iotops所显示的慢一倍左右,但是和psutil显示一致
        # 未初始化
        if self.prev_disk_time == 0:
            self.prev_disk_rbytes, self.prev_disk_wbytes = self.get_disk_io()
            self.prev_disk_time = time()
            return 0., 0.
        # 计算io速度
        current_disk_rbytes, current_disk_wbytes = self.get_disk_io()
        current_disk_time = time()
        read_MBs = round((current_disk_rbytes - self.prev_disk_rbytes) / (1024. ** 2)
                         / (current_disk_time - self.prev_disk_time), 2)
        write_MBs = round((current_disk_wbytes - self.prev_disk_wbytes) / (1024. ** 2)
                          / (current_disk_time - self.prev_disk_time), 2)
        self.prev_disk_rbytes, self.prev_disk_wbytes = current_disk_rbytes, current_disk_wbytes
        self.prev_disk_time = current_disk_time
        return read_MBs, write_MBs
