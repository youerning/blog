# -*- coding: UTF-8 -*-
# @author youerning
# @email 673125641@qq.com

import socket

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# 防止socket关闭之后，系统保留socket一段时间，以致于无法重新绑定同一个端口
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


CRLF = b"\r\n"
host = "127.0.0.1"
port = 6666
server.bind((host, port))
server.listen()
print("启动服务器: http://{}:{}".format(host, port))

resp = b"HTTP/1.1 200 OK" + (CRLF * 2) + b"Hello world"

while True:
    peer, addr = server.accept()
    print("客户端来自于: {}".format(str(addr)))

    # 暂时不考虑client的request的内容超过1024字节的情况
    data = peer.recv(1024)
    print("收到请求如下:")
    print("字节码格式数据")
    print(data)
    print()
    print("字符串格式数据")
    print(data.decode("utf8"))
    peer.send(resp)
    peer.close()
    # 因为windows没办法ctrl+c取消, 所以这里直接退出了
    break