#!/usr/bin/env python
# encoding:utf-8

"""
进程监测核心功能实现 - 进程管理

主要包括
- 获取所有进程名
- 按进程名称搜索进程
- 关闭进程
- 关闭进程(连同相关进程)
- 获取同组进程
- 获取所有子进程
- 获取进程执行文件地址
- 后台创建一个新的进程(不随主进程退出,返回创建的进程号)
- 重启进程
- 判断日志文件是否存在
- 获取日志文件前n行
- 获取日志文件最后n行
- 获取日志文件最后更新时间
- 获取日志文件含有关键词的行

详细的代码与文档
code & doc  :   https://github.com/h-j-13/Watch_Dogs/blob/master/Watch_Dogs/Core/process_manage.py
"""

import os
import signal
import subprocess
from time import localtime, strftime

from prcess_exception import wrap_process_exceptions, NoSuchProcess, ZombieProcess, AccessDenied


class ProcManage(object):
    """进程管理类"""

    _instance = None

    def __new__(cls, *args, **kw):
        """单例模式"""

        if not cls._instance:
            cls._instance = super(ProcManage, cls).__new__(cls, *args, **kw)
        return cls._instance

    def __init__(self):
        pass

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

    def get_all_pid_name(self, name_type="cmdline"):
        """获取所有进程名"""
        res = {}
        # 按照命令ps -ef的逻辑,以 cmdline 作为进程名称,当然也可以选择 comm 作为备选
        for pid in self.get_all_pid():
            process_info = self.get_process_info(pid)
            process_name = process_info[name_type] if \
                self.get_process_info(pid)[name_type].strip() else process_info['comm']
            res[pid] = process_name

        return res

    def search_pid_by_keyword(self, keyword, search_type='contain'):
        """按进程名搜索进程号 (搜索类型 contain-包含关键词,match-完全匹配)"""
        res = []
        for pid, process_name in self.get_all_pid_name().items():
            if search_type == 'contain':
                if keyword in process_name:
                    res.append((pid, process_name))
            elif search_type == 'match':
                if keyword == process_name:
                    res.append((pid, process_name))

        return res

    def kill_process(self, pid):
        """关闭进程"""
        try:
            if self.get_process_info(pid)['state'] == 'Z':  # zombie process
                raise ZombieProcess(pid)
            os.kill(int(pid), signal.SIGKILL)
        except OSError as e:
            if e.args[0] == 1:  # Operation not permitted
                raise AccessDenied(pid)
            if e.args[0] == 3:  # No such process
                raise NoSuchProcess(pid)

    def kill_all_process(self, pid, kill_child=True, kill_process_gourp=True):
        """关闭进程 (pid所指进程, 该进程的子进程, 该进程的同组进程)"""
        # 获取需要关闭的进程
        self_pid = os.getpid()
        need_killed_process = [pid]
        if kill_child:
            need_killed_process.extend(self.get_all_child_process(pid))
        if kill_process_gourp and self.get_process_group_id(pid) != self.get_process_group_id(self_pid):
            need_killed_process.extend(self.get_same_group_process(self.get_process_group_id(pid)))
        need_killed_process = sorted(list(set(need_killed_process)), reverse=True)
        # 去掉监控进程本身 (因为启动进程会将启动的进程变成监控进程的子进程,这地方逻辑不是很清晰 todo:更好的进程关闭方式? )
        if self_pid in need_killed_process:
            need_killed_process.remove(self_pid)
        # 逐一关闭
        try:
            for p in need_killed_process:
                self.kill_process(p)
        except NoSuchProcess as e:
            pass

        return True

    def get_process_parent_pid(self, pid):
        """获取进程父进程id - ppid"""
        return self.get_process_info(pid)['ppid']

    def get_process_group_id(self, pid):
        """获取进程组id - pgrp"""
        return self.get_process_info(pid)['pgrp']

    def get_same_group_process(self, pid):
        """获取同组进程"""
        result = []
        pgrp = self.get_process_group_id(pid)

        for p in self.get_all_pid():
            if pgrp == self.get_process_group_id(p):
                result.append(p)
        # 一般最小的pid为组id和整个进程的父pid
        return sorted(result, reverse=False)

    def get_all_child_process(self, pid):
        """获取所有子进程"""
        result = []

        for p in self.get_all_pid():
            if pid == self.get_process_parent_pid(p):
                result.append(p)

        return sorted(result, reverse=False)

    @wrap_process_exceptions
    def get_process_execute_path(self, pid):
        """获取进程执行文件地址 - /proc/[pid]/cwd"""

        cwd_path = "/proc/{}/cwd".format(pid)
        return os.readlink(cwd_path)

    def start_process(self, execute_file_full_path):
        """后台创建一个新的进程(不随主进程退出,返回创建的进程号)"""
        # reference : https://stackoverflow.com/questions/1605520/how-to-launch-and-run-external-script-in-background
        # reference : https://www.cnblogs.com/zhoug2020/p/5079407.html
        # reference : https://stackoverflow.com/questions/89228/calling-an-external-command-in-python/92395#92395
        # reference : https://stackoverflow.com/questions/1196074/how-to-start-a-background-process-in-python

        # 获取执行文件相关地址
        cwd = execute_file_full_path[:execute_file_full_path.rindex("/")]
        execute_file = execute_file_full_path[execute_file_full_path.rindex("/") + 1:]
        # 启动进程
        if execute_file.endswith('.py'):  # python
            p = subprocess.Popen(["nohup", "python", execute_file_full_path],
                                 cwd=cwd,
                                 close_fds=True,
                                 stderr=subprocess.STDOUT)
            return p.pid
        # todo : support more execute file
        else:
            return False

    def restart_process(self, pid, execute_file_full_path):
        """重启进程"""
        # 关闭
        self.kill_all_process(pid)
        # 启动
        return self.start_process(execute_file_full_path)

    def is_log_exist(self, path):
        """判断日志文件是否存在 (输入绝对路径)"""
        return os.path.exists(path) and os.path.isfile(path) and os.access(path, os.R_OK)

    @wrap_process_exceptions
    def get_log_head(self, path, n=100):
        """获取文件前n行"""
        res = []
        line_count = 0

        with open(path, "r") as log_f:
            for line in log_f:
                res.append(line)
                line_count += 1
                if line_count >= n:
                    return res

        return res

    @wrap_process_exceptions
    def get_log_tail(self, path, n=10):
        """获取日志文件最后n行"""

        # author    : Armin Ronacher
        # reference : https://stackoverflow.com/questions/136168/get-last-n-lines-of-a-file-with-python-similar-to-tail
        def tail(f, n, offset=0):
            """Reads a n lines from f with an offset of offset lines."""
            avg_line_length = 74
            to_read = n + offset
            while 1:
                try:
                    f.seek(-(avg_line_length * to_read), 2)
                except IOError:
                    # woops.  apparently file is smaller than what we want
                    # to step back, go to the beginning instead
                    f.seek(0)
                pos = f.tell()
                lines = f.read().splitlines()
                if len(lines) >= to_read or pos == 0:
                    return lines[-to_read:offset and -offset or None]
                avg_line_length *= 1.3

        with open(path, "r") as log_f:
            return tail(log_f, n)

    @wrap_process_exceptions
    def get_log_last_update_time(self, path):
        """获取文件最后更新时间"""
        return strftime("%Y-%m-%d %H:%M:%S", localtime(os.stat(path).st_atime))

    @wrap_process_exceptions
    def get_log_keyword_lines(self, path, keyword):
        """获取日志文件含有关键词的行"""
        result = []
        n = 1
        with open(path, "r") as log_f:
            for line in log_f:
                if keyword in line:
                    result.append((n, line.strip()))
                n += 1

        return result

