#!/usr/bin/env python3
"""统计蜜罐 JSONL：来源、用户名、密码、客户端标识与小时分布。"""
import argparse
import csv
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

DEFAULT_LOG = "/opt/sshpot/log/attempts.jsonl"


def parse_since(text):
    """将相对时间参数转换为 UTC 截止时间。"""
    if not text or text == "all":
        return None
    m = re.fullmatch(r"(\d+)\s*([mhd])", text.strip().lower())
    if not m:
        sys.exit("--since 格式: 30m / 24h / 7d / all")
    n, unit = int(m.group(1)), m.group(2)
    return datetime.now(timezone.utc) - timedelta(**{{"m": "minutes", "h": "hours", "d": "days"}[unit]: n})


def load(path, since):
    """加载有效的 JSONL 记录，跳过无效时间和窗口外数据。"""
    rows = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
                ts = datetime.fromisoformat(rec["timestamp"])
            except (ValueError, KeyError):
                continue
            if ts.tzinfo is None:
                ts = ts.replace(tzinfo=timezone.utc)
            if since and ts < since:
                continue
            rec["_ts"] = ts
            rows.append(rec)
    return rows


def bar(n, top):
    """按最高计数生成文本条形图。"""
    return "#" * max(1, round(n / top * 24)) if top else ""


def table(title, counter, extra=None, top=10):
    """按频次输出榜单，展示值截断到 38 字符。"""
    print("\n== %s ==" % title)
    if not counter:
        print("  （无记录）")
        return
    print("  %-4s %-38s %6s  %s" % ("#", "key", "count", ""))
    highest = counter.most_common(1)[0][1]
    for i, (key, n) in enumerate(counter.most_common(top), 1):
        note = "  " + extra(key) if extra else ""
        print("  %-4d %-38s %6d  %s%s" % (i, str(key)[:38], n, bar(n, highest), note))


def main():
    """解析参数，统计认证事件并按需导出 CSV。"""
    ap = argparse.ArgumentParser(description="统计 SSH 蜜罐认证日志")
    ap.add_argument("--log", default=DEFAULT_LOG, help="JSONL 日志路径")
    ap.add_argument("--since", default="all", help="30m / 24h / 7d / all")
    ap.add_argument("--top", type=int, default=10, help="榜单展示条数")
    ap.add_argument("--csv", help="导出明细到 CSV")
    args = ap.parse_args()

    since = parse_since(args.since)
    rows = load(args.log, since)
    if not rows:
        print("没有数据（%s）" % args.log)
        return

    attempts = [r for r in rows if r["eventid"] == "cowrie.login.failed"]
    connects = [r for r in rows if r["eventid"] == "cowrie.connect"]
    first, last = min(r["_ts"] for r in rows), max(r["_ts"] for r in rows)
    span = last - first

    print("== 概览 ==")
    print("  日志文件 : %s" % args.log)
    print("  时间范围 : %s → %s (跨度 %s)" % (
        first.astimezone().strftime("%Y-%m-%d %H:%M"), last.astimezone().strftime("%Y-%m-%d %H:%M"),
        str(span).split(".")[0]))
    print("  连接数   : %d" % len(connects))
    print("  认证尝试 : %d" % len(attempts))
    print("  来源 IP  : %d" % len({r.get("src_ip") for r in connects}))
    print("  用户名   : %d 种" % len({r.get("username") for r in attempts}))

    ip_stats = defaultdict(lambda: {"conns": 0, "n": 0, "first": None, "last": None,
                                    "user": Counter()})
    for r in connects:
        ip_stats[r.get("src_ip", "?")]["conns"] += 1
    for r in attempts:
        ip = r.get("src_ip", "?")
        s = ip_stats[ip]
        s["n"] += 1
        s["first"] = r["_ts"] if s["first"] is None or r["_ts"] < s["first"] else s["first"]
        s["last"] = r["_ts"] if s["last"] is None or r["_ts"] > s["last"] else s["last"]
        s["user"][r.get("username")] += 1

    print("\n== 来源 IP Top %d ==" % args.top)
    print("  %-4s %-16s %6s %6s  %-17s %-17s %s" % ("#", "ip", "conns", "tries",
                                                   "first", "last", "top user"))
    for i, (ip, s) in enumerate(sorted(ip_stats.items(), key=lambda kv: -kv[1]["n"])[: args.top], 1):
        fmt = lambda t: t.astimezone().strftime("%m-%d %H:%M") if t else "-"
        top_user = s["user"].most_common(1)[0][0] if s["user"] else "-"
        print("  %-4d %-16s %6d %6d  %-17s %-17s %s" % (
            i, ip, s["conns"], s["n"], fmt(s["first"]), fmt(s["last"]), top_user))

    table("被猜用户名 Top %d" % args.top, Counter(r.get("username") for r in attempts), top=args.top)
    table("尝试密码 Top %d" % args.top,
          Counter(r.get("password") for r in attempts if r.get("password") is not None),
          top=args.top)
    # 沿用原报告口径：所有携带客户端标识的事件，不按连接去重。
    table("客户端版本 Top %d" % args.top,
          Counter(r.get("client_version") for r in rows if r.get("client_version")), top=args.top)
    table("publickey 指纹", Counter(r.get("fingerprint") for r in attempts if r.get("fingerprint")),
          top=args.top)

    hours = Counter(r["_ts"].astimezone().strftime("%m-%d %H") for r in attempts)
    print("\n== 按小时 ==")
    highest = max(hours.values()) if hours else 0
    for h in sorted(hours):
        print("  %s  %4d  %s" % (h, hours[h], bar(hours[h], highest)))

    if args.csv:
        cols = ["timestamp", "eventid", "src_ip", "src_port", "username", "password",
                "method", "fingerprint", "key_type", "client_version", "attempts"]
        with open(args.csv, "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow({k: r.get(k, "") for k in cols})
        print("\n已导出 %d 行 → %s" % (len(rows), args.csv))


if __name__ == "__main__":
    main()
