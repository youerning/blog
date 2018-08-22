# PyalgoTrade源码阅读完结篇
## 前言
本文着重于回测相关得模块。

由于上一篇文章实在是写得太烂了, 这一篇文章重新开始写。

## Pyalgotrade业务逻辑及实现原理
以官方教程示例为例

### 下载数据
```
python -c "from pyalgotrade.tools import yahoofinance; yahoofinance.download_daily_bars('orcl', 2000, 'orcl-2000.csv')"
```

### 构建策略并运行
```
from pyalgotrade import strategy
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade.technical import ma


class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument, smaPeriod):
        super(MyStrategy, self).__init__(feed, 1000)
        self.__position = None
        self.__instrument = instrument
        # We'll use adjusted close values instead of regular close values.
        self.setUseAdjustedValues(True)
        self.__sma = ma.SMA(feed[instrument].getPriceDataSeries(), smaPeriod)

    def onEnterOk(self, position):
        execInfo = position.getEntryOrder().getExecutionInfo()
        self.info("BUY at $%.2f" % (execInfo.getPrice()))

    def onEnterCanceled(self, position):
        self.__position = None

    def onExitOk(self, position):
        execInfo = position.getExitOrder().getExecutionInfo()
        self.info("SELL at $%.2f" % (execInfo.getPrice()))
        self.__position = None

    def onExitCanceled(self, position):
        # If the exit was canceled, re-submit it.
        self.__position.exitMarket()

    def onBars(self, bars):
        # Wait for enough bars to be available to calculate a SMA.
        if self.__sma[-1] is None:
            return

        bar = bars[self.__instrument]
        # If a position was not opened, check if we should enter a long position.
        if self.__position is None:
            if bar.getPrice() > self.__sma[-1]:
                # Enter a buy market order for 10 shares. The order is good till canceled.
                self.__position = self.enterLong(self.__instrument, 10, True)
        # Check if we have to exit the position.
        elif bar.getPrice() < self.__sma[-1] and not self.__position.exitActive():
            self.__position.exitMarket()


def run_strategy(smaPeriod):
    # Load the yahoo feed from the CSV file
    feed = yahoofeed.Feed()
    feed.addBarsFromCSV("orcl", "orcl-2000.csv")

    # Evaluate the strategy with the feed.
    myStrategy = MyStrategy(feed, "orcl", smaPeriod)
    myStrategy.run()
    print "Final portfolio value: $%.2f" % myStrategy.getBroker().getEquity()

run_strategy(15)
```

### 业务逻辑概括
1. 创建Feed对象加载回测历史数据
2. 创建策略
3. 将Feed对象传入策略
4. 内部创建Broker对象
5. 在策略中初始化技术指标
6. 运行策略(内部会创建事件循环,依次读取每一个bars数据调用策略逻辑,即onBars函)

### 回测数据 Feed对象
用于承载回测的数据，提供接口访问，驱动整个事件循环。

#### 创建Feed对象

```
# 导入yahoofeed模块
from pyalgotrade.barfeed import yahoofeed


# 创建yahoofeed.Feed类创建其实例
feed = yahoofeed.Feed()

# 通过addBarsFromCSV加载本地csv文件
# 传入股票代码名, 文件路径
feed.addBarsFromCSV("orcl", "orcl-2000.csv")

```
#### Feed对象继承链
![feed-class](img/feed-class.png)

> 注: 由IntelliJ Idea生成

由上图可知, 分别继承不同的BarFeed,最终业务逻辑基类pyalgotrade.observer.subject.

#### Feed数据结构构建过程
主要方法调用顺序如下:

yahooFeed.addBarsFromCSV 

-> csvFeed.BarFeed.addBarsFromCSV 

-> membf.BarFeed.addBarsFromSequence 

-> barfeed.registerInstrument

-> feed.registerDataSeries 

-> barfeed.createDataSeries


#### Feed数据结构
在Feed中有两个比较重要的数据对象
1. self.__bars = {}    
2. self.__ds = BarDataSeries()
其中BarDataSeries对象有以下定义

```
pyalgotrade/pyalgotrade/dataseries/bards.py

class BarDataSeries(dataseries.SequenceDataSeries):
    def __init__(self, maxLen=None):
        super(BarDataSeries, self).__init__(maxLen)
        self.__openDS = dataseries.SequenceDataSeries(maxLen)
        self.__closeDS = dataseries.SequenceDataSeries(maxLen)
        self.__highDS = dataseries.SequenceDataSeries(maxLen)
        self.__lowDS = dataseries.SequenceDataSeries(maxLen)
        self.__volumeDS = dataseries.SequenceDataSeries(maxLen)
        self.__adjCloseDS = dataseries.SequenceDataSeries(maxLen)
        self.__extraDS = {}
        self.__useAdjustedValues = False
```
BarDataSeries提供一系列方法返回相应的数据序列，以getOpenDataSeries为例

```
pyalgotrade/pyalgotrade/dataseries/bards.py:87

    def getOpenDataSeries(self):
        """Returns a :class:`pyalgotrade.dataseries.DataSeries` with the open prices."""
        return self.__openDS
```


而dataseries.SequenceDataSeries对象是一个数据存储在collections.ListDeque对象上，并集成事件监听的类对象.


self.__bars在membf.BarFeed.addBarsFromSequence方法中读取csv文件生成.    
self.__ds在barfeed.createDataSeries方法中创建一个默认长度为1024的BarDataSeries空数据对象.

#### 小结
bar是含有时间, 开盘价, 收盘价, 当日最高价, 当日最低价, 成交量，复权收盘价的数据对象.   

self.__bars是key为股票代码, value是元素为bars数据对象的列表的字典.

self.__ds是BarDataSeries对象


### 事件循环
事件循环是PyalgoTrade的数据引擎，驱动着整个策略运转.

下面是Pyalgotrade内部事件循环的一个简单的实现。 

```
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

output: 
dispatch before.
on Bar: 0
dispatch after
dispatch before.
on Bar: 1
dispatch after
dispatch before.
on Bar: 2
dispatch after
```

上面的代码主要说明策略的onBars方法是怎么被调用的。
> 关于Broker怎么被驱动，在后面讲解
1. 策略中维护一个调度器dispatcher,当策略启动的时候, 调度器dipatcher启动, 并尝试调用feed,broker start方法.
2. 不断调用feed, broker的dispatch方法, 判断是否结束, 如果结束, 则做结束动作, 调用feed, broker的stop方法
3. feed对象在调用dispatch方法的时候, feed对象会触发自身维护的self.__event. 而self.__event在MyStrategy.__init__方法中，通过self.__feed.getNewValueEvent().subscribe(self.__onBars)订阅了MyStrategy.__onBars方法, 所以Feed对象每次dispatch的时候，MyStrategy.__onBars都会被调用.

至此, Feed对象怎么驱动策略的逻辑已经清晰。  
接下来，讲解BaseStrategy, BacktestingStrategy初始化过程


### 策略初始化
策略的继承链并不复杂, 所有策略的基类是BaseStartegy, BacktestingStrategy是提供给用户使用的策略，至少实现onBars函数则可以回测。

BaseStrategy, BacktestingStrategy的初始化源代码如下

```
pyalgotrade/pyalgotrade/strategy/__init__.py

class BaseStartegy(object):
    def __init__(self, barFeed, broker):
        # 绑定barFeed对象
        self.__barFeed = barFeed
        # 绑定broker对象
        self.__broker = broker
        # 交易相关的仓位
        self.__activePositions = set()
        # 订单处理顺序
        self.__orderToPosition = {}
        # bar被处理后的事件
        self.__barsProcessedEvent = observer.Event()
        # analyzer列表
        self.__analyzers = []
        # 命名的analyzer列表
        self.__namedAnalyzers = {}
        # 重新取样的feed对象列表
        self.__resampledBarFeeds = []
        # 调度器对象
        self.__dispatcher = dispatcher.Dispatcher()
        # broker的订单被更新时的事件, 订阅self.__onOrderEvent方法
        self.__broker.getOrderUpdatedEvent().subscribe(self.__onOrderEvent)
        # barfeed值被更新的时候的事件(当barfeed被调度的时候),订阅self.__onBars方法
        self.__barFeed.getNewValuesEvent().subscribe(self.__onBars)

        # 调度器的开始事件，订阅self.onStart方法
        self.__dispatcher.getStartEvent().subscribe(self.onStart)
        # 调度器的空闲事件, 订阅self.__onIdle方法
        self.__dispatcher.getIdleEvent().subscribe(self.__onIdle)

        # 分别将继承了Subject类的broker,barFeed对象加入到调度器的subject列表
        self.__dispatcher.addSubject(self.__broker)
        self.__dispatcher.addSubject(self.__barFeed)

        # 日志级别的初始化
        self.__logger = logger.getLogger(BaseStrategy.LOGGER_NAME)


class BacktestingStrategy(BaseStrategy):
    # 默认初始化一个持有100w现金的虚拟账户
    def __init__(self, barFeed, cash_or_brk=1000000):
        
        # 如果没有传入cash_or_brk参数, 或者传入数值类型的值
        # 则传入cash_or_brk,barFeed对象新建一个backtesting.Broker实例，并调用父类的__init__方法
        # 如果传入的cash_or_brk参数值是backtesting.Broker的实例, 则直接使用
        if isinstance(cash_or_brk, pyalgotrade.broker.Broker):
            broker = cash_or_brk
        else:
            broker = backtesting.Broker(cash_or_brk, barFeed)

        BaseStrategy.__init__(self, barFeed, broker)
        # 默认self.__useAdjustedValue=False
        self.__useAdjustedValues = False
        # 配置日志参数
        self.setUseEventDateTimeInLogs(True)
        self.setDebugMode(True)
```


总的来说真正Strategy对象,barFeed对象,broker对象订阅了更多的事件, 以及更多的判断。但，内核都是调度器驱动着barFeed, broker对象不断的被调度(调用dispatch方法), 而barFeed对象会不断的从self.__bars中取数据追加到self.__ds对象中，并将取出来的数据提交的self.__event中,而self.__event订阅了Strategy.__onBars方法, 所以不断的驱动着Strategy的自定义策略(onBars里面定义的交易逻辑).


### 交易账户 Broker对象
在Strategy对象初始化时候, 会初始化一个虚拟的回测账户.

回测账户broker需要传入barfeed对象, 并在barfeed的event对象里面订阅自己的onBars函数，源码如下:

```
pyalgotrade/pyalgotrade/broker/__init__.py

class Broker(broker.Broker):
    LOGGER_NAME = "broker.backtesting"

    def __init__(self, cash, barFeed, commission=None):
        super(Broker, self).__init__()

        assert(cash >= 0)
        self.__cash = cash
        if commission is None:
            self.__commission = NoCommission()
        else:
            self.__commission = commission
        self.__shares = {}
        self.__activeOrders = {}
        self.__useAdjustedValues = False
        # 持仓策略, 使用DefaultStrategy
        # 使用DefaultStrategy.volumeLimit = 0.25
        # 当交易订单的成交量大于当前bar的成交量的25%则不能成交
        # 没有滑点
        # 没有手续费
        self.__fillStrategy = fillstrategy.DefaultStrategy()
        self.__logger = logger.getLogger(Broker.LOGGER_NAME)

        # 让barfeed对象订阅self.onBars方法
        barFeed.getNewValuesEvent().subscribe(self.onBars)
        self.__barFeed = barFeed
        self.__allowNegativeCash = False
        self.__nextOrderId = 1

```
由上可知，当barFeed对象数据更新的时候，还会调用BackTestBroker.onBars方法.


### 交易仓位 Position对象
当使用enterLong之类交易方法，则会返回一个Postion的对象，这个对象承载着当前各股的持仓比例，以及持有现金.

以enterLong方法说明持仓流程.
1. 实例化一个LongPosition对象
2. 调用broker的createMarketOrder方法创建一个MarketOrder.
3. 注册order, 以便barFeed对象数据驱动的时候，使用该order

以exitMarket方法说明平仓流程.
1. 使用Position对象的exitMarket方法提交平仓订单.
2. 注册order, 以便barFeed对象数据驱动的时候，使用该order

> 源代码调用链太长....所以文字概括.

### 交易订单 Order对象
当我们买入或者卖出的时候，其实是提交一个订单给交易账户(broker), 交易账户会根据交易订单的类型,动作等相关信息执行相关的操作.

> 交易订单的类型参考: https://www.thebalance.com/understanding-stock-orders-3141318

一般有买入(做多), 卖出(做空)两种交易类型, 但是这两种类型成交的方式分别由市价成交, 限价成交.

所以一共由以下四种类型，对应Strategy的四个方法: 
1. enterLong 以市价(下一个Bar的**开盘价**)买入
2. enterLongLimit 当市价(下一个Bar的**开盘价**)低于或等于指定的价格时买入
3. enterShort 与enterLong相反
4. enterShortLimit 与enterLongShort相反.

> 以enter开头是更加上层的方法, 建议使用.

goodTillCanceled为了适配实盘接口, 实盘接口可能有前一天的订单不会再执行的限制，所以设置goodTillCanceled=True保证第二天或者更后的时间，订单依然有效，直至手动取消.


除了提交交易订单还可以提交止损订单, 分别对应Strategy的两个方法.
1. StopOrder 提交一个止损订单, 传入止损价格, 当价格突破止损价位, 以市价成交进行止损.
2. StopLimitOrder 提交一个止损订单, 传入止损价格, 当价格突破止损价位, 并且价格在限定的价格区间才会止损.

> 每个提交的订单会到下一个事件循环才会判断条件是否符合，才会执行.

### 技术指标 EventBasedFilter对象
通过借助自定义指标或者自带的指标，如SMA,EMA,MACD等可以更全面的看待股票的走势以及信号.

下面是技术指标基类的初始化过程.


```
pyalgotrade/pyalgotrade/technical/__init__.py

class EventWindow(object):
    """数据实际承载类
    数据保存在self__values里面
    """
    def __init__(self, windowSize, dtype=float, skipNone=True):
        assert(windowSize > 0)
        assert(isinstance(windowSize, int))
        self.__values = collections.NumPyDeque(windowSize, dtype)
        self.__windowSize = windowSize
        self.__skipNone = skipNone

    
    def onNewValue(self, dateTime, value):
        """提供onNewValue方法将新的值传入"""
        if value is not None or not self.__skipNone:
            self.__values.append(value)

    def getValues(self):
        """获取EventWindows的所有值"""
        return self.__values.data()

    def getWindowSize(self):
        """获取EventWindow Size"""
        return self.__windowSize

    def windowFull(self):
        """eventWindow是否已经填满"""
        return len(self.__values) == self.__windowSize

    def getValue(self):
        """子类须实现的类"""
        raise NotImplementedError()


class EventBasedFilter(dataseries.SequenceDataSeries):
    def __init__(self, dataSeries, eventWindow, maxLen=None):
        super(EventBasedFilter, self).__init__(maxLen)
        self.__dataSeries = dataSeries
        # 当dataseries数据有新值的时候，调用self.__onNewValues方法
        self.__dataSeries.getNewValueEvent().subscribe(self.__onNewValue)
        self.__eventWindow = eventWindow

    def __onNewValue(self, dataSeries, dateTime, value):
        # 让EventWindow对象计算新值
        self.__eventWindow.onNewValue(dateTime, value)
        # 获取计算后的结果
        newValue = self.__eventWindow.getValue()
        # 将值保存到自身实例里面, 即self.__values
        # 因为继承了dataseries.SequenceDataSeries类
        # 而dataseries.SequenceDataSeries父类实现了__getitem__方法, 所以可以使用索引取值.
        self.appendWithDateTime(dateTime, newValue)

    def getDataSeries(self):
        return self.__dataSeries

    def getEventWindow(self):
        return self.__eventWindow
```

在Feed对象初始过程中，会初始化两个比较重要的数据结构, 一个是self.__bars, 一个是self.__ds,在整个事件驱动中, 策略不停的从self__bars中取数据，然后使用appendWithDateTime方法将数据追加的self.__ds里面。
源码如下:

```
pyalgotrade/pyalgotrade/dataseries/bards.py

# 首先调用BarDataSeries的appendWithDateTime方法
class BarDataSeries(dataseries.SequenceDataSeries):
    def appendWithDateTime(self, dateTime, bar):
        assert(dateTime is not None)
        assert(bar is not None)
        bar.setUseAdjustedValue(self.__useAdjustedValues)

        super(BarDataSeries, self).appendWithDateTime(dateTime, bar)

        self.__openDS.appendWithDateTime(dateTime, bar.getOpen())
        self.__closeDS.appendWithDateTime(dateTime, bar.getClose())
        self.__highDS.appendWithDateTime(dateTime, bar.getHigh())
        self.__lowDS.appendWithDateTime(dateTime, bar.getLow())
        self.__volumeDS.appendWithDateTime(dateTime, bar.getVolume())
        self.__adjCloseDS.appendWithDateTime(dateTime, bar.getAdjClose())

        # Process extra columns.
        for name, value in bar.getExtraColumns().iteritems():
            extraDS = self.__getOrCreateExtraDS(name)
            extraDS.appendWithDateTime(dateTime, value)
            
pyalgotrade/dataseries/__init__.py

# 然后调用SequenceDataSeries对象的appendWithDateTime
# 在这个方法中提交数据更新的事件
class SequenceDataSeries(DataSeries):
    def appendWithDateTime(self, dateTime, value):
        """
        Appends a value with an associated datetime.

        .. note::
            If dateTime is not None, it must be greater than the last one.
        """

        if dateTime is not None and len(self.__dateTimes) != 0 and self.__dateTimes[-1] >= dateTime:
            raise Exception("Invalid datetime. It must be bigger than that last one")

        assert(len(self.__values) == len(self.__dateTimes))
        self.__dateTimes.append(dateTime)
        self.__values.append(value)

        self.getNewValueEvent().emit(self, dateTime, value)            
```

#### 小结
使用技术指标需要传入dataSeries对象, 可以通过getPriceDataSeries, getOpenDataSeries等获得.


### 创建策略
由于上面已经有完整版本的代码，这里做一定的删减, 并做注解.

```
# 集成strategy.BacktestingStrategy类
class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument, smaPeriod):
        # 调用父类__init__方法
        super(MyStrategy, self).__init__(feed, 1000)
        # 初始情况下，postion设置为零, postion一般只持仓比例
        self.__position = None
        # 股票代码
        self.__instrument = instrument
        # We'll use adjusted close values instead of regular close values.
        # 是否使用复权收盘价
        self.setUseAdjustedValues(True)
        # 初始化策略指标
        self.__sma = ma.SMA(feed[instrument].getPriceDataSeries(), smaPeriod)

    # 省略其他钩子函数

    # 必须实现的onBars函数,用于买卖的主要逻辑
    def onBars(self, bars):
        # 如果没有简单移动平均值则什么都不做
        if self.__sma[-1] is None:
            return

        # 取出指定股票代码的bar对象
        bar = bars[self.__instrument]
        
        # 如果postion is None，即持仓为0
        if self.__position is None:
            # 如果收盘价大于简单移动平均值则买入
            if bar.getPrice() > self.__sma[-1]:
                # 买入,enterLong=做多
                self.__position = self.enterLong(self.__instrument, 10, True)
        # 反之卖出
        elif bar.getPrice() < self.__sma[-1] and not self.__position.exitActive():
            self.__position.exitMarket()
```



## 总结
BarFeed像是PyalgoTrade中的燃料，不断的供给给策略的Dispatcher调度器, 使整个策略不断运行，直至没有燃料(没有新的数据.)

BarFeed使数据源的一个抽象，里面保存着两个重要的数据结构, self.__bars, self.__ds.

self.__bars是key为股票代码, value是元素为bar数据对象的列表的字典.

self.__ds为BarDataSeries对象.

Broker维护着虚拟账户里面的现金以及相关股票的仓位.接收订单并实时的处理订单, 计算收益等.

Position为股票仓位持有情况的对象, 提供交易的相关接口.

EventBasedFilter为技术指标, 可以计算相关指标如MACD, SMA等, 也可以自定义自己的技术指标.

Strategy为自定义策略,只需实现onBars函数即可完成买卖逻辑, 将Broker,Position相关接口放在Strategy实例方法里面, 同一调用接口.


