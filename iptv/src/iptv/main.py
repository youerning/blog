

import aiohttp
from deta import Deta
from fastapi import FastAPI, HTTPException, status
from fastapi.responses import PlainTextResponse


app = FastAPI()
deta = Deta("a058rcve_itN3A1yk19dh69NwbwrU1YUjPuBCvRs5")
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