# -*- coding: UTF-8 -*-
# @author youerning
# @email 673125641@qq.com

import sys
import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import tushare as ts
# pip install mplfinance
from mplfinance.original_flavor import candlestick_ohlc 
from matplotlib.pylab import date2num
from glob import glob
from os import path
from datetime import timedelta


# ggplot好看点
mpl.style.use("ggplot")

DATE_FORMAT = "%Y%m%d"
TS_TOKEN = "<你的Token>"
ts.set_token(TS_TOKEN)
pro = ts.pro_api(TS_TOKEN)


def ohlc_plot(df, ax=None):
    if ax is None:
        ax = plt.gca()

    data_lst = []
    for date, row in df.iterrows():
        t = date2num(date)
        data = (t, ) + tuple(row)
        data_lst.append(data)

    candlestick_ohlc(ax, data_lst, colorup="r", colordown="green", alpha=0.7, width=0.8)
    ax.xaxis_date()
    return ax

def load_all_local_data(data_path, tail_size=None):
    glob_pattern = path.join(data_path, "*.csv")
    # print(glob_pattern)
    files = glob(glob_pattern)
    
    ret = {}
    for fp in files:
        fname = path.basename(fp)
        ts_code = fname.split("-")[0]
        df = pd.read_csv(fp, index_col="trade_date", parse_dates=["trade_date"])
        if tail_size:
            df = df.tail(tail_size)
        ret[ts_code] = df

    return ret

def cos(vector_a, vector_b):
    vector_a = np.mat(vector_a)
    vector_b = np.mat(vector_b)
    num = float(vector_a * vector_b.T)
    denom = np.linalg.norm(vector_a) * np.linalg.norm(vector_b)
    cos = num / denom
    return cos

def select_doji():
    # fp = "by_ts_code/600249.SH-.csv"
    fp = "by_ts_code/300130.SZ-.csv"
    df = pd.read_csv(fp, index_col="trade_date", parse_dates=["trade_date"])
    df = df[["open", "high", "low", "close"]]
    
    # k线数量
    k_size = 6

    # 起始幅度大小
    treand_threshold = 0.025

    # 长实体最小长度
    entity_length_threshold = 0.025
    # 长实体上下最大影线长度
    entity_shadow_line_length_threshold = 0.03

    # 十字星实体长度最大长度
    doji_entity_length_threshold = 0.015
    # 十字星上下影线长度最小长度
    # doji_shadow_line_length_threshold = 0.005

    trend_map = {1: "向上", -1: "向下"}

    def up_or_down_trend(row):
        """1代表向上, -1代表向下, 0代表震荡"""
        first = row[0]
        last = row[-1]

        if all(first > row[1:]) and first > (last * treand_threshold):
            return -1
        elif all(first < row[1:]) and last > (first * treand_threshold):
            return 1
        else:
            return 0

    df["trend"] = df.close.rolling(k_size).apply(up_or_down_trend, raw=True)
    df.fillna(value=0, inplace=True)

    def k_sharp(k):
        """返回k线的上下影线长度, 实体长度"""
        open_, high, low, close = k[:4]
        if open_ > close:
            upper_line_length = (high - open_) / high
            lower_line_length = (close - low) / close
            entity_length = (open_ - close) / open_
        else:
            upper_line_length = (high - close) / high
            lower_line_length = (open_ - low) / open_
            entity_length = (close - open_) / close

        return upper_line_length, lower_line_length, entity_length

    def is_up_or_down_doji(k_lst, trend):
        # open, high, low, close
        if len(k_lst) != 3:
            sys.exit("判断十字星需要三根K线")

        is_ok = False
        k1, k2, k3 = k_lst

        # 判断是否跳空
        # 通过high, close过于严格      
        if trend > 0:
            # 趋势向上时,最低点是否大于两个实体的最高价
            if k2[0] < k1[1] or k2[0] < k3[1]:
            # if k2[0] < k1[1] :
                return is_ok
        else:
            # 趋势向下时,最高点是否小于两个实体的最高价
            if k2[0] > k1[2] or k2[0] > k3[2]:
                return is_ok 

        k1_sharp = k_sharp(k1)
        # print("k1 sharp")
        # print(k1_sharp)
        # 判断是否为长实体
        if (k1_sharp[2] < entity_length_threshold 
            or k1_sharp[0] > entity_shadow_line_length_threshold 
            or k1_sharp[1] > entity_shadow_line_length_threshold):
            return is_ok

        k3_sharp = k_sharp(k3)
        # print("k3 sharp")        
        # print(k3_sharp)
        if (k3_sharp[2] < entity_length_threshold 
            or k3_sharp[0] > entity_shadow_line_length_threshold 
            or k3_sharp[1] > entity_shadow_line_length_threshold):
            return is_ok

        # print("ok")
        # 判断是否为十字星
        k2_sharp = k_sharp(k2)
        # print("k2 sharp")        
        # print(k2_sharp)
        # 实体长度不超过0.2%, 上下影线长度超过0.6%, 如果规定上下影线的长度不太好找
        # if (k2_sharp[2] > doji_entity_length_threshold
        #     or k2_sharp[0] < doji_shadow_line_length_threshold
        #     or k2_sharp[1] < doji_shadow_line_length_threshold):
        
        if k2_sharp[2] > doji_entity_length_threshold:
            return is_ok

        return True

    df_values = df.values
    ret = []

    for index in range(len(df_values)):
        if index < k_size:
            continue
        
        trend = df_values[index - 1][-1]
        if trend == 0:
            continue

        val_slice = slice(index-2, index+1)
        k_lst = df_values[val_slice]
        if is_up_or_down_doji(k_lst, trend):
            ret.append(index-1)
            print("在>>%s<<<找到趋势为[%s]的十字星" % (df.index[index-1], trend_map[trend]))

    if not ret:
        print("没有发现任何十字星")
    
    ax = ohlc_plot(df[["open", "high", "low", "close"]])
    for i in ret:
        # print(i)
        mark_x = df.index[i]
        # mark_y = df.loc[mark_x].low
        # print(mark_x, mark_y)
        ax.axvline(mark_x)
    plt.show()

    return ret

def select_by_amount(data_path, top_size=20):
    # 或许交易日比较好
    day_range = 100

    all_df = load_all_local_data(data_path, tail_size=day_range)
    ret = []
    for ts_code, df in all_df.items():
        df["amount_avg"] = df.amount.rolling(day_range).mean()
        amount_avg = df["amount_avg"][-1]

        # NaN的布尔值为True, 所以需要np.isnan判断
        if np.isnan(amount_avg):
            continue

        ret.append((ts_code, amount_avg))

    ret.sort(key=lambda x:x[1])
    print("交易额排名前%s的结果如下" % top_size)
    print(ret[-top_size:])
    return ret[-top_size:]

def select_by_float_market_value(trade_date, top_size=20):
    df = pro.daily_basic(ts_code='', trade_date=trade_date, fields="ts_code,close,float_share")

    ret = []
    for row in df.values:
        ts_code = row[0]
        float_market_value = row[1] * row[2]

        if np.isnan(float_market_value) or not float_market_value:
            continue
        
        ret.append((ts_code, float_market_value))

    ret.sort(key=lambda x:x[1])
    print("流通市值名前%s的结果如下" % top_size)
    print(ret[-top_size:])
    return ret[-top_size:]

def select_by_similarity(data_path, code_name, top_size=10):
    day_range = 100
    # 交易日的起始截至时间做大不能超过这个间隔
    max_delta = timedelta(days=7)

    all_df = load_all_local_data(data_path, tail_size=day_range)
    # code_name = "000001.SZ"
    if code_name not in all_df:
        print("要比对的股票不在当前下载的股票数据中")

    vector_a = all_df[code_name].pct_chg
    start_date_a = vector_a.index[0]
    end_date_a = vector_a.index[-1]

    ret = []
    for ts_code, df in all_df.items():
        if ts_code == code_name:
            continue

        if len(df) < 100:
            print("股票[%s]交易日不足%s" % (ts_code, day_range))
            continue

        vector_b = df.pct_chg
        start_date_b = vector_b.index[0]
        end_date_b = vector_b.index[-1]

        # 计算开始结束交易日之间的时间间隔
        start_delta = abs(start_date_a - start_date_b)
        end_delta = abs(end_date_a - end_date_b)
        if start_delta > max_delta or end_delta > max_delta:
            print("股票[%s]与股票[%s]交易日间隔过大!" % (ts_code, code_name))
            continue

        cos_similarity = cos(vector_a, vector_b)
        ret.append((ts_code, cos_similarity))

    ret.sort(key=lambda x:x[1])
    print("相似度前%s的结果如下" % top_size)
    print(ret[-top_size:])

    print("最不相似的股票前%s的结果如下:" % top_size)
    print(ret[:top_size])
    return ret[-top_size:]

def select_by_trend(data_path, code_name, ma_lst=None):
    fp = path.join(data_path, ("%s-.csv" % code_name))
    if not path.exists(fp):
        print("股票[%s]不存在本地数据" % code_name)
 
    df = pd.read_csv(fp, index_col="trade_date", parse_dates=["trade_date"])
    ohlc_columns = ["open", "high", "low", "close"]
    df = df[ohlc_columns]

    if ma_lst is None:
        ma_lst = [5, 20, 60, 120, 220]
        
    max_ma = max(ma_lst)
    ma_name_lst = []
    for ma in ma_lst:
        ma_name = "ma_%s" % ma
        ma_name_lst.append(ma_name)
        df[ma_name] = df.close.rolling(ma).mean()

    # 设置图片大小
    plt.figure(figsize=(10,6))

    # 过滤掉没有最长均线数据的交易日
    df2 = df.iloc[max_ma:]

    # 绘制k线图
    ax = ohlc_plot(df2[ohlc_columns])

    # 绘制均线图
    df2[ma_name_lst].plot(ax=ax)
    plt.savefig("ma.png")
    plt.show()


def select_by_nobody(data_path, code_name, ma_lst=None, threshold=20, atr_period=14, diff_ma=20):
    fp = path.join(data_path, ("%s-.csv" % code_name))
    if not path.exists(fp):
        print("股票[%s]不存在本地数据" % code_name)
 
    df = pd.read_csv(fp, index_col="trade_date", parse_dates=["trade_date"])
    ohlc_columns = ["open", "high", "low", "close"]
    df = df[ohlc_columns]

    if ma_lst is None:
        ma_lst = [5, 20, 60, 120, 220]
        
    max_ma = max(ma_lst)
    # 计算均线
    ma_name_lst = []
    for ma in ma_lst:
        ma_name = "ma%s" % ma
        ma_name_lst.append(ma_name)
        df[ma_name] = df.close.rolling(ma).mean()

    # 默认以20日最高价作为上突破阈值, 20日最低价作为下突破阈值
    threshold_high_name = "threshold_high%s" % threshold
    threshold_low_name = "threshold_low%s" % threshold
    df[threshold_high_name] = df.high.rolling(threshold).max()
    df[threshold_low_name] = df.low.rolling(threshold).min()


    # 默认atr的计算时间范围是14天
    # talib一般通过包装好的whl包安装
    # 参考: https://www.lfd.uci.edu/~gohlke/pythonlibs/
    import talib
    atr_name = "atr%s" % atr_period
    df[atr_name] = talib.ATR(df.high, df.low, df.close, atr_period)

    # 默认计算乖离率收盘价与20日均线的差值, 然后将这个差值比上收盘价, 这个值被称为乖离率
    # 通过乖离率可以观察收盘价与均值之间的差异，差异越大则可能回弹的概率比较大
    if diff_ma not in ma_lst:
        ma_name = "ma%s" % diff_ma
        df[ma_name] = df.close.rolling(ma).mean()

    diff_name = "diff%s" % diff_ma
    df[diff_name] = (df["close"] - df[ma_name]) / df["close"]

    # 设置图片大小
    plt.figure(figsize=(10,18))

    # 配置子图
    ax1 = plt.subplot(311)
    ax2 = plt.subplot(312)
    ax3 = plt.subplot(313)

    # 过滤掉没有最长均线数据的交易日
    df2 = df.iloc[max_ma:]

    # 绘制k线图
    ohlc_plot(df2[ohlc_columns], ax1)

    # 绘制均线图
    df2[ma_name_lst].plot(ax=ax1)

    # 绘制上下最高最低突破线
    df2[[threshold_high_name, threshold_low_name]].plot(ax=ax1)

    # 绘制atr
    df2[atr_name].plot(ax=ax2)

    # 绘制乖离率
    df2[diff_name].plot(ax=ax3)

    plt.savefig("nobody.png")
    plt.show()


if __name__ == "__main__":
    # select_doji()
    # select_by_amount("by_trade_date")
    # select_by_float_market_value("20200522")
    # select_by_similarity("by_trade_date", "000001.SZ")
    # select_by_trend("by_trade_date", "000001.SZ")
    select_by_nobody("by_trade_date", "000001.SZ")
    # pass    
