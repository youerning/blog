# -*- coding: utf-8 -*-
# @Author: youerning
# @Date:   2019-03-30 12:02:01
# @Last Modified by:   youerning
# @Last Modified time: 2019-03-30 12:43:03
from bs4 import BeautifulSoup
import requests
import logging
import json


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
    "Origin": "https://www.racenet.com.au",
    "Referer": "https://www.racenet.com.au/horse-racing-results/singapore",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 \
                    (KHTML, like Gecko) Chrome/72.0.3626.121 Safari/537.36"
}

base_url = "https://www.racenet.com.au"
entry_url = "https://www.racenet.com.au/horse-racing-results/singapore"
all_race_suffix = "/all-races"
result_url_list_fp = "result_url.json"


def downloader(url):
    logger.debug("request url: %s" % url)
    soup = None
    resp = requests.get(url, headers=headers)
    if resp.ok:
        soup = BeautifulSoup(resp.content)
    else:
        logger.error("request failed")
    return soup


def parse_result_url(soup):
    result_url_lis = soup.select("a.rn-pill")
    if not result_url_lis:
        logger.error("have no any result url")
    else:
        with open(result_url_list_fp, "w") as wf:
            json.dump(result_url_lis, wf, indent=4)

    return result_url_lis


def parse_result(soup):
    pass


def save(data):
    pass


def fetcher():
    result_url_lis = downloader(entry_url)
    for result_url in result_url_lis:
        result_url_parsed = base_url + result_url + all_race_suffix
        race_resp_soup = downloader(result_url_parsed)
        if not race_resp_soup:
            return

        data_lis = parse_result(race_resp_soup)
        for data in data_lis:
            yield data


def main():
    data_gen = fetcher()
    for data in data_gen:
        save(data)


if __name__ == '__main__':
    init_log()
    main()
