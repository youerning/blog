# -*- coding: UTF-8 -*-
# @author youerning
# @email 673125641@qq.com

import socket

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

CRLF = b"\r\n"
req = b"GET / HTTP/1.1" + (CRLF * 3)

client.connect(("www.baidu.com", 80))
client.send(req)

resp = b""
while True:
    data = client.recv(1024)
    if data:
        resp += data
    else:
        break

client.close()
# 查看未解码的前1024的bytes
print(resp[:1024])
# 查看解码后的前1024个字符
print()
print(resp.decode("utf8")[:1024])
