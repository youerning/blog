#coding: utf-8
from __future__ import print_function
from multiprocessing.dummy import Pool
import tushare as ts
import random
import os
import json
import datetime
import glob
# import numpy as np


code_file = "code_lis.json"
# cache_file = "cache.json"
download_path = "download"


def choose_code(num=300):
    """分别从中小板，沪深300中随机选择相等数量的股票代码，默认分别选择150个

    Args:
        num: 股票的选择数量，默认为300

    Returns:
        返回随机选择的股票列表
    """
    if not os.path.exists(code_file):
        json.dump([], open(code_file, "w"))

    if os.path.exists(code_file):
        lis = json.load(open(code_file))
        if len(lis) == num:
            return lis

    # 最终股票代码列表
    code_lis = []

    # 获取中小板数据
    zxb_df = ts.get_gem_classified()
    zxb_lis = list(zxb_df.code)

    # 获取沪深三百
    hs300_df = ts.get_hs300s()
    hs300_lis = list(hs300_df.code)

    # 依次从中小板，沪深300中随机选取 num/2支股票代码
    zxb_rand = random.sample(zxb_lis, int(num / 2))
    hs300_rand = random.sample(hs300_lis, int(num / 2))

    # 保存到code_lis并保存
    code_lis.extend(zxb_rand)
    code_lis.extend(hs300_rand)
    with open(code_file, "w") as wf:
        json.dump(code_lis, wf)

    return code_lis


def download(code, years=7):
    """下载指定股票代码的历史数据到本地, 文件名为<code>.csv, 默认下载7年的数据

    Args:
        code: 股票代码，例如000001
        years: 至今多少年的行情数据

    Returns:
        None

    """

    # 存储路径
    save_path = os.path.join(download_path, "{}.csv".format(code))
    # 判断之前是否下载过
    if os.path.exists(save_path):
        print("{} 已下载".format(code))
        return

    now = datetime.datetime.now()
    start_time = now - datetime.timedelta(days=years * 365)
    start = start_time.strftime("%Y-%m-%d")

    try:
        print("{} 正在下载".format(code))
        df = ts.get_k_data(code, start=start)
        print("{} 下载完成".format(code))
    except Exception as e:
        print("{} 下载失败".format(code))
        return

    if len(df) < 1:
        print("{} 下载失败".format(code))
        return

    # 新建Adj Close字段
    df["Adj Close"] = df.close

    # 将tushare下的数据的字段保存为pyalgotrade所要求的数据格式
    df.columns = ["Date", "Open", "Close", "High", "Low", "Volume", "code", "Adj Close"]

    # 将数据保存成本地csv文件
    df.to_csv(save_path, index=False)


def statistics():
    """统计download目录下面有多少下载了的股票

    Args:
        None

    Returns:
        None
    """
    if not os.path.exists(download_path):
        os.mkdir(download_path)
        print("{}目录下并无已下载的股票".format(download_path))
        return

    csv_path = os.path.join(download_path, "*.csv")
    csv_files = glob.glob(csv_path)
    if len(csv_files) > 0:
        print("download目录下一共有{}文件".format(len(csv_files)))


def main():
    # if not os.path.exists(cache_file):
    #     cache_lis = []
    # else:
    #     cache_lis = json.load(cache_file, open(cache_file))
    code_lis = choose_code()
    if not os.path.exists(download_path):
        os.mkdir(download_path)
    pool = Pool(4)
    pool.map(download, code_lis)
    pool.close()
    pool.join()
    statistics()


def test():
    code_lis = choose_code()
    if not os.path.exists(download_path):
        os.mkdir(download_path)
    download(code_lis[0])
    statistics()


if __name__ == '__main__':
    # test()
    main()

