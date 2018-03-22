#coding: utf-8
from __future__ import print_function
from gevent import socket


host = "127.0.0.1"
port = 5000

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((host, port))

try:
    data = s.recv(1024)
except socket.error as e:
    print(e)
    print("a exception")
else:
    print(type(data))
    print(data)
    print(data == "ok")

finally:
    s.close()
