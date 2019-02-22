#!/usr/bin/env python
# encoding:utf8

"""
flask异步请求实验

- 基于多线程方式

在启用threaded选项之后,对于每一个来到的请求,flask都会新开一个线程进行处理

reference : https://www.cnblogs.com/jamespei/p/7158107.html
reference : https://www.jianshu.com/p/6f19f4fe6e19
"""

from flask import Flask, request, g
import os
import time

app = Flask(__name__)
app.config.update(DEBUG=True)


@app.route('/test1')
def the_test1():
    print "test1 print start"
    time.sleep(10)
    print "test1 print after sleep"
    return 'hello asyn'


@app.route('/test2')
def the_test2():
    print "test2 print!"
    return 'test2 return'


if __name__ == '__main__':
    app.run(host='0.0.0.0',
            port=8001,
            debug=False,
            threaded=True)

    # threaded开启以后 不需要等队列 threaded=True



    # app.run(host=myaddr,port=myport,debug=False,processes=3) ### processes=N 进程数量，默认为1个

"""
def run_simple()
...
    :param threaded: should the process handle each request in a separate
                     thread?
    :param processes: if greater than 1 then handle each request in a new process
                      up to this maximum number of concurrent processes.

原来是ThreadingMixIn的实例以多线程的方式去处理每一个请求，
这样对开发者来说，只有在启动app时将threaded参数设定为True,flask才会真正以多线程的方式去处理每一个请求。
实际去测试一下，发现将threaded设置没True后，果然每一个请求都会开启一个单独的线程去处理。

原来一个flask应用的server并非只有一种类型，它是可以设定的，默认情况下创建的是一个 BaseWSGIServer，
如果指定了threaded参数就启动一个ThreadedWSGIServer，
如果设定的processes>1则启动一个ForkingWSGIServer。
"""