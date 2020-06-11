# -*- coding: UTF-8 -*-
# @author youerning
# @email 673125641@qq.com
# 主要参考于: https://github.com/sirMackk/diy_framework/blob/master/diy_framework/application.py

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

