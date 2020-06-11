# -*- coding: UTF-8 -*-
# @author youerning
# @email 673125641@qq.com

import socket
from response import Response
from http_parser import http_parse

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
# 防止socket关闭之后，系统保留socket一段时间，以致于无法重新绑定同一个端口
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)


CRLF = b"\r\n"
host = "127.0.0.1"
port = 6666
server.bind((host, port))
server.listen()
print("启动服务器: http://{}:{}".format(host, port))

resp = Response()

while True:
    peer, addr = server.accept()
    print("客户端来自于: {}".format(str(addr)))

    # 暂时不考虑client的request的内容超过1024字节的情况
    data = peer.recv(1024)
    request = http_parse(data)
    print("收到请求如下:")
    print("请求方法: {}".format(request.method))
    print("请求路径: {}".format(request.path))
    print("请求参数: {}".format(request.query_params))
    print("请求头: {}".format(request.headers))
    print("请求内容: {}".format(request.data))
    
    peer.send(resp.to_bytes())
    peer.close()
    # 因为windows没办法ctrl+c取消, 所以这里直接退出了
    break