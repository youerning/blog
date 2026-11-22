#!/bin/bash
# 统一探针：只输出可解析的数字，不打印表头。
#   probe.sh lat <host> <port> [n]            每行一个 TCP 握手耗时（秒）
#   probe.sh tcp <host> <port> [秒] [流数]    单行：Mbps
#   probe.sh udp <host> <port> [秒] [带宽]    单行：Mbps 抖动ms 丢包%
set -u
case "${1:-}" in
  lat)
    h=$2; p=$3; n=${4:-30}
    for _ in $(seq "$n"); do
      curl -s -o /dev/null -m 6 -w "%{time_connect}\n" "http://$h:$p/" || echo "TIMEOUT"
    done
    ;;
  tcp)
    h=$2; p=$3; d=${4:-10}; s=${5:-1}
    iperf3 -c "$h" -p "$p" -t "$d" -P "$s" -J 2>/dev/null \
      | python3 -c 'import json,sys;d=json.load(sys.stdin);print(round(d["end"]["sum_received"]["bits_per_second"]/1e6,2))'
    ;;
  udp)
    h=$2; p=$3; d=${4:-10}; b=${5:-100M}
    iperf3 -c "$h" -p "$p" -t "$d" -u -b "$b" -J 2>/dev/null \
      | python3 -c 'import json,sys;d=json.load(sys.stdin);s=d["end"]["sum"];print(round(s["bits_per_second"]/1e6,2),round(s.get("jitter_ms",0),3),round(s.get("lost_percent",0),2))'
    ;;
  *) echo "用法: probe.sh lat|tcp|udp host port [参数]"; exit 2;;
esac
