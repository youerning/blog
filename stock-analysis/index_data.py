#coding: utf-8
"""查看上证指数"""
import datetime
import pandas as pd
import tushare as ts
import matplotlib.pyplot as plt


now = datetime.datetime.now()
start_time = now - datetime.timedelta(days=7 * 365)
start = start_time.strftime("%Y-%m-%d")

df = ts.get_k_data("000001", start=start, index=True)
df.index = pd.to_datetime(df.date)
df.close.plot(grid=True)
plt.show()
