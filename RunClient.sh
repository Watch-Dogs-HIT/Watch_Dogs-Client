#!/bin/sh
# 启动进程
start_time=`date +%s`
if test $( ps ax | grep Watch_Dogs-Client.py | grep -v grep | wc -l ) -eq 1;
then
    echo `date "+%Y-%m-%d %H:%M:%S"` "监控客户端已经存在"
else
    nohup python -u Watch_Dogs-Client.py &
    echo `date "+%Y-%m-%d %H:%M:%S"` "监控客户端启动完成"
fi

# 远程客户端检测脚本, 若检测进程挂掉则自动拉起
while true
do
    if test $( ps ax | grep Watch_Dogs-Client.py | grep -v grep | wc -l ) -eq 1;
    then
        sleep 10
    else
        now_time=`date +%s`
        if test $(( now_time -  start_time )) -gt 60
        then
            nohup python -u Watch_Dogs-Client.py &
            start_time=`date +%s`
            echo `date "+%Y-%m-%d %H:%M:%S"` "监控客户端重新启动完成"
        else
            echo `date "+%Y-%m-%d %H:%M:%S"` "两次监控客户端重启间隔过短！系统自动退出"
            break
        fi
    fi
done