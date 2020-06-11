# -*- coding: UTF-8 -*-
# @author youerning
# @email 673125641@qq.com
# 主要参考自: https://github.com/sirMackk/diy_framework/blob/master/diy_framework/http_parser.py

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





