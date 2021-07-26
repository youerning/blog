import json
from glob import glob
from typing import List
from collections import defaultdict, Counter

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

index = defaultdict(list)
for doc_index, doc in enumerate(docs):
    for word in doc["lyric2"]:
        index[word].append({
            "doc_index": doc_index,
        })


def search(keyword: str, index: dict) -> List[dict]:
    doc_indexs = index.get(keyword)
    if not doc_indexs:
        return []

    return Counter([d["doc_index"] for d in doc_indexs])


ret = search("梦想", index)

print(len(ret)) #4509

print(ret.most_common(10))
# [(70990, 30), (39809, 21), (41760, 20), (87130, 16), (44325, 15), (338, 14), (83351, 14), (93432, 14), (16683, 12), (69966, 12)]


