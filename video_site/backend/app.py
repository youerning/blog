# -*- coding: UTF-8 -*-
# @author youerning
# @email 673125641@qq.com

import logging
from typing import List

from fastapi import FastAPI, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from db import collection


LOG_LEVEL = logging.DEBUG
logger = logging.getLogger(__name__)
fmt = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
console_handler = logging.StreamHandler()
console_handler.setFormatter(fmt)
logger.addHandler(console_handler)

logger.setLevel(LOG_LEVEL)
console_handler.setLevel(LOG_LEVEL)


with open("index.html", encoding="utf8") as rf:
    html = rf.read()

app = FastAPI(
    title="Simple Video APP Backend",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory="static"), name="static")

origins = [
    "http://localhost",
    "http://localhost:8080",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 响应数据结构
class ResponseModel(BaseModel):
    data: list

class SuccessResponseModel(ResponseModel):
    status: str = "ok"

class ErrorResponseModel(BaseModel):
    status: str = "error"
    msg: str


def parse_vod_urls(video: dict) -> list:
    vod_url = video.pop("vod_url", "")
    vod_links = []

    if not vod_url:
        logger.warning("the content of video[{}] is not vaild".format(video["_id"]))
        return vod_links

    name_urls = vod_url.split("\r\n")
    for name_url in name_urls:
        name, url = name_url.split("$")
        vod_links.append({"name": name, "url": url})

    return vod_links


@app.get("/", response_class=HTMLResponse)
def index_page():
    return html


@app.get("/api/search",
    status_code=200,
    response_model=SuccessResponseModel,
    response_model_exclude_none=True,
    responses={501: {"model": ErrorResponseModel}})
async def search(q: str = Query(..., title="query", description="The name of the video you want to search", max_length=30)):
    data = await collection.find({"vod_name": {"$regex": ".*{}.*".format(q)}}).to_list(10)
    for video in data:
        video["vod_links"] = parse_vod_urls(video)
    return SuccessResponseModel(data=data)


@app.post("/api/videos/",
    status_code=200,
    response_model=SuccessResponseModel,
    response_model_exclude_none=True,
    responses={501: {"model": ErrorResponseModel}})
async def search_videos(video_ids: List[str] = Body(..., embed=True)):
    video_ids = list(set(video_ids))[:10]
    data = await collection.find({"_id": {"$in": video_ids}}).to_list(10)
    for video in data:
        video["vod_links"] = parse_vod_urls(video)
    return SuccessResponseModel(data=data)


@app.get("/api/videos/{video_id}",
    status_code=200,
    response_model=SuccessResponseModel,
    response_model_exclude_none=True,
    responses={501: {"model": ErrorResponseModel}, 400: {"model": ErrorResponseModel}})
async def search_video(video_id: str):
    data = await collection.find_one({"_id": video_id})
    if not data:
        return JSONResponse(status_code=400, content={"msg": "video id do not exists"})

    data["vod_links"] = parse_vod_urls(data)
    return SuccessResponseModel(data=[data])