# coding: utf8
import abc


class Event(object):
    """事件类.
    用于订阅指定的操作,如函数
    当事件执行emit方法的时候,遍历订阅了的操作,并执行该操作"""
    def __init__(self):
        # 内部handlers列表
        self.__handlers = []

    def subscribe(self, handler):
        if handler not in self.__handlers:
            self.__handlers.append(handler)

    def emit(self, *args, **kwargs):
        """执行所有订阅了的操作"""
        for handler in self.__handlers:
            handler(*args, **kwargs)


class Subject(object):
    """将元类指向abc.ABCMeta元类
    1. 当抽象方法未被实现的时候,不能新建该类的实例
    2. abstractmethod相当于子类要实现的接口,如果不实现,则不能新建该类的实例"""
    __metaclass__ = abc.ABCMeta

    @abc.abstractmethod
    def start(self):
        pass

    @abc.abstractmethod
    def stop(self):
        pass

    @abc.abstractmethod
    def dispatch(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def eof(self):
        raise NotImplementedError()


class Dispatcher(object):
    """调度类
    1. 维护事件循环
    2. 不断的调度subject的disptch操作并判断是否结束"""
    def __init__(self):
        self.__subjects = []
        self.__stop = False

    def run(self):
        """运行整个事件循环并在调度之前,之后分别调用subject的start, stop方法"""
        try:
            for subject in self.__subjects:
                subject.start()

            while not self.__stop:
                eof, dispatched = self.dispatch()
                if eof:
                    self.__stop = True
        finally:
            for subject in self.__subjects:
                subject.stop()

    def dispatch(self):
        ret = False
        eof = False
        for subject in self.__subjects:
            ret = subject.dispatch() is True
            eof = subject.eof()

        return eof, ret

    def addSubject(self, subject):
        self.__subjects.append(subject)


class Broker(Subject):
    """Broker 类"""
    def dispatch(self):
        return None

    def eof(self):
        return None

    def start(self):
        pass

    def stop(self):
        pass


class Feed(Subject):
    """Feed类
    1. 承载数据源
    2. 通过数据驱动事件循环"""
    def __init__(self, size):
        self.__data = range(size)
        self.__nextPos = 0
        self.__event = Event()

    def start(self):
        pass

    def stop(self):
        pass

    def dispatch(self):
        value = self.__data[self.__nextPos]
        self.__event.emit(value)
        self.__nextPos += 1
        return True

    def getNewValueEvent(self):
        return self.__event

    def eof(self):
        return self.__nextPos >= len(self.__data)


class Strategy(object):
    def __init__(self, broker, feed):
        self.__dispatcher = Dispatcher()
        self.__feed = feed
        self.__broker = broker
        # 将策略的self.__onBars方法传入Feed的self.__event里面
        # 当Feed调用dispatch方法的时候, 会指定self.__onBars函数
        self.__feed.getNewValueEvent().subscribe(self.__onBars)
        # 注意顺序,Feed对象必须在最后
        self.__dispatcher.addSubject(self.__broker)
        self.__dispatcher.addSubject(self.__feed)

    def __onBars(self, value):
        print("dispatch before.")
        self.onBars(value)
        print("dispatch after")

    def onBars(self, value):
        print("on Bar: {}".format(value))

    def run(self):
        self.__dispatcher.run()


if __name__ == '__main__':
    feed = Feed(3)
    broker = Broker()
    myStrategy = Strategy(broker, feed)
    myStrategy.run()



