#!/usr/bin/env python
# encoding:utf8

from flask import Flask
import time
from concurrent.futures import ThreadPoolExecutor

executor = ThreadPoolExecutor(1)

app = Flask(__name__)


@app.route('/test2')
def test2():
    print "test2"
    return 'ok'


@app.route('/test1')
def update_redis():
    executor.submit(do_update)
    return 'ok'


def do_update():
    time.sleep(10)
    print('start update')


if __name__ == '__main__':
    app.run(host='0.0.0.0',
            port=8003, )
