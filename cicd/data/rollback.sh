#!/bin/bash

# 执行回撤脚本
ansible servers -m shell -a "/bin/bash /data/share/rollback.sh"

# 重启服务
ansible servers -m service -a "name=webapp state=restarted"
ansible servers -m service -a "name=nginx state=restarted"
