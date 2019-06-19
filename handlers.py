#!/usr/bin/env python
# encoding:utf-8

"""
Watch_Dogs
base handler
"""

import os
import json
import traceback

import tornado.web
from tornado import gen


def byteify(input_unicode_dict, encoding='utf-8'):
    """
    将unicode字典转为str字典
    reference : https://www.jianshu.com/p/90ecc5987a18
    """
    if isinstance(input_unicode_dict, dict):
        return {byteify(key): byteify(value) for key, value in input_unicode_dict.iteritems()}
    elif isinstance(input_unicode_dict, list):
        return [byteify(element) for element in input_unicode_dict]
    elif isinstance(input_unicode_dict, unicode):
        return input_unicode_dict.encode(encoding)
    else:
        return input_unicode_dict


class BaseHandler(tornado.web.RequestHandler):
    """"""

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header("Access-Control-Allow-Methods", "GET")
        self.set_header("Access-Control-Allow-Credentials", True)

    def get(self):
        """get"""
        self.check_require_address()
        self.return_result()

    def check_require_address(self):
        """检查请求地址"""
        if "0.0.0.0" in self.allowed_request_addr_list or self.request.remote_ip in self.allowed_request_addr_list:
            try:
                self.return_result()
            except Exception as err:
                self.finish({"error": str(err)})
        else:
            self.finish({"error": "ip address not allowed"})

    def return_result(self):
        """返回响应结果"""

    @property
    def log(self):
        """日志对象"""
        return self.application.log

    @property
    def setting(self):
        """静态设置"""
        return self.application.setting

    @property
    def allowed_request_addr_list(self):
        """静态设置"""
        return self.application.allowed_request_addr_list

    def write_error(self, status_code, **kwargs):
        """500"""
        error_message = ["Oops! Something wrong,"]

        if self.settings.get("serve_traceback") and "exc_info" in kwargs:
            error_message = traceback.format_exception(*kwargs["exc_info"])

        return self.render(
            'error.html',
            http_code=500,
            error_message=error_message
        )


class TestHandler(BaseHandler):
    """/test"""

    def return_result(self):
        """返回响应结果"""
        return self.finish({"hello, world": self.setting.get_local_time(), "version": "beta ver"})


class NotFoundHandler(BaseHandler):
    """404"""

    def get(self):
        return self.render("404.html", status_code=404)
