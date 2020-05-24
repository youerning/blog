# -*- coding: utf-8 -*-
# @Author: youerning
# @Email: 673125641@qq.com

# 下载日线数据
import tushare as ts
import pandas as pd
import time
import os
import sys
import traceback
from functools import partial
from datetime import datetime
from datetime import timedelta
from os import path
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import concurrent.futures as futures


DATE_FORMAT = "%Y%m%d"
TS_TOKEN = "<你的Token>"
ts.set_token(TS_TOKEN)
pro = ts.pro_api(TS_TOKEN)


def retry(fn, max_retry=3, sleep_init=14):
    """简单的retry函数"""
    count = 1
    while count < max_retry:
        count += 1
        try:
            return fn()
        except Exception as e:
            # traceback.print_exc("")
            # 等待时间递增
            time_sleep = sleep_init * count + 1
            print("遇到异常%s, 在%s秒后再次尝试第%s次" % (e, time_sleep, count))
            time.sleep(time_sleep)

def save_to_csv(ret, data_path="stock"):
    if not path.exists(data_path):
        # 如果父不存在不会报错
        os.makedirs(data_path)

    for ts_code, df in ret.items():
        fname = "-".join([ts_code, ".csv"])
        fp = path.join(data_path, fname)

        df.to_csv(fp, index=False)


def download_by_trade_date(start_date, end_date, data_path="by_trade_date", worker_size=2, debug=False):
    """
    通过交易日来遍历时间范围内的数据，当交易日的个数小于股票的数量时，效率较高.
    
    一年一般220个交易日左右，但是股票却有3800多个，那么通过交易日来下载数据就高效的多了
    """
    now = datetime.now()
    start_time = now
    try:
        start_date_ = datetime.strptime(start_date, DATE_FORMAT)
        end_date_ = datetime.strptime(end_date, DATE_FORMAT)
        
        if end_date_ < start_date_:
            sys.exit("起始时间应该大于结束时间")

        if start_date_ > now:
            sys.exit("起始时间应该大于当前时间")            

        if end_date_ > now:
            end_date = now.strftime(DATE_FORMAT)

    except Exception:
        traceback.print_exc("")
        sys.exit("传入的start_date[%s]或end_date[%s]时间格式不正确, 格式应该像20200101" % (start_date, end_date))

    # 获取交易日历
    try:
        trade_cal = pro.trade_cal(exchange="SSE", is_open="1", 
                                    start_date=start_date, 
                                    end_date=end_date,
                                    fields="cal_date")
    except Exception:
        sys.exit("获取交易日历失败")

    trade_date_lst = trade_cal.cal_date
    pool = ThreadPoolExecutor(max_workers=worker_size)
    print("准备开始获取 %s到%s 的股票数据" % (start_date, end_date))

    def worker(trade_date):
        # 用偏函数包装一下
        # pro = ts.pro_api(TS_TOKEN)
        fn = partial(pro.daily, trade_date=trade_date)
        return retry(fn)

    # 最终保存到一个列表中
    ret = defaultdict(list)
    # future 列表
    fs_lst = []

    # 通过线程并发获取数据
    for trade_date in trade_date_lst:
        # print(trade_date)
        # 这里不使用pool.map的原因是, map返回的future列表会乱序
        # submit的位置参数不需要需要放到可迭代对象里面(一般是元组), 卧槽。。。
        fs = pool.submit(worker, trade_date)
        fs_lst.append(fs)
        # break

    # *****************************
    # 获取每个交易日的股票数据
    # *****************************
    for trade_date, fs in zip(trade_date_lst, fs_lst):
        if debug:
            print("开始获取交易日[%s]的数据" % trade_date)

        # 如果有异常或者结果为空的话
        if fs.exception() or not isinstance(fs.result(), pd.DataFrame):
            print(fs.exception())
            sys.exit("在交易日[%s]超过重试最大的次数也没有获取到数据" % trade_date)

        day_df = fs.result()
        columns = day_df.columns
        # 遍历一个交易日的所有股票数据
        # print(datetime.now())
        # 遍历day_df.values 大概2ms 
        # 2 ms ± 63.2 µs per loop (mean ± std. dev. of 7 runs, 1000 loops each)
        # 遍历day_df.iterrows() 大概285ms
        # 285 ms ± 2.64 ms per loop (mean ± std. dev. of 7 runs, 1 loop each)
        for row in day_df.values:
            ts_code = row[0]

            ret[ts_code].append(row)
        
        # print(datetime.now())
    
    merge_start_time = datetime.now()
    new_ret = {}
    for key, value in ret.items():
        new_ret[key] = pd.DataFrame(value, columns=columns) 
    merge_end_time = datetime.now()
    # 组合[series...] 需要142ms
    # 142 ms ± 1.12 ms per loop (mean ± std. dev. of 7 runs, 10 loops each)
    # 组合[array....] 需要6.56ms
    # 6.56 ms ± 66.9 µs per loop (mean ± std. dev. of 7 runs, 100 loops each)
    print("合并共花费时间: %s" % (merge_end_time - merge_start_time))
    # *****************************
    # 获取将结果保存到本地的csv文件中
    # *****************************
    print("数据已经获取完毕准备保存到本地")
    save_to_csv(new_ret, data_path=data_path)
    end_time = datetime.now()
    print("*****************************")
    print("下载完成, 共花费时间%s" % (end_time - start_time))
    print("*****************************")


def download_by_ts_code(start_date, end_date, data_path="by_ts_code", debug=False, worker_size=3):
    """因为按股票代码的方式实在太慢了(如果你宽带速度比较快的话), 也就没必要多线程了"""
    now = datetime.now()
    start_time = now
    try:
        start_date_ = datetime.strptime(start_date, DATE_FORMAT)
        end_date_ = datetime.strptime(end_date, DATE_FORMAT)
        
        if end_date_ < start_date_:
            sys.exit("起始时间应该大于结束时间")

        if start_date_ > now:
            sys.exit("起始时间应该大于当前时间")

        if end_date_ > now:
            end_date = now.strftime(DATE_FORMAT)

    except Exception:
        traceback.print_exc("")
        sys.exit("传入的start_date[%s]或end_date[%s]时间格式不正确, 格式应该像20200101" % (start_date, end_date))
    
    def worker(ts_code):
        fn = partial(ts.pro_bar, ts_code=ts_code, adj='qfq', start_date=start_date, end_date=end_date)
        return retry(fn)

    pool = ThreadPoolExecutor(max_workers=worker_size)
    print("准备开始获取 %s到%s 的股票数据" % (start_date, end_date))
    # 不指定任何参数会获取5000条最近的数据，ts_code会重复
    day = pro.daily()

    # 固定顺序，set是无法包装有序的
    all_ts_code = list(set(day.ts_code))
    fs_lst = []

    for ts_code in all_ts_code:
        fs_lst.append(pool.submit(worker, ts_code))
        # break

    for ts_code, fs in zip(all_ts_code, fs_lst):
        # 如果有异常或者结果为空的话
        if fs.exception() or not isinstance(fs.result(), pd.DataFrame):
            print(fs.exception())
            sys.exit("在股票[%s]超过重试最大的次数也没有获取到数据" % ts_code)

        df = fs.result()
        # %timeit df.sort_index()
        # 192 µs ± 3.73 µs per loop (mean ± std. dev. of 7 runs, 10000 loops each)

        # %timeit df.sort_index(inplace=True)
        # 2.54 µs ± 177 ns per loop (mean ± std. dev. of 7 runs, 100000 loops each)
        df.sort_index(inplace=True, ascending=False)

        if not isinstance(df, pd.DataFrame):
            sys.exit("在股票[%s]超过重试最大的次数也没有获取到数据" % ts_code)

        save_to_csv({ts_code: df}, data_path=data_path)
        if debug:
            print("股票[%s]历史数据下载保存完成" % ts_code)

        
        
    end_time = datetime.now()
    print("*****************************")
    print("下载完成, 共花费时间%s" % (end_time - start_time))
    print("*****************************")


if __name__ == '__main__':
    now = datetime.now()
    start_date = "20160101"
    # start_date = "20200101"
    end_date = now.strftime(DATE_FORMAT)
    download_by_trade_date(start_date, end_date, worker_size=4)
    # download_by_ts_code(start_date, end_date, debug=True)
    # download()
    # test_worker()
