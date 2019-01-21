#!/usr/bin/env python
# encoding:utf8

import os
import json
import datetime
import logging.config


class Setting(object):
    """静态配置"""

    # Singleton
    _instance = None
    _init_done = False

    def __new__(cls, *args, **kw):
        """单例模式"""
        if not cls._instance:
            cls._instance = super(Setting, cls).__new__(cls, *args, **kw)
        return cls._instance

    def __init__(self):
        pass

    @staticmethod
    def get_local_time():
        """获取本地时间"""
        return str(datetime.datetime.now()).split('.')[0]

    @staticmethod
    def get_local_date():
        """获取本地日期"""
        return str(datetime.datetime.now()).split(" ")[0]
