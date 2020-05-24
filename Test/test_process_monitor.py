#!/usr/bin/env python
# encoding:utf-8

import os
import sys
import unittest
from time import sleep

root_path = os.path.dirname(sys.path[0])
os.chdir(root_path)
sys.path.append(root_path)

from Core.process_monitor import ProcMonitor
from Core.process_manage import ProcManager


class TestSysMontor(unittest.TestCase):
    """系统监控功能测试类"""

    def setUp(self, test_process='self'):
        self.P = ProcMonitor()
        self.PM = ProcManager()
        self.test_process_name = test_process
        self.pid = os.getpid()
        self.P.watch_process(self.pid)
        # init
        self.assertEqual(self.P.calc_process_cpu_percent(self.pid), 0)
        self.assertEqual(self.P.calc_process_io_speed(self.pid), (0., 0.))

    def test_process_info(self):
        """进程信息测试"""
        print "进程信息测试",
        if self.pid:
            self.assertEqual(self.P.is_process_watched(self.pid), True)
            test_process_info = self.P.get_process_info(self.pid)
            self.assertIsInstance(test_process_info, dict)
            print "进程信息 :"
            print "进程号 :", test_process_info["pid"]
            print "启动命令 :", test_process_info["comm"]
            print "进程状态 :", test_process_info["state"]
            print "父进程号 :", test_process_info["ppid"]
            print "组进程号 :", test_process_info["pgrp"]
            print "线程数目 :", test_process_info["thread num"]
            print "命令行 :", test_process_info["cmdline"]
        else:
            print "未获取到{}进程".format(self.test_process_name)

    def test_process_cpu(self):
        """进程CPU占用率测试"""
        print "进程CPU占用率测试",
        if self.pid:
            sleep(3)
            c = self.P.calc_process_cpu_percent(self.pid)
            self.assertIsInstance(c, float)
            print c,
            print "%"
        else:
            print "未获取到{}进程".format(self.test_process_name)

    def test_process_io(self):
        """进程IO速度测试"""
        print "进程IO速度测试",
        if self.pid:
            sleep(3)
            r, w = self.P.calc_process_io_speed(self.pid)
            self.assertIsInstance(r, float)
            self.assertIsInstance(w, float)
            print "read :",
            print r,
            print "kbps"
            print "write :",
            print w,
            print "kbps"
        else:
            print "未获取到{}进程".format(self.test_process_name)

    def test_process_mem(self):
        """进程内存占用测试"""
        print "进程内存占用测试",
        if self.pid:
            m = self.P.get_process_mem(self.pid)
            self.assertIsInstance(m, float)
            print "use memory :",
            print m,
            print "MB"
        else:
            print "未获取到{}进程".format(self.test_process_name)

    def test_process_path(self):
        """进程相关路径大小测试"""
        print "进程相关路径大小测试",
        test_path = "/tmp"
        ts = self.P.get_path_total_size(test_path)
        a = self.P.get_path_avail_size(test_path)
        self.assertIsInstance(ts, float)
        self.assertIsInstance(a, float)
        print "测试地址", test_path
        print "总占用大小", ts, "M"
        print "剩余可用大小", a, "G"

    def test_process_net(self):
        """进程网络速度测试"""
        print "进程网络速度测试",
        if self.pid:
            sleep(5)
            self.assertIsInstance(self.P.get_process_net_info(self.pid), dict)
            u, d = self.P.calc_process_net_speed(self.pid)
            self.assertIsInstance(u, float)
            self.assertIsInstance(d, float)
            print "上传速度", u, "KB/s"
            print "下载速度", d, "KB/s"

        else:
            print "未获取到{}进程".format(self.test_process_name)

    def teardown_class(self):
        print "clear..."
        os.kill(os.getpid(), 9)

# todo : 仍有一些问题(跟单元测试有关)

if __name__ == '__main__':
    unittest.main()  
