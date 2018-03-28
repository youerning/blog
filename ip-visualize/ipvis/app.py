#coding:utf-8
from __future__ import print_function
from flask import Flask
from flask import render_template
from flask import jsonify
from flask import send_file
from collections import defaultdict, Counter
from functools import lru_cache
import geoip2.database
import re

app = Flask(__name__)


@lru_cache(maxsize=512)
def get_coord(ip):
    """
    return coord of ip

    returns:
        longitude, latitude
    """
    try:
        resp = reader.city(ip)
    except Exception as e:
        print("the ip is bad: {}".format(ip))
        print("=" * 30)
        print(e)
        return False, False
    return resp.location.longitude, resp.location.latitude


@lru_cache(maxsize=512)
def get_info(ip):
    """
    return info of ip

    Returns:
        city, country, sourceCoord, destCoord
    """
    try:
        resp = reader.city(ip)
        city = resp.city.name
        if not city:
            city = "unknow"
        country = resp.country.names["zh-CN"]
        if not country:
            country = "unknow"
    except Exception as e:
        print("the ip is bad: {}".format(ip))
        print("=" * 30)
        print(e)
        return False

    sourceCoord = [resp.location.longitude, resp.location.latitude]
    return city, country, sourceCoord, destCoord


@app.route('/p1')
def p1():
    return render_template("line.html")


@app.route('/p2')
def p2():
    return render_template("bar.html")


@app.route('/test')
def test():
    return render_template("test.html")


@app.route('/<path:path>')
def static_file(path):
    # print(path)
    return send_file("static/img/world.jpg")


@app.route("/data")
def data():
    from glob import glob

    # dict of return
    ret = {}

    # 创建ip列表
    ip_lis = list()

    # files of logs
    files = glob("logs/*")

    # complie regex
    pat = "\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}"
    ipfind = re.compile(pat)

    # extract ip from  every file
    for logfile in files:
        with open(logfile) as fp:
            # 通过循环每次读取日志一行,如果日志量大建议以下方式，日志文件不大，可以直接readlines，一次性全部读取出来
            # 如果太大则用readline一行一行的读

            lines = fp.readlines()
            for line in lines:
                if len(line.strip()) < 1:
                    continue
                ip = ipfind.findall(line)
                if ip:
                    ip = ip[0]
                    ip_lis.append(ip)

    # 利用Counter数据结构对所有ip信息计数
    # 结构如下
    # [
    # 'ipCount', [ latitude, longitude, magnitude, latitude, longitude, magnitude, ... ]
    # ]
    ip_counter = Counter(ip_lis)

    # 获取IP数据的统计信息
    ip_count = []
    for ip, count in ip_counter.items():
        ip_longitude, ip_latitude = get_coord(ip)
        if not ip_longitude:
            continue
        ip_count.extend([ip_latitude, ip_longitude, count / 100])

    # 获取IP数据源Top10
    # 格式如下
    # [[ip, count], [ip, count], ...]
    ip_top = ip_counter.most_common(10)

    # 获取所有IP地址相关信息,[city, country, sourceCoord, destCoord]
    ipinfo_lis = [get_info(ip) for ip in ip_lis]
    # 去除获取失败的IP
    ipinfo_lis = [info for info in ipinfo_lis if info]
    groupByCountry = defaultdict(list)

    # 将得到的IP信息按照国家名分组.
    for ipinfo in ipinfo_lis:
        country = ipinfo[1]
        groupByCountry[country].append([ipinfo[2], ipinfo[3]])

    ret["ipInfoFields"] = ["city", "country", "longitude", "latitude"]
    # groupByCountry: {
    # "contryname": [
    # [
    # [
    # sourceLongitude,
    # sourceLatitude
    # ],
    # [
    # destLongitude,
    # destLatitude
    # ]
    ret["ipTopFields"] = ["ip", "count"]
    ret["groupByCountryFields"] = ["country"]
    ret["ipCountFields"] = []
    ret["ipInfo"] = ipinfo_lis
    ret["groupByCountry"] = groupByCountry
    ret["ipCount"] = [["ipCount", ip_count]]
    ret["ipTop"] = ip_top

    return jsonify(ret)


@app.route("/realtime")
def realtime():
    pass


if __name__ == '__main__':
    reader = geoip2.database.Reader("GeoLite2-City.mmdb")
    # 这里将下面的IP作为所有路径的终点
    destIP = "14.215.177.38"
    resp = reader.city(destIP)
    destCoord = [resp.location.longitude, resp.location.latitude]

    app.run(debug=True, host="0.0.0.0", port=80)
