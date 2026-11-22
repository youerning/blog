#!/bin/bash
# B 组（云端托管）用：measure_web.sh <标签> <URL> [是否加 /big]
# 输出一行 CSV：tag,p50,p95,max,down_mbps,超时数
set -u
tag=$1; url=$2; big=${3:-1}
raw=/root/bench/raw/$tag
rm -rf "$raw"; mkdir -p "$raw"

for _ in $(seq 20); do
  curl -s -o /dev/null -m 15 -w "%{time_starttransfer}\n" "$url/" || echo "TIMEOUT"
done > "$raw/lat.txt" 2>&1

if [ "$big" = "1" ]; then
  for i in 1 2 3; do
    curl -s -o /dev/null -m 60 -w "%{speed_download}\n" "$url/big" || echo 0
  done > "$raw/dl.txt" 2>&1
fi

python3 - "$tag" "$raw" <<'PY'
import sys, statistics as st
tag, raw = sys.argv[1], sys.argv[2]
lat = []
for line in open(f'{raw}/lat.txt'):
    line = line.strip()
    lat.append(15000.0 if (line == 'TIMEOUT' or not line) else float(line) * 1000)
ok = sorted(x for x in lat if x < 15000) or [15000.0]
p50 = st.median(ok)
p95 = ok[min(len(ok) - 1, int(len(ok) * 0.95))]
try:
    dl = [float(x) for x in open(f'{raw}/dl.txt').read().split()]
except FileNotFoundError:
    dl = []
mb = [round(x * 8 / 1e6, 2) for x in dl]
print(f'{tag},{p50:.1f},{p95:.1f},{max(lat):.1f},'
      f'{",".join(f"{x:.2f}" for x in mb) or "-"},{len([x for x in lat if x >= 15000])}')
PY
