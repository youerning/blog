from dataclasses import replace
from typing import List, Tuple, Union
import re

import yaml

text = """# 主要维护人
name: zhangsan

# 各集群运维人员
cluster1:
  node1:
    tomcat: user11

cluster2:
  node1:
    tomcat: user21"""

text2 = """# 用户列表
users:
  - user1: wangwu
  - user2: zhangsan

# 集群中间件版本
cluster:
  - name: tomcat
    version: 9.0.63
  - name: nginx
    version: 1.21.6"""


def ignore_comment():
    data = yaml.load(text, Loader=yaml.Loader)
    data["name"] = "wangwu"
    print(yaml.dump(data))

def regex1():
    pattern = "name:\s+\w+"
    pat = re.compile(pattern=pattern)
    # 首先匹配到对应的字符串
    sub_text = pat.findall(text)[0]
    # 根据这个字符串找到在文本的位置
    start_index = text.index(sub_text)
    # 根据起始位置计算结束位置
    end_index = start_index + len(sub_text)
    print(start_index, end_index, text[start_index:end_index])

    # 将根据索引替换内容
    replace_text = "name: wangwu"
    new_text = text[:start_index] + replace_text + text[end_index:]
    print("="*10)
    print(new_text)


def tree1():
    tree = yaml.compose(text)
    print(tree)

def tree2():
    tree = yaml.compose(text)
    key_name_node = tree.value[0][0]
    value_name_node = tree.value[0][1]
    print(key_name_node.start_mark.pointer, value_name_node.end_mark.pointer, key_name_node.value, value_name_node.value)


def find_slice(tree: yaml.MappingNode, keys: List[str]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """
    找到yaml文件中对应键值对的索引, 返回一个((key起始索引, key结束索引+1), (value起始索引, value结束索引+1))的元组
    暂时只支持键值对的寻找.

    比如:
    >>> find_slice("key: value", ["key"])
    ((0, 3), (5, 10))
    >>> find_slice("key1: value2\nkey2:\n  key21: value21\n  key22: value22", ["key2", "key22"])
    ((38, 43), (45, 52))
    """
    if isinstance(tree, str):
        tree = yaml.compose(tree, Loader=yaml.Loader)
    assert isinstance(tree, yaml.MappingNode), "未支持的yaml格式"
    target_key = keys[0]
    for node in tree.value:
        if target_key == node[0].value:
            key_node, value_node = node
            if len(keys) == 1:
                key_pointers = (key_node.start_mark.pointer, key_node.end_mark.pointer)
                value_pointers = (value_node.start_mark.pointer, value_node.end_mark.pointer)
                return (key_pointers, value_pointers)

            return find_slice(node[1], keys[1:])

    return ValueError("没有找到对应的值")


def find_slice2(tree: yaml.MappingNode, keys: List[str]) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """
    找到yaml文件中对应键值对的索引, 返回一个((key起始索引, key结束索引+1), (value起始索引, value结束索引+1))的元组
    暂时只支持键值对的寻找.

    比如:
    >>> find_slice("key: value", ["key"])
    ((0, 3), (5, 10))
    >>> find_slice("key1: value2\nkey2:\n  key21: value21\n  key22: value22", ["key2", "key22"])
    ((38, 43), (45, 52))
    """
    if isinstance(tree, str):
        tree = yaml.compose(tree, Loader=yaml.Loader)
    target_key = keys[0]

    assert isinstance(tree, yaml.MappingNode) or isinstance(tree, yaml.SequenceNode), "未支持的yaml格式"

    ret_key_node = None
    ret_value_node = None
    value_pointers= (-1, -1)

    if isinstance(tree, yaml.SequenceNode):
        assert isinstance(target_key, int), "错误的数据格式"
        # 索引可以是负索引, 比如[1,2,3][-1]
        if len(tree.value) < abs(target_key):
            raise IndexError("索引值大于列表长度")

        node = tree.value[target_key]
        if len(keys) > 1:
            return find_slice2(tree.value[target_key], keys[1:])

        if isinstance(node, yaml.MappingNode):
            ret_key_node, ret_value_node = node.value[0]
        else:
            ret_key_node = node

    if isinstance(tree, yaml.MappingNode):
        for node in tree.value:
            if target_key == node[0].value:
                key_node, value_node = node
                if len(keys) > 1:
                    return find_slice2(node[1], keys[1:])
                ret_key_node = key_node
                ret_value_node = value_node

    if ret_key_node:
        key_pointers = (ret_key_node.start_mark.pointer, ret_key_node.end_mark.pointer)

    if ret_value_node:
        value_pointers = (ret_value_node.start_mark.pointer, ret_value_node.end_mark.pointer)

    if ret_key_node:
        return (key_pointers, value_pointers)

    return ValueError("没有找到对应的值")

def tree3():
    slices = find_slice(text, ["cluster1", "node1", "tomcat"])
    value_start_index, value_end_index = slices[1]
    replace_text = "changed"
    new_text = text[:value_start_index] + replace_text + text[value_end_index:]
    print(new_text)

def tree4():
    slices = find_slice2(text2, ["cluster", 1, "version"])
    value_start_index, value_end_index = slices[1]
    replace_text = "1.22.0"
    new_text = text2[:value_start_index] + replace_text + text2[value_end_index:]
    print(new_text)



def get1():
    data1 = {"message": "success", "data": {"limit": 0, "offset": 10, "total": 100, "data": ["value1", "value1"]}}
    data2 = {"message": "success", "data": None}
    data3 = {"message": "success", "data": {"limit": 0, "offset": 10, "total": 100, "data": None}}

    ret = data1.get("data", {}).get("data", [])
    if ret:
        pass # 做一些操作
    if data2.get("data"):
        ret = data2["data"].get("data", [])
    ret = data3.get("data", {}).get("data", [])


def super_get(data: Union[dict, list], keys: List[Union[str, int]]):
    assert isinstance(data, dict) or isinstance(data, list), "只支持字典和列表类型"
    key = keys[0]

    if isinstance(data, list) and isinstance(key, int):
        try:
            new_data = data[key]
        except IndexError as exc:
            raise IndexError("索引值大于列表长度") from exc
    elif isinstance(data, dict) and isinstance(key, str):
        new_data = data.get(key)
    else:
        raise ValueError(f"数据类型({type(data)})与索引值类型(f{type(key)}不匹配")

    if len(keys) == 1:
        return new_data

    if not isinstance(new_data, dict) and not isinstance(new_data, list):
        raise ValueError("找不到对应的值")
    return super_get(new_data, keys[1:])

def get2():
    data = {"message": "success", "data": {"data": {"zhangsan": {"scores": {"math": {"mid-term": 88, "end-of-term": 90}}}}}}
    print(super_get(data, ["data", "data", "zhangsan", "scores", "math", "mid-term"]))
    # 输出 88
    data = {"message": "success", "data": {"data": {"zhangsan": {"scores": {"math": [88, 90]}}}}}
    print(super_get(data, ["data", "data", "zhangsan", "scores", "math", 0]))
    # 输出 88
    data = {"message": "success", "data": {"data": {"zhangsan": {"scores": {"math": [88, 90]}}}}}
    print(super_get(data, ["data", "data", "zhangsan", "scores", "math", -1]))
    # 输出 90
if __name__ == "__main__":
    ignore_comment()
    regex1()
    tree1()
    tree2()
    tree3()
    tree4()
    get1()
    get2()

