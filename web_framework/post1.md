# 从tcp开始，用Python写一个web框架
想尝试写一个web框架，不是因为Django, Flask, Sanic, tornado等web框架不香, 而是尝试造一个轮子会对框架的认识更深，为了认识更深自然不应该依赖第三方库(仅使用内置库)。

大多数写web框架的文章专注于应用层的实现，比如在wsgi接口的基础上实现web框架，这样当然是没有问题的，就是少了更底层一点的东西，比如不知道request到底怎么来的，但是我也理解如此做法，因为解析http请求实在不是太有意思的内容。

本文主要会从tcp传输开始讲起，依次介绍tcp传输，http协议的解析，路由解析，框架的实现。

而其中框架的实现会分为三个阶段:单线程，多线程，异步IO。

最终的目标就是一个使用上大概类似flask, sanic的框架。

> 因为http的内容比较多，本文自然也不会实现http协议的所有内容。

文章目录结构如下:
- TCP传输
- HTTP解析
- 路由
- WEB框架


## 环境说明
Python: 3.6.8 不依赖任何第三方库

> 高于此版本应该都可以

## HTTP协议
HTTP应该是受众最广的应用层协议了，没有之一。

HTTP协议一般分为两个部分，客户端，服务端。其中客户端一般指浏览器。客户端发送HTTP请求给服务端，服务端根据客户端的请求作出响应。

那么这些请求和响应是什么呢？下面在tcp层面模拟http请求及响应。


## TCP传输

HTTP是应用层的协议，而所谓协议自然是一堆约定，比如第一行内容应该怎么写，怎么组织内容的格式。

TCP作为传输层承载着这些内容的传输任务，自然可以在不使用任何http库的情况下，用tcp模拟http请求，或者说发送http请求。所谓传输无非发送(send)接收(recv)。


```
#socket_http_client.py

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
```

输出如下:
```
b'HTTP/1.1 200 OK\r\nAccept-Ranges: bytes\r\nCache-Control: no-cache\r\nConnection: keep-alive\r\nContent-Length: 14615\r\nContent-Type: text/html\r\nDate: Wed, 10 Jun 2020 10:14:37 GMT\r\nP3p: CP=" OTI DSP COR IVA OUR IND COM "\r\nP3p: CP=" OTI DSP COR IVA OUR IND COM "\r\nPragma: no-cache\r\nServer: BWS/1.1\r\nSet-Cookie: BAIDUID=32C6E7B012F4DBAAB40756844698B7DF:FG=1; expires=Thu, 31-Dec-37 23:55:55 GMT; max-age=2147483647; path=/; domain=.baidu.com\r\nSet-Cookie: BIDUPSID=32C6E7B012F4DBAAB40756844698B7DF; expires=Thu, 31-Dec-37 23:55:55 GMT; max-age=2147483647; path=/; domain=.baidu.com\r\nSet-Cookie: PSTM=1591784077; expires=Thu, 31-Dec-37 23:55:55 GMT; max-age=2147483647; path=/; domain=.baidu.com\r\nSet-Cookie: BAIDUID=32C6E7B012F4DBAA3C9883ABA2DD201E:FG=1; max-age=31536000; expires=Thu, 10-Jun-21 10:14:37 GMT; domain=.baidu.com; path=/; version=1; comment=bd\r\nTraceid: 159178407703725358186803341565479700940\r\nVary: Accept-Encoding\r\nX-Ua-Compatible: IE=Edge,chrome=1\r\n\r\n<!DOCTYPE html><!--STATUS OK-->\r\n<html>\r\n<head>\r\n\t<meta http-equi'

HTTP/1.1 200 OK
Accept-Ranges: bytes
Cache-Control: no-cache
Connection: keep-alive
Content-Length: 14615
Content-Type: text/html
Date: Wed, 10 Jun 2020 10:14:37 GMT
P3p: CP=" OTI DSP COR IVA OUR IND COM "
P3p: CP=" OTI DSP COR IVA OUR IND COM "
Pragma: no-cache
Server: BWS/1.1
Set-Cookie: BAIDUID=32C6E7B012F4DBAAB40756844698B7DF:FG=1; expires=Thu, 31-Dec-37 23:55:55 GMT; max-age=2147483647; path=/; domain=.baidu.com
Set-Cookie: BIDUPSID=32C6E7B012F4DBAAB40756844698B7DF; expires=Thu, 31-Dec-37 23:55:55 GMT; max-age=2147483647; path=/; domain=.baidu.com
Set-Cookie: PSTM=1591784077; expires=Thu, 31-Dec-37 23:55:55 GMT; max-age=2147483647; path=/; domain=.baidu.com
Set-Cookie: BAIDUID=32C6E7B012F4DBAA3C9883ABA2DD201E:FG=1; max-age=31536000; expires=Thu, 10-Jun-21 10:14:37 GMT; domain=.baidu.com; path=/; version=1; comment=bd
Traceid: 159178407703725358186803341565479700940
Vary: Accept-Encoding
X-Ua-Compatible: IE=Edge,chrome=1

<!DOCTYPE html><!--STATUS OK-->
<html>
<head>
        <meta http-equi
```

既然通过tcp就能完成http的客户端的请求，那么完成服务端的实现不也是理所当然么？
```
#socket_http_server.py

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

```

在启动之后，我们可以通过requests进行测试
```
In [1]: import requests
In [2]: resp = requests.get("http://127.0.0.1:6666")
In [3]: resp.ok
Out[3]: True
In [4]: resp.text
Out[4]: 'Hello world'
```

然后服务端会输出一些信息然后退出。
```
收到请求如下:
字节码格式数据
b'GET / HTTP/1.1\r\nHost: 127.0.0.1:6666\r\nUser-Agent: python-requests/2.18.4\r\nAccept-Encoding: gzip, deflate\r\nAccept: */*\r\nConnection: keep-alive\r\n\r\n'

字符串格式数据
GET / HTTP/1.1
Host: 127.0.0.1:6666
User-Agent: python-requests/2.18.4
Accept-Encoding: gzip, deflate
Accept: */*
Connection: keep-alive
```

> 这里之所孜孜不倦的既输出bytes也输出str类型的数据, 主要是为了让大家注意到其中的**\r\n**, 这两个不可见字符很重要。

> 谁说不可见字符不可见，我在字节码格式数据格式数据中不看到了么？这是一个很有意思的问题呢。


至此，我们知道http(超文本传输协议)就如它的名字一样， 它定义的客户端端应该使用怎样格式的**文本**发送请求，服务端应该使用怎样格式的**文本**回应请求。


上面完成了http客户端，服务端的模拟，这里可以进一步将服务端的响应内容做封装，抽象出Response类来
> 为什么不也抽象出客户端的Request类呢? 因为本文打算写的是web服务端的框架它 : )。


```
# response.py

from collections import namedtuple

RESP_STATUS = namedtuple("RESP_STATUS", ["code", "phrase"])
CRLF = "\r\n"

status_ok = RESP_STATUS(200, "ok")
status_bad_request = RESP_STATUS(400, "Bad Request")
statue_server_error = RESP_STATUS(500, "Internal Server Error")

default_header = {"Server": "youerning", "Content-Type": "text/html"}


class Response(object):
    http_version = "HTTP/1.1"
    def __init__(self, resp_status=status_ok, headers=None, body=None):
        self.resp_status = resp_status
        if not headers:
            headers = default_header
        if not body:
            body = "hello world"

        self.headers = headers
        self.body = body
    
    def to_bytes(self):
        status_line = "{} {} {}".format(self.http_version, self.resp_status.code, self.resp_status.phrase)
        header_lines = ["{}: {}".format(k, v) for k,v in self.headers.items()]
        headers_text = CRLF.join(header_lines)
        if self.body:
            headers_text += CRLF

        message_body = self.body
        data = CRLF.join([status_line, headers_text, message_body])

        return data.encode("utf8")

```

所以前面的响应可以这么写。

```
# socket_http_server2.py

import socket
from response import Response

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

    data = peer.recv(1024)
    print("收到请求如下:")
    print("二进制数据")
    print(data)
    print()
    print("字符串")
    print(data.decode("utf8"))
    peer.send(resp.to_bytes())
    peer.close()
    # 因为windows没办法ctrl+c取消, 所以这里直接退出了
    break
```

最终的结果大同小异，唯一的不同是后者的响应中还有http头信息。


关于HTTP请求(Request)及响应(Response)的具体定义可以参考下面链接:

https://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html#sec5

https://www.w3.org/Protocols/rfc2616/rfc2616-sec6.html#sec6


## HTTP解析
前面的内容虽然完成了HTTP交互的模拟，却没有达到根据请求返回指定响应的要求，这是因为我们还没有解析客户端发送来的请求，自然也就判断请求的不同。

下面列出两个比较常见的请求，内容如下。

GET请求
```
# Bytes类型
b'GET / HTTP/1.1\r\nHost: 127.0.0.1:6666\r\nUser-Agent: python-requests/2.18.4\r\nAccept-Encoding: gzip, deflate\r\nAccept: */*\r\nConnection: keep-alive\r\n\r\n'

# string类型
GET / HTTP/1.1
Host: 127.0.0.1:6666
User-Agent: python-requests/2.18.4
Accept-Encoding: gzip, deflate
Accept: */*
Connection: keep-alive
```

POST请求
```
# Bytes类型
b'POST / HTTP/1.1\r\nHost: 127.0.0.1:6666\r\nUser-Agent: python-requests/2.18.4\r\nAccept-Encoding: gzip, deflate\r\nAccept: */*\r\nConnection: keep-alive\r\nContent-Length: 29\r\nContent-Type: application/x-www-form-urlencoded\r\n\r\nusername=admin&password=admin'

# string类型
POST / HTTP/1.1
Host: 127.0.0.1:6666
User-Agent: python-requests/2.18.4
Accept-Encoding: gzip, deflate
Accept: */*
Connection: keep-alive
Content-Length: 29
Content-Type: application/x-www-form-urlencoded

username=admin&password=admin
```


这里依旧"多此一举"的贴出了两个类型的内容，是因为字符串在打印的时候会将不可见字符格式化，比如\n就是一个换行符，而我们之所以看到的HTTP协议是一行一行的数据，就是因为我们在打印的时候将其格式化了，如果没有这个意识的话，我们就无法确定Request Line(请求行), Request Header Fields(请求头字段), message-body(消息主题)

> 之所以中英文混写是为了避免歧义


为了更好的将客户端发送过来的信息抽象，我们写一个Request类来容纳所有请求的所有信息。

```
# request.py

class Request(object):
    def __init__(self):
        self.method = None
        self.path = None
        self.raw_path = None
        self.query_params = {}
        self.path_params = {}
        self.headers = {}
        self.raw_body = None
        self.data = None
```

那么解析一下吧
```
# http_parser.py

import re
import json
from urllib import parse
from request import Request
from http_exceptions import BadRequestException, InternalServerErrorException

CRLF = b"\r\n"
SEPARATOR = CRLF + CRLF
HTTP_VERSION = b"1.1"
REQUEST_LINE_REGEXP = re.compile(br"[a-z]+ [a-z0-9.?_\[\]=&-\\]+ http/%s" % HTTP_VERSION, flags=re.IGNORECASE)
SUPPORTED_METHODS = {"GET", "POST"}


def http_parse(buffer):
    print(type(buffer[:]))
    request = Request()

    def remove_buffer(buffer, stop_index):
        buffer = buffer[stop_index:]
        return buffer

    def parse_request_line(line):
        method, raw_path = line.split()[:2]
        method = method.upper()

        if method not in SUPPORTED_METHODS:
            raise BadRequestException("{} method noy supported".format(method))
        
        request.method = method
        request.raw_path = raw_path
        
        # 处理路径, 比如/a/b/c?username=admin&password=admin
        # 路径是/a/b/c
        # ?后面的是路径参数
        # 值得注意的路径参数可以重复，比如/a/b/c?filter=name&filter=id
        # 所以解析后的路径参数应该是字符串对应着列表, 比如{"filter": ["name", "id"]}
        url_obj = parse.urlparse(raw_path)
        path = url_obj.path
        query_params = parse.parse_qs(url_obj.query)
        request.path = path
        request.query_params = query_params

    def parse_headers(header_lines):
        # 其实这里使用bytes应该会更快，但是为了跟上面的parse_request_line方法解析模式保持一致
        header_iter = (line for line in header_lines.split(CRLF.decode("utf8")) if line)
        headers = {}
        
        for line in header_iter:
            header, value = [i.strip() for i in line.strip().split(":")][:2]
            header = header.lower()
            headers[header] = value

        request.headers = headers

    def parse_body(body):
        # 为了代码简洁就不加异常捕获了
        data = body_parser(raw_body)

        request.raw_body = raw_body
        request.data = data

    # 判断是否有request line
    if REQUEST_LINE_REGEXP.match(buffer):
        line = buffer.split(CRLF, maxsplit=1)[0].decode("utf8")
        parse_request_line(line)
        # 因为request line已经处理完成了，所以可以移除
        first_line_end = buffer.index(CRLF)
        # 之所以加, 因为\r\n站两个字节
        # 个人觉得参考链接这里不加2是错误的，因为没有移除\r\n那么判断是否有http header的时候会因为没有http header出错。
        # del buffer[:first_line_end + 2]
        buffer = remove_buffer(buffer, first_line_end + 2)

    # 如果存在\r\n\r\n说明之前有http header
    if SEPARATOR in buffer:
        header_end = buffer.index(SEPARATOR)
        header_lines = buffer[:header_end].decode("utf8")
        parse_headers(header_lines)
        # 同上
        # del buffer[:header_end + 4]
        buffer = remove_buffer(buffer, header_end + 4)

    headers = request.headers
    if headers and "content-length" in headers:
        # 这里只处理请求主体是application/x-www-form-urlencoded及application/json两种content-type
        # 内容格式为application/x-www-form-urlencoded时，内容长这个样:username=admin&password=admin就像url里面的query_params一样
        # 内容格式为application/json时，内容就是json的字符串
        content_type = headers.get("content-type")
        # content_length = headers.get("content-length", "0")

        body_parser = parse.parse_qs
        if content_type == "application/json":
            # 源链接应该错了
            body_parser = json.loads

        # 这就版本就不是纠结内容是否接受完毕了
        raw_body = buffer.decode("utf8")
        parse_body(raw_body)

    return request
```
然后测试一下
```
# 启动服务器
python socket_http_server3.py
```
使用request发送http请求
```
In [115]: requests.post("http://127.0.0.1:6666/test/path?asd=aas", data={"username": "admin", "password": "admin"})
Out[115]: <Response [200]>
```

服务端输出如下:
```
客户端来自于: ('127.0.0.1', 1853)
<class 'bytes'>
收到请求如下:
请求方法: POST
请求路径: /test/path
请求参数: {'asd': ['aas']}
请求头: {'host': '127.0.0.1', 'user-agent': 'python-requests/2.18.4', 'accept-encoding': 'gzip, deflate', 'accept': '*/*', 'connection': 'keep-alive', 'content-length': '29', 'content-type': 'application/x-www-form-urlencoded'}
请求内容: {'username': ['admin'], 'password': ['admin']}
```


至此通过一个解析客户端发来的请求，我们得到了一个Request对象，在这个Request对象里面我们可以得到我们需要的一切信息。

## 路由

### 路由解析
根据经验我们知道不同的网页路径对应着不同的内容，通过路径的不同响应不同的内容，这部分内容一般称为路由解析。

所以在得到请求之后，我们需要根据客户端访问的路径来判断返回什么样的内容，存储这些对应关系的对象我们一般叫做路由。

路由至少提供两个接口，一是添加这种对应关系的方法，二是根据路径返回可以响应请求的可执行函数, 这个函数我们一般叫做handler.

所谓路径一般有两种，静态的，动态的。

#### 静态路由
静态的简单，一个字典就可以解决，通过将请求方法及路径作为一个二元组作为字典的key, 而对应的处理方法作为value就可以了。如下

```
# router1.py

import re
from collections import namedtuple
from functools import partial


def home():
    return "home"

def info():
    return "info"

def not_found():
    return "not found"


class Router(object):
    def __init__(self):
        self._routes = {}

    def add(self, path, handler, methods=None):
        if methods is None:
            methods = ["GET"]

        if not isinstance(methods, list):
            raise Exception("methods需要一个列表")

        for method in methods:
            key = (method, path)
            if key in self._routes:
                raise Exception("路由重复了: {}".format(path))
            self._routes[key] = handler

    def get_handler(self, method, path):
        method_path = (method, path)
        return self._routes.get(method_path, not_found)


route = Router()
route.add("/home", home)
route.add("/info", info, methods=["GET", "POST"])
print(route.get_handler("GET", "/home")())
print(route.get_handler("POST", "/home")())
print(route.get_handler("GET", "/info")())
print(route.get_handler("POST", "/info")())
print(route.get_handler("GET", "/xxxxxx")())
```

执行结果如下:
```
home
not found
info
info
not found
```


#### 动态路由
动态就稍微复杂一些，需要使用到正则表达式。不过为了简单，这里就不提供过滤动态路径类型的接口了，比如/user/{id:int}这样的骚操作。

代码如下
```
# router2.py

import re
from collections import namedtuple
from functools import partial


Route = namedtuple("Route", ["methods", "pattern", "handler"])


def home():
    return "home"

def item(name):
    return name

def not_found():
    return "not found"


class Router(object):
    def __init__(self):
        self._routes = []

    @classmethod
    def build_route_regex(self, regexp_str):
        # 路由的路径有两种格式
        # 1. /home 这种格式没有动态变量, 返回^/home$这样的正则表达式
        # 2. /item/{name} 这种格式用动态变量,  将其处理成^/item/(?P<name>[a-zA-Z0-9_-]+)$这种格式
        def named_groups(matchobj):
            return '(?P<{0}>[a-zA-Z0-9_-]+)'.format(matchobj.group(1))

        re_str = re.sub(r'{([a-zA-Z0-9_-]+)}', named_groups, regexp_str)
        re_str = ''.join(('^', re_str, '$',))
        return re.compile(re_str)


    @classmethod
    def match_path(self, pattern, path):
        match = pattern.match(path)
        try:
            return match.groupdict()
        except AttributeError:
            return None

    def add(self, path, handler, methods=None):
        if methods is None:
            methods = {"GET"}
        else:
            methods = set(methods)
        pattern = self.__class__.build_route_regex(path)
        route = Route(methods, pattern, handler)
        
        if route in self._routes:
            raise Exception("路由重复了: {}".format(path))
        self._routes.append(route)

    def get_handler(self, method, path):
        for route in self._routes:
            if method in route.methods:
                params = self.match_path(route.pattern, path)

                if params is not None:
                    return partial(route.handler, **params)

        return not_found


route = Router()
route.add("/home", home)
route.add("/item/{name}", item, methods=["GET", "POST"])
print(route.get_handler("GET", "/home")())
print(route.get_handler("POST", "/home")())
print(route.get_handler("GET", "/item/item1")())
print(route.get_handler("POST", "/item/item1")())
print(route.get_handler("GET", "/xxxxxx")())
```

执行结果如下
```
home
not found
item1
item1
not found
```


### 通过装饰器添加路由
之所以单独在说一下路由的添加，是因为显式的调用感觉不够花哨(不够甜) : ).所以类似flask那样通过装饰器(语法糖)来添加路由是很棒(甜)的一个选择。


```
# router3.py

import re
from collections import namedtuple
from functools import partial
from functools import wraps


SUPPORTED_METHODS = {"GET", "POST"}
Route = namedtuple("Route", ["methods", "pattern", "handler"])


class View:
    pass

class Router(object):
    def __init__(self):
        self._routes = []

    @classmethod
    def build_route_regex(self, regexp_str):
        # 路由的路径有两种格式
        # 1. /home 这种格式没有动态变量, 返回^/home$这样的正则表达式
        # 2. /item/{name} 这种格式用动态变量,  将其处理成^/item/(?P<name>[a-zA-Z0-9_-]+)$这种格式
        def named_groups(matchobj):
            return '(?P<{0}>[a-zA-Z0-9_-]+)'.format(matchobj.group(1))

        re_str = re.sub(r'{([a-zA-Z0-9_-]+)}', named_groups, regexp_str)
        re_str = ''.join(('^', re_str, '$',))
        return re.compile(re_str)


    @classmethod
    def match_path(self, pattern, path):
        match = pattern.match(path)
        try:
            return match.groupdict()
        except AttributeError:
            return None

    def add_route(self, path, handler, methods=None):
        if methods is None:
            methods = {"GET"}
        else:
            methods = set(methods)
        pattern = self.__class__.build_route_regex(path)
        route = Route(methods, pattern, handler)
        
        if route in self._routes:
            raise Exception("路由重复了: {}".format(path))
        self._routes.append(route)

    def get_handler(self, method, path):
        for route in self._routes:
            if method in route.methods:
                params = self.match_path(route.pattern, path)

                if params is not None:
                    return partial(route.handler, **params)

        return not_found
    
    def route(self, path, methods=None):
        def wrapper(handler):
            # 闭包函数中如果有该变量的赋值语句，会认为是本地变量，就不上去上层找了
            nonlocal methods
            if callable(handler):
                if methods is None:
                    methods = {"GET"}
                else:
                    methods = set(methods)
                self.add_route(path, handler, methods)

            return handler
        return wrapper


route = Router()


@route.route("/home")
def home():
    return "home"


@route.route("/item/{name}", methods=["GET", "POST"])
def item(name):
    return name


def not_found():
    return "not found"


print(route.get_handler("GET", "/home")())
print(route.get_handler("POST", "/home")())
print(route.get_handler("GET", "/item/item1")())
print(route.get_handler("POST", "/item/item1")())
print(route.get_handler("GET", "/xxxxxx")())
```

输出结果如下，与上面没有使用装饰器时是一样的。
```
home
not found
item1
item1
not found
```

至此我们完成了一个web应该支持的大部分工作了。 那么接下来就是如何将这些部分有机的组合在一起。


## WEB框架
单线程或者多线程版本关于request的处理比较像flask, 因为这两个版本的request是可以在需要的时候导入，就像flask一样, 而异步版本就是模仿sanic了。

不过无论哪个版本, 都追求的只是满足最基本的需求，在讲明白了大多数核心概念以及代码在不损失易读性的前提下尽可能少的代码，这点又是模仿的 《500 Lines or Less》

待续。。。

> 话说《500 Lines or Less》是一个很棒的项目，强烈安利。



## 源代码
https://github.com/youerning/blog/tree/master/web_framework

如果期待后续文章可以关注我的微信公众号(又耳笔记)，头条号(又耳笔记)，github。


## 参考链接
https://www.w3.org/Protocols/rfc2616/rfc2616.html

https://github.com/sirMackk/diy_framework

https://github.com/hzlmn/diy-async-web-framework

https://github.com/huge-success/sanic

https://www.cnblogs.com/Zzbj/p/10207128.html