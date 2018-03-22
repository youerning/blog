#coding: utf-8
from __future__ import print_function
from locust import HttpLocust, TaskSet, task


class WebsiteUser(HttpLocust):
    host = "http://192.168.111.30"
    # 目标端口
    port = 80
    min_wait = 100
    max_wait = 1000

    class task_set(TaskSet):
        @task(1)
        def index(self):
            self.client.get("/")
