import json
import math
from glob import glob
from typing import List, Tuple
from collections import defaultdict
from functools import lru_cache

import jieba

files = glob("ChineseLyrics/*json")

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


def search(keywords: List[str], docs: List[dict], index: dict) -> List[Tuple]:
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



