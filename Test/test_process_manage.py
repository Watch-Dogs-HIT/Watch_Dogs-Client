#!/usr/bin/env python
# encoding:utf-8

import unittest

from Core.process_manage import ProcManage


class TestSysMontor(unittest.TestCase):
    """进程管理功能测试类"""

    def setUp(self):
        self.P = ProcManage()

    def test_process_info(self, test_process_name="mysql"):
        print "\n-----进程检索测试-----"
        self.assertIsInstance(self.P.get_all_pid(), list)
        print "系统进程个数 :", str(len(self.P.get_all_pid()))
        pn = self.P.get_all_pid_name()
        self.assertIsInstance(pn, dict)
        print "系统进程详细信息(前十个进程)"
        print "进程号|\t进程名"
        for i in pn.keys()[:10]:
            print str(i) + "\t" + str(pn[i])
        self.assertIsInstance(self.P.search_pid_by_keyword(test_process_name), list)
        print "含有{}关键词的进程".format(test_process_name)
        print "进程号 进程名"
        for pid, name in self.P.search_pid_by_keyword(test_process_name):
            print pid, name
        mysql_process = self.P.search_pid_by_keyword(test_process_name)[0]
        if mysql_process:
            print "查询到{}进程".format(test_process_name)
            mysql_pid = mysql_process[0]
            mysql_process_info = self.P.get_process_info(mysql_pid)
            self.assertIsInstance(mysql_process_info, dict)
            print "进程信息 :"
            print "进程号 :", mysql_process_info["pid"]
            print "启动命令 :", mysql_process_info["comm"]
            print "进程状态 :", mysql_process_info["state"]
            print "父进程号 :", mysql_process_info["ppid"]
            print "组进程号 :", mysql_process_info["pgrp"]
            print "线程数目 :", mysql_process_info["thread num"]
            print "命令行 :", mysql_process_info["cmdline"]
            self.assertEqual(mysql_process_info["ppid"],
                             self.P.get_process_parent_pid(mysql_pid))
            self.assertEqual(mysql_process_info["pgrp"],
                             self.P.get_process_group_id(mysql_pid))
            self.assertIsInstance(self.P.get_same_group_process(mysql_pid), list)
            print "同组进程 : ", self.P.get_same_group_process(mysql_pid)
            self.assertIsInstance(self.P.get_all_child_process(mysql_pid), list)
            print "子进程 : ", self.P.get_all_child_process(mysql_pid)
            self.assertIsInstance(self.P.get_process_execute_path(mysql_pid), str)
            print "进程执行地址 : ",self.P.get_process_execute_path(mysql_pid)
            # todo 解决权限问题!
        else:
            print "尚未查询到{}进程".format(test_process_name)

    def test_process_manage(self):
        print "\n-----进程管理测试-----"

    def test_log_func(self):
        print "\n-----日志功能测试-----"
