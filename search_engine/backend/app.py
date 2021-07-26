import json
import math
import logging
from glob import glob
from typing import List, Optional, Union, Tuple
from collections import defaultdict
from functools import lru_cache

import jieba
from fastapi import FastAPI, HTTPException, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field


LOG_LEVEL = logging.DEBUG
logger = logging.getLogger(__name__)
fmt = logging.Formatter("%(asctime)s - %(filename)s[line:%(lineno)d] - %(levelname)s: %(message)s")
console_handler = logging.StreamHandler()
console_handler.setFormatter(fmt)
logger.addHandler(console_handler)

logger.setLevel(LOG_LEVEL)
console_handler.setLevel(LOG_LEVEL)


# 测试时不使用所有数据
# files = glob("ChineseLyrics/test.jsonx")
files = glob("ChineseLyrics/*.json")

docs = []
for file in files:
    with open(file, encoding="utf8") as rf:
        data = json.load(rf)
        for doc in data:
            # 将歌词的文本列表转换成一个字符串
            lyric = "".join(doc["lyric"])
            # 去除特殊符号
            lyric = "".join(filter(str.isalnum, lyric))
            # 分词
            lyric2 = list(jieba.cut_for_search(lyric))
            doc["lyric2"] = lyric2

        docs.extend(data)

index = defaultdict(set)
for doc_index, doc in enumerate(docs):
    for word in doc["lyric2"]:
        index[word].add(doc_index)


def tf(word: str, doc_index: List[str], docs: List[dict]) -> float:
    return docs[doc_index]["lyric2"].count(word) / len(docs[doc_index]["lyric2"])

@lru_cache()
# 因为参数需要哈希缓存，所以docs, index不放在参数中传递了
def idf(word: str) -> float:
    # 多少文档包含word
    doc_included = len(index.get(word, []))
    return math.log(doc_included / len(docs))

def tf_idf(word: str, doc_index: List[str], docs: List[List[str]], index: List[dict]) -> float:
    return tf(word, doc_index, docs) * idf(word)


def full_text_search(keywords: List[str], docs: List[dict], index: dict) -> List[Tuple]:
    doc_indexs = list()
    for keyword in keywords:
        doc_indexs.extend(index.get(keyword, []))

    if not doc_indexs:
        return []

    # 所有包含关键字的doc_index去重
    doc_indexs = set(doc_indexs)

    scores = []
    for doc_index in doc_indexs:
        keywords_scores = []

        for keyword in keywords:
            score = tf_idf(keyword, doc_index, docs, index)
            keywords_scores.append(score)

        scores.append((doc_index, sum(keywords_scores)))

    return sorted(scores, key=lambda x:x[1], reverse=True)



app = FastAPI(
    title="Simple Full-text search engine",
    version="1.0.0",
)


# 请求数据结构
class SearchPayload(BaseModel):
    query: List[str]
    size: int = Field(10, le=100, gt=0, description="The query size must be greater than zero")


exmaples = {
    "one keyword": {
        "summary": "A normal example",
        "description": "search one keyword",
        "value": {
            "query": ["梦想"]
        },
    },
    "two keyword": {
        "summary": "A normal example",
        "description": "search one keyword",
        "value": {
            "query": ["梦想", "美丽"]
        },
    },
    "invalid data type": {
        "summary": "Invalid data is rejected with an error",
        "value": {
             "query": "梦想"
        },
    },
    "invalid data size": {
        "summary": "Invalid data is rejected with an error",
        "value": {
             "query": ["梦想"],
             "size": -1
        },
    },
}

# 响应数据结构
class ResponseModel(BaseModel):
    data: list

class SuccessResponseModel(ResponseModel):
    status: str = "ok"

class ErrorResponseModel(BaseModel):
    status: str = "error"
    msg: str


@app.post("/api/search",
    status_code=200,
    response_model=SuccessResponseModel,
    response_model_exclude_none=True,
    responses={501: {"model": ErrorResponseModel}})
async def search(payload: SearchPayload = Body(
    ..., examples=exmaples
)):
    query = payload.query
    size = payload.size
    # 仅返回指定数量结果
    try:
        ret = full_text_search(query, docs, index)[:size]
    except Exception:
        msg = "unexpected search error"
        logger.exception(msg)
        return JSONResponse(status_code=501, content={"status": "error", "msg": msg})

    data = []
    for doc_index, score in ret:
        value = {}
        doc = docs[doc_index]

        value["doc"] = doc
        
        value["title"] = doc["name"]
        value["key"] = doc["name"]
        value["subTitle"] = doc.get("singer", "")
        value["score"] = score
        data.append(value)
    # logger.debug(data)

    return SuccessResponseModel(data=data)

