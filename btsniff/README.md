# bt-sniff

一个小型 BitTorrent DHT 嗅探器：被动收集 DHT 上流动的 infohash，再用
libtorrent 只拉取元数据（BEP 9），把 **文件名、文件列表、大小、完整 info dict**
存进 SQLite。全程不下载任何数据块。

> 配套文章：[互联网的垃圾堆里有什么？我让 AI 写了个爬虫，在 BT 网络里蹲了两天](https://youerning.top/post/dht-garbage-heap/)
> ——写这个的起因、跑出来的数据和结论都在那篇里。

**仅供学习协议之用。** 跑起来会看到大量违法内容的 hash 和文件名，这类数据不要
公开分享、不要二次分发。本仓库不含任何数据库、导出物或 infohash。

## 工作原理

```
UDP/6881  ──▶ DHT 节点（自建）
               ├─ 应答 ping / find_node / get_peers / announce_peer
               ├─ 从入站 get_peers / announce_peer 里抓 infohash（被动）
               └─ 主动 BEP 51 sample_infohashes 抽样（产量主要来源）
                              │
                              ▼
                    candidates 队列（SQLite）
                              │
                              ▼
              iterative get_peers 查 peer → 喂给 libtorrent
                              │
                              ▼
        magnet + default_dont_download（只取 info dict）
                              │
                              ▼
              torrents 表：name / files / info_dict(zlib)
```

## 安装

```bash
uv sync
cp config.example.toml config.toml   # 按需修改
uv run bt-sniff run
```

需要 Python 3.12（libtorrent 目前没有 3.13/3.14 的 wheel，`.python-version` 已固定）。

## 命令

服务器上装了一个 `sniff` 包装脚本（等价于 `/opt/bt-sniff/.venv/bin/bt-sniff`，配置从
`/etc/bt-sniff/config.toml` 读取）：

```bash
sniff run                          # 常驻：爬虫 + 抓取
sniff tail                         # 实时看新抓到的
sniff search <关键词>             # 按名称子串搜索
sniff search --ext mkv --min-size 2G --since 24h --order size
sniff show <infohash>              # 详情 + 文件列表 + magnet
sniff stats                        # 总量 / 24h / 7d / Top 扩展名
sniff export --since 24h -o out/   # 导出 .torrent 文件
sniff lookup <infohash>            # 只做一次 DHT 查询，调试用
sniff prune --days 30
```

本地开发用 `uv run bt-sniff ...`。`--db path` 和 `--config path` 可以覆盖配置。

## 运维

```bash
systemctl status bt-sniff
journalctl -fu bt-sniff
sudo systemctl restart bt-sniff     # node_id 存在库里，重启不会掉身份
sqlite3 /var/lib/bt-sniff/bt.db '.backup /tmp/bt.db'   # 热备份
```

改配额：编辑 `/opt/bt-sniff/config.toml` 里的 `harvest.max_per_day` /
`max_per_minute` / `dht.query_rate`，然后 restart。

## 产量参考（香港 2C2G VPS，单节点实测）

- 被动 30 分钟：111 个唯一 infohash，速率仍在爬升（末段 ≈ 8/分钟）
- 抽 30 个查询 peer：5 个有 peer（其余是死种或其他爬虫的随机探测噪音）
- 有 peer 的样本 4/4 成功取到元数据，1–20 秒/条

默认 `max_per_day = 5000`，一天约 200–400MB 数据库（含压缩后的 info dict）。

## 部署到服务器

```bash
# 本机
rsync -av --exclude .venv --exclude data --exclude config.toml ./ ubuntu@HOST:/opt/bt-sniff/
# 服务器
cd /opt/bt-sniff && bash deploy/install.sh
# 编辑 config.toml，把 harvest.self_ip 设成公网 IP，然后
sudo systemctl restart bt-sniff && journalctl -fu bt-sniff
```

实测（香港 2C2G VPS，单节点，ufw 只开 6881/udp + 6882/tcp+udp）：

```
crawl: passive=139/min samples=280/min nodes=2358 pending=408
harvest: 7/min ok=7 total=7/5000 active=4 pending=408 failed=0 skipped=0
```

约 9 分钟就能抓满 1000 条；按 `max_per_day = 5000` 会在 9–10 小时后停手，
第二天自动重置。数据库约 260MB/5000 条（info dict 平均 50KB，已 zlib 压缩）。

## 注意事项

- 只取元数据，不下载内容（`default_dont_download`）。
- 索引里会出现违法内容的 hash 和文件名。不要把数据库/导出物公开分享。
- VPS 服务商可能因 BT 流量发 abuse 工单；`max_per_day` / `query_rate` 就是限流阀。
- libtorrent 2.1 的 `parse_magnet_uri` 返回的对象**默认带 paused 标志**，必须清掉，
  否则永远 0 peer（代码里已处理）。
