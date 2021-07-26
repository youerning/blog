import json
from glob import glob
from typing import List

files = glob("ChineseLyrics/*json")

docs = []
for file in files:
    with open(file, encoding="utf8") as rf:
        data = json.load(rf)
        for doc in data:
            # 将歌词的文本列表转换成一个字符串
            doc["lyric2"] = "\n".join(doc["lyric"])
        docs.extend(data)

print(len(docs)) # 102198  

def search(keyword: str, docs: List[dict]) -> List[dict]:
    ret = []

    for index, doc in enumerate(docs):
        lyric = doc["lyric2"]
        # 统计歌词中关键词出现的次数
        count = lyric.count(keyword)
        if count > 1:
            ret.append({
                "doc": doc,
                "index": index,
                "count": count
            })
    return ret

ret = search("梦想", docs)

print(len(ret)) # 2235

# 通过歌词中关键字出现的次数排序
ret2 = sorted(ret, key=lambda x:x["count"], reverse=True)

print(ret2[0])