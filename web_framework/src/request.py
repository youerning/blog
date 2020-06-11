# -*- coding: UTF-8 -*-
# @author youerning
# @email 673125641@qq.com

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