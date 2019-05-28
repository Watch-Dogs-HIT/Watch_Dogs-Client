#!/bin/sh
# 远程客户端检测脚本, 若检测进程挂掉则自动拉起
while true
do
    if test $( ps ax | grep Watch_Dogs-Client.py | grep -v grep | wc -l ) -eq 1;
    then
        sleep 1m
    else
        nohup python -u Watch_Dogs-Client.py &
        echo `date "+%Y-%m-%d %H:%M:%S"` "监控客户端重新启动完成"
    fi
done