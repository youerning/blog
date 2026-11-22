#!/bin/bash
# 在服务端机器上跑：measure.sh <标签> <目标host> <http端口> <iperf端口>
# 直连基线用真实 IP，隧道测量用 127.0.0.1（隧道暴露在本地）
# 输出一行 CSV：tag,p50,p95,max,tcp1x3(tcp4),超时数
set -u
tag=$1; host=$2; hp=$3; ip=$4
raw=/root/bench/raw/$tag
rm -rf "$raw"; mkdir -p "$raw"

for _ in $(seq 20); do
  curl -s -o /dev/null -m 5 -w "%{time_starttransfer}\n" "http://$host:$hp/" || echo "TIMEOUT"
done > "$raw/lat.txt" 2>&1

for i in 1 2 3; do
  iperf3 -c "$host" -p "$ip" -t 10 -P 1 -J 2>/dev/null \
    | python3 -c 'import json,sys;d=json.load(sys.stdin);print(round(d["end"]["sum_received"]["bits_per_second"]/1e6,2))' >> "$raw/tcp1.txt" 2>/dev/null \
    || echo "FAIL" >> "$raw/tcp1.txt"
done
iperf3 -c "$host" -p "$ip" -t 10 -P 4 -J 2>/dev/null \
  | python3 -c 'import json,sys;d=json.load(sys.stdin);print(round(d["end"]["sum_received"]["bits_per_second"]/1e6,2))' >> "$raw/tcp4.txt" 2>/dev/null \
  || echo "FAIL" >> "$raw/tcp4.txt"

python3 - "$tag" "$raw" <<'PY'
import sys, statistics as st
tag, raw = sys.argv[1], sys.argv[2]
lat = []
for line in open(f'{raw}/lat.txt'):
    line = line.strip()
    lat.append(5000.0 if (line == 'TIMEOUT' or not line) else float(line) * 1000)
ok = sorted(x for x in lat if x < 5000) or [5000.0]
p50 = st.median(ok)
p95 = ok[min(len(ok) - 1, int(len(ok) * 0.95))]
def rd(p):
    try:
        return [x for x in open(p).read().split()]
    except FileNotFoundError:
        return []
t1, t4 = rd(f'{raw}/tcp1.txt'), rd(f'{raw}/tcp4.txt')
to = len([x for x in lat if x >= 5000])
print(f'{tag},{p50:.1f},{p95:.1f},{max(lat):.1f},{",".join(t1) or "-"},{",".join(t4) or "-"},{to}')
PY
