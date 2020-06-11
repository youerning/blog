# -*- coding: UTF-8 -*-
# @author youerning
# @email 673125641@qq.com

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
        