Watch_Dogs - Client
===================
基于Linux远程主机及进程状态监测系统 - 远程监控客户端

todo : 完成api列表说明文档

以下均为 HTTP `GET` 方法访问
|地址|请求参数|返回内容|HTTP code|
|:--|:--|:--|:--:|
| /    | 无| 系统用户名称,本地时间,nethogs环境     |200|
| /sys/info    | 无|系统版本,内核版本      |200|
| /sys/loadavg    | 无|系统平均负载      |200|
| /sys/uptime     | 无|系统运行时间      |200|
| /sys/cpu/info    | 无|CPU型号信息(一颗一条记录)      |200|
| /sys/cpu/percent    | 无|CPU总占用率(百分比)     |200|
| /sys/cpu/percents    | 无 |CPU各个核心占用率(百分比)      |200|
| /sys/mem/info    | 无|内存总大小,空闲大小,可用大小(KB)      |200|
| /sys/mem/size    | 无|内存总大小(MB)      |200|
| /sys/mem/percent    | 无|内存占用率(百分比)      |200|
| /sys/net/devices    | 无|网卡设备列表      |200|
| /sys/net/default_device    | 无|默认网卡      |200|
| /sys/net/ip    | 无 | 内网,外网IP     |200|
| /sys/net/percent    | 无 | 上传速度,下载速度(Kbps)     |200|
| /sys/disk/stat     | 无 |系统各个挂载点数据      |200|
| /proc/search/\<string:key_word\>    |[可选]type(查询类型):contain(包含),match(完全匹配)     |查询到的进程号,名称构成的列表      |200      |
| /proc/kill/\<int:pid\>    |无     | 无     |200|
| /proc/start/\<string:execute_file_full_path\>   |无     | 启动之后的进程号     |200 |
| /log/exist     |path(日志文件地址)     | 日志文件是否存在(true,false)     | 200  |
| /log/head    |path(日志文件地址),[可选]n(行数)    | 日志文件前n行构成的列表     | 200     |
| /log/tail    | path(日志文件地址),[可选]n(行数)      | 日志文件后n行构成的列表       |200      |
| /log/last_update_time    |path(日志文件地址)      | 日志文件上次更新时间      |   200   |
| /log/keyword_lines    |path(日志文件地址) ,key_word(关键词)     | 日志文件含有关键词额数行构成的列表(行号,内容) |  200    |
| /proc/\<int:pid\>/    |无     | 进程数据总览     | 200     |
| /proc/all_pid/    |  无   | 正在运行的所有进程号     |    200  |
| /proc/all_pid_name/    |  无   |  正在运行的所有进程号,进程名    | 200    |
| /proc/watch/all    |   无  | 正在监控的所有进程号     |   200   |
| /proc/watch/is/\<int:pid\>    |  无   | 是否在监控此进程(true,false)     |  200    |
| /proc/watch/add/\<int:pid\>    |   无  | 无     | 200     |
| /proc/watch/remove/<\int:pid\>    |  无   | 无     | 200     |
| /proc/\<int:pid\>/info    | 无    | 进程信息     | 200     |
| /proc/\<int:pid\>/cpu    | 无    | 进程CPU占用率(百分比)     | 200     |
| /proc/\<int:pid\>/io    |  无   | 进程IO占用\[读取,写入\]\(MB/s\)     | 200     |
| /proc/\<int:pid\>/net    | 无    |进程上传,下载速度(Kbps)      |200      |
| /proc/\<int:pid\>/mem    |  无   | 进程内存占用(M)     | 200     |
| /path/size/total    | path(文件夹地址)    | 此路径总大小(M)     |  200    |
| /path/size/avail    | path(文件夹地址)    | 此路径剩余可用大小(G)     |200      |
| NOT FOUND    | 无    | 页面不存在     | 404     |
| Untrusted Address    | 无    | 未认证的请求来源地址      | 403     |
