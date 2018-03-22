#coding: utf-8
import time
from gevent import socket
from locust import Locust, TaskSet, events, task


class SocketClient(object):
    """
    Simple, sample socket client implementation that wraps xmlrpclib.ServerProxy and
    fires locust events on request_success and request_failure, so that all requests
    gets tracked in locust's statistics.
    """

    def __init__(self):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__connected = False

    def __getattr__(self, name):
        skt = self._socket

        def wrapper(*args, **kwargs):
            start_time = time.time()
            if not self.__connected:
                try:
                    skt.connect(args[0])
                    self.__connected = True
                except Exception as e:
                    total_time = int((time.time() - start_time) * 1000)
                    events.request_failure.fire(request_type="connect", name=name, response_time=total_time, exception=e)
            else:
                try:
                    data = skt.recv(1024)
                    # print(data)
                except Exception as e:
                    total_time = int((time.time() - start_time) * 1000)
                    events.request_failure.fire(request_type="recv", name=name, response_time=total_time, exception=e)
                else:
                    total_time = int((time.time() - start_time) * 1000)
                    if data == "ok":
                        events.request_success.fire(request_type="recv", name=name, response_time=total_time, response_length=len(data))
                    elif len(data) == 0:
                        events.request_failure.fire(request_type="recv", name=name, response_time=total_time, exception="server closed")
                    else:
                        events.request_failure.fire(request_type="recv", name=name, response_time=total_time, exception="wrong data: {}".format(data))

        return wrapper


class SocketLocust(Locust):
    """
    This is the abstract Locust class which should be subclassed. It provides an XML-RPC client
    that can be used to make XML-RPC requests that will be tracked in Locust's statistics.
    """

    def __init__(self, *args, **kwargs):
        super(SocketLocust, self).__init__(*args, **kwargs)
        self.client = SocketClient()


class SocketUser(SocketLocust):
    # 目标地址
    host = "192.168.111.30"
    # 目标端口
    port = 80
    min_wait = 100
    max_wait = 1000

    class task_set(TaskSet):
        @task(1)
        def connect(self):
            self.client.connect((self.locust.host, self.locust.port))
