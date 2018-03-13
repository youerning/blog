# coding: utf-8
from __future__ import print_function
import pandas as pd
from pyalgotrade import strategy
from pyalgotrade.technical import ma
from pyalgotrade.barfeed import yahoofeed
from pyalgotrade import plotter
from pyalgotrade.stratanalyzer import returns
from pyalgotrade.stratanalyzer import drawdown
from pyalgotrade.stratanalyzer import trades
from pyalgotrade.broker import backtesting


class MyStrategy(strategy.BacktestingStrategy):
    def __init__(self, feed, instrument):
        super(MyStrategy, self).__init__(feed, 1000000)
        self.__broker = self.getBroker()
        self.__broker.setCommission(backtesting.TradePercentage(0.0005))
        self.__instrument = instrument
        self.__position = None
        # self.setUseAdjustedValues(True)
        self.__prices = feed[instrument].getPriceDataSeries()
        self.__sma10 = ma.SMA(self.__prices, 10)
        self.__sma25 = ma.SMA(self.__prices, 25)

    def getSMA10(self):
        return self.__sma10

    def getSMA25(self):
        return self.__sma25

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

        if self.__position is None:
            one = bar.getPrice() * 100
            oneUnit = account // one
            if oneUnit > 0 and self.__sma10[-1] > self.__sma25[-1]:
                self.__position = self.enterLong(self.__instrument, oneUnit * 100, True)
        elif self.__sma10[-1] < self.__sma25[-1] and not self.__position.exitActive():
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

    # add sma 10 dataseries to plot
    plt.getInstrumentSubplot(code).addDataSeries("SMA10", myStrategy.getSMA10())

    # add sma 10 dataseries to plot
    plt.getInstrumentSubplot(code).addDataSeries("SMA25", myStrategy.getSMA25())

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
    import os
    download_dir = "download"
    result_dir = "result"
    result_path = "strategy_sma.csv"
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
    import os
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

