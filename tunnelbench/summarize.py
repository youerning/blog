#!/usr/bin/env python3
# 汇总 raw/<tag>/ 下的原始数据 -> results.csv
# lat.txt: 每行 curl time_starttransfer（秒）或 TIMEOUT
# tcp1.txt/tcp4.txt: iperf3 单流/4流吞吐（Mbps）
# dl.txt: curl speed_download（字节/秒）
import os, statistics as st

BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "raw")
CAP = 5000.0  # 隧道内测延迟超时上限(ms)


def lines(p):
    try:
        return [x.strip() for x in open(p) if x.strip()]
    except FileNotFoundError:
        return []


def lat_stats(raw, cap=CAP):
    vals = []
    for line in lines(os.path.join(raw, "lat.txt")):
        if line in ("TIMEOUT", ""):
            vals.append(cap)
        else:
            try:
                vals.append(float(line) * 1000)
            except ValueError:
                vals.append(cap)
    ok = sorted(x for x in vals if x < cap) or [cap]
    p50 = st.median(ok)
    p95 = ok[min(len(ok) - 1, int(len(ok) * 0.95))]
    return p50, p95, max(vals), sum(1 for x in vals if x >= cap)


def nums(p, scale=1.0):
    out = []
    for x in lines(p):
        try:
            out.append(round(float(x) * scale, 2))
        except ValueError:
            pass
    return out


tags = sorted(d for d in os.listdir(BASE) if os.path.isdir(os.path.join(BASE, d)))
rows = []
print(f"{'tag':18} {'p50ms':>8} {'p95ms':>8} {'maxms':>9} {'tcp1(Mbps)':>22} {'tcp4(Mbps)':>12} {'dl(Mbps)':>20} {'to':>3}")
for tag in tags:
    raw = os.path.join(BASE, tag)
    p50, p95, mx, to = lat_stats(raw)
    t1 = nums(os.path.join(raw, "tcp1.txt"))
    t4 = nums(os.path.join(raw, "tcp4.txt"))
    dl = nums(os.path.join(raw, "dl.txt"), 8 / 1e6)
    rows.append((tag, p50, p95, mx, t1, t4, dl, to))
    print(f"{tag:18} {p50:8.1f} {p95:8.1f} {mx:9.1f} "
          f"{','.join(map(str, t1)) or '-':>22} "
          f"{','.join(map(str, t4)) or '-':>12} "
          f"{','.join(f'{x:.2f}' for x in dl) or '-':>20} {to:3d}")

with open(os.path.join(os.path.dirname(BASE), "results.csv"), "w") as f:
    f.write("tag,p50_ms,p95_ms,max_ms,tcp1_mbps,tcp4_mbps,dl_mbps,timeout\n")
    for tag, p50, p95, mx, t1, t4, dl, to in rows:
        f.write(f"{tag},{p50:.1f},{p95:.1f},{mx:.1f},"
                f"{'|'.join(map(str, t1)) or ''},"
                f"{'|'.join(map(str, t4)) or ''},"
                f"{'|'.join(f'{x:.2f}' for x in dl) or ''},{to}\n")
print("\n-> results.csv 已写入")
