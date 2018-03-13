# coding: utf-8
from __future__ import print_function
import os
import pandas as pd
import collections
from pyalgotrade import technical
from pyalgotrade import strategy
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade import plotter
from pyalgotrade.stratanalyzer import returns
from pyalgotrade.stratanalyzer import drawdown
from pyalgotrade.stratanalyzer import trades
from pyalgotrade.broker import backtesting


class CustomEventWindow(object):
    """An EventWindow class is responsible for making calculation over a moving window of values.

    :param windowSize: The size of the window. Must be greater than 0.
    :type windowSize: int.

    .. note::
        This is a base class and should not be used directly.
    """

    def __init__(self, windowSize):
        assert(windowSize > 0)
        assert(isinstance(windowSize, int))
        self.__values = collections.deque([], windowSize)
        self.__windowSize = windowSize

    def onNewValue(self, dateTime, value):
        self.__values.append(value)

    def getValues(self):
        return self.__values

    def getWindowSize(self):
        """Returns the window size."""
        return self.__windowSize

    def windowFull(self):
        return len(self.__values) == self.__windowSize

    def getValue(self):
        """Override to calculate a value using the values in the window."""
        raise NotImplementedError()


class DualEventWindow(CustomEventWindow):
    def __init__(self, period):
        assert(period > 0)
        super(DualEventWindow, self).__init__(period)
        self.__value = None

    def _calculateTrueRange(self, value):
        ret = None
        values = self.getValues()
        HH = max([bar.getHigh() for bar in values])
        LC = min([bar.getClose() for bar in values])
        HC = max([bar.getClose() for bar in values])
        LL = min([bar.getLow() for bar in values])
        ret = max((HH - LC), (HC - LL))
        return ret

    def onNewValue(self, dateTime, value):
        super(DualEventWindow, self).onNewValue(dateTime, value)

        if self.windowFull():
            self.__value = self._calculateTrueRange(value)

    def getValue(self):
        return self.__value


class Dual(technical.EventBasedFilter):
    def __init__(self, bardataSeries, period=15, maxLen=None):
        super(Dual, self).__init__(bardataSeries, DualEventWindow(period), maxLen)


class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument):
        super(MyStrategy, self).__init__(feed, 1000000)
        self.__broker = self.getBroker()
        self.__broker.setCommission(backtesting.TradePercentage(0.0005))
        self.__instrument = instrument
        self.__position = None
        # self.setUseAdjustedValues(True)
        self.__k = 0.08
        self.__bars = feed[self.__instrument]
        self.__dual = Dual(self.__bars)

    def onEnterCanceled(self, position):
        self.__position = None

    def onEnterOk(self, position):
        # execInfo = position.getEntryOrder().getExecutionInfo()
        # self.info("BUY at $%.2f" % (execInfo.getPrice()))
        pass

    def onExitOk(self, position):
        # execInfo = position.getExitOrder().getExecutionInfo()
        # self.info("SELL at $%.2f" % (execInfo.getPrice()))
        self.__position = None

    def onExitCanceled(self, position):
        # If the exit was canceled, re-submit it.
        self.__position.exitMarket()

    def onBars(self, bars):
        account = self.getBroker().getCash()
        bar = bars[self.__instrument]
        if self.__position is None and self.__dual[-1] is not None:
            current_price = bar.getClose()
            open_price = bar.getOpen()
            buy_line = open_price + (self.__k * self.__dual[-1])

            one = bar.getPrice() * 100
            oneUnit = account // one
            if oneUnit > 0 and current_price > buy_line:
                self.__position = self.enterLong(self.__instrument, oneUnit * 100, True)
        elif self.__position is not None and not self.__position.exitActive() and self.__dual[-1] is not None:
            current_price = bar.getClose()
            open_price = bar.getOpen()
            sell_line = open_price - (self.__k * self.__dual[-1])

            one = bar.getPrice() * 100
            oneUnit = account // one
            if current_price < sell_line:
                self.__position.exitMarket()


def runStrategy(code, csv_file, stdout=False):
    feed = yahoofeed.Feed()
    # feed.addBarsFromCSV("000001", "download\\000001.csv")

    feed.addBarsFromCSV(code, csv_file)
    myStrategy = MyStrategy(feed, code)

    # init analyzers
    returnsAnalyzer = returns.Returns()
    drawDownAnalyzer = drawdown.DrawDown()
    tradesAnalyzer = trades.Trades()

    # attach analyzers
    myStrategy.attachAnalyzer(returnsAnalyzer)
    myStrategy.attachAnalyzer(drawDownAnalyzer)
    myStrategy.attachAnalyzer(tradesAnalyzer)

    # add subplot to plot
    plt = plotter.StrategyPlotter(myStrategy)

    # create returns subplot
    plt.getOrCreateSubplot("returns").addDataSeries("Simple returns", returnsAnalyzer.getReturns())

    myStrategy.run()
    result = myStrategy.getResult()
    cumReturn = returnsAnalyzer.getCumulativeReturns()[-1] * 100
    maxDrawdown = drawDownAnalyzer.getMaxDrawDown() * 100
    tradeCount = tradesAnalyzer.getCount()

    if stdout:
        print("Total trades: %d" % tradeCount)
        print("Final portfolio value: $%.2f" % result)
        print("Cumulative returns: %.2f %%" % cumReturn)
        print("Max. drawdown: %.2f %%" % maxDrawdown)
        plt.plot()

    return cumReturn, maxDrawdown, tradeCount


def main():
    from glob import glob
    download_dir = "download"
    result_dir = "result"
    result_path = "strategy_dual_trust.csv"
    if not os.path.exists("result"):
        os.mkdir(result_dir)

    ret_dict = {"code": [], "start": [], "end": [], "cum return": [], "max drawdown": [], "trade count": []}
    csvs_path = os.path.join(download_dir, "*csv")
    csv_lis = glob(csvs_path)
    for csv in csv_lis:
        csv_file = csv
        df = pd.read_csv(csv)
        startTime = df.Date.iloc[0]
        endTime = df.Date.iloc[-1]
        code = os.path.basename(csv)[:6]
        cumReturn, maxDrawdown, tradeCount = runStrategy(code, csv_file)
        ret_dict["code"].append(code)
        ret_dict["start"].append(startTime)
        ret_dict["end"].append(endTime)
        ret_dict["cum return"].append(cumReturn)
        ret_dict["max drawdown"].append(maxDrawdown)
        ret_dict["trade count"].append(tradeCount)

    result_path = os.path.join(result_dir, result_path)
    ret_df = pd.DataFrame(ret_dict)
    ret_df.to_csv(result_path, index=False)


def test():
    from glob import glob
    download_path = "download"
    csvs_path = os.path.join(download_path, "*csv")
    csv_lis = glob(csvs_path)
    code = os.path.basename(csv_lis[0])[:6]
    csv_file = csv_lis[0]
    df = pd.read_csv(csv_file)
    startTime = df.Date.iloc[0]
    endTime = df.Date.iloc[-1]
    print("start at %s" % startTime)
    runStrategy(code, csv_file, stdout=True)
    print("end at %s" % endTime)


if __name__ == '__main__':
    # test()
    main()

