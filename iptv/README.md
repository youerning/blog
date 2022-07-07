# 打造属于自己的IPTV直播源

> 免责声明: 所有资源来源于网络，并不实际存储任何资源，也不参与任何与该片相关的视频录制、剪辑、上传。若无意中触及到了版权方利益，请及时给本文留言，笔者会即使删除相关资源。
> 
> 本文及代码仅用于教育及实验目的。

由于众所周知的原因，电视上不能直接观看电视节目的直播，需要额外买一个电视盒子用于播放，但是这样就多了一套遥控器和系统，有点麻烦并且占地方，所以是否可以通过安装一个APP来解决这个问题呢。但，也是因为众所周知的原因，也没有可以一直使用的APP, 即使有，也属于不合法，随时有被封的可能。

因此，我想看看是否能自己收集一份直播源自己用。

## 万能的交友站

如果自己去收集这些资源，显然有些麻烦，所以先看看交友网站有没有相关资源。然后得到了下面这个代码库。

[GitHub - iptv-org/iptv: Collection of publicly available IPTV channels from all over the world](https://github.com/iptv-org/iptv)

这个仓库收集了全球的直播资源。

但是本人只需要中国的，所以找到以下链接:

`https://iptv-org.github.io/iptv/countries/cn.m3u`

> 这个m3u8列表有950个左右的资源，并且包含了对应的电子节目单。

这个m3u8播放列表虽然资源丰富，但是有两个问题

- 很多资源可能播放不了

- 资源列表访问不了

针对这两问题可以有以下解决办法

### 资源播放不了的问题

这个可能是地域限制或者资源失效了，所以在导入前最好将资源列表全部检查以便，将不能播放的资源过滤掉，这个过滤的过程要放在本地进行，不能放在云主机，或者不用用来播放资源的网络环境中进行，否则会导致过滤的列表还是有不能播放的情况。

这个工作自然需要用代码来解决。

### 资源列表访问不了的问题

第一个解决办法是通过一些方法将链接对应的资源保存成文件，然后在iptv 应用中通过打开文件的方式导入，但是这会引入新的问题，就是无法更新资源。

第二个解决办法是通过梯子或者路由层面的梯子，让电视或者手机能够快速的访问这些链接，这样就可以时常的同步最新的资源列表。

第三个解决办法是本人选择的方法，通过一个代理的方式将资源映射到国内能访问的地方，这样就能时刻的更新了，这个方法在后面的代码部分会说明。

当然了，还有许多方法，这里就不一一列举了。

## 用代码自动化

> python >= 3.7

其实即使过滤掉几乎一般的资源之后，还有四百多个资源，所以我们可以根据自己的喜好对这些列表排一下序，或者过滤掉一些节目列表。

下面是要过滤的资源列表的片段

```m3u8
#EXTM3U x-tvg-url="https://iptv-org.github.io/epg/guides/ao/guide.dstv.com.epg.xml,https://iptv-org.github.io/epg/guides/ar/mi.tv.epg.xml,https://iptv-org.github.io/epg/guides/bf/canalplus-afrique.com.epg.xml,https://iptv-org.github.io/epg/guides/bi/startimestv.com.epg.xml,https://iptv-org.github.io/epg/guides/bo/comteco.com.bo.epg.xml,https://iptv-org.github.io/epg/guides/br/mi.tv.epg.xml,https://iptv-org.github.io/epg/guides/cn/tv.cctv.com.epg.xml,https://iptv-org.github.io/epg/guides/cz/m.tv.sms.cz.epg.xml,https://iptv-org.github.io/epg/guides/dk/allente.se.epg.xml,https://iptv-org.github.io/epg/guides/fr/chaines-tv.orange.fr.epg.xml,https://iptv-org.github.io/epg/guides/ga/startimestv.com.epg.xml,https://iptv-org.github.io/epg/guides/gr/cosmote.gr.epg.xml,https://iptv-org.github.io/epg/guides/hk-en/nowplayer.now.com.epg.xml,https://iptv-org.github.io/epg/guides/id-en/mncvision.id.epg.xml,https://iptv-org.github.io/epg/guides/it/guidatv.sky.it.epg.xml,https://iptv-org.github.io/epg/guides/my/astro.com.my.epg.xml,https://iptv-org.github.io/epg/guides/ng/dstv.com.epg.xml,https://iptv-org.github.io/epg/guides/nl/delta.nl.epg.xml,https://iptv-org.github.io/epg/guides/tr/digiturk.com.tr.epg.xml,https://iptv-org.github.io/epg/guides/uk/bt.com.epg.xml,https://iptv-org.github.io/epg/guides/us-pluto/i.mjh.nz.epg.xml,https://iptv-org.github.io/epg/guides/us/tvtv.us.epg.xml,https://iptv-org.github.io/epg/guides/za/guide.dstv.com.epg.xml"
#EXTINF:-1 tvg-id="AlJazeeraEnglish.qa" tvg-country="INT" tvg-language="English" tvg-logo="https://upload.wikimedia.org/wikipedia/en/thumb/f/f2/Aljazeera_eng.svg/512px-Aljazeera_eng.svg.png" group-title="News",Al Jazeera English (1080p)
https://live-hls-web-aje.getaj.net/AJE/index.m3u8
#EXTINF:-1 tvg-id="BabyTV.uk" tvg-country="INT" tvg-language="English" tvg-logo="https://upload.wikimedia.org/wikipedia/en/4/45/BabyTV.png" group-title="Kids" user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",Baby TV Asia (Vietnamese dub) (1080p)
#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36
https://livecdn.fptplay.net/hda3/babytvhd_vhls.smil/chunklist.m3u8
#EXTINF:-1 tvg-id="BBCEarthAsia.uk" tvg-country="ASIA" tvg-language="Chinese;English;Thai;Vietnamese" tvg-logo="https://i.imgur.com/xXM60fa.png" group-title="Undefined" user-agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36",BBC Earth (Vietnamese dub) (1080p)
#EXTVLCOPT:http-user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36
https://livecdn.fptplay.net/hda2/bbcearth_vhls.smil/chunklist.m3u8
```

`#EXTM3U`这一行作为文件头声明m3u8文件格式以及引用一些电子节目单，通过这个电子节目单你就可以在播放列表中看到对应资源会显示当前播放的节目。

`#EXTIN` 这一行是直播资源的相关信息，比如语言，节目名等。
`#EXTVLCOPT` 似乎可以用来指定user-agent, 并不是每一个资源都有。

`http://`或`https://`开头的行就是具体的播放资源链接了。

### 异步编程

因为async, await关键字的引入，是的python的异步编程变得十分容易，也有很多异步库可以使用，笔者比较喜欢异步，比多线程要优雅。

#### info对象

每个资源可以抽象成两部分，header和url。

所以使用 `namedtuple`将其抽象成一个整体，便于后面使用。

```python
# 这里score是为了排序
Info = namedtuple("Info", ["header", "url", "score"])



# 将m3u8文件解析成一串的info列表
# 这里的data就是m3u8文件的文本内容
url_start_index = data.index("#EXTINF")
index_header = data[:url_start_index]
infos = []
header = []
url = ""
for line in data[url_start_index:].splitlines():
    if line.startswith("#"):
        header.append(line)
    elif line.startswith("http"):
        url = line
    else:
        raise ValueError(f"未知的m3u8格式: {line}")

    if url:
        header = "\n".join(header)
        infos.append(Info(header, url, 0))
        header = []
        url = ""
```

#### 检测链接是否有用

```python
async def test(sess: aiohttp.ClientSession, info: Info) -> bool:
    try:
        async with sess.get(info.url, headers={"User-Agent": ua()}) as resp:
            if resp.ok:
                return True
    except Exception:
        logger.debug(f"播放地址无效: {info.url}")
        return Falseasync def test(sess: aiohttp.ClientSession, info: Info) -> bool:
    try:
        async with sess.get(info.url, headers={"User-Agent": ua()}) as resp:
            if resp.ok:
                return True
    except Exception:
        logger.debug(f"播放地址无效: {info.url}")
        return False
```

检测连接是否有用只需要检测是否能够在指定时间得到响应且状态码ok即为可用。

#### user-agent列表

一个反反爬的小技巧就是设置user-agent，设置user-agent的方式有很多，这里直接从一个地方复制一个列表然后随机选择即可。

```python
# 复制自https://gist.github.com/pzb/b4b6f57144aea7827ae4
from random import choice

ua_list = [
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.94 Chrome/37.0.2062.94 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    # 代码中复制了100个左右
]

def ua() -> str:
    return choice(ua_list)
```

#### 替换英文分类

由于这个仓库的作者可能是外国人，所以关于中国的分类也是用的中文，所以为了更易于自己使用，将分类替换成中文。

```python
gorup_title_map = {
    'group-title="Undefined"': 'group-title="未定义"',
    'group-title="Entertainment"': 'group-title="娱乐"',
    'group-title="Movies"': 'group-title="电影"',
    'group-title="Science"': 'group-title="科技"',
    'group-title="Kids"': 'group-title="儿童"',
    'group-title="Business"': 'group-title="商业"',
    'group-title="Sports"': 'group-title="体育"',
    'group-title="Lifestyle"': 'group-title="生活时尚"',
    'group-title="Culture"': 'group-title="文化"',
    'group-title="Culture;News"': 'group-title="文化与新闻"',
    'group-title="Classic"': 'group-title="经典"',
    'group-title="Religious"': 'group-title="宗教"',
    'group-title="Documentary"': 'group-title="纪录片"',
    'group-title="News"': 'group-title="新闻"',
    'group-title="General"': 'group-title="综合"',
    'group-title="Education"': 'group-title="教育"',
    'group-title="Music"':  'group-title="音乐"'
}

def replace(info: Info):
    for k, v in gorup_title_map.items():
        if k in info.header:
            header: str = info.header
            header = header.replace(k ,v)
            info = info._replace(header=header)
            break
    return info
```

#### 排序

根据自己的喜好将列表大致排一个序。

```python
# 分值越小，排名越靠前
score_map: Dict[str, int] = {
    "卫视": -1,
    "CCTV": -1,
    "湖南卫视": -2,
    "浙江卫视": -1,
    "江苏卫视": -1,
    "浙江卫视": -1,
}

def score(info: Info):
    for k, v in score_map.items():
        if k in info.header:
            info = info._replace(score=info.score + v)
    return info
```

#### 保存结果

```python
# 保存文件到本地
with open("new_cn.m3u8", "w", encoding="utf8") as wf:
    wf.write(content)

# 保存文件到云上
deta = Deta("你的deta project key")
drive = deta.Drive("iptv")
```

关于deta相关的部分就不赘述了，自行搜索吧。

### 完整代码

```python
from collections import namedtuple
from datetime import datetime
import math
import asyncio
import logging

from typing import List, Tuple, Dict
from random import choice

import aiohttp
import typer
from deta import Deta
from bs4 import BeautifulSoup

app = typer.Typer()
# 复制自https://gist.github.com/pzb/b4b6f57144aea7827ae4
ua_list = [
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/37.0.2062.94 Chrome/37.0.2062.94 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/45.0.2454.85 Safari/537.36',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; Trident/7.0; rv:11.0) like Gecko',
    'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:40.0) Gecko/20100101 Firefox/40.0',
]

logger = logging.getLogger("iptv-checker")
Info = namedtuple("Info", ["header", "url", "score"])

gorup_title_map = {
    'group-title="Undefined"': 'group-title="未定义"',
    'group-title="Entertainment"': 'group-title="娱乐"',
    'group-title="Movies"': 'group-title="电影"',
    'group-title="Science"': 'group-title="科技"',
    'group-title="Kids"': 'group-title="儿童"',
    'group-title="Business"': 'group-title="商业"',
    'group-title="Sports"': 'group-title="体育"',
    'group-title="Lifestyle"': 'group-title="生活时尚"',
    'group-title="Culture"': 'group-title="文化"',
    'group-title="Culture;News"': 'group-title="文化与新闻"',
    'group-title="Classic"': 'group-title="经典"',
    'group-title="Religious"': 'group-title="宗教"',
    'group-title="Documentary"': 'group-title="纪录片"',
    'group-title="News"': 'group-title="新闻"',
    'group-title="General"': 'group-title="综合"',
    'group-title="Education"': 'group-title="教育"',
    'group-title="Music"':  'group-title="音乐"'
}

score_map: Dict[str, int] = {
    "卫视": -1,
    "CCTV": -1,
    "湖南卫视": -2,
    "浙江卫视": -1,
    "江苏卫视": -1,
    "浙江卫视": -1,
}

header_tpl = '#EXTINF:-1 tvg-id="" tvg-country="CN" tvg-language="" tvg-logo="" group-title="未定义",{name}'

def ua() -> str:
    return choice(ua_list)

def score(info: Info):
    for k, v in score_map.items():
        if k in info.header:
            info = info._replace(score=info.score + v)
    return info

def filters(info) -> bool:
    return True

def replace(info: Info):
    for k, v in gorup_title_map.items():
        if k in info.header:
            header: str = info.header
            header = header.replace(k ,v)
            info = info._replace(header=header)
            break
    return info

async def test(sess: aiohttp.ClientSession, info: Info) -> bool:
    try:
        async with sess.get(info.url, headers={"User-Agent": ua()}) as resp:
            if resp.ok:
                return True
    except Exception:
        logger.debug(f"播放地址无效: {info.url}")
        return False


async def checker(urls: List[Info], timeout: int = 2) -> List[Info]:
    new_infos = []
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(timeout)) as sess:
        for url in urls:
            ok = await test(sess, url)
            if ok:
                new_infos.append(url)
    return new_infos


async def crawl() -> List[Info]:
    source_url = "http://m.hunanweishi.tv/"
    infos = []
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(5)) as sess:
            async with sess.get(source_url, headers={"User-Agent": ua()}) as resp:
                soup = BeautifulSoup(await resp.text(encoding="gb2312"), "lxml")
                options = soup.select("div#playbox option")
                for opt in options:
                    url = opt.attrs["value"]
                    header = header_tpl.format(name="湖南卫视")
                    infos.append(Info(header, url, -10))
                return infos
    except Exception as exc:
        logger.debug(f"请求{source_url}失败: " + str(exc))


async def run(index_timeout, index_url, timeout, workers) -> Tuple[str, List[Info]]:
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(index_timeout)) as sess:
            resp = await sess.get(index_url)
            data = await resp.text()
    except Exception:
        msg = typer.style("下载播放播放源失败", fg=typer.colors.WHITE, bg=typer.colors.RED)
        typer.echo(msg, err=True)
        raise

    url_start_index = data.index("#EXTINF")
    index_header = data[:url_start_index]
    infos = []
    header = []
    url = ""
    for line in data[url_start_index:].splitlines():
        if line.startswith("#"):
            header.append(line)
        elif line.startswith("http"):
            url = line
        else:
            raise ValueError(f"未知的m3u8格式: {line}")

        if url:
            header = "\n".join(header)
            infos.append(Info(header, url, 0))
            header = []
            url = ""

    logger.debug(f"一共有{len(infos)}条播放地址")
    step = math.ceil(len(infos) / workers)
    futures = []
    # infos = infos[:10]
    for i in range(workers):
        _infos = infos[i*step:(i+1)*step]
        # 如果workers大于infos数量就会出现空列表
        if _infos:
            futures.append(asyncio.ensure_future(checker(_infos, timeout)))

    ret = await asyncio.wait(futures)
    # print(ret)
    infos: List[Info] = [i for task in ret[0] for i in task.result()]
    return index_header, infos

@app.command()
def main(
    index_timeout: int = typer.Option(30, help="访问播放源的超时时间(秒)"),
    index_url: str = typer.Option("https://iptv-org.github.io/iptv/countries/cn.m3u", help="iptv地址播放源的url"),
    timeout: int = typer.Option(2, help="每个测试url地址的超时时间(秒)"),
    workers: int = typer.Option(32, help="工作进程数"),
    verbose: int = typer.Option(0, "--verbose", "-v", count=True)
):
    log_level = 50 - 10 * verbose
    if log_level < 0:
        log_level = 10
    logging.basicConfig(level=log_level, format="%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
    loop = asyncio.get_event_loop()
    start = datetime.now()
    logger.debug("开始检测")
    end = datetime.now()
    index_header, infos = loop.run_until_complete(run(index_timeout, index_url, timeout, workers))
    logger.debug(f"检测花费时间: {end - start}")

    logger.debug(f"检测之后有{len(infos)}条新播放地址")
    new_infos = []
    for info in infos:
        info = score(info)
        info = replace(info)
        if not filters(info):
            continue
        new_infos.append(info)

    new_infos.sort(key=lambda info:info.score)
    other_infos = loop.run_until_complete(crawl())
    if other_infos:
        new_infos = other_infos + new_infos

    lines = [f"{i.header}\n{i.url}" for i in new_infos]
    index_header = index_header.replace("https://iptv-org.github.io/epg", "https://youer-iptv.deta.dev/epg")
    content = index_header + "\n".join(lines)
    with open("new_cn.m3u8", "w", encoding="utf8") as wf:
        wf.write(content)

    deta = Deta("你的 deta project key")
    drive = deta.Drive("iptv")
    drive.put("cn.m3u8", content.encode("utf8"))


if __name__ == "__main__":
    app()
```

### 代理

由于交友网站在国内访问效率不是很快，所以在deta上部署一个代理

```python
import aiohttp
from deta import Deta
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse


app = FastAPI()
deta = Deta("你的 project key")
drive = deta.Drive("iptv")


real_endpoint_prefix = "https://iptv-org.github.io/epg/"
sess: aiohttp.ClientSession = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10))


@app.on_event("startup")
def startup():
    global sess
    # deta不会调用startup 似乎
    sess = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(10))

@app.on_event("shutdown")
def shutdown():
    sess.close()

@app.get("/cn")
async def index():
    content = drive.get("cn.m3u8")
    if not content:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="没有数据")
    return PlainTextResponse(content=content.read(), media_type="audio/x-mpegurl")

@app.get("/epg/{path:path}")
async def proxy(path):
    try:
        async with sess.get(real_endpoint_prefix + path) as resp:
            content = await resp.text()
            return PlainTextResponse(content=content, media_type="application/xml")
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="代理请求失败: " + str(exc)) from exc
```

大家可以访问: https://youer-iptv.deta.dev/cn 这个是本文的测试链接，不保证后续可用。

## 总结

 一个脚本用来过滤并保存到本地(如果你有deta账号的话，还保存到线上)。

一个deta的微服务用来代理资源，并且暴露最新过滤的资源列表，用于不断更新列表。

本人在深圳测试这些资源，发现都有一点卡顿，可能跟地域有关，所以在脚本里面还去自己爬了一个某卫视的资源，这个资源比较流畅。

> 代码地址: https://github.com/youerning/blog/iptv/src