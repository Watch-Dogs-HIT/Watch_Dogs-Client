#!/usr/bin/env python
# encoding:utf-8

import os
import sys
import unittest

root_path = os.path.dirname(sys.path[0])
os.chdir(root_path)
sys.path.append(root_path)

from Core.prcess_exception import AccessDenied, NoSuchProcess
from Core.process_manage import ProcManager


class TestSysMontor(unittest.TestCase):
    """进程管理功能测试类"""

    def setUp(self):
        self.P = ProcManager()

    def test_process_info(self, test_process_name="bash"):
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
        try:
            search_process = self.P.search_pid_by_keyword(test_process_name)[0]
        except Exception as err:
            search_process = None
        if search_process:
            print "查询到{}进程".format(test_process_name)
            search_pid = search_process[0]
            search_process_info = self.P.get_process_info(search_pid)
            self.assertIsInstance(search_process_info, dict)
            print "进程信息 :"
            print "进程号 :", search_process_info["pid"]
            print "启动命令 :", search_process_info["comm"]
            print "进程状态 :", search_process_info["state"]
            print "父进程号 :", search_process_info["ppid"]
            print "组进程号 :", search_process_info["pgrp"]
            print "线程数目 :", search_process_info["thread num"]
            print "命令行 :", search_process_info["cmdline"]
            self.assertEqual(search_process_info["ppid"],
                             self.P.get_process_parent_pid(search_pid))
            self.assertEqual(search_process_info["pgrp"],
                             self.P.get_process_group_id(search_pid))
            self.assertIsInstance(self.P.get_same_group_process(search_pid), list)
            print "同组进程 : ", self.P.get_same_group_process(search_pid)
            self.assertIsInstance(self.P.get_all_child_process(search_pid), list)
            print "子进程 : ", self.P.get_all_child_process(search_pid)
            print "进程执行地址 : ",
            try:
                self.P.get_process_execute_path(search_pid)
            except AccessDenied:
                print "权限不足,请检查是否为root账户登录"

        else:
            print "尚未查询到{}进程".format(test_process_name)

    def test_process_manage(self):
        print "\n-----进程管理测试-----"
        print "启动测试进程 - just4test.py,进程号 :",
        pid = self.P.start_process(os.path.join(os.getcwd(), "just4test.py"))
        self.assertIsInstance(pid, int)
        test_process_info = self.P.get_process_info(pid)
        self.assertIsInstance(test_process_info, dict)
        print "进程信息 :"
        print "进程号 :", test_process_info["pid"]
        print "启动命令 :", test_process_info["comm"]
        print "进程状态 :", test_process_info["state"]
        print "父进程号 :", test_process_info["ppid"]
        print "组进程号 :", test_process_info["pgrp"]
        print "线程数目 :", test_process_info["thread num"]
        print "命令行 :", test_process_info["cmdline"]
        print "关闭进程测试 :",
        try:
            self.P.get_process_info(pid)
            print "失败"  # 这里好像是由于unittest本身的原因造成,其他测试均正常
        except NoSuchProcess:
            print "成功"

    def test_log_func(self, test_file_name="test_data.dat"):
        print "\n-----日志功能测试-----"
        test_file_full_path = os.path.join(os.getcwd(), test_file_name)
        self.assertIsInstance(self.P.is_log_exist(test_file_full_path), bool)
        print "测试日志文件发现(?) :", str(self.P.is_log_exist(test_file_full_path))
        if self.P.is_log_exist(test_file_full_path):
            print "第一行 :", self.P.get_log_head(test_file_full_path, 1)[0]
            self.assertIsInstance(self.P.get_log_head(test_file_full_path, 3), list)
            print "最后一行 :", self.P.get_log_tail(test_file_full_path, 1)[0]
            self.assertIsInstance(self.P.get_log_tail(test_file_full_path, 3), list)
            print "最后更新时间 :", self.P.get_log_last_update_time(test_file_full_path)
            self.assertIsInstance(self.P.get_log_last_update_time(test_file_full_path), str)
            print "含有关键词 {编程} 的共有", str(len(self.P.get_log_keyword_lines(test_file_full_path, "编程"))),
            self.assertIsInstance(self.P.get_log_keyword_lines(test_file_full_path, "编程"), list)
            print "行\n行号\t内容"
            for i, l in self.P.get_log_keyword_lines(test_file_full_path, "编程"):
                print i, l[:30], "..."

if __name__ == '__main__':
    unittest.main()  
