# SSH 蜜罐实验源码

博文[《用 Python 写个 SSH 蜜罐，来一场密码字典的“草船借箭”》](./README.md)的配套源码。

站点阅读地址：https://youerning.top/post/sshpot/
这是实际实验脚本的脱敏中文注释版，保留认证流程、事件字段和统计口径，不包含真实地址、主机私钥和原始凭据日志。

## 使用边界

仅用于自有或明确授权环境的被动观察。所有认证都拒绝，不提供 Shell、文件传输或转发；不得将收集的凭据用于登录其他系统。
这是实验脚本，不是完整的生产级蜜罐，不保证长期运行的并发、磁盘控制或日志容错。

## 环境与启动

实验版本：Python 3.12.3、AsyncSSH 2.24.1。下载仓库后进入 `sshpot` 目录：

```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
SSHPOT_PORT=2222 python honeypot.py
```

默认端口为 2222，通过 `SSHPOT_PORT` 配置；`SSHPOT_VERSION` 可以配置服务端版本标识。
程序绑定所有本机接口，并非只监听回环。请在隔离环境使用，限制入站和出站网络访问；不要误将本地测试服务开放到公网。

从同一授权环境测试，使用专门虚构的密码，不要输入日常密码：

```bash
ssh -p 2222 -o PreferredAuthentications=password \
  -o PubkeyAuthentication=no demo@127.0.0.1
```

认证被拒绝是预期结果。按 Ctrl+C 结束程序。

## 文件与权限

- `honeypot.py`：记录连接、认证和断开事件；单连接达到 6 次认证回调尝试后请求断开。
- `report.py`：统计 JSONL；标准库实现，无额外依赖。
- `log/attempts.jsonl`：结构化事件，UTC 时间戳。
- `log/attempts.log`：文本事件，按运行机器的本地时区展示。
- `hostkeys/`：首次启动自动生成的主机私钥，不要上传或分享。

日志包含明文凭据。脚本设置的 umask 限制后续新建日志文件，但不修复既有文件权限；
目录在 umask 设置前创建，务必自行检查目录、旧文件和备份的访问权限。
建议使用独立低权限用户运行，并配置日志轮转、磁盘配额、资源限制及隔离措施。
真实管理 SSH 必须独立，修改公网端口前确保不会丢失管理连接。

## 统计

本地使用必须显式指定日志文件，因为默认路径沿用实验部署位置：

```bash
python report.py --log ./log/attempts.jsonl --top 20
python report.py --log ./log/attempts.jsonl --since 24h --top 20
```

`--since` 支持 `30m`、`24h`、`7d`、`all`，统计按运行机器的本地时区显示。
`--csv` 可导出明细，但包含敏感凭据，不要公开上传。

## 统计口径与已知限制

- 连接数按 `cowrie.connect` 事件，认证尝试按 `cowrie.login.failed` 事件。
- `cowrie.*` 是脚本采用的事件命名，不代表运行了 Cowrie 项目。
- 密码榜只统计带密码字段的失败事件，公钥尝试不含密码。
- 客户端版本榜累加所有带版本字段的事件，不按连接去重。
- 榜单展示值截断为 38 字符，公钥指纹不能从截断展示中还原。
- 本机测试也会进入统计；来源地址不等于真实攻击者身份。
- 当前统计器将日志载入内存，日志持续增长时需要另外处理资源使用。
- 当前加载器会跳过无效 JSON 和无效时间，但不对任意外来 JSON 做完整结构校验；只用于本脚本生成的日志。

项目参考：[AsyncSSH 文档](https://asyncssh.readthedocs.io/)。
