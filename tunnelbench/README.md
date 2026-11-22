# tunnelbench

一套可复现的内网穿透工具实测脚本与原始数据。同一台被测服务，分别用 frp、rathole、nps、chisel、bore、sish、cloudflared、localtunnel 暴露出来，量 HTTP 首字节时间（TTFB）、吞吐和常驻内存，看「同一件事用不同工具做，代价差多少」。

> 配套文章：[我把八种内网穿透都跑了一遍，发现「哪个最快」是个伪问题](https://youerning.top/post/tunnel-tools-benchmark/)
> —— 分类方法、数据表、六条结论和选型清单都在那篇里，这里是它的原始数据与复现脚本。

**仅供学习研究用途。** 实测涉及 nps 的历史 RCE、以及用 WebSocket 把流量伪装成普通 HTTPS 绕过端口限制的做法，请勿用于任何未授权的场景。仓库里所有公网 IP 均为 RFC 5737 文档保留段（`203.0.113.x`），口令为占位符 `CHANGE_ME`；真实机器信息不含在其中。

## 结论速览

| 工具 | TTFB p50 / p95 | 单流 | 4 流 | 常驻内存 |
|---|---|---|---|---|
| 直连基线 | 22 / 43 ms | 7.80 | 7.65 | — |
| frp | 9 / 310 ms* | 6.87 | 失败 | 27.0 MB |
| rathole | 16 / 21 ms | 7.47 | 14.99 | **9.1 MB** |
| nps | 24 / 30 ms | 7.06 | 6.98 | 21.8 MB |
| chisel | 35 / 42 ms | 7.42 | 5.96 | 13.7 MB |
| cloudflared | **1100 / 2950 ms** | 2.29 | — | 约 40 MB |
| bore / sish / localtunnel | — | — | — | 本环境未跑通 |

\* frp 有一次 p95 尖刺和一次 iperf3 连不上，属偶发。中继式之间性能差异可忽略，真正的分水岭是「要不要自己的公网机器」。完整结论见 `results.md`。

## 目录结构

```
.
├── PLAN.md              # 实测执行计划（工具清单、方法、风险红线）
├── results.md           # 完整结果汇总与结论
├── results.csv          # 机器可读的汇总表
├── probe.sh             # 统一探针：TCP 握手 / 吞吐 / UDP，只输出数字
├── measure.sh           # 中继式测量：TTFB + iperf3 单流/4 流（在服务端机跑）
├── measure_web.sh       # 托管式测量：TTFB + 下载吞吐
├── target.py            # 被测 HTTP 服务：200 字节 / 2MB，端口 60990
├── summarize.py         # 把 raw/ 汇总成 results.csv
├── make_figs.py         # 用 results.csv 画四张图（深色主题）
├── conf/                # frp / rathole 的 server 与 client 配置样例（已脱敏）
├── raw/<tool>/          # 每个工具的原始数据（lat.txt / tcp1.txt / tcp4.txt / dl.txt）
└── figs/                # 四张对比图，PNG + WebP
```

## 复现

需要两台能互通的云主机（一台跑 server / 探测端，一台跑 client / 被测服务），装 `iperf3`、`curl`、`python3`。二进制工具请从各项目官方 releases 自行下载，本仓库不含二进制。

```bash
# 1. 在 client 机上启动被测服务
python3 target.py 60990          # HTTP：/ 返回 200 字节，/big 返回 2MB
iperf3 -s -p 61000               # 吞吐服务

# 2. 按 conf/ 里的样例配置隧道（把 IP 换成你的 server、token 换成随机串）
#    frp:     conf/frp/
#    rathole: conf/rathole/

# 3. 在 server 机上测量（tag 自定，host 用 127.0.0.1 打本地映射端口）
bash measure.sh rathole 127.0.0.1 60013 60012
bash measure_web.sh cloudflared https://xxx.trycloudflare.com

# 4. 汇总与出图（在本仓库根目录，数据放 raw/<tag>/）
python3 summarize.py
python3 make_figs.py             # 需要 matplotlib；中文字体按本机调整 FONT
```

`measure.sh` 输出一行 CSV：`tag,p50,p95,max,tcp1×3,tcp4,超时数`。`probe.sh` 的三个子命令 `lat|tcp|udp` 只输出可解析数字，方便接自己的流水线。

## 字段与口径

- **TTFB**：curl `time_starttransfer`，每工具 20 次取 p50/p95。隧道里 TCP 握手在本地完成，测握手没意义，所以用首字节替代延迟指标。
- **吞吐**：iperf3，单流测 3 次、4 流测 1 次，取 Mbps。本机实测跨境链路单流被限到约 7.8 Mbps、多流可叠到约 15（per-flow 限速）。
- **常驻内存**：测完用 `ps -o rss=` 取服务端进程 RSS。
- **未跑通项如实记录**：bore（控制端口写死 7835，不在放行段）、sish（4.x 参数大改，限定时间内没配通）、localtunnel（公共服务端 `loca.lt` 连不上）。失败本身也是结论。

## 图表

| 图 | 内容 |
|---|---|
| `figs/01-latency` | 首字节延迟对比，cloudflared 高两个数量级 |
| `figs/02-throughput` | 单流吞吐 vs 链路天花板 |
| `figs/03-memory` | 常驻内存，rathole 约为 frp 的三分之一 |
| `figs/04-usability` | 部署门槛与可用性，红色 = 本环境未跑通 |

## License

MIT
