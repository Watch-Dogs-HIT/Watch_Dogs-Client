#!/usr/bin/env python
# encoding:utf-8

"""
进程检测异常

异常类型
- 无此进程
- Zombie进程
- 无读取权限
- 读取超时

灵感及思路参考 psutil
reference   :   https://github.com/giampaolo/psutil/blob/master/psutil/_exceptions.py
"""

import errno

from functools import wraps


# Note eerno : Standard errno system symbols
# 一个标准的系统错误系统符号,类似于 linux/include/errno.h
# reference : https://docs.python.org/2/library/errno.html
# reference : https://www.cnblogs.com/Security-Darren/p/4168392.html
# reference : https://www.cnblogs.com/xuchunlin/p/7763728.html


class ProcessException(Exception):
    """
    进程监测异常类
    """

    def __init__(self, msg=""):
        Exception.__init__(self, msg)
        self.msg = msg


# todo : 有时间要弄清楚python oop的相关内容,感觉这里异常类写的有点问题.

class NoSuchProcess(ProcessException):
    """
    进程不存在
    """

    def __init__(self, pid, msg=None):
        # 获取信息
        self.pid = pid
        self.msg = msg
        details = ""
        if not msg:
            if self.pid:
                details = " (pid={})".format(self.pid)
            self.msg = "process no longer exists" + details
        # 构造异常
        ProcessException.__init__(self, self.msg)


class ZombieProcess(ProcessException):
    """
    僵尸进程

    Exception raised when querying a zombie process. This is
    raised on macOS, BSD and Solaris only, and not always: depending
    on the query the OS may be able to succeed anyway.
    On Linux all zombie processes are querable (hence this is never
    raised). Windows doesn't have zombie processes.
    """

    def __init__(self, pid, msg=None):
        # 获取信息
        self.pid = pid
        self.msg = msg
        details = ""
        if not msg:
            if self.pid:
                details = " (pid={})".format(self.pid)
            self.msg = "process still exists but it's a zombie" + details
        # 构造异常
        ProcessException.__init__(self, self.msg)


class AccessDenied(ProcessException):
    """拒绝访问"""

    def __init__(self, pid=None, msg=None):
        # 获取信息
        self.pid = pid
        self.msg = msg
        details = ""
        if not msg:
            if self.pid:
                details = " (pid={})".format(self.pid)
            self.msg = "Access Denied" + details
        # 构造异常
        ProcessException.__init__(self, self.msg)


def wrap_process_exceptions(func):
    """装饰器 - 进程信息获取异常"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except EnvironmentError as err:
            # 2019.2.15 : 为了配合将函数归类的需求,这里的参数默认改为函数的第二个参数,第一个是self
            # EPERM(Operation not permitted), EACCES(Permission denied)
            if err.errno in (errno.EPERM, errno.EACCES):
                raise AccessDenied(args[1]) if args else AccessDenied()
            # ESRCH (no such process), ENOENT (no such file or directory)
            if err.errno in (errno.ESRCH, errno.ENOENT, errno.ENOTDIR):
                raise NoSuchProcess(args[1]) if args else NoSuchProcess(pid=-1)
            # Note: zombies will keep existing under /proc until they're
            # gone so there's no way to distinguish them in here.
            raise

    return wrapper
