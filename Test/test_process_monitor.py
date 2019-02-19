#!/usr/bin/env python
# encoding:utf-8

import unittest

from Core.process_monitor import ProcMontor
from Core.process_manage import ProcManage


class TestSysMontor(unittest.TestCase):
    """系统监控功能测试类"""

    def setUp(self):
        self.P = ProcMontor()
        self.PM = ProcManage()
        self.pid_of_mysql = 0
        if self.PM.search_pid_by_keyword("mysql")[0]:
            self.pid_of_mysql = self.PM.search_pid_by_keyword("mysql")[0][0]

    def test_process_info(self):
        """进程信息测试"""
        print "进程信息测试",

    def test_process_cpu(self):
        """进程CPU占用率测试"""
        print "进程CPU占用率测试",

    def test_process_io(self):
        """进程IO速度测试"""
        print "进程IO速度测试",

    def test_process_mem(self):
        """进程内存占用测试"""
        print "进程内存占用测试",

    def test_process_path(self):
        """进程相关路径大小测试"""
        print "进程相关路径大小测试",

    def test_process_net(self):
        """进程网络速度测试"""
        print "进程网络速度测试",
