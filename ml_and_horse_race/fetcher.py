# -*- coding: utf-8 -*-
# @Author: youerning
# @Date:   2019-03-30 12:02:01
# @Last Modified by:   youerning
# @Last Modified time: 2019-03-31 10:57:10
import requests
import logging
import sys
import sqlite3
import re
from datetime import datetime
from bs4 import BeautifulSoup


def init_db():
    global conn
    conn = sqlite3.connect('data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS DATA
           (ID CHAR(30) PRIMARY KEY     NOT NULL,
           DATE         CHAR(20)    NOT NULL,
           LOCATION     CHAR(30) NOT NULL,
           LENGTH       INT     NOT NULL,
           TRACK        CHAR(30) NOT NULL,
           TRACK_TYPE   CHAR(30),
           TRACK_STATUS CHAR(30)     NOT NULL,
           RACE_NUM     INT     NOT NULL,
           H_NO         INT     NOT NULL,
           HORSE_NAME   CHAR(30)     NOT NULL,
           GEAR         CHAR(30),
           HORSE_RATING INT     NOT NULL,
           H_WT         REAL     NOT NULL,
           HCP_WT       REAL     NOT NULL,
           C_WT         REAL     NOT NULL,
           BAR          INT     NOT NULL,
           JOCKEY       CHAR(30)     NOT NULL,
           TRAINER      CHAR(30)     NOT NULL,
           RUNING_POSITION   CHAR(10)     NOT NULL,
           PI           INT     NOT NULL,
           TOTAL_SECONDS     INT,
           LBW          REAL     NOT NULL
           );''')
    # TIME: TOTAL MILLOSECONDS
    conn.commit()


def output_csv():
    import pandas as pd

    df = pd.read_sql("SELECT * FROM DATA", conn, index_col="ID", parse_dates=["DATE"])
    df.to_csv()


def init_log():
    global logger
    logger = logging.getLogger("horse_race")
    logger.setLevel(level=logging.DEBUG)
    handler = logging.FileHandler("horse_race.log")
    handler.setLevel(logging.DEBUG)

    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    ch = logging.StreamHandler()
    ch.setLevel(logging.DEBUG)
    ch.setFormatter(formatter)
    logger.addHandler(ch)


headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "Accept-Encoding": "gzip, deflate",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,ja;q=0.7,zh-TW;q=0.6",
    "Cache-Control": "max-age=0",
    "Connection": "keep-alive",
    "Host": "cn.turfclub.com.sg",
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"
}

proxies = None
if sys.platform.startswith("win"):
    proxies = {"http": "http://127.0.0.1:1080/"}


base_url = "http://cn.turfclub.com.sg/Racing/Pages/ViewRaceResult/%s/All"
# manually check
current_number = 8375
dt_format = "%d/%m/%Y"
race_pattern = re.compile(r".(\d+).+")


class FakeResp:
    pass


def download(url, test=False):
    logger.debug("request url: %s" % url)
    soup = None
    if test:
        resp = FakeResp()
        resp.ok = True
        resp.content = open("test3.html", encoding="utf8").read()
    else:
        if proxies:
            resp = requests.get(url, headers=headers, proxies=proxies)
        else:
            resp = requests.get(url, headers=headers, proxies=proxies)
    if resp.ok:
        soup = BeautifulSoup(resp.content, "lxml")
    else:
        logger.error("request failed")
        logger.error("error code: %s" % resp.status_code)
    return soup


def try_float(data):
    ret = 0
    try:
        ret = float(data)
    except Exception as e:
        pass
    return ret


def try_int(data):
    ret = 0
    try:
        ret = int(data)
    except Exception as e:
        pass
    return ret


def parse_result(soup):
    date_header = soup.select_one(".STC_Cell_Padding")
    if date_header:
        date_header = date_header.text
    else:
        logger.info("have no table")
        return
    date_header_split = date_header.split("-")
    if len(date_header_split) != 2:
        logger.info("location is not 新加坡")
        return
    location, date = date_header_split
    location = location.strip()
    if location != "新加坡":
        logger.info("location is not 新加坡")
        return
    date = date.strip()
    date = datetime.strptime(date, dt_format)
    date_str = date.strftime("%Y-%m-%d")

    table_lst = soup.select(".STC_Table_Tab")
    for table in table_lst:
        header = table.select_one(".STC_Label_Header").text
        header_split = header.split(" - ")
        if len(header_split) < 2:
            return
        # print("header: %s" % header)
        labels = table.select(".STC_Label_Normal")[1].text.split()
        if len(labels) < 2:
            logger.info("have no label")
            continue
        track_status = labels[1]
        race_info = header_split[0].split()
        track_info = header_split[1].split()
        if "第" in header:
            length = try_int(track_info[0][:-1])
            if length == 0:
                logger.info("cann't parse length")
                continue
            track = track_info[1]
            track_type = track_info[2]
            # race_num = int(race_info[0][1:-1])
            race_num = int(re.findall(race_pattern, race_info[0])[0])

        elif "RACE" in header:
            length = try_int(track_info[0][:-1])
            if length == 0:
                logger.info("cann't parse length")
                continue
            track = "unkonw"
            track_type = track_info[1]
            race_str = race_info[1].split(":")
            race_num = int(race_str[0])
        else:
          continue

        table_table = table.select_one("table.STC_Gdv")
        table_table_rows = table_table.select("tr")
        race_data = []
        for row in table_table_rows[1:]:
            row_td_lst = row.select("td")
            col_length = len(row_td_lst)
            td_lst = []

            for row_td in row_td_lst:
                td_lst.append(row_td.text.strip())

            if col_length == 11:
                td_lst_tmp = [0] * 14
                td_lst_tmp[0] = td_lst[0]
                td_lst_tmp[1] = td_lst[1]
                # td_lst_tmp[2] = 
                td_lst_tmp[3] = td_lst[2]
                td_lst_tmp[4] = td_lst[3]
                td_lst_tmp[5] = td_lst[4]
                td_lst_tmp[6] = td_lst[5]
                td_lst_tmp[7] = td_lst[6]
                td_lst_tmp[8] = td_lst[7]
                td_lst_tmp[9] = td_lst[8]
                # td_lst_tmp[10] = td_lst[0]
                td_lst_tmp[11] = td_lst[9]
                td_lst_tmp[12] = 0
                td_lst_tmp[13] = td_lst[10]
                td_lst = td_lst_tmp

            td_lst[0] = try_int(td_lst[0])
            td_lst[3] = try_float(td_lst[3])
            td_lst[4] = try_float(td_lst[4])
            td_lst[5] = try_float(td_lst[5])
            td_lst[6] = try_float(td_lst[6])
            td_lst[7] = try_int(td_lst[7])
            td_lst[11] = try_int(td_lst[11])
            # 或许时间一样，所以加上名称/100, 用于排序
            if td_lst[12]:
                dt_lst = td_lst[12].split(":")
                td_lst[12] = int(dt_lst[0]) * 60 + float(dt_lst[1]) + td_lst[11] / 100
            else:
                td_lst[12] = 0
            td_lst[13] = float(td_lst[13])
            bar = td_lst[7]
            rank = td_lst[11]

            data_id = "-".join([date_str, str(race_num), str(bar), str(rank)])
            data = [data_id, date_str, location, length, track,  
                    track_type, track_status, race_num, *td_lst]
            race_data.append(data)

        yield race_data


def save(table_data):
    cursor = conn.cursor()

    for data in table_data:
        sql_tpl = ("INSERT INTO DATA (ID,DATE,LOCATION,LENGTH,TRACK,"
              "TRACK_TYPE,TRACK_STATUS,RACE_NUM,H_NO,HORSE_NAME,GEAR,"
              "HORSE_RATING, H_WT, HCP_WT, C_WT, BAR, JOCKEY, TRAINER,"
              "RUNING_POSITION, PI, TOTAL_SECONDS, LBW)"
              "VALUES ('%s', '%s', '%s', %d, '%s', '%s','%s', %d, %d,"
              "\"%s\", '%s', %f, %f, %f, %f, %d,\"%s\",\"%s\",'%s', %d, %f, %f)")
        # print(data)
        sql = sql_tpl % tuple(data)
        try:
          cursor.execute(sql)
        except Exception as e:
          # print(e)
          print(sql)
          raise e

    conn.commit()


def fetcher():
    break_point = ".break_point"
    start_num = 1
    with open(break_point) as rf:
        content = rf.read().strip()
        if content.isdigit():
          start_num = int(content) + 1

    logger.info("start from last break point: %s" % start_num)
    for num in range(start_num, current_number + 1):
        url = base_url % num
        # soup = download(url, test=True)
        soup = download(url)
        if not soup:
            break
        data_gen = parse_result(soup)
        for table_data in data_gen:
            yield table_data

        with open(break_point, "w") as wf:
            wf.write(str(num))
        # break


def main():
    data_gen = fetcher()
    for data in data_gen:
        save(data)
    conn.close()


if __name__ == '__main__':
    init_log()
    init_db()
    main()
