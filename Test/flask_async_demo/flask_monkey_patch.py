#!/usr/bin/env python
# encoding:utf8

# Flask
from flask import Flask, request, g
import time
# gevent
from gevent import monkey
from gevent.pywsgi import WSGIServer

monkey.patch_all()
# gevent end

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
    http_server = WSGIServer(('0.0.0.0', 8002), app)
    http_server.serve_forever()
