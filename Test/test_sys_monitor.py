#!/usr/bin/env python
# encoding:utf-8

import unittest

from Core.sys_monitor import SysMonitor


class TestSysMontor(unittest.TestCase):
    """系统监控功能测试类"""

    def setUp(self):
        self.S = SysMonitor()

    def test_sys_info(self):
        """测试系统监控"""
        print "\n-----系统信息测试-----"
        self.assertIsInstance(self.S.get_sys_info(), dict)
        print "Linux内核版本 :", self.S.get_sys_info()["kernel"]
        print "系统版本 :", self.S.get_sys_info()["system"]
        self.assertIsInstance(self.S.get_sys_uptime(), dict)
        print "系统运行时间 :", self.S.get_sys_uptime()["system_uptime"]
        print "系统空闲时间 :", self.S.get_sys_uptime()["idle_time"]
        print "系统空闲比例 :", self.S.get_sys_uptime()["free rate"]
        self.assertIsInstance(self.S.get_sys_loadavg(), dict)
        print "1分钟负载 :", self.S.get_sys_loadavg()["lavg_1"]
        print "5分钟负载 :", self.S.get_sys_loadavg()["lavg_5"]
        print "15分钟负载 :", self.S.get_sys_loadavg()["lavg_15"]
        print "最近运行进程号 :", self.S.get_sys_loadavg()["last_pid"]
        print "运行进程数/总进程数 :", self.S.get_sys_loadavg()["nr"]
        self.assertIsInstance(self.S.get_local_time(), str)
        print "系统本地时间 :", self.S.get_local_time()

    def test_cpu_monitor(self):
        print "\n-----处理器信息-----"
        self.assertIsInstance(self.S.get_cpu_info(), list)
        print "CPU信息"
        for c in self.S.get_cpu_info():
            print c
        cp = self.S.calc_cpu_percent()
        self.assertIsInstance(cp, float)
        print "系统CPU占用率 :", str(cp), "%"
        cpbc = self.S.calc_cpu_percent_by_cores()
        self.assertIsInstance(cpbc, dict)
        print "系统CPU占用率(分核计算)"
        for k in cpbc.keys():
            print k, ":", cpbc[k], "%"

    def test_mem_montor(self):
        print "\n-----内存信息-----"
        self.assertIsInstance(self.S.get_mem_info(), list)
        print "系统总内存(KB) :", self.S.get_mem_info()[0]
        print "空闲内存(KB) :", self.S.get_mem_info()[1]
        print "可利用内存(KB) :", self.S.get_mem_info()[2]
        self.assertIsInstance(self.S.get_sys_total_mem(), float)
        print "系统总内存(G) :", self.S.get_sys_total_mem(style="G")
        self.assertIsInstance(self.S.calc_mem_percent(), float)
        print "系统内存占用率 :", self.S.calc_mem_percent(), "%"

    def test_net_montor(self):
        print "\n-----网络信息-----"
        self.assertIsInstance(self.S.get_all_net_device(), list)
        print "系统网卡 :", " ".join(self.S.get_all_net_device())
        self.assertIsInstance(self.S.get_default_net_device(), str)
        print "系统默认网卡 :", self.S.get_default_net_device()
        cns = self.S.calc_net_speed()
        self.assertIsInstance(cns, tuple)
        print "系统网络上传速度(Kbps)", str(cns[0])
        print "系统网络下载速度(Kbps)", str(cns[1])
        self.assertIsInstance(self.S.get_extranet_ip(), str)
        print "本机外网IP :", self.S.get_extranet_ip()
        self.assertIsInstance(self.S.get_intranet_ip(), str)
        print "本地内网IP :", self.S.get_intranet_ip()

    def test_dist_montor(self):
        print "\n-----磁盘信息-----"
        ds = self.S.get_disk_stat(style="G")
        self.assertIsInstance(ds, list)
        for i in ds:
            print "设备 :", i[0]
            print "文件系统 :", i[1]
            print "磁盘大小(G) :", i[2]
            print "已用大小(G) :", i[3]
            print "磁盘占用率 :", i[4], "%"
            print "挂载点 :", i[5]
