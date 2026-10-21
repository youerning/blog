#!/usr/bin/env python3
"""用于授权环境的最小 SSH 蜜罐：记录认证尝试，始终拒绝登录。"""
import asyncio
import json
import os
import sys
from datetime import datetime, timezone

import asyncssh

BASE = os.path.dirname(os.path.abspath(__file__))
LOGD = os.path.join(BASE, "log")
KEYD = os.path.join(BASE, "hostkeys")
PORT = int(os.environ.get("SSHPOT_PORT", "2222"))
MAX_TRIES = 6  # 参考 sshd 默认的 MaxAuthTries
SERVER_VERSION = os.environ.get("SSHPOT_VERSION", "OpenSSH_9.6p1 Ubuntu-3ubuntu13.5")

os.makedirs(LOGD, exist_ok=True)
os.makedirs(KEYD, exist_ok=True)
os.umask(0o027)  # 日志包含明文密码，新建文件权限限制为 0640
_jsonl = open(os.path.join(LOGD, "attempts.jsonl"), "a", buffering=1)
_text = open(os.path.join(LOGD, "attempts.log"), "a", buffering=1)


def log(event, **kw):
    """将事件写入 JSONL 和便于阅读的文本日志。"""
    now = datetime.now(timezone.utc)
    rec = {"eventid": "cowrie." + event, "timestamp": now.isoformat(), **kw}
    _jsonl.write(json.dumps(rec, ensure_ascii=False) + "\n")
    bits = [now.astimezone().strftime("%m-%d %H:%M:%S"), "%-16s" % event, kw.get("src_ip", "-")]
    if kw.get("username"):
        bits.append("user=%s" % kw["username"])
    if kw.get("password") is not None:
        bits.append("pass=%r" % kw["password"])
    if kw.get("method"):
        bits.append("method=%s" % kw["method"])
    if kw.get("fingerprint"):
        bits.append("key=%s" % kw["fingerprint"])
    if kw.get("client_version"):
        bits.append("client=%r" % kw["client_version"])
    _text.write(" ".join(bits) + "\n")


class Pot(asyncssh.SSHServer):
    """为每个连接维护认证状态，不提供会话功能。"""

    def __init__(self):
        """初始化连接信息与尝试计数。"""
        self._conn = None
        self.src_ip, self.src_port = "?", 0
        self.tries = 0

    def _cv(self):
        """版本交换完成后，按需读取客户端标识。"""
        try:
            return self._conn.get_extra_info("client_version") or ""
        except Exception:
            return ""

    def connection_made(self, conn):
        """保存连接来源并记录连接事件。"""
        self._conn = conn
        peer = conn.get_extra_info("peername")
        if peer:
            self.src_ip, self.src_port = peer[0], peer[1]
        log("connect", src_ip=self.src_ip, src_port=self.src_port)

    def connection_lost(self, exc):
        """记录断开事件及本连接的认证尝试数。"""
        log("disconnect", src_ip=self.src_ip, src_port=self.src_port,
            attempts=self.tries)

    def _reject(self, **kw):
        """记录失败事件，到达尝试上限后断开连接。"""
        self.tries += 1
        log("login.failed", src_ip=self.src_ip, src_port=self.src_port,
            client_version=self._cv(), **kw)
        if self.tries >= MAX_TRIES:
            try:
                self._conn.disconnect(asyncssh.DISC_TOO_MANY_AUTH_FAILURES)
            except Exception:
                pass
        return False

    def begin_auth(self, username):
        """要求客户端进入认证流程，不能跳过认证。"""
        log("auth.start", src_ip=self.src_ip, username=username,
            client_version=self._cv())
        return True

    def password_auth_supported(self):
        """向客户端声明支持密码认证。"""
        return True

    def validate_password(self, username, password):
        """记录密码认证请求，始终拒绝登录。"""
        return self._reject(username=username, password=password, method="password")

    # 同时保留新旧接口拼写，认证逻辑不变。
    def public_key_auth_supported(self):
        """通过当前接口声明支持公钥认证。"""
        return True

    def publickey_auth_supported(self):
        """保留旧版本公钥认证接口。"""
        return True

    def validate_public_key(self, username, key):
        """记录公钥指纹与算法，始终拒绝登录。"""
        return self._reject(username=username, method="publickey",
                            fingerprint=key.get_fingerprint(),
                            key_type=key.get_algorithm())

    def validate_publickey(self, username, key):
        """通过兼容接口调用统一的公钥认证处理。"""
        return self.validate_public_key(username, key)

    def kbdint_auth_supported(self):
        """声明支持键盘交互认证。"""
        return True

    def keyboard_interactive_auth_supported(self):
        """保留键盘交互认证的兼容接口。"""
        return True

    def get_kbdint_challenge(self, username, lang, submethods):
        """提供一个不回显输入的密码提示。"""
        # 保留 Password，兼容按英文提示自动识别密码的客户端。
        return "", "", "", [("密码 (Password): ", False)]

    def kbdint_auth_requested(self):
        """请求由服务端自定义键盘交互挑战。"""
        return ""

    def validate_kbdint_response(self, username, responses):
        """记录首个交互响应，始终拒绝登录。"""
        return self._reject(username=username, method="keyboard-interactive",
                            password=(responses[0] if responses else None))


def load_keys():
    """生成缺失的主机密钥，并返回密钥文件路径。"""
    keys = []
    for name, algo, size in (("ssh_host_ed25519_key", "ssh-ed25519", None),
                             ("ssh_host_rsa_key", "ssh-rsa", 3072)):
        path = os.path.join(KEYD, name)
        if not os.path.exists(path):
            key = asyncssh.generate_private_key(algo, key_size=size) if size \
                else asyncssh.generate_private_key(algo)
            key.write_private_key(path)
            os.chmod(path, 0o600)
        keys.append(path)
    return keys


async def main():
    """在所有本机接口启动蜜罐，持续等待连接。"""
    await asyncssh.create_server(
        Pot, "", PORT,
        server_host_keys=load_keys(),
        server_version=SERVER_VERSION,
        login_timeout=120,
    )
    log("server.start", src_ip="-", port=PORT)
    await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
