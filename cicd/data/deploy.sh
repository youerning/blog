#!/bin/bash

# 部署公共文件
ansible servers -m copy -a "src=/data/share/ dest=/data/share/"

# 备份上一个版本业务代码
ansible servers -m shell -a "/bin/bash /data/share/backup.sh"

# 部署业务代码
ansible server1 -m copy -a "src=/data/server1/ dest=/data/code"
ansible server2 -m copy -a "src=/data/server2/ dest=/data/code"
ansible server3 -m copy -a "src=/data/server3/ dest=/data/code"


# 配置nginx
ansible servers -m shell -a "cp /data/code/web.exmaple.com.conf /etc/nginx/conf.d/web.exmaple.com.conf"

# 重新启动业务代码
ansible servers -m service -a "name=webapp state=restarted"
ansible servers -m service -a "name=nginx state=restarted enabled=yes"

