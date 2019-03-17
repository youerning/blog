#!/bin/bash

# 软件初始化
# pip nginx
ansible servers -m yum -a "name=nginx"
ansible servers -m yum -a "name=python-pip"

# 业务代码库依赖
ansible servers -m pip -a "name=flask"

# 服务状态依赖
# ansible servers -m service -a "name=nginx state=started enabled=yes"

# 部署启动脚本
ansible servers -m copy -a "src=/data/share/webapp dest=/etc/init.d/webapp"
ansible servers -m shell -a "chmod +x /etc/init.d/webapp"

